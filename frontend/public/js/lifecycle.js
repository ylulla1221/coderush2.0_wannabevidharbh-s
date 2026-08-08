/**
 * lifecycle.js — Phase 1 Frontend Integration
 *
 * Provides three isolated namespaces that wire Phase 1 backend to the
 * existing dashboard UI. No redesign — renders into existing modal/container IDs.
 *
 * Namespaces
 * ──────────
 *   LifecyclePanel      — AI Explainability + lifecycle status inside details-modal
 *   HumanOverridePanel  — Override form inside details-modal
 *   ResidentTracker     — Reference number lookup in resident portal
 */

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────

function lcSLABadge(sla) {
  if (!sla || !sla.status) return '<span class="px-2 py-0.5 text-[10px] rounded-full bg-gray-100 text-gray-600 font-bold">UNKNOWN</span>';
  const map = {
    ACTIVE:    'bg-emerald-100 text-emerald-800',
    WARNING:   'bg-amber-100 text-amber-800',
    BREACHED:  'bg-red-100 text-red-800',
    COMPLETED: 'bg-blue-100 text-blue-700'
  };
  const cls = map[sla.status] || 'bg-gray-100 text-gray-600';
  return `<span class="px-2 py-0.5 text-[10px] rounded-full ${cls} font-bold">${sla.status}</span>`;
}

function lcLifecycleBadge(status) {
  const map = {
    SUBMITTED:    'bg-gray-100 text-gray-700',
    AI_PROCESSED: 'bg-purple-100 text-purple-800',
    ROUTED:       'bg-blue-100 text-blue-800',
    ASSIGNED:     'bg-indigo-100 text-indigo-800',
    IN_PROGRESS:  'bg-amber-100 text-amber-800',
    RESOLVED:     'bg-emerald-100 text-emerald-800',
    ESCALATED:    'bg-red-100 text-red-800'
  };
  const cls = map[status] || 'bg-gray-100 text-gray-600';
  return `<span class="px-2 py-0.5 text-[10px] rounded-full ${cls} font-bold">${status || 'SUBMITTED'}</span>`;
}

function lcRemainingTime(deadline) {
  if (!deadline) return 'No deadline';
  const diffMs = new Date(deadline).getTime() - Date.now();
  const absMs  = Math.abs(diffMs);
  const h = Math.floor(absMs / 3600000);
  const m = Math.floor((absMs % 3600000) / 60000);
  const label = h > 0 ? `${h}h ${m}m` : `${m}m`;
  return diffMs >= 0 ? `⏱ ${label} remaining` : `⚠️ BREACHED ${label} ago`;
}

function lcPriorityColor(priority) {
  const map = { CRITICAL: 'text-red-700', HIGH: 'text-orange-600', MODERATE: 'text-blue-700', LOW: 'text-emerald-700' };
  return map[(priority || '').toUpperCase()] || 'text-gray-600';
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. LIFECYCLE PANEL (AI Explainability + Status in details-modal)
// ─────────────────────────────────────────────────────────────────────────────

const LifecyclePanel = {

  /**
   * Inject the lifecycle + AI panel into the existing details-modal.
   * Called from OverviewTab.inspectDetails() after existing fields are set.
   */
  async render(complaintId, baseComplaint) {
    // Inject container into modal if not already there
    this._ensureContainer();

    const panel = document.getElementById('lc-lifecycle-panel');
    if (!panel) return;

    panel.innerHTML = `<div class="text-xs text-on-surface-variant italic animate-pulse">Loading lifecycle data…</div>`;

    try {
      const status = await window.API.getComplaintStatus(complaintId);

      const slaDeadline = status.sla?.deadline ? new Date(status.sla.deadline).toLocaleString() : 'Not assigned';
      const slaRemaining = lcRemainingTime(status.sla?.deadline);
      const escalationHTML = status.escalation
        ? `<div class="bg-red-50 border border-red-200 rounded-lg p-3 space-y-1">
            <span class="text-[10px] font-bold text-red-700 uppercase tracking-wider block">⚠ Escalated</span>
            <span class="text-xs text-red-900">Level ${status.escalation.escalationLevel} → ${status.escalation.escalationTarget}</span>
            <span class="text-[10px] text-red-700 block">${status.escalation.reason || ''}</span>
           </div>`
        : '';

      panel.innerHTML = `
        <!-- Lifecycle Status -->
        <div class="border-t border-outline-variant pt-4 mt-2 space-y-3">
          <h5 class="text-[10px] font-bold text-primary uppercase tracking-wider flex items-center gap-1">
            <span class="material-symbols-outlined text-sm text-secondary">timeline</span>
            Complaint Lifecycle
          </h5>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">Reference No.</span>
              <span class="font-mono font-bold text-primary">${status.referenceNumber || 'Not assigned'}</span>
            </div>
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">Lifecycle Stage</span>
              ${lcLifecycleBadge(status.lifecycleStatus)}
            </div>
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">SLA Status</span>
              ${lcSLABadge(status.sla)}
            </div>
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">SLA Remaining</span>
              <span class="font-semibold text-primary text-[11px]">${slaRemaining}</span>
            </div>
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">SLA Deadline</span>
              <span class="text-[11px]">${slaDeadline}</span>
            </div>
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">Assigned Dept.</span>
              <span class="text-[11px]">${status.assignedDepartment || 'Unassigned'}</span>
            </div>
          </div>
          ${escalationHTML}
        </div>

        <!-- Quick Lifecycle Actions -->
        <div class="flex flex-wrap gap-2 pt-2">
          <button onclick="LifecyclePanel.quickAssign('${complaintId}')" 
            class="bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">person_add</span> Assign
          </button>
          <button onclick="LifecyclePanel.quickStart('${complaintId}')"
            class="bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">play_arrow</span> Start Work
          </button>
          <button onclick="LifecyclePanel.quickResolve('${complaintId}')"
            class="bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">check_circle</span> Resolve
          </button>
          <button onclick="LifecyclePanel.quickEscalate('${complaintId}')"
            class="bg-red-600 hover:bg-red-700 text-white text-[10px] font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">warning</span> Escalate
          </button>
        </div>

        <!-- Audit Timeline -->
        <div class="border-t border-outline-variant pt-3 mt-1 space-y-2">
          <h5 class="text-[10px] font-bold text-secondary uppercase tracking-wider flex items-center gap-1 mb-2">
            <span class="material-symbols-outlined text-sm">history</span>
            Lifecycle Timeline (${status.timeline?.length || 0} events)
          </h5>
          <div id="lc-timeline-${complaintId}" class="space-y-2 max-h-48 overflow-y-auto pr-1">
            ${(status.timeline || []).length === 0
              ? `<p class="text-[10px] text-outline italic">No audit events recorded yet.</p>`
              : (status.timeline || []).map(e => `
              <div class="flex items-start gap-2 text-[10px] bg-surface-container-low rounded p-2">
                <span class="material-symbols-outlined text-secondary text-sm mt-0.5">fiber_manual_record</span>
                <div class="flex-grow">
                  <span class="font-bold text-primary block">${e.action.replace(/_/g,' ')}</span>
                  <span class="text-on-surface-variant">${e.details || ''}</span>
                  <span class="text-outline block mt-0.5">${e.performedBy} · ${new Date(e.timestamp).toLocaleString()}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- AI Explainability -->
        <div class="border-t border-outline-variant pt-3 mt-1 space-y-2">
          <button onclick="LifecyclePanel.toggleTimeline('lc-ai-panel-${complaintId}')"
            class="text-[10px] font-bold text-purple-700 hover:underline flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">smart_toy</span>
            AI Decision Explainability
          </button>
          <div id="lc-ai-panel-${complaintId}" class="hidden bg-purple-50 border border-purple-200 rounded-lg p-3 space-y-2 text-[10px]">
            <div class="grid grid-cols-2 gap-2">
              <div><span class="text-purple-600 font-bold block">Category Detected</span><span class="text-purple-900">${baseComplaint?.category || '—'}</span></div>
              <div><span class="text-purple-600 font-bold block">Priority Level</span><span class="${lcPriorityColor(baseComplaint?.priority)} font-bold">${baseComplaint?.priority || '—'}</span></div>
              <div><span class="text-purple-600 font-bold block">Assigned Department</span><span class="text-purple-900">${status.assignedDepartment || baseComplaint?.assignedDepartment || '—'}</span></div>
              <div><span class="text-purple-600 font-bold block">SLA Allotted</span><span class="text-purple-900">${status.sla?.hoursAllotted ? status.sla.hoursAllotted + ' hours' : '—'}</span></div>
              <div><span class="text-purple-600 font-bold block">Escalation Flag</span><span class="${status.escalation ? 'text-red-700 font-bold' : 'text-emerald-700'}">${status.escalation ? 'YES — Escalated' : 'No escalation'}</span></div>
              <div><span class="text-purple-600 font-bold block">SLA Status</span>${lcSLABadge(status.sla)}</div>
            </div>
            <div class="bg-white rounded p-2 border border-purple-100 leading-relaxed text-purple-900 mt-1">
              <strong>Routing Decision:</strong> This complaint was automatically classified as
              <em>${baseComplaint?.category || 'unknown category'}</em> and routed to 
              <em>${status.assignedDepartment || 'the assigned department'}</em> based on 
              AI analysis. SLA of ${status.sla?.hoursAllotted || '—'} hours was assigned for priority level 
              <strong class="${lcPriorityColor(baseComplaint?.priority)}">${baseComplaint?.priority || '—'}</strong>.
              ${status.escalation ? `<br/><br/><strong class="text-red-700">Escalation Active:</strong> Complaint escalated to ${status.escalation.escalationTarget} — "${status.escalation.reason}".` : ''}
            </div>
          </div>
        </div>

        <!-- Human Override -->
        <div class="border-t border-outline-variant pt-3 mt-1 space-y-2" id="lc-override-section-${complaintId}">
          <button onclick="LifecyclePanel.toggleTimeline('lc-override-form-${complaintId}')"
            class="text-[10px] font-bold text-amber-700 hover:underline flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">edit_note</span>
            Human Override
          </button>
          <div id="lc-override-form-${complaintId}" class="hidden bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
            <p class="text-[10px] text-amber-800 leading-relaxed">Override AI decision. Original values are preserved in audit trail.</p>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="text-[10px] font-bold text-amber-800 block mb-1">Override Field</label>
                <select id="lc-override-field-${complaintId}" class="w-full p-1.5 border border-amber-300 rounded text-xs bg-white focus:border-amber-500">
                  <option value="priority">Priority</option>
                  <option value="department">Department</option>
                  <option value="duplicate">Duplicate Decision</option>
                </select>
              </div>
              <div>
                <label class="text-[10px] font-bold text-amber-800 block mb-1">New Value</label>
                <input id="lc-override-value-${complaintId}" type="text" placeholder="e.g. CRITICAL" 
                  class="w-full p-1.5 border border-amber-300 rounded text-xs bg-white focus:border-amber-500"/>
              </div>
            </div>
            <div>
              <label class="text-[10px] font-bold text-amber-800 block mb-1">Reason (required)</label>
              <input id="lc-override-reason-${complaintId}" type="text" placeholder="Explain why you're overriding the AI decision…"
                class="w-full p-1.5 border border-amber-300 rounded text-xs bg-white focus:border-amber-500"/>
            </div>
            <button onclick="LifecyclePanel.submitOverride('${complaintId}')"
              class="bg-amber-600 hover:bg-amber-700 text-white text-[10px] font-bold px-4 py-1.5 rounded transition-all">
              Apply Override
            </button>
          </div>
        </div>
      `;
    } catch (err) {
      panel.innerHTML = `<div class="text-xs text-error">Failed to load lifecycle data: ${err.message}</div>`;
    }
  },

  _ensureContainer() {
    const modal = document.getElementById('details-modal');
    if (!modal || document.getElementById('lc-lifecycle-panel')) return;

    // Find the scrollable content area inside the modal card
    const contentArea = modal.querySelector('.overflow-y-auto');
    if (contentArea) {
      const panel = document.createElement('div');
      panel.id = 'lc-lifecycle-panel';
      panel.className = 'space-y-3 border-t border-outline-variant pt-3 mt-2';
      contentArea.appendChild(panel);
    }
  },

  toggleTimeline(id) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden');
  },

  async quickAssign(id) {
    const officer = window.appState.currentUser?.name || 'Municipal Officer';
    try {
      await window.API.assignComplaint(id, officer);
      window.showToast(`Complaint assigned to ${officer}`, 'success');
      await this._refreshAndRender(id);
    } catch (e) { window.showToast('Assignment failed: ' + e.message, 'error'); }
  },

  async quickStart(id) {
    try {
      const result = await window.API.startWork(id);
      if (!result || result.error) throw new Error(result?.error || 'API error');
      window.showToast('Work started — lifecycle updated to IN_PROGRESS', 'success');
      window.appState.cachedComplaints = await window.API.getComplaints();
      if (window.ActiveTasksTab) window.ActiveTasksTab.renderTable();
      if (window.ResidentPortal) window.ResidentPortal.renderResidentStats();
      if (window.OverviewTab) await window.OverviewTab.init();
      await this._refreshAndRender(id);
    } catch (e) { window.showToast('Failed to start work: ' + e.message, 'error'); }
  },

  async quickResolve(id) {
    const notes = prompt('Resolution notes (optional):') || 'Resolved by officer via dashboard.';
    try {
      await window.API.resolveComplaint(id, notes);
      window.showToast('Complaint resolved successfully', 'success');
      // Refresh global state then close modal
      window.appState.cachedComplaints = await window.API.getComplaints();
      if (window.ActiveTasksTab) window.ActiveTasksTab.renderTable();
      if (window.ResidentPortal) window.ResidentPortal.renderResidentStats();
      closeDetailsModal();
      if (window.OverviewTab) await window.OverviewTab.init();
    } catch (e) { window.showToast('Failed to resolve: ' + e.message, 'error'); }
  },

  async quickEscalate(id) {
    const reason = prompt('Escalation reason:') || 'Manual escalation via dashboard.';
    try {
      await window.API.escalateComplaint(id, reason);
      window.showToast('Complaint escalated', 'success');
      await this._refreshAndRender(id);
    } catch (e) { window.showToast('Escalation failed: ' + e.message, 'error'); }
  },

  // Refresh appState and re-render both the panel and dependent tables
  async _refreshAndRender(id) {
    try {
      window.appState.cachedComplaints = await window.API.getComplaints();
      window.appState.cachedStats = await window.API.getStats();
    } catch (_) {}

    // Refresh Overview/Dashboard tab
    if (window.OverviewTab) {
      try {
        await window.OverviewTab.init();
      } catch (err) {
        console.error('Error refreshing OverviewTab:', err);
      }
    }

    // Also refresh Active Tasks table if visible
    if (window.ActiveTasksTab) {
      try {
        if (typeof window.ActiveTasksTab.init === 'function') {
          await window.ActiveTasksTab.init();
        } else {
          window.ActiveTasksTab.renderTable();
        }
      } catch (err) {
        console.error('Error refreshing ActiveTasksTab:', err);
      }
    }

    // Refresh resident stats & timeline & map
    if (window.ResidentPortal) {
      try {
        await window.ResidentPortal.fetchData();
        window.ResidentPortal.renderResidentStats();
        if (typeof window.ResidentPortal.renderTimeline === 'function') {
          window.ResidentPortal.renderTimeline();
        }
        if (typeof window.ResidentPortal.initMiniMap === 'function') {
          window.ResidentPortal.initMiniMap();
        }
      } catch (err) {
        console.error('Error refreshing ResidentPortal:', err);
      }
    }

    // Refresh Details Modal (if open for this complaint)
    if (window.appState.activeDetailId === id && window.OverviewTab) {
      try {
        window.OverviewTab.inspectDetails(id);
      } catch (err) {
        console.error('Error refreshing Details Modal:', err);
      }
    } else {
      const updated = window.appState.cachedComplaints?.find(c => c.id === id);
      await this.render(id, updated);
    }
  },

  async submitOverride(id) {
    const field  = document.getElementById(`lc-override-field-${id}`)?.value;
    const value  = document.getElementById(`lc-override-value-${id}`)?.value?.trim();
    const reason = document.getElementById(`lc-override-reason-${id}`)?.value?.trim();

    if (!value || !reason) {
      window.showToast('Please fill in New Value and Reason', 'error');
      return;
    }

    const reviewer = window.appState.currentUser?.name || 'Reviewer';

    try {
      // Record override in audit trail via status endpoint
      await window.API.updateComplaintStatus(id, {
        status: undefined,
        details: `[HUMAN OVERRIDE] Field: ${field} | AI Value: (original) | Human Value: ${value} | Reason: ${reason} | Reviewer: ${reviewer} | At: ${new Date().toISOString()}`,
        assignedOfficer: reviewer
      });
      window.showToast(`Override applied: ${field} → ${value}`, 'success');
      document.getElementById(`lc-override-form-${id}`)?.classList.add('hidden');
    } catch (e) {
      window.showToast('Override failed: ' + e.message, 'error');
    }
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// 2. RESIDENT TRACKER — Lookup by reference number
// ─────────────────────────────────────────────────────────────────────────────

const ResidentTracker = {

  async lookup(refNum) {
    if (!refNum || !refNum.trim()) {
      window.showToast('Please enter a reference number', 'error');
      return;
    }

    const container = document.getElementById('res-tracker-result');
    if (!container) return;

    container.innerHTML = `<div class="text-xs text-on-surface-variant animate-pulse italic py-4 text-center">Looking up ${refNum.trim()}…</div>`;
    container.classList.remove('hidden');

    try {
      const data = await window.API.trackByReference(refNum.trim());

      const slaLabel = data.slaStatus === 'BREACHED' ? '⚠️ BREACHED' : data.slaStatus || 'N/A';
      const slaClass = { BREACHED: 'text-red-600', WARNING: 'text-amber-600', ACTIVE: 'text-emerald-600', COMPLETED: 'text-blue-600' }[data.slaStatus] || 'text-gray-600';
      const deadline = data.expectedResolutionTime ? new Date(data.expectedResolutionTime).toLocaleString() : 'N/A';
      const remaining = lcRemainingTime(data.expectedResolutionTime);

      container.innerHTML = `
        <div class="space-y-4">
          <!-- Header -->
          <div class="flex justify-between items-start flex-wrap gap-2">
            <div>
              <span class="text-[10px] font-bold text-outline uppercase tracking-wider block">Reference Number</span>
              <span class="font-mono font-bold text-primary text-base">${data.referenceNumber}</span>
            </div>
            ${lcLifecycleBadge(data.lifecycleStatus)}
          </div>

          <!-- Details Grid -->
          <div class="grid grid-cols-2 gap-3 text-xs bg-surface-container-low p-3 rounded-xl border border-outline-variant">
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">Category</span>
              <span class="font-semibold text-primary">${data.category || '—'}</span>
            </div>
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">Priority</span>
              <span class="font-semibold ${lcPriorityColor(data.priority)}">${data.priority || '—'}</span>
            </div>
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">Department</span>
              <span class="font-semibold text-primary">${data.assignedDepartment || 'Processing…'}</span>
            </div>
            <div>
              <span class="text-outline block text-[10px] uppercase tracking-wider">SLA Status</span>
              <span class="font-bold ${slaClass}">${slaLabel}</span>
            </div>
            <div class="col-span-2">
              <span class="text-outline block text-[10px] uppercase tracking-wider">Expected Resolution</span>
              <span class="font-semibold text-primary">${deadline}</span>
              <span class="text-[10px] ${slaClass} ml-2">${remaining}</span>
            </div>
          </div>

          <!-- SLA Countdown Bar -->
          ${data.expectedResolutionTime ? (() => {
            const total = data.sla?.hoursAllotted ? data.sla.hoursAllotted * 3600000 : 172800000;
            const elapsed = Date.now() - (new Date(data.expectedResolutionTime).getTime() - total);
            const pct = Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));
            const barColor = pct >= 100 ? 'bg-red-500' : pct > 80 ? 'bg-amber-500' : 'bg-emerald-500';
            return `<div>
              <div class="flex justify-between text-[10px] font-semibold text-primary mb-1">
                <span>SLA Progress</span><span>${pct}%</span>
              </div>
              <div class="w-full bg-surface-container rounded-full h-2">
                <div class="${barColor} h-2 rounded-full transition-all" style="width: ${pct}%"></div>
              </div>
            </div>`;
          })() : ''}

          <!-- Timeline -->
          <div>
            <h5 class="text-[10px] font-bold text-primary uppercase tracking-wider mb-2 flex items-center gap-1">
              <span class="material-symbols-outlined text-sm text-secondary">history</span>
              Activity Timeline
            </h5>
            <div class="space-y-2 max-h-60 overflow-y-auto">
              ${(data.timeline || []).map(e => `
                <div class="flex items-start gap-2 text-[10px] bg-white rounded-lg p-2 border border-outline-variant">
                  <span class="material-symbols-outlined text-secondary text-sm mt-0.5">radio_button_checked</span>
                  <div>
                    <span class="font-bold text-primary block">${e.action.replace(/_/g, ' ')}</span>
                    <span class="text-on-surface-variant">${e.details || ''}</span>
                    <span class="text-outline block mt-0.5">${new Date(e.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      container.innerHTML = `
        <div class="text-center py-6 space-y-2">
          <span class="material-symbols-outlined text-3xl text-error">search_off</span>
          <p class="text-sm font-semibold text-primary">Complaint Not Found</p>
          <p class="text-xs text-on-surface-variant">No complaint found for reference "<strong>${refNum.trim()}</strong>". Check the number and try again.</p>
        </div>`;
    }
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// 3. NOTIFICATION PANEL — Live notification feed in officer dashboard
// ─────────────────────────────────────────────────────────────────────────────

const NotificationPanel = {
  async loadIntoDropdown() {
    try {
      const notifications = await window.API.getNotifications();
      const container = document.getElementById('notif-list');
      const badge = document.getElementById('notif-badge');
      if (!container) return;

      const unread = notifications.filter(n => !n.read);
      if (badge) {
        if (unread.length > 0) badge.classList.remove('hidden');
        else badge.classList.add('hidden');
      }

      if (notifications.length === 0) {
        container.innerHTML = '<p class="text-center text-outline py-4 italic text-xs">No notifications.</p>';
        return;
      }

      container.innerHTML = notifications.slice(0, 10).map(n => {
        const eventIcon = {
          COMPLAINT_SUBMITTED:  'add_circle',
          COMPLAINT_ASSIGNED:   'person_add',
          SLA_WARNING:          'warning',
          COMPLAINT_ESCALATED:  'error',
          COMPLAINT_RESOLVED:   'check_circle',
          STATUS_CHANGED:       'update'
        }[n.event] || 'info';

        const eventColor = {
          COMPLAINT_ESCALATED: 'text-red-500',
          SLA_WARNING:         'text-amber-500',
          COMPLAINT_RESOLVED:  'text-emerald-500'
        }[n.event] || 'text-secondary';

        return `
          <div class="p-2 border border-outline-variant rounded-lg bg-surface hover:bg-surface-container transition-all flex items-start gap-2 ${n.read ? 'opacity-60' : ''}">
            <span class="material-symbols-outlined text-base mt-0.5 ${eventColor}">${eventIcon}</span>
            <div class="flex-grow">
              <p class="leading-relaxed text-[11px]">${n.message}</p>
              <span class="text-[9px] text-outline block mt-0.5">${new Date(n.createdAt).toLocaleString()}</span>
            </div>
          </div>`;
      }).join('');
    } catch (e) {
      console.warn('[NotificationPanel] Could not load notifications:', e.message);
    }
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// EXPORTS
// ─────────────────────────────────────────────────────────────────────────────

window.LifecyclePanel  = LifecyclePanel;
window.ResidentTracker = ResidentTracker;
window.NotificationPanel = NotificationPanel;

// Auto-load live notifications into dropdown on page ready
document.addEventListener('DOMContentLoaded', () => {
  // Load after a short delay to let other modules initialize
  setTimeout(() => {
    NotificationPanel.loadIntoDropdown();
  }, 2000);
});
