// CivicPulse Analytics & Reports Module

const ReportsTab = {
  trendsChart: null,
  slaMap: null,
  markersGroup: null,

  async init() {
    console.log('Initializing Reports Tab...');
    await this.fetchData();
    this.renderStats();
    this.initChart();
    this.initSLAMap();
    this.renderNeighborhoodCharts();
    this.renderTopNeighborhoods();
  },

  async fetchData() {
    try {
      window.appState.cachedComplaints = await window.API.getComplaints();
      window.appState.cachedStats = await window.API.getStats();
    } catch (e) {
      window.showToast('Failed to sync analytics.', 'error');
    }
  },

  renderStats() {
    const stats = window.appState.cachedStats;
    if (!stats) return;

    // Direct binding from sqlite db calculated statistics
    document.getElementById('rep-stat-total').textContent = stats.totalComplaints.toLocaleString() || '1,284';
    document.getElementById('rep-stat-compliance').textContent = `${stats.slaCompliance}%`;
    document.getElementById('rep-stat-critical').textContent = stats.urgentQueue || 0;
  },

  initChart() {
    const ctx = document.getElementById('resolutionTrendsChart');
    if (!ctx) return;

    // Reset chart instance if exists
    if (this.trendsChart) {
      this.trendsChart.destroy();
    }

    // Generate real data from cached complaints
    const complaints = window.appState.cachedComplaints || [];
    const categoryCounts = {};
    complaints.forEach(c => {
      categoryCounts[c.category] = (categoryCounts[c.category] || 0) + 1;
    });

    const labels = Object.keys(categoryCounts).slice(0, 7);
    const data = labels.map(l => categoryCounts[l]);

    // Chart.js configuration styled according to DESIGN.md
    this.trendsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Total Complaints',
          data: data,
          backgroundColor: '#006a61', // Secondary teal
          borderRadius: 4,
          maxBarThickness: 40
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: '#eae7e9'
            },
            ticks: {
              color: '#75777d',
              font: {
                family: 'Inter',
                size: 10
              }
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#75777d',
              font: {
                family: 'Inter',
                size: 10
              }
            }
          }
        }
      }
    });
  },

  initSLAMap() {
    const mapContainer = document.getElementById('reports-sla-map');
    if (!mapContainer) return;

    if (this.slaMap) {
      this.slaMap.remove();
      this.slaMap = null;
    }

    const lat = 21.1458;
    const lng = 79.0882;

    this.slaMap = L.map('reports-sla-map', {
      zoomControl: true,
      attributionControl: false
    }).setView([lat, lng], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(this.slaMap);

    this.markersGroup = L.layerGroup().addTo(this.slaMap);

    // Plot only SLA breached / Overdue complaints
    const overdueComplaints = window.appState.cachedComplaints.filter(c => 
      c.sla?.status === 'BREACHED' && c.status !== 'RESOLVED' && c.lifecycleStatus !== 'RESOLVED' && (c.latitude || c.lat) && (c.longitude || c.lng)
    );
    
    overdueComplaints.forEach(c => {
      const cLat = c.latitude || c.lat;
      const cLng = c.longitude || c.lng;
      L.circleMarker([cLat, cLng], {
        radius: 8,
        fillColor: '#ba1a1a',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 0.85
      }).addTo(this.markersGroup).bindPopup(`
        <div class="text-xs space-y-1 text-red-950">
          <strong class="block text-error">⚠️ SLA BREACHED</strong>
          <b>Ref No:</b> ${c.referenceNumber || c.id}<br/>
          <b>Category:</b> ${c.category}<br/>
          <b>Assigned To:</b> ${c.assignedDepartment || 'Unassigned'}<br/>
          <b>Address:</b> ${c.address}
        </div>
      `);
    });
  },

  renderNeighborhoodCharts() {
    const complaints = window.appState.cachedComplaints || [];
    
    // Ward Distribution
    const ctxWard = document.getElementById('reportsWardChart');
    if (ctxWard) {
      if (this.wardChart) this.wardChart.destroy();
      const counts = {};
      complaints.forEach(c => {
        const ward = c.ward || 'Unknown';
        counts[ward] = (counts[ward] || 0) + 1;
      });
      this.wardChart = new Chart(ctxWard, {
        type: 'doughnut',
        data: {
          labels: Object.keys(counts),
          datasets: [{ data: Object.values(counts), backgroundColor: ['#006a61', '#89f5e7', '#004f48', '#aec6ff', '#4ade80'] }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
      });
    }

    // Category Distribution
    const ctxCat = document.getElementById('reportsCategoryChart');
    if (ctxCat) {
      if (this.catChart) this.catChart.destroy();
      const counts = {};
      complaints.forEach(c => {
        counts[c.category] = (counts[c.category] || 0) + 1;
      });
      this.catChart = new Chart(ctxCat, {
        type: 'doughnut',
        data: {
          labels: Object.keys(counts),
          datasets: [{ data: Object.values(counts), backgroundColor: ['#ba1a1a', '#ff897d', '#93000a', '#ffb4ab', '#f43f5e'] }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
      });
    }

    // Department Distribution
    const ctxDept = document.getElementById('reportsDepartmentChart');
    if (ctxDept) {
      if (this.deptChart) this.deptChart.destroy();
      const counts = {};
      complaints.forEach(c => {
        const dept = c.assignedDepartment || 'Unassigned';
        counts[dept] = (counts[dept] || 0) + 1;
      });
      this.deptChart = new Chart(ctxDept, {
        type: 'doughnut',
        data: {
          labels: Object.keys(counts),
          datasets: [{ data: Object.values(counts), backgroundColor: ['#001334', '#4b5563', '#aec6ff', '#e0e7ff', '#64748b'] }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
      });
    }
  },

  renderTopNeighborhoods() {
    const container = document.getElementById('reports-neighborhoods-list');
    if (!container) return;

    const complaints = window.appState.cachedComplaints || [];
    // Aggregate by landmark or first part of address
    const areaCounts = {};
    complaints.forEach(c => {
      const area = c.landmark || (c.address ? c.address.split(',')[0].trim() : null) || 'Unknown';
      areaCounts[area] = (areaCounts[area] || 0) + 1;
    });

    const sorted = Object.entries(areaCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    if (sorted.length === 0) {
      container.innerHTML = '<p class="text-outline text-[10px] italic">No data available.</p>';
      return;
    }

    const max = sorted[0][1] || 1;
    container.innerHTML = sorted.map(([area, count]) => {
      const pct = Math.round((count / max) * 100);
      return `<div>
        <div class="flex justify-between mb-1 font-semibold text-primary">
          <span class="truncate max-w-[150px]" title="${area}">${area}</span>
          <span class="font-mono font-bold text-primary">${count}</span>
        </div>
        <div class="w-full bg-surface-container rounded-full h-1.5">
          <div class="bg-secondary h-1.5 rounded-full" style="width:${pct}%"></div>
        </div>
      </div>`;
    }).join('');
  }
};

window.ReportsTab = ReportsTab;
