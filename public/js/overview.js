// CivicPulse Overview & Needs Review Queue Module

const OverviewTab = {
  miniMap: null,
  markersGroup: null,

  async init() {
    console.log('Initializing Overview Tab...');
    await this.fetchData();
    this.renderStats();
    this.renderComplaints();
    this.initMiniMap();
  },

  async fetchData() {
    try {
      window.appState.cachedComplaints = await window.API.getComplaints();
      window.appState.cachedStats = await window.API.getStats();
    } catch (err) {
      window.showToast('Failed to load dashboard data from SQLite.', 'error');
    }
  },

  renderStats() {
    const stats = window.appState.cachedStats;
    if (!stats) return;

    document.getElementById('stat-total-active').textContent = stats.totalActive || 0;
    document.getElementById('stat-urgent-queue').textContent = stats.urgentQueue || 0;
    
    // Officer Availability: calculated based on unassigned vs assigned ratio, or direct value
    const availability = stats.totalCrews > 0 
      ? Math.round(((stats.totalCrews - stats.activeCrews) / stats.totalCrews) * 100) 
      : 82;
    document.getElementById('stat-availability').textContent = `${availability}%`;

    // Resource simulation progress bars update
    const patrolFill = document.getElementById('bar-fill-patrol');
    const patrolLabel = document.getElementById('bar-label-patrol');
    const maintenanceFill = document.getElementById('bar-fill-maintenance');
    const maintenanceLabel = document.getElementById('bar-label-maintenance');

    // Make simulation look dynamic depending on active complaints density
    if (stats.urgentQueue > 3) {
      patrolFill.style.width = '90%';
      patrolFill.className = 'bg-error h-2 rounded-full';
      patrolLabel.textContent = 'High Need';
      patrolLabel.className = 'text-error';
    } else {
      patrolFill.style.width = '45%';
      patrolFill.className = 'bg-amber-500 h-2 rounded-full';
      patrolLabel.textContent = 'Moderate';
      patrolLabel.className = 'text-amber-500';
    }

    const activeRoadIssues = window.appState.cachedComplaints.filter(c => c.category.includes('Road') && c.status !== 'Resolved').length;
    if (activeRoadIssues > 2) {
      maintenanceFill.style.width = '75%';
      maintenanceFill.className = 'bg-amber-500 h-2 rounded-full';
      maintenanceLabel.textContent = 'Moderate';
      maintenanceLabel.className = 'text-amber-500';
    } else {
      maintenanceFill.style.width = '25%';
      maintenanceFill.className = 'bg-emerald-600 h-2 rounded-full';
      maintenanceLabel.textContent = 'Low Need';
      maintenanceLabel.className = 'text-emerald-600';
    }
  },

  renderComplaints() {
    const container = document.getElementById('incoming-complaints-list');
    const complaints = window.appState.cachedComplaints.filter(c => c.status !== 'Resolved');

    if (complaints.length === 0) {
      container.innerHTML = `
        <div class="p-8 text-center text-on-surface-variant italic">
          No complaints awaiting review. All clear!
        </div>
      `;
      return;
    }

    container.innerHTML = complaints.slice(0, 4).map(c => {
      let priorityClass = '';
      if (c.priority === 'Urgent') {
        priorityClass = 'bg-red-100 text-red-800';
      } else if (c.priority === 'Moderate') {
        priorityClass = 'bg-amber-100 text-amber-800';
      } else {
        priorityClass = 'bg-emerald-100 text-emerald-800';
      }

      // Calculate simple relative time
      const dateStr = c.date || '2026-08-07';
      const fileDate = new Date(dateStr);
      const diffTime = Math.abs(new Date() - fileDate);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      const relativeTime = diffDays <= 1 ? '12m ago' : `${diffDays} days ago`;

      return `
        <div class="p-4 bg-surface-container-low rounded-xl border border-outline-variant hover:border-secondary transition-all flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="space-y-1.5 flex-grow">
            <div class="flex items-center gap-2 text-[10px]">
              <span class="font-bold px-2 py-0.5 rounded-full uppercase ${priorityClass}">${c.priority}</span>
              <span class="font-mono text-outline font-semibold uppercase">${c.id}</span>
              <span class="text-outline">•</span>
              <span class="text-on-surface-variant font-medium">${relativeTime}</span>
            </div>
            <h4 class="font-sans font-bold text-sm text-primary leading-tight">${c.category} - ${c.address}</h4>
            <p class="text-xs text-on-surface-variant line-clamp-2 max-w-xl">${c.description}</p>
          </div>
          <div class="flex items-center gap-2">
            <button onclick="OverviewTab.inspectDetails('${c.id}')" class="border border-outline-variant bg-white hover:bg-surface-container text-primary text-xs font-semibold px-3 py-1.5 rounded-lg transition-all active:scale-95">
              Details
            </button>
            <button onclick="OverviewTab.assignCrewDirectly('${c.id}')" class="bg-secondary hover:bg-[#00524b] text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-all active:scale-95">
              Assign
            </button>
          </div>
        </div>
      `;
    }).join('');
  },

  initMiniMap() {
    const mapContainer = document.getElementById('overview-mini-map');
    if (!mapContainer) return;

    // Reset if map already initialized
    if (this.miniMap) {
      this.miniMap.remove();
      this.miniMap = null;
    }

    // Default coordinates (Chicago main road)
    const lat = 41.8795;
    const lng = -87.6255;

    this.miniMap = L.map('overview-mini-map', {
      zoomControl: false,
      attributionControl: false
    }).setView([lat, lng], 13);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19
    }).addTo(this.miniMap);

    this.markersGroup = L.layerGroup().addTo(this.miniMap);

    // Plot active complaints on the map
    const activeComplaints = window.appState.cachedComplaints.filter(c => c.status !== 'Resolved' && c.lat && c.lng);
    activeComplaints.forEach(c => {
      let color = '#3b82f6'; // default moderate blue
      if (c.priority === 'Urgent') color = '#ef4444'; // urgent red
      else if (c.priority === 'Low') color = '#10b981'; // low emerald

      L.circleMarker([c.lat, c.lng], {
        radius: 6,
        fillColor: color,
        color: '#ffffff',
        weight: 1.5,
        fillOpacity: 0.95
      }).addTo(this.markersGroup).bindPopup(`<b>${c.id}</b><br/>${c.category}`);
    });
  },

  // Modal Dialog actions
  inspectDetails(id) {
    const c = window.appState.cachedComplaints.find(x => x.id === id);
    if (!c) return;

    // Populate details modal
    document.getElementById('details-ticket-id').textContent = c.id;
    document.getElementById('details-title-category').textContent = c.category;
    document.getElementById('details-description').textContent = c.description;
    
    const reporter = document.getElementById('details-reporter');
    reporter.innerHTML = `${c.reporterName || 'Anonymous'}<br/>${c.reporterContact || 'No contact'}`;
    // Re-apply privacy masking to reporter info
    window.applyPrivacyMaskingUI();

    document.getElementById('details-date').textContent = c.date;
    document.getElementById('details-address').textContent = c.address;
    document.getElementById('details-coords').textContent = `Coords: ${c.lat ? c.lat.toFixed(4) : 'N/A'}, ${c.lng ? c.lng.toFixed(4) : 'N/A'}`;
    document.getElementById('details-confidence').textContent = `Confidence: ${c.locationConfidence || 0.85}`;

    // Select current status & crew values
    document.getElementById('details-status-select').value = c.status;
    document.getElementById('details-crew-select').value = c.assignedOfficer || '';

    // Bind current details modal focus ID
    window.appState.activeDetailId = c.id;

    // SLA display warning
    const slaBox = document.getElementById('details-sla-box');
    if (c.slaBreached && c.status !== 'Resolved') {
      slaBox.classList.remove('hidden');
      slaBox.classList.add('flex');
    } else {
      slaBox.classList.add('hidden');
      slaBox.classList.remove('flex');
    }

    // Show details modal
    document.getElementById('details-modal').classList.remove('hidden');
  },

  assignCrewDirectly(id) {
    this.inspectDetails(id);
    // Direct focus to the select dropdown for quick action
    setTimeout(() => {
      document.getElementById('details-crew-select').focus();
    }, 100);
  }
};

// Modal Actions bindings
async function onDetailsStatusChange() {
  const id = window.appState.activeDetailId;
  const status = document.getElementById('details-status-select').value;
  if (!id) return;

  try {
    await window.API.updateComplaintStatus(id, {
      status,
      auditAction: 'STATUS_UPDATED',
      auditDetails: `Status manually updated to ${status} via details editor.`,
      performedBy: window.appState.currentUser.name
    });
    window.showToast(`Updated status of #${id} to ${status}`);
    
    // Refresh feed
    await OverviewTab.init();
  } catch (err) {
    window.showToast('Failed to update status in SQLite.', 'error');
  }
}

async function onDetailsCrewChange() {
  const id = window.appState.activeDetailId;
  const crew = document.getElementById('details-crew-select').value;
  if (!id) return;

  const status = crew ? 'Assigned' : 'Submitted';

  try {
    await window.API.updateComplaintStatus(id, {
      status,
      assignedOfficer: crew,
      auditAction: 'CREW_ASSIGNED',
      auditDetails: crew ? `Assigned to field repair unit: ${crew}` : 'De-allocated crew / Set back to Submitted queue.',
      performedBy: window.appState.currentUser.name
    });
    
    document.getElementById('details-status-select').value = status;
    window.showToast(crew ? `Assigned #${id} to ${crew}` : `Cleared crew assignment of #${id}`);
    
    // Refresh feed
    await OverviewTab.init();
  } catch (err) {
    window.showToast('Failed to update crew assignment in SQLite.', 'error');
  }
}

async function triggerSLAOverride() {
  const id = window.appState.activeDetailId;
  if (!id) return;

  try {
    await window.API.overrideSLA(id);
    window.showToast(`Manual override executed. Priority locked to URGENT. SLA reset.`);
    
    // Close modal
    closeDetailsModal();
    // Refresh feed
    await OverviewTab.init();
  } catch (err) {
    window.showToast('Failed to execute SLA override.', 'error');
  }
}

function closeDetailsModal() {
  document.getElementById('details-modal').classList.add('hidden');
  window.appState.activeDetailId = null;
}

// Bind to window
window.OverviewTab = OverviewTab;
window.onDetailsStatusChange = onDetailsStatusChange;
window.onDetailsCrewChange = onDetailsCrewChange;
window.triggerSLAOverride = triggerSLAOverride;
window.closeDetailsModal = closeDetailsModal;
