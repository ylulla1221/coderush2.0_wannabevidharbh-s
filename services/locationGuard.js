/**
 * services/locationGuard.js
 *
 * Location validation layer for duplicate detection.
 * Intercepts AI duplicate results and confirms they are within a
 * configurable geographic radius before allowing the duplicate flag through.
 *
 * Rules:
 *  1. Semantic similarity must already pass the AI threshold (already done).
 *  2. Category must match (already weighted by AI).
 *  3. Complaints must be within DUPLICATE_RADIUS_METERS of each other.
 *
 * If coordinates are unavailable on either side, falls back to
 * address/locality string comparison.
 */

const Complaint = require('../models/Complaint');

// Maximum distance in metres to still be considered the same location.
const DUPLICATE_RADIUS_METERS = 100;

/**
 * Haversine distance between two lat/lng points in metres.
 */
function haversineMeters(lat1, lng1, lat2, lng2) {
  const R = 6_371_000; // Earth radius in metres
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Lightweight address similarity: true when the two strings share a
 * meaningful locality token (city, landmark, area keyword > 4 chars).
 */
function addressesOverlap(addr1, addr2) {
  if (!addr1 || !addr2) return false;
  const STOP_WORDS = new Set([
    'near', 'road', 'street', 'main', 'gate', 'with', 'from', 'side', 'area',
    'lane', 'cross', 'behind', 'front', 'opposite', 'floor', 'block', 'phase'
  ]);
  const tokenize = (s) =>
    s
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((t) => t.length >= 3 && !STOP_WORDS.has(t));
  const tokens1 = new Set(tokenize(addr1));
  return tokenize(addr2).some((t) => tokens1.has(t));
}

/**
 * Validate whether an AI duplicate result is geographically consistent
 * with the incoming complaint's location.
 *
 * @param {object} duplicateResult  - analysis.duplicate from the AI pipeline
 * @param {number|null} incomingLat - resolved latitude of the new complaint
 * @param {number|null} incomingLng - resolved longitude of the new complaint
 * @param {string|null} incomingAddress - address string of the new complaint
 * @param {string} incomingCategory - category of the new complaint
 *
 * @returns {Promise<{
 *   allowed: boolean,
 *   reason: string,
 *   matchedComplaint: object|null
 * }>}
 */
async function validateDuplicateLocation(
  duplicateResult,
  incomingLat,
  incomingLng,
  incomingAddress,
  incomingCategory
) {
  if (!duplicateResult || !duplicateResult.is_duplicate) {
    return { allowed: false, reason: 'Not flagged as duplicate by AI', matchedComplaint: null };
  }

  // ── Step 1: Find the matched complaint in MongoDB ─────────────────────────
  // The AI's matched_complaint_id is an internal Qdrant ID (cmp_XXXXXXXX).
  // We find the best MongoDB candidate by category + proximity query.
  let matchedComplaint = null;

  try {
    const hasCoords =
      incomingLat != null &&
      incomingLng != null &&
      !isNaN(incomingLat) &&
      !isNaN(incomingLng);

    if (hasCoords) {
      // Use MongoDB $nearSphere to find the nearest same-category complaint
      // within a generous 50 km radius (the AI threshold does the tighter cut).
      const SEARCH_RADIUS_METERS = 50_000;
      matchedComplaint = await Complaint.findOne({
        category: { $regex: new RegExp(incomingCategory.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') },
        location: {
          $nearSphere: {
            $geometry: { type: 'Point', coordinates: [incomingLng, incomingLat] },
            $maxDistance: SEARCH_RADIUS_METERS,
          },
        },
      }).lean();
    }

    if (!matchedComplaint && incomingAddress) {
      // Fallback: find any complaint with the same category and overlapping address tokens
      const sameCatComplaints = await Complaint.find({
        category: { $regex: new RegExp(incomingCategory.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') },
      })
        .select('address location category')
        .lean();

      matchedComplaint =
        sameCatComplaints.find((c) => addressesOverlap(c.address, incomingAddress)) || null;
    }
  } catch (err) {
    // If the lookup itself fails (e.g. no 2dsphere index yet), be conservative
    // and allow the AI duplicate flag through unchanged.
    console.warn('[locationGuard] MongoDB lookup failed, passing AI result through:', err.message);
    return { allowed: true, reason: 'Location lookup unavailable — AI result accepted', matchedComplaint: null };
  }

  if (!matchedComplaint) {
    // No complaint of the same category found within 50 km, and no address token match.
    // The AI flagged a duplicate but we cannot verify geographic proximity — reject it.
    console.warn('[locationGuard] No nearby complaint found in MongoDB — treating as different location for category:', incomingCategory);
    return {
      allowed: false,
      reason: 'Similar complaint but different location (no matching complaint within search radius)',
      matchedComplaint: null,
    };
  }

  // ── Step 2: Compare coordinates ───────────────────────────────────────────
  const matchCoords = matchedComplaint.location && matchedComplaint.location.coordinates;
  const matchLng = matchCoords && matchCoords[0];
  const matchLat = matchCoords && matchCoords[1];

  const hasIncoming = incomingLat != null && incomingLng != null && !isNaN(incomingLat) && !isNaN(incomingLng);
  const hasMatched  = matchLat   != null && matchLng   != null && !isNaN(matchLat)  && !isNaN(matchLng);

  if (hasIncoming && hasMatched) {
    const distanceM = haversineMeters(incomingLat, incomingLng, matchLat, matchLng);
    console.log(`[locationGuard] Distance to matched complaint: ${distanceM.toFixed(1)} m (limit: ${DUPLICATE_RADIUS_METERS} m)`);

    if (distanceM > DUPLICATE_RADIUS_METERS) {
      return {
        allowed: false,
        reason: `Similar complaint but different location (${distanceM.toFixed(0)} m apart — threshold: ${DUPLICATE_RADIUS_METERS} m)`,
        matchedComplaint,
      };
    }

    return {
      allowed: true,
      reason: `Within ${DUPLICATE_RADIUS_METERS} m radius (${distanceM.toFixed(0)} m)`,
      matchedComplaint,
    };
  }

  // ── Step 3: Coordinate fallback — address text comparison ─────────────────
  const matched = addressesOverlap(incomingAddress, matchedComplaint.address);
  console.log(`[locationGuard] Address overlap check: ${matched} ("${incomingAddress}" vs "${matchedComplaint.address}")`);

  if (!matched) {
    return {
      allowed: false,
      reason: 'Similar complaint but different location (address mismatch)',
      matchedComplaint,
    };
  }

  return {
    allowed: true,
    reason: 'Address locality matches',
    matchedComplaint,
  };
}

module.exports = { validateDuplicateLocation, DUPLICATE_RADIUS_METERS };
