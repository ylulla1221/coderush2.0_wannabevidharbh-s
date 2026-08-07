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
  }
};

window.API = API;
