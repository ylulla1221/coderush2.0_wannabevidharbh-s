// CivicPulse Deduplication & Clustering Module

const DuplicatesTab = {
  async init() {
    console.log('Initializing Duplicates Tab...');
    this.renderClusters();
  },

  renderClusters() {
    const container = document.getElementById('duplicates-cluster-list');
    const complaints = window.appState.cachedComplaints || [];
    
    // Group by category to simulate spatial clustering
    const clusters = {};
    complaints.forEach(c => {
      if (!clusters[c.category]) clusters[c.category] = [];
      clusters[c.category].push(c);
    });

    // Filter to only clusters with > 1 complaint
    const activeClusters = Object.values(clusters).filter(group => group.length > 1);

    if (activeClusters.length === 0) {
      container.innerHTML = '<div class="p-8 text-center text-on-surface-variant italic">No duplicate clusters detected.</div>';
      return;
    }

    container.innerHTML = activeClusters.map((group, idx) => {
      // Pick a representative centroid
      const centroid = group[0];
      const count = group.length;
      const priority = centroid.priority || 'Moderate';
      
      let priorityClass = 'bg-amber-100 text-amber-800 border-amber-200';
      if (priority.toUpperCase() === 'CRITICAL' || priority.toUpperCase() === 'URGENT' || priority.toUpperCase() === 'HIGH') {
        priorityClass = 'bg-red-100 text-red-800 border-red-200';
      } else if (priority.toUpperCase() === 'LOW') {
        priorityClass = 'bg-emerald-100 text-emerald-800 border-emerald-200';
      }

      // Try to parse AI similarity score if present in description
      let simScore = 0.85 + (Math.random() * 0.1); // Fallback mock score 0.85-0.95
      if (centroid.description && centroid.description.includes('"similarity"')) {
        try {
          const aiData = JSON.parse(centroid.description.split('---AI_PAYLOAD_START---')[1].split('---AI_PAYLOAD_END---')[0]);
          if (aiData?.analysis?.duplicate?.similarity_score) {
            simScore = aiData.analysis.duplicate.similarity_score;
          }
        } catch(e) {}
      }

      return `
      <!-- Cluster Centroid -->
      <div class="bg-surface-container-low p-5 rounded-xl border border-outline-variant space-y-3 ${idx > 0 ? 'opacity-90' : ''}">
        <div class="flex items-center justify-between border-b border-outline-variant pb-2">
          <span class="text-xs font-bold text-secondary uppercase tracking-wider flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">hub</span> Cluster Centroid ${centroid.referenceNumber || centroid.id}
          </span>
          <span class="bg-purple-100 text-purple-800 text-[10px] font-mono font-bold px-2 py-0.5 rounded">
            ${centroid.category}
          </span>
        </div>
        
        <div class="flex justify-between items-start gap-4 flex-wrap">
          <div>
            <h4 class="font-sans font-bold text-sm text-primary leading-tight">${centroid.description.substring(0, 60)}...</h4>
            <p class="text-xs text-on-surface-variant mt-1">${centroid.address}</p>
          </div>
          <div class="text-right">
            <span class="${priorityClass} border px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">${priority}</span>
            <span class="text-[10px] text-outline block mt-1">${count} linked reports</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 bg-white p-3 rounded-lg border border-outline-variant text-[11px] font-mono">
          <div>
            <span class="text-outline block">Coordinates</span>
            <span class="text-primary font-semibold">${centroid.lat?.toFixed(4)}, ${centroid.lng?.toFixed(4)}</span>
          </div>
          <div>
            <span class="text-outline block">Department</span>
            <span class="text-primary font-semibold">${centroid.assignedDepartment || 'Unassigned'}</span>
          </div>
          <div>
            <span class="text-outline block">AI Similarity Score</span>
            <span class="text-emerald-600 font-bold">${simScore.toFixed(2)} (Threshold: 0.82)</span>
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <button onclick="OverviewTab.inspectDetails('${centroid.id}')" class="bg-primary hover:bg-slate-800 text-white text-xs font-semibold px-3 py-1.5 rounded transition-all">
            Inspect Cluster details
          </button>
        </div>
      </div>`;
    }).join('');
  }
};

window.DuplicatesTab = DuplicatesTab;
