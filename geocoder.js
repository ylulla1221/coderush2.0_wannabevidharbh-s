/**
 * CivicPulse Geocoding Module (Nominatim API wrapper)
 */

const USER_AGENT = 'CivicPulse/1.0 (contact@civicpulse.gov; developer-agent)';

/**
 * Resolves a formatted address from coordinates (Reverse Geocoding)
 * @param {number|string} lat 
 * @param {number|string} lng 
 * @returns {Promise<string>} Formatted address string
 */
async function getAddressFromCoords(lat, lng) {
  const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`;
  
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': USER_AGENT
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.display_name || `Coordinates: ${lat}, ${lng}`;
  } catch (error) {
    console.error('Reverse Geocoding Error:', error);
    throw error;
  }
}

/**
 * Resolves coordinates from an address string (Forward Geocoding)
 * @param {string} address 
 * @returns {Promise<{lat: number, lon: number}>} Coordinates object
 */
async function getCoordsFromAddress(address) {
  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1`;

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': USER_AGENT
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    if (data && data.length > 0) {
      return {
        lat: parseFloat(data[0].lat),
        lon: parseFloat(data[0].lon)
      };
    } else {
      throw new Error('Address not found');
    }
  } catch (error) {
    console.error('Forward Geocoding Error:', error);
    throw error;
  }
}

module.exports = {
  getAddressFromCoords,
  getCoordsFromAddress
};
