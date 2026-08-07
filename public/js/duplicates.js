// CivicPulse Deduplication & Clustering Module

const DuplicatesTab = {
  async init() {
    console.log('Initializing Duplicates Tab...');
    this.renderClusters();
  },

  renderClusters() {
    const container = document.getElementById('duplicates-cluster-list');
    
    // Find active complaints related to clusters or simulate
    const c = window.appState.cachedComplaints.find(x => x.id === 'INC-2026-0412');
    const count = c ? (c.reportCount || 8) : 8;
    const priority = c ? c.priority : 'Urgent';

    container.innerHTML = `
      <!-- Cluster Centroid 1 -->
      <div class="bg-surface-container-low p-5 rounded-xl border border-outline-variant space-y-3">
        <div class="flex items-center justify-between border-b border-outline-variant pb-2">
          <span class="text-xs font-bold text-secondary uppercase tracking-wider flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">hub</span> Centroid Cluster INC-2026-0412
          </span>
          <span class="bg-purple-100 text-purple-800 text-[10px] font-mono font-bold px-2 py-0.5 rounded">
            Water Supply Pipeline
          </span>
        </div>
        
        <div class="flex justify-between items-start gap-4 flex-wrap">
          <div>
            <h4 class="font-sans font-bold text-sm text-primary leading-tight">Leak near St. Jude School Main Road</h4>
            <p class="text-xs text-on-surface-variant mt-1">St. Jude School Main Road, Ward 12, Chicago, IL</p>
          </div>
          <div class="text-right">
            <span class="bg-red-100 text-red-800 border border-red-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">${priority}</span>
            <span class="text-[10px] text-outline block mt-1">${count} linked reports</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 bg-white p-3 rounded-lg border border-outline-variant text-[11px] font-mono">
          <div>
            <span class="text-outline block">Coordinates</span>
            <span class="text-primary font-semibold">41.8795, -87.6255</span>
          </div>
          <div>
            <span class="text-outline block">Max Proximity Distance</span>
            <span class="text-primary font-semibold">32.4m (Radius: 50m)</span>
          </div>
          <div>
            <span class="text-outline block">Cosine Similarity Score</span>
            <span class="text-emerald-600 font-bold">0.89 (Threshold: 0.82)</span>
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <button onclick="OverviewTab.inspectDetails('INC-2026-0412')" class="bg-primary hover:bg-slate-800 text-white text-xs font-semibold px-3 py-1.5 rounded transition-all">
            Inspect Cluster details
          </button>
        </div>
      </div>

      <!-- Cluster Centroid 2 -->
      <div class="bg-surface-container-low p-5 rounded-xl border border-outline-variant space-y-3 opacity-80">
        <div class="flex items-center justify-between border-b border-outline-variant pb-2">
          <span class="text-xs font-bold text-outline uppercase tracking-wider flex items-center gap-1">
            <span class="material-symbols-outlined text-sm text-outline">hub</span> Centroid Cluster INC-2026-0892
          </span>
          <span class="bg-amber-100 text-amber-800 text-[10px] font-mono font-bold px-2 py-0.5 rounded">
            Pothole / Road Repair
          </span>
        </div>
        
        <div class="flex justify-between items-start gap-4 flex-wrap">
          <div>
            <h4 class="font-sans font-bold text-sm text-primary leading-tight">Large pothole in middle lane</h4>
            <p class="text-xs text-on-surface-variant mt-1">5th Ave & Main St, Chicago, IL</p>
          </div>
          <div class="text-right">
            <span class="bg-amber-100 text-amber-800 border border-amber-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Moderate</span>
            <span class="text-[10px] text-outline block mt-1">3 linked reports</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 bg-white p-3 rounded-lg border border-outline-variant text-[11px] font-mono">
          <div>
            <span class="text-outline block">Coordinates</span>
            <span class="text-primary font-semibold">41.8781, -87.6298</span>
          </div>
          <div>
            <span class="text-outline block">Max Proximity Distance</span>
            <span class="text-primary font-semibold">14.8m (Radius: 50m)</span>
          </div>
          <div>
            <span class="text-outline block">Cosine Similarity Score</span>
            <span class="text-emerald-600 font-bold">0.93 (Threshold: 0.82)</span>
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <button onclick="OverviewTab.inspectDetails('CP-8921')" class="bg-primary hover:bg-slate-800 text-white text-xs font-semibold px-3 py-1.5 rounded transition-all">
            Inspect Cluster details
          </button>
        </div>
      </div>
    `;
  }
};

window.DuplicatesTab = DuplicatesTab;
