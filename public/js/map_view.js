// CivicPulse Map View Grid Module

const MapViewTab = {
  maps: [],
  markerGroups: [],
  currentCategory: 'All',
  isSplitGrid: true,

  async init() {
    console.log('Initializing Map View Grid...');
    await this.fetchData();
    this.initMaps();
  },

  async fetchData() {
    try {
      window.appState.cachedComplaints = await window.API.getComplaints();
    } catch (e) {
      window.showToast('Failed to sync map complaints.', 'error');
    }
  },

  initMaps() {
    // Clear existing maps if any
    this.maps.forEach(m => m.remove());
    this.maps = [];
    this.markerGroups = [];

    // Define 6 sectors and coordinates
    const sectors = [
      { id: 'grid-map-1', name: 'Downtown Sector', center: [41.8781, -87.6298], zoom: 14 },
      { id: 'grid-map-2', name: 'Westside Subsector', center: [41.8756, -87.6244], zoom: 14 },
      { id: 'grid-map-3', name: 'North Hills Sector', center: [41.8835, -87.6321], zoom: 14 },
      { id: 'grid-map-4', name: 'South End Sector', center: [41.8818, -87.6278], zoom: 14 },
      { id: 'grid-map-5', name: 'Ward 12 Central', center: [41.8850, -87.6350], zoom: 14 },
      { id: 'grid-map-6', name: 'Industrial Corridor', center: [41.8795, -87.6255], zoom: 14 }
    ];

    sectors.forEach((sec, idx) => {
      const container = document.getElementById(sec.id);
      if (!container) return;

      // In full-screen single-map mode, hide all except the first map
      if (!this.isSplitGrid && idx > 0) {
        container.parentElement.classList.add('hidden');
        return;
      } else {
        container.parentElement.classList.remove('hidden');
      }

      const mapInstance = L.map(sec.id, {
        zoomControl: true,
        attributionControl: false
      }).setView(sec.center, sec.zoom);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(mapInstance);

      const mGroup = L.layerGroup().addTo(mapInstance);
      
      this.maps.push(mapInstance);
      this.markerGroups.push(mGroup);
    });

    this.renderMarkers();
  },

  renderMarkers() {
    // Clear all previous markers
    this.markerGroups.forEach(g => g.clearLayers());

    // Filter complaints by category
    let complaints = window.appState.cachedComplaints.filter(c => c.status !== 'Resolved' && c.lat && c.lng);
    if (this.currentCategory !== 'All') {
      if (this.currentCategory === 'Infrastructure') {
        complaints = complaints.filter(c => c.category.includes('Road') || c.category.includes('Supply') || c.category.includes('Streetlight'));
      } else if (this.currentCategory === 'Sanitation') {
        complaints = complaints.filter(c => c.category.includes('Dumping') || c.category.includes('Waste') || c.category.includes('Graffiti'));
      }
    }

    // Add markers to all active maps in the grid
    complaints.forEach(c => {
      let color = '#3b82f6';
      if (c.priority === 'Urgent') color = '#ef4444';
      else if (c.priority === 'Low') color = '#10b981';

      // Custom marker icon using HTML/CSS
      const customIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div class="w-5 h-5 rounded-full bg-white border-2 border-[${color}] flex items-center justify-center shadow-md">
                 <span class="w-2.5 h-2.5 rounded-full bg-[${color}]"></span>
               </div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      });

      this.markerGroups.forEach((g, mapIdx) => {
        // Calculate distance from map center to prevent mapping markers that are miles away from the sector
        const mapCenter = this.maps[mapIdx].getCenter();
        const markerLatLng = L.latLng(c.lat, c.lng);
        const distance = mapCenter.distanceTo(markerLatLng);

        // Show marker if it's within 1.5km of map center, or show all if in full screen single map mode
        if (distance < 1500 || !this.isSplitGrid) {
          L.marker([c.lat, c.lng], { icon: customIcon })
            .addTo(g)
            .bindPopup(`
              <div class="text-xs space-y-1">
                <span class="font-bold text-primary uppercase block">${c.id}</span>
                <span class="text-on-surface-variant font-medium">${c.category}</span>
                <p class="text-on-surface line-clamp-2">${c.description}</p>
                <button onclick="OverviewTab.inspectDetails('${c.id}')" class="text-[10px] text-secondary font-bold hover:underline block mt-1">Inspect Details</button>
              </div>
            `);
        }
      });
    });
  },

  filterCategory(cat) {
    this.currentCategory = cat;

    // Toggle button style classes
    ['All', 'Infrastructure', 'Sanitation'].forEach(c => {
      const btn = document.getElementById(`btn-map-cat-${c}`);
      if (btn) {
        if (c === cat) {
          btn.className = "px-3 py-1.5 bg-white text-primary rounded-md shadow-sm border border-outline-variant/10";
        } else {
          btn.className = "px-3 py-1.5 text-on-surface-variant hover:text-primary";
        }
      }
    });

    this.renderMarkers();
  },

  toggleLayout() {
    this.isSplitGrid = !this.isSplitGrid;
    const gridContainer = document.getElementById('map-grid-container');
    
    if (this.isSplitGrid) {
      gridContainer.className = "flex-grow grid grid-cols-1 md:grid-cols-3 gap-4";
    } else {
      // Single Map takes full viewport width/height
      gridContainer.className = "flex-grow grid grid-cols-1 gap-0";
    }

    this.initMaps();
  }
};

// Bind functions
function filterMapCategories(cat) {
  MapViewTab.filterCategory(cat);
}

function toggleMapLayout() {
  MapViewTab.toggleLayout();
}

window.MapViewTab = MapViewTab;
window.filterMapCategories = filterMapCategories;
window.toggleMapLayout = toggleMapLayout;
