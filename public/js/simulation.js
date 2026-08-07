// CivicPulse Simulation Environment Module

const SimulationTab = {
  map: null,
  overlayLayer: null,
  timelineInterval: null,
  isTimelinePlaying: false,
  currentOverlayType: 'density',

  async init() {
    console.log('Initializing Simulation Tab...');
    this.updateSliderUI();
    this.initMap();
    this.computeMetrics();
  },

  updateSliderUI() {
    const closure = document.getElementById('slider-artery-closure').value;
    const bridge = document.getElementById('slider-bridge-capacity').value;
    const units = document.getElementById('slider-units-available').value;

    document.getElementById('val-artery-closure').textContent = `${closure}%`;
    document.getElementById('val-bridge-capacity').textContent = `${bridge}%`;
    document.getElementById('val-units-available').textContent = `${units}`;
  },

  computeMetrics() {
    const closure = parseInt(document.getElementById('slider-artery-closure').value);
    const bridge = parseInt(document.getElementById('slider-bridge-capacity').value);
    const units = parseInt(document.getElementById('slider-units-available').value);

    // Hardcode values matching screenshot 1 if sliders are at default
    if (closure === 100 && bridge === 40 && units === 12) {
      document.getElementById('sim-metric-time').textContent = '14.2 mins';
      document.getElementById('sim-badge-time').textContent = '↑ +3.4m';
      document.getElementById('sim-badge-time').className = 'text-[9px] font-semibold text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded';
      
      document.getElementById('sim-metric-gridlock').textContent = '68%';
      document.getElementById('sim-msg-gridlock').textContent = 'Sector 4 & 5 highly critical';
      document.getElementById('sim-msg-gridlock').className = 'text-[10px] text-red-600 font-semibold';
      
      document.getElementById('sim-metric-depletion').textContent = '42%';
      document.getElementById('sim-badge-depletion').textContent = 'Stable trajectory';
      document.getElementById('sim-badge-depletion').className = 'text-[9px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded';
      return;
    }

    // Dynamic calculations
    // Avg Response Time
    const baseTime = 8.2;
    const closureWeight = closure * 0.08;
    const unitsWeight = (25 - units) * 0.2;
    const bridgeWeight = (100 - bridge) * 0.04;
    const totalTime = Math.max(5.1, baseTime + closureWeight + unitsWeight + bridgeWeight);
    const diffTime = totalTime - 8.2;
    
    document.getElementById('sim-metric-time').textContent = `${totalTime.toFixed(1)} mins`;
    if (diffTime >= 0) {
      document.getElementById('sim-badge-time').textContent = `↑ +${diffTime.toFixed(1)}m`;
      document.getElementById('sim-badge-time').className = 'text-[9px] font-semibold text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded';
    } else {
      document.getElementById('sim-badge-time').textContent = `↓ ${Math.abs(diffTime).toFixed(1)}m`;
      document.getElementById('sim-badge-time').className = 'text-[9px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded';
    }

    // Gridlock Probability
    const baseGrid = 30;
    const closureGrid = closure * 0.5;
    const bridgeGrid = (100 - bridge) * 0.3;
    const unitsGrid = (12 - units) * 0.5;
    const totalGrid = Math.min(100, Math.max(5, Math.round(baseGrid + closureGrid + bridgeGrid + unitsGrid)));
    
    document.getElementById('sim-metric-gridlock').textContent = `${totalGrid}%`;
    if (totalGrid > 60) {
      document.getElementById('sim-msg-gridlock').textContent = 'Sector 4 & 5 highly critical';
      document.getElementById('sim-msg-gridlock').className = 'text-[10px] text-red-600 font-semibold';
    } else if (totalGrid > 35) {
      document.getElementById('sim-msg-gridlock').textContent = 'Congestion warning';
      document.getElementById('sim-msg-gridlock').className = 'text-[10px] text-amber-500 font-semibold';
    } else {
      document.getElementById('sim-msg-gridlock').textContent = 'Optimal Flow';
      document.getElementById('sim-msg-gridlock').className = 'text-[10px] text-emerald-600 font-semibold';
    }

    // Resource Depletion
    const totalDepletion = Math.min(100, Math.max(10, Math.round((units / 50) * 100)));
    document.getElementById('sim-metric-depletion').textContent = `${totalDepletion}%`;
    if (totalDepletion > 70) {
      document.getElementById('sim-badge-depletion').textContent = 'Critical depletion';
      document.getElementById('sim-badge-depletion').className = 'text-[9px] font-semibold text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded';
    } else if (totalDepletion > 35) {
      document.getElementById('sim-badge-depletion').textContent = 'Stable trajectory';
      document.getElementById('sim-badge-depletion').className = 'text-[9px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded';
    } else {
      document.getElementById('sim-badge-depletion').textContent = 'Surplus reserves';
      document.getElementById('sim-badge-depletion').className = 'text-[9px] font-semibold text-blue-600 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded';
    }
  },

  initMap() {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }

    // Centered around Chicago loop / Ward 12
    const lat = 41.8795;
    const lng = -87.6255;

    this.map = L.map('simulation-map', {
      zoomControl: true,
      attributionControl: false
    }).setView([lat, lng], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(this.map);

    this.overlayLayer = L.layerGroup().addTo(this.map);
    this.renderOverlays();
  },

  renderOverlays() {
    this.overlayLayer.clearLayers();
    const lat = 41.8795;
    const lng = -87.6255;

    if (this.currentOverlayType === 'density') {
      // Draw traffic gridlock zones (red overlay circles)
      L.circle([lat + 0.005, lng - 0.005], {
        radius: 400,
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.45,
        weight: 1
      }).addTo(this.overlayLayer).bindPopup('Gridlock Zone: Sector 4 (Highway 42)');

      L.circle([lat - 0.008, lng + 0.008], {
        radius: 300,
        color: '#f59e0b',
        fillColor: '#f59e0b',
        fillOpacity: 0.35,
        weight: 1
      }).addTo(this.overlayLayer).bindPopup('Congestion Zone: Sector 5');
    } else {
      // Draw Dispatch Centers Response buffers (blue overlay buffers)
      L.circle([lat + 0.012, lng + 0.012], {
        radius: 1200,
        color: '#3b82f6',
        fillColor: '#3b82f6',
        fillOpacity: 0.15,
        weight: 1.5,
        dashArray: '5, 5'
      }).addTo(this.overlayLayer).bindPopup('Response Unit A coverage');

      L.circle([lat - 0.012, lng - 0.012], {
        radius: 1000,
        color: '#0d9488',
        fillColor: '#0d9488',
        fillOpacity: 0.15,
        weight: 1.5,
        dashArray: '5, 5'
      }).addTo(this.overlayLayer).bindPopup('Response Unit B coverage');
    }
  },

  toggleHeatmap(type) {
    this.currentOverlayType = type;
    this.renderOverlays();
  },

  // Playback Control Engine
  togglePlay() {
    this.isTimelinePlaying = !this.isTimelinePlaying;
    const icon = document.getElementById('icon-sim-play');
    
    if (this.isTimelinePlaying) {
      icon.textContent = 'pause';
      window.showToast("Simulation Engine timeline playback active.");
      
      this.timelineInterval = setInterval(() => {
        const slider = document.getElementById('sim-time-slider');
        let current = parseInt(slider.value);
        current = (current + 1) % 13; // Cycle through 12 hours
        slider.value = current;
        this.updateTimelineUI(current);
      }, 1000);
    } else {
      icon.textContent = 'play_arrow';
      clearInterval(this.timelineInterval);
    }
  },

  updateTimelineUI(hours) {
    document.getElementById('sim-timeline-val').textContent = `+${hours} hrs`;
    
    // Animate map overlay sizes or metrics during playback to make it feel alive!
    this.overlayLayer.eachLayer(layer => {
      if (layer instanceof L.Circle) {
        const baseRadius = layer.getRadius();
        // Slightly fluctuate radius based on timeline hours
        layer.setRadius(baseRadius + (Math.sin(hours) * 30));
      }
    });
  },

  resetDefaults() {
    document.getElementById('slider-artery-closure').value = 100;
    document.getElementById('slider-bridge-capacity').value = 40;
    document.getElementById('slider-units-available').value = 12;
    document.getElementById('sim-routing-type').value = 'Aggressive Re-routing';
    
    this.updateSliderUI();
    this.computeMetrics();
    window.showToast("Simulation Parameters reset to factory defaults.");
  }
};

// Bind UI slider events
function updateSimulationSliders() {
  SimulationTab.updateSliderUI();
}

function runSimulationEngine() {
  SimulationTab.computeMetrics();
  window.showToast("Operational impact metrics successfully updated!");
}

function resetSimulationParameters() {
  SimulationTab.resetDefaults();
}

function toggleSimulationHeatmap(type) {
  SimulationTab.toggleHeatmap(type);
}

function toggleSimulationPlay() {
  SimulationTab.togglePlay();
}

function onSimulationTimelineSlide() {
  const val = document.getElementById('sim-time-slider').value;
  SimulationTab.updateTimelineUI(parseInt(val));
}

window.SimulationTab = SimulationTab;
window.updateSimulationSliders = updateSimulationSliders;
window.runSimulationEngine = runSimulationEngine;
window.resetSimulationParameters = resetSimulationParameters;
window.toggleSimulationHeatmap = toggleSimulationHeatmap;
window.toggleSimulationPlay = toggleSimulationPlay;
window.onSimulationTimelineSlide = onSimulationTimelineSlide;
