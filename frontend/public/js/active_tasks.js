// CivicPulse Active Tasks & Work Order Control Module

const ActiveTasksTab = {
  selectedTicketIds: new Set(),

  async init() {
    console.log('Initializing Active Tasks Tab...');
    await this.fetchData();
    this.renderTable();
  },

  async fetchData() {
    try {
      window.appState.cachedComplaints = await window.API.getComplaints();
    } catch (err) {
      window.showToast('Failed to sync work order data.', 'error');
    }
  },

  renderTable() {
    const tableBody = document.getElementById('work-orders-table-body');
    const filterDept = document.getElementById('active-tasks-filter').value;
    
    // Show active (non-resolved) complaints
    let complaints = window.appState.cachedComplaints.filter(c => c.status !== 'Resolved' && c.status !== 'RESOLVED' && c.lifecycleStatus !== 'RESOLVED');
    
    // Apply department filter
    if (filterDept) {
      complaints = complaints.filter(c => c.category === filterDept);
    }

    if (complaints.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6" class="p-8 text-center text-on-surface-variant italic bg-white">
            No active work orders in queue.
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = complaints.map(c => {
      let priorityClass = '';
      if (c.priority?.toUpperCase() === 'URGENT' || c.priority?.toUpperCase() === 'CRITICAL' || c.priority?.toUpperCase() === 'HIGH') {
        priorityClass = 'bg-red-100 text-red-800 border-red-200';
      } else if (c.priority?.toUpperCase() === 'MODERATE') {
        priorityClass = 'bg-amber-100 text-amber-800 border-amber-200';
      } else {
        priorityClass = 'bg-emerald-100 text-emerald-800 border-emerald-200';
      }

      let slaClass = 'bg-gray-100 text-gray-700';
      if (c.sla?.status === 'BREACHED') slaClass = 'bg-red-100 text-red-800 font-bold';
      else if (c.sla?.status === 'WARNING') slaClass = 'bg-amber-100 text-amber-800 font-bold';
      else if (c.sla?.status === 'ACTIVE') slaClass = 'bg-emerald-100 text-emerald-800';

      const isChecked = this.selectedTicketIds.has(c.id) ? 'checked' : '';

      return `
        <tr class="hover:bg-surface-container-low transition-all border-b border-outline-variant bg-white">
          <td class="p-3 text-center">
            <input type="checkbox" data-id="${c.id}" ${isChecked} onchange="ActiveTasksTab.toggleSelectTask('${c.id}', this)" class="rounded text-secondary focus:ring-secondary"/>
          </td>
          <td class="p-3 font-mono text-[11px] font-bold text-primary">
            ${c.referenceNumber || c.id}
            <div class="mt-1 text-[9px] uppercase ${slaClass} px-1.5 py-0.5 rounded inline-block">SLA: ${c.sla?.status || 'UNKNOWN'}</div>
          </td>
          <td class="p-3">
            <div class="font-semibold text-primary">${c.category}</div>
            <div class="text-[10px] text-on-surface-variant">${c.address}</div>
          </td>
          <td class="p-3">
            <span class="px-2 py-0.5 text-[10px] rounded-full border font-bold uppercase ${priorityClass}">${c.priority}</span>
          </td>
          <td class="p-3">
            <div class="text-on-surface-variant font-medium text-xs mb-1">
              ${c.assignedDepartment || '<span class="text-outline italic">Unassigned</span>'}
            </div>
            <span class="px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 text-[9px] font-bold uppercase border border-blue-100">${c.lifecycleStatus || c.status}</span>
          </td>
          <td class="p-3 text-center flex flex-col gap-1.5 items-center justify-center">
            <button onclick="OverviewTab.inspectDetails('${c.id}')" class="border border-outline-variant hover:bg-surface-container text-primary text-[10px] font-bold px-2.5 py-1 rounded transition-all w-full">
              Details
            </button>
            ${c.lifecycleStatus !== 'IN_PROGRESS' ? `
            <button onclick="LifecyclePanel.quickStart('${c.id}')" class="bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold px-2.5 py-1 rounded transition-all w-full">
              Start
            </button>` : `
            <button onclick="LifecyclePanel.quickResolve('${c.id}')" class="bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] font-bold px-2.5 py-1 rounded transition-all w-full">
              Resolve
            </button>
            `}
          </td>
        </tr>
      `;
    }).join('');
  },

  toggleSelectTask(id, checkbox) {
    if (checkbox.checked) {
      this.selectedTicketIds.add(id);
    } else {
      this.selectedTicketIds.delete(id);
    }
  },

  toggleSelectAll(selectAllCheckbox) {
    const checkboxes = document.querySelectorAll('#work-orders-table-body input[type="checkbox"]');
    checkboxes.forEach(cb => {
      cb.checked = selectAllCheckbox.checked;
      const id = cb.getAttribute('data-id');
      if (selectAllCheckbox.checked) {
        this.selectedTicketIds.add(id);
      } else {
        this.selectedTicketIds.delete(id);
      }
    });
  },

  async bulkDispatch() {
    const selected = Array.from(this.selectedTicketIds);
    if (selected.length === 0) {
      window.showToast('Please select at least one work order to bulk dispatch.', 'error');
      return;
    }

    try {
      await window.API.bulkDispatch(selected);
      window.showToast(`Successfully dispatched ${selected.length} work orders to Ward 12 Emergency Repair Rig!`);
      this.selectedTicketIds.clear();
      document.getElementById('select-all-workorders').checked = false;
      await this.init();
    } catch (err) {
      window.showToast('Failed to dispatch work orders to database.', 'error');
    }
  }
};

// Bind elements
function renderWorkOrdersTable() {
  ActiveTasksTab.renderTable();
}

function toggleSelectAllWorkorders(checkbox) {
  ActiveTasksTab.toggleSelectAll(checkbox);
}

function bulkCrewDispatch() {
  ActiveTasksTab.bulkDispatch();
}

window.ActiveTasksTab = ActiveTasksTab;
window.renderWorkOrdersTable = renderWorkOrdersTable;
window.toggleSelectAllWorkorders = toggleSelectAllWorkorders;
window.bulkCrewDispatch = bulkCrewDispatch;
