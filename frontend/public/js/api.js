// CivicPulse Frontend API Client Module

const API = {
  async request(url, method = 'GET', body = null) {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json'
      }
    };
    if (body) {
      options.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(url, options);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! Status: ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error on ${method} ${url}:`, err);
      throw err;
    }
  },

  async getComplaints() {
    return this.request('/api/complaints');
  },

  async createComplaint(data) {
    return this.request('/api/complaints', 'POST', data);
  },

  async updateComplaintStatus(id, data) {
    return this.request(`/api/complaints/${id}/status`, 'PUT', data);
  },

  async overrideSLA(id) {
    return this.request(`/api/complaints/${id}/override`, 'PUT');
  },

  async bulkDispatch(ticketIds) {
    return this.request('/api/complaints/bulk-dispatch', 'POST', { ticketIds });
  },

  async getCrews() {
    return this.request('/api/crews');
  },

  async getOfficers() {
    return this.request('/api/officers');
  },

  async provisionOfficer(data) {
    return this.request('/api/officers', 'POST', data);
  },

  async getAuditLogs() {
    return this.request('/api/audit-logs');
  },

  async executeSQL(sql) {
    return this.request('/api/sql', 'POST', { sql });
  },

  async getStats() {
    return this.request('/api/stats');
  },

  // ── Phase 1: Lifecycle Endpoints ─────────────────────────────────────────

  async getComplaintStatus(id) {
    return this.request(`/api/complaints/${id}/status`);
  },

  async getTimeline(id) {
    return this.request(`/api/complaints/${id}/timeline`);
  },

  async assignComplaint(id, officerName, officerId) {
    return this.request(`/api/complaints/${id}/assign`, 'POST', { officerName, officerId });
  },

  async startWork(id) {
    return this.request(`/api/complaints/${id}/start`, 'POST', {});
  },

  async resolveComplaint(id, resolutionNotes) {
    return this.request(`/api/complaints/${id}/resolve`, 'POST', { resolutionNotes });
  },

  async escalateComplaint(id, reason) {
    return this.request(`/api/complaints/${id}/escalate`, 'POST', { reason });
  },

  async trackByReference(ref) {
    return this.request(`/api/track/${encodeURIComponent(ref)}`);
  },

  async getNotifications(complaintId) {
    const qs = complaintId ? `?complaintId=${complaintId}` : '';
    return this.request(`/api/notifications${qs}`);
  },

  async runEscalationCheck() {
    return this.request('/api/admin/escalation-check', 'POST', {});
  }
};

window.API = API;
