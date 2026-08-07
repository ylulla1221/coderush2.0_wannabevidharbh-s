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
    let complaints = window.appState.cachedComplaints.filter(c => c.status !== 'Resolved');
    
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
      if (c.priority === 'Urgent') {
        priorityClass = 'bg-red-100 text-red-800 border-red-200';
      } else if (c.priority === 'Moderate') {
        priorityClass = 'bg-amber-100 text-amber-800 border-amber-200';
      } else {
        priorityClass = 'bg-emerald-100 text-emerald-800 border-emerald-200';
      }

      const isChecked = this.selectedTicketIds.has(c.id) ? 'checked' : '';

      return `
        <tr class="hover:bg-surface-container-low transition-all border-b border-outline-variant bg-white">
          <td class="p-3 text-center">
            <input type="checkbox" data-id="${c.id}" ${isChecked} onchange="ActiveTasksTab.toggleSelectTask('${c.id}', this)" class="rounded text-secondary focus:ring-secondary"/>
          </td>
          <td class="p-3 font-mono text-[11px] font-bold text-primary">${c.id}</td>
          <td class="p-3">
            <div class="font-semibold text-primary">${c.category}</div>
            <div class="text-[10px] text-on-surface-variant">${c.address}</div>
          </td>
          <td class="p-3">
            <span class="px-2 py-0.5 text-[10px] rounded-full border font-bold uppercase ${priorityClass}">${c.priority}</span>
          </td>
          <td class="p-3 text-on-surface-variant font-medium">
            ${c.assignedOfficer || '<span class="text-outline italic">Unassigned</span>'}
          </td>
          <td class="p-3 text-center">
            <button onclick="OverviewTab.inspectDetails('${c.id}')" class="border border-outline-variant hover:bg-surface-container text-primary font-semibold px-2.5 py-1.5 rounded transition-all">
              Details
            </button>
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
