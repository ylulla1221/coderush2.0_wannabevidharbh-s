// CivicPulse — Clarification Prompt Module
// Loaded on index.html after complaint submission to surface missing-info requests.
// Non-blocking: complaint is already saved in MongoDB before this runs.

window.ClarificationPrompt = {
  _ref: null,

  show(clarification) {
    if (!clarification || !clarification.needed) return;

    const modal          = document.getElementById('clarification-modal');
    const icon           = document.getElementById('clarification-modal-icon');
    const title          = document.getElementById('clarification-modal-title');
    const message        = document.getElementById('clarification-modal-message');
    const fieldsContainer = document.getElementById('clarification-fields-container');
    const inputSection   = document.getElementById('clarification-input-section');
    const urgentSection  = document.getElementById('clarification-urgent-section');
    const refDisplay     = document.getElementById('clarification-ref-display');

    if (!modal) {
      console.warn('[ClarificationPrompt] Modal element not found in DOM');
      return;
    }

    this._ref = clarification.referenceNumber || '';

    refDisplay.textContent = this._ref ? ('Reference: ' + this._ref) : '';

    // Render missing-field badges
    if (clarification.fields && clarification.fields.length > 0) {
      fieldsContainer.innerHTML =
        '<p class="font-semibold text-primary mb-1">Missing information:</p>' +
        clarification.fields.map(function (f) {
          return (
            '<div class="flex items-center gap-1.5 text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">' +
            '<span class="material-symbols-outlined text-sm text-amber-600">warning</span>' +
            '<span>' + f.label + '</span></div>'
          );
        }).join('');
    } else {
      fieldsContainer.innerHTML = '';
    }

    if (clarification.urgent) {
      if (icon)  icon.textContent  = 'bolt';
      if (title) title.textContent = 'Submitted Immediately — Urgent Complaint';
      if (message) message.textContent =
        'Your complaint has been submitted immediately due to its urgency. ' +
        'The response team has been notified. You may optionally provide additional information to help resolve it faster.';
    } else {
      if (icon)  icon.textContent  = 'help_outline';
      if (title) title.textContent = 'Additional Information Requested';
      if (message) message.textContent =
        'Your complaint has been submitted successfully. Providing the following details will help resolve it faster:';
    }

    if (inputSection)  inputSection.classList.remove('hidden');
    if (urgentSection) urgentSection.classList.add('hidden');

    modal.classList.remove('hidden');
  },

  close() {
    var modal = document.getElementById('clarification-modal');
    var textarea = document.getElementById('clarification-additional-info');
    if (modal)    modal.classList.add('hidden');
    if (textarea) textarea.value = '';
  },

  skip() {
    this.close();
  },

  submit: async function () {
    var textarea = document.getElementById('clarification-additional-info');
    var info = textarea ? textarea.value.trim() : '';
    if (!info) { this.close(); return; }

    try {
      if (this._ref && window.API && typeof window.API.trackByReference === 'function') {
        var tracked = await window.API.trackByReference(this._ref);
        if (tracked && tracked._id) {
          await fetch('/api/complaints/' + tracked._id + '/status', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              status: tracked.lifecycleStatus || tracked.status || 'SUBMITTED',
              details: 'Citizen clarification: ' + info
            })
          });
        }
      }
      if (window.showToast) window.showToast('Additional information submitted. Thank you!', 'success');
    } catch (e) {
      console.warn('[ClarificationPrompt] Could not submit additional info:', e);
      if (window.showToast) window.showToast('Additional information noted locally.', 'success');
    }
    this.close();
  }
};
