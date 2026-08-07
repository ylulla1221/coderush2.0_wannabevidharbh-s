// CivicPulse Resident Portal JavaScript Controller

const ResidentPortal = {
  currentTab: 'dashboard',
  currentIntakeMode: 'standard',
  miniMap: null,
  intakeMap: null,
  aiIntakeMap: null,
  portalMap: null,
  portalMarkers: [],
  mapTypeFilters: { potholes: true, lighting: true, water: true, sanitation: true },
  
  // Charts
  categoriesChart: null,
  statusChart: null,

  async init() {
    console.log('Initializing Resident Portal...');
    document.body.classList.add('resident-layout');
    
    await this.fetchData();
    this.switchTab(this.currentTab);
  },

  async fetchData() {
    try {
      window.appState.cachedComplaints = await window.API.getComplaints();
      window.appState.cachedStats = await window.API.getStats();
    } catch (e) {
      window.showToast('Failed to sync citizen data.', 'error');
    }
  },

  switchTab(tabId) {
    this.currentTab = tabId;

    // Toggle active underlines in top header
    const links = ['dashboard', 'complaints', 'map', 'analytics'];
    links.forEach(l => {
      const btn = document.getElementById(`res-nav-${l}`);
      if (btn) {
        if (l === tabId) {
          btn.className = "text-secondary font-bold text-sm h-full px-1 border-b-2 border-secondary flex items-center";
        } else {
          btn.className = "text-on-surface-variant hover:text-primary font-medium text-sm h-full px-1 border-b-2 border-transparent flex items-center";
        }
      }
    });

    // Toggle Tab contents
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(t => {
      if (t.id === `tab-res-${tabId}`) {
        t.classList.remove('hidden');
      } else {
        t.classList.add('hidden');
      }
    });

    // Handle tab specific actions
    if (tabId === 'dashboard') {
      this.initMiniMap();
      this.renderTimeline();
    } else if (tabId === 'complaints') {
      this.toggleIntakeMode(this.currentIntakeMode);
    } else if (tabId === 'map') {
      this.initPortalMap();
      this.renderNearbyIssues();
    } else if (tabId === 'analytics') {
      this.initCharts();
    }
  },

  // 1. Citizen Dashboard
  initMiniMap() {
    if (this.miniMap) {
      this.miniMap.remove();
      this.miniMap = null;
    }
    const container = document.getElementById('res-mini-map');
    if (!container) return;

    // Center at Seattle coordinates for resident visual mapping
    this.miniMap = L.map('res-mini-map', {
      zoomControl: false,
      attributionControl: false
    }).setView([47.6062, -122.3321], 11);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(this.miniMap);
  },

  renderTimeline() {
    // Standard timeline matches Screenshot 1, but we append newly created citizen reports
    const container = document.getElementById('res-action-timeline');
    if (!container) return;

    const citizenComplaints = window.appState.cachedComplaints.filter(c => c.reporterName === window.appState.currentUser.name || c.id.startsWith('CR-'));
    
    let extraTimelineHtml = '';
    citizenComplaints.forEach((c, idx) => {
      let priorityColor = 'bg-amber-100 text-amber-800 border-amber-200';
      if (c.priority === 'Urgent') priorityColor = 'bg-red-100 text-red-800 border-red-200';
      else if (c.priority === 'Low') priorityColor = 'bg-emerald-100 text-emerald-800 border-emerald-200';

      let icon = 'mail';
      if (c.status === 'Assigned') icon = 'engineering';
      else if (c.status === 'Resolved') icon = 'check_circle';

      extraTimelineHtml = `
        <div class="relative">
          <span class="absolute -left-[41px] top-0.5 bg-secondary text-white w-6 h-6 rounded-full flex items-center justify-center border-2 border-white shadow">
            <span class="material-symbols-outlined text-xs">${icon}</span>
          </span>
          <div class="bg-white p-4 rounded-xl border border-outline-variant max-w-2xl space-y-1">
            <div class="flex justify-between items-center text-[10px]">
              <span class="font-bold px-2 py-0.5 rounded uppercase ${priorityColor}">${c.priority}</span>
              <span class="text-outline font-mono">Today, Just Now</span>
            </div>
            <h4 class="font-sans font-bold text-sm text-primary">Report Status: ${c.status}</h4>
            <p class="text-xs text-on-surface-variant">${c.category} - ${c.description}</p>
            <div class="text-[10px] text-outline flex items-center gap-3 pt-1">
              <span>📍 ${c.address}</span>
              <span>Ref ID: <span class="font-mono">${c.id}</span></span>
            </div>
          </div>
        </div>
      ` + extraTimelineHtml;
    });

    container.innerHTML = extraTimelineHtml + `
      <!-- Timeline Item 1 -->
      <div class="relative">
        <span class="absolute -left-[41px] top-0.5 bg-secondary text-white w-6 h-6 rounded-full flex items-center justify-center border-2 border-white shadow">
          <span class="material-symbols-outlined text-xs">engineering</span>
        </span>
        <div class="bg-white p-4 rounded-xl border border-outline-variant max-w-2xl space-y-1">
          <div class="flex justify-between items-center text-[10px]">
            <span class="bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded uppercase">Moderate</span>
            <span class="text-outline font-mono">Today, 09:45 AM</span>
          </div>
          <h4 class="font-sans font-bold text-sm text-primary">Pothole Repair Scheduled</h4>
          <p class="text-xs text-on-surface-variant">Assigned to Crew Beta. Estimated completion by EOD.</p>
          <div class="text-[10px] text-outline flex items-center gap-3 pt-1">
            <span>📍 1240 Main St, District 4</span>
            <span>Ref ID: <span class="font-mono">CP-8921</span></span>
          </div>
        </div>
      </div>
      <!-- Timeline Item 2 -->
      <div class="relative">
        <span class="absolute -left-[41px] top-0.5 bg-blue-600 text-white w-6 h-6 rounded-full flex items-center justify-center border-2 border-white shadow">
          <span class="material-symbols-outlined text-xs">visibility</span>
        </span>
        <div class="bg-white p-4 rounded-xl border border-outline-variant max-w-2xl space-y-1">
          <div class="flex justify-between items-center text-[10px]">
            <span class="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded uppercase">Low</span>
            <span class="text-outline font-mono">Yesterday, 14:30 PM</span>
          </div>
          <h4 class="font-sans font-bold text-sm text-primary">Inspection Completed</h4>
          <p class="text-xs text-on-surface-variant">Streetlight outage verified by field agent. Parts ordered.</p>
          <div class="text-[10px] text-outline flex items-center gap-3 pt-1">
            <span>📍 89 Park Ave, District 2</span>
            <span>Ref ID: <span class="font-mono">CP-4731</span></span>
          </div>
        </div>
      </div>
    `;
  },

  // 2. Citizen Form Tab
  toggleIntakeMode(mode) {
    this.currentIntakeMode = mode;
    const stdCard = document.getElementById('res-intake-standard-card');
    const aiCard = document.getElementById('res-intake-ai-card');
    const stdBtn = document.getElementById('btn-res-intake-standard');
    const aiBtn = document.getElementById('btn-res-intake-ai');

    if (mode === 'standard') {
      stdCard.classList.remove('hidden');
      aiCard.classList.add('hidden');
      stdBtn.className = "px-4 py-2 bg-white text-primary rounded-md shadow-sm border border-outline-variant/10";
      aiBtn.className = "px-4 py-2 text-on-surface-variant hover:text-primary";
      
      this.initIntakeMap();
    } else {
      stdCard.classList.add('hidden');
      aiCard.classList.remove('hidden');
      stdBtn.className = "px-4 py-2 text-on-surface-variant hover:text-primary";
      aiBtn.className = "px-4 py-2 bg-white text-primary rounded-md shadow-sm border border-outline-variant/10";
      
      this.initAIIntakeMap();
      this.resetAIChat();
    }
  },

  initIntakeMap() {
    if (this.intakeMap) return;
    
    // Seattle coords
    const lat = 47.6062;
    const lng = -122.3321;

    this.intakeMap = L.map('res-intake-map', {
      zoomControl: false,
      attributionControl: false
    }).setView([lat, lng], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(this.intakeMap);

    const marker = L.marker([lat, lng], { draggable: true }).addTo(this.intakeMap);
    
    // Update lat/lng inputs on drag
    marker.on('dragend', () => {
      const pos = marker.getLatLng();
      // Reverse geocode mock
      document.getElementById('res-form-address').value = `Seattle Subsector, lat: ${pos.lat.toFixed(4)}`;
    });
  },

  initAIIntakeMap() {
    if (this.aiIntakeMap) return;
    
    const lat = 47.6062;
    const lng = -122.3321;

    this.aiIntakeMap = L.map('res-ai-intake-map', {
      zoomControl: false,
      attributionControl: false
    }).setView([lat, lng], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(this.aiIntakeMap);
    L.marker([lat, lng]).addTo(this.aiIntakeMap);
  },

  useCitizenLocation() {
    const lat = 47.6062;
    const lng = -122.3321;
    document.getElementById('res-form-address').value = '123 Pine St, Seattle, WA';
    if (this.intakeMap) {
      this.intakeMap.setView([lat, lng], 15);
    }
    window.showToast("Acquired current GPS coordinate locks.");
  },

  previewMedia(input) {
    const file = input.files[0];
    const preview = document.getElementById('media-preview-container');
    const img = document.getElementById('media-preview-img');
    const label = document.getElementById('media-upload-label');

    if (file) {
      label.textContent = `File selected: ${file.name}`;
      const reader = new FileReader();
      reader.onload = (e) => {
        img.src = e.target.result;
        preview.classList.remove('hidden');
        preview.classList.add('flex');
      };
      reader.readAsDataURL(file);
    }
  },

  async submitComplaint(e) {
    e.preventDefault();

    const category = document.getElementById('res-form-category').value;
    const description = document.getElementById('res-form-description').value;
    const address = document.getElementById('res-form-address').value;
    
    const id = `CR-${Math.floor(1000 + Math.random() * 9000)}`;

    const newTicket = {
      id,
      category,
      description,
      lat: 47.6062,
      lng: -122.3321,
      address,
      reporterName: window.appState.currentUser.name,
      reporterContact: window.appState.currentUser.email,
      priority: 'Moderate',
      status: 'Submitted'
    };

    try {
      await window.API.createComplaint(newTicket);
      window.showToast(`Report logged successfully. Ticket reference: ${id}`);
      document.getElementById('res-form-category').value = '';
      document.getElementById('res-form-description').value = '';
      document.getElementById('res-form-address').value = '';
      document.getElementById('media-preview-container').classList.add('hidden');
      document.getElementById('media-upload-label').textContent = 'Click to upload or drag and drop';
      
      await this.fetchData();
      this.switchTab('dashboard');
    } catch (err) {
      window.showToast('Failed to insert report.', 'error');
    }
  },

  // Chat State Initialization
  chatState: {
    history: [],
    draft: {
      category: null,
      priority: 'Moderate',
      description: null,
      location: null,
      name: null,
      contact: null,
      duration: 'Not specified'
    },
    started: false
  },

  resetAIChat() {
    this.chatState = {
      history: [
        { sender: 'ai', text: `Hi! I am your CivicPulse AI Assistant. Describe the issue you noticed (and include details like location, name, and description if possible), and I will help format the redressal request.` }
      ],
      draft: {
        category: null,
        priority: 'Moderate',
        description: null,
        location: null,
        name: null,
        contact: null,
        duration: 'Not specified'
      },
      started: true
    };
    this.updateAIChatUI();
    this.updateAIDraftUI();
  },

  updateAIChatUI() {
    const historyContainer = document.getElementById('res-ai-chat-history');
    if (!historyContainer) return;

    historyContainer.innerHTML = '';
    this.chatState.history.forEach(msg => {
      const isAI = msg.sender === 'ai';
      const msgDiv = document.createElement('div');
      msgDiv.className = `flex gap-2.5 items-start ${isAI ? '' : 'justify-end'}`;
      
      const avatarHTML = isAI ? `
        <div class="w-6 h-6 rounded-full bg-secondary/10 text-secondary flex items-center justify-center shrink-0">
          <span class="material-symbols-outlined text-sm font-semibold">smart_toy</span>
        </div>
      ` : `
        <div class="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 order-2">
          <span class="material-symbols-outlined text-sm font-semibold">person</span>
        </div>
      `;

      msgDiv.innerHTML = `
        ${avatarHTML}
        <div class="${isAI ? 'bg-white border border-outline-variant/60 text-primary' : 'bg-secondary text-white'} p-2.5 rounded-lg max-w-[80%] ${isAI ? '' : 'order-1'}">
          <p class="font-sans leading-relaxed text-[11px] whitespace-pre-wrap">${msg.text}</p>
        </div>
      `;
      historyContainer.appendChild(msgDiv);
    });

    // Scroll to bottom
    historyContainer.scrollTop = historyContainer.scrollHeight;
  },

  updateAIDraftUI() {
    const awaiting = document.getElementById('res-ai-awaiting-view');
    const content = document.getElementById('res-ai-draft-content');

    if (awaiting && content) {
      awaiting.classList.add('hidden');
      content.classList.remove('hidden');
    }

    const catEl = document.getElementById('res-ai-suggested-cat');
    const priEl = document.getElementById('res-ai-suggested-pri');
    const landmarkEl = document.getElementById('res-ai-landmark');
    const durationEl = document.getElementById('res-ai-duration');
    const descEl = document.getElementById('res-ai-formal-desc');
    const nameEl = document.getElementById('res-ai-reporter-name');
    const contactEl = document.getElementById('res-ai-reporter-contact');

    if (catEl) catEl.textContent = this.chatState.draft.category || 'Not identified yet';
    if (priEl) {
      const priority = this.chatState.draft.priority || 'Moderate';
      priEl.textContent = priority;
      priEl.className = priority === 'Urgent'
        ? 'inline-block px-2.5 py-0.5 bg-red-100 text-red-800 border border-red-200 rounded-full font-bold uppercase text-[9px]'
        : 'inline-block px-2.5 py-0.5 bg-amber-100 text-amber-800 border border-amber-200 rounded-full font-bold uppercase text-[9px]';
    }
    if (landmarkEl) landmarkEl.textContent = this.chatState.draft.location || 'Not identified yet';
    if (durationEl) durationEl.textContent = this.chatState.draft.duration || 'Not specified';
    if (descEl) descEl.textContent = this.chatState.draft.description || 'Provide details on the left...';
    if (nameEl) nameEl.textContent = this.chatState.draft.name || 'Not identified yet';
    if (contactEl) contactEl.textContent = this.chatState.draft.contact || 'Not identified yet';
  },

  parseUserMessage(text) {
    const lower = text.toLowerCase();

    // -- Extract Category --
    if (lower.includes('water') || lower.includes('pipe') || lower.includes('leak') || lower.includes('sewage') || lower.includes('flood') || lower.includes('drain')) {
      this.chatState.draft.category = 'Water Supply';
      this.chatState.draft.priority = 'Urgent';
    } else if (lower.includes('pothole') || lower.includes('road') || lower.includes('crack') || lower.includes('street repair') || lower.includes('asphalt')) {
      this.chatState.draft.category = 'Road Repair / Pothole';
      this.chatState.draft.priority = 'Moderate';
    } else if (lower.includes('streetlight') || lower.includes('lamp') || lower.includes('dark') || lower.includes('light bulb') || lower.includes('blackout')) {
      this.chatState.draft.category = 'Streetlight Outage';
      this.chatState.draft.priority = 'Low';
    } else if (lower.includes('garbage') || lower.includes('trash') || lower.includes('waste') || lower.includes('bin') || lower.includes('sanitation') || lower.includes('smell')) {
      this.chatState.draft.category = 'Sanitation & Waste';
      this.chatState.draft.priority = 'Moderate';
    } else if (lower.includes('graffiti') || lower.includes('paint') || lower.includes('spray') || lower.includes('vandalism')) {
      this.chatState.draft.category = 'Graffiti';
      this.chatState.draft.priority = 'Low';
    } else if (lower.includes('dumping') || lower.includes('debris') || lower.includes('illegal dump')) {
      this.chatState.draft.category = 'Illegal Dumping';
      this.chatState.draft.priority = 'Moderate';
    }

    // -- Extract Location / Landmark --
    let locationMatch = null;
    const roadMatches = text.match(/(?:at|near|on|in front of|opposite|address is)\s+([^,.\n]+)/i);
    if (roadMatches && roadMatches[1]) {
      locationMatch = roadMatches[1].trim();
    } else {
      const streetRegex = /\b\d+\s+[A-Za-z0-9\s]+(?:St|Street|Ave|Avenue|Rd|Road|Lane|Ln|Dr|Drive|Way)\b/i;
      const match = text.match(streetRegex);
      if (match) {
        locationMatch = match[0];
      }
    }
    if (locationMatch && locationMatch.length > 3) {
      this.chatState.draft.location = locationMatch;
    }

    // -- Extract Name --
    const nameMatches = text.match(/(?:my name is|this is|i am|reporter is)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)/i);
    if (nameMatches && nameMatches[1]) {
      this.chatState.draft.name = nameMatches[1].trim();
    }

    // -- Extract Contact --
    const emailMatch = text.match(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/);
    const phoneMatch = text.match(/\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b/);
    if (emailMatch) {
      this.chatState.draft.contact = emailMatch[0];
    } else if (phoneMatch) {
      this.chatState.draft.contact = phoneMatch[0];
    }

    // -- Extract Duration --
    const durationMatch = text.match(/(?:since|for|about)\s+(\d+\s+\w+|\w+\s+days|\w+\s+weeks|yesterday|today)/i);
    if (durationMatch && durationMatch[1]) {
      this.chatState.draft.duration = durationMatch[1].trim();
    }

    // -- Update/Append Description --
    if (this.chatState.draft.description) {
      if (text.length > 10 && !this.chatState.draft.description.includes(text)) {
        this.chatState.draft.description += `. Additional context: ${text}`;
      }
    } else {
      this.chatState.draft.description = text;
    }
  },

  getAIResponse() {
    const draft = this.chatState.draft;

    if (!draft.category) {
      return `I see. Could you clarify what category of issue this is? (e.g., Water Supply, Road Repair / Pothole, Streetlight Outage, Sanitation & Waste, Graffiti, or Illegal Dumping)`;
    }

    if (!draft.location) {
      return `Got it, I've noted the issue as ${draft.category}. Could you please specify where this issue is located? An address, cross street, or landmark would be helpful.`;
    }

    if (!draft.name) {
      return `Thanks. What is your name so I can link it as the reporter?`;
    }

    if (!draft.contact) {
      return `Got it, ${draft.name}. What email address or phone number should we use to send you status updates?`;
    }

    const summary = `Perfect! I have collected all the necessary details. Here is a summary of what I've prepared:
• **Category**: ${draft.category}
• **Location**: ${draft.location}
• **Reporter**: ${draft.name} (${draft.contact})
• **Details**: ${draft.description}

Please review the final draft on the right and click "Submit Report" when you are ready to log the complaint.`;
    return summary;
  },

  generateAIDraft() {
    const raw = document.getElementById('res-ai-chat-input').value.trim();
    if (!raw) {
      window.showToast('Please type a message first.', 'error');
      return;
    }

    // Add user message
    this.chatState.history.push({ sender: 'user', text: raw });
    document.getElementById('res-ai-chat-input').value = '';
    this.updateAIChatUI();

    // Parse details
    this.parseUserMessage(raw);
    this.updateAIDraftUI();

    // Formulate response
    setTimeout(() => {
      const response = this.getAIResponse();
      this.chatState.history.push({ sender: 'ai', text: response });
      this.updateAIChatUI();
    }, 600);
  },

  async submitAIDraft() {
    const draft = this.chatState.draft;
    if (!draft.category || !draft.location || !draft.name || !draft.contact) {
      window.showToast('AI draft is incomplete. Please finish the conversation or provide missing info.', 'error');
      return;
    }

    const id = `CR-${Math.floor(1000 + Math.random() * 9000)}`;
    const newTicket = {
      id,
      category: draft.category,
      description: draft.description || `Complaint logged via AI generator at ${draft.location}`,
      lat: 47.6062,
      lng: -122.3321,
      address: draft.location,
      reporterName: draft.name || (window.appState && window.appState.currentUser ? window.appState.currentUser.name : 'Resident'),
      reporterContact: draft.contact || (window.appState && window.appState.currentUser ? window.appState.currentUser.email : 'contact@municipal.gov'),
      priority: draft.priority || 'Moderate',
      status: 'Submitted'
    };

    try {
      await window.API.createComplaint(newTicket);
      window.showToast(`AI Draft successfully submitted! Reference: ${id}`);
      
      this.resetAIChat();

      await this.fetchData();
      this.switchTab('dashboard');
    } catch (err) {
      window.showToast('Failed to save report.', 'error');
    }
  },

  // 3. Citizen Map View with side-panels (Seattle Coords)
  initPortalMap() {
    if (this.portalMap) {
      this.portalMap.remove();
      this.portalMap = null;
    }
    const container = document.getElementById('res-portal-map');
    if (!container) return;

    this.portalMap = L.map('res-portal-map', {
      zoomControl: true,
      attributionControl: false
    }).setView([47.6062, -122.3321], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(this.portalMap);

    this.plotPortalMarkers();
  },

  plotPortalMarkers() {
    // Clear previous
    this.portalMarkers.forEach(m => m.remove());
    this.portalMarkers = [];

    // Filter logic
    const showMy = document.getElementById('res-filter-my-reports').checked;
    const showNeigh = document.getElementById('res-filter-local-issues').checked;

    let complaints = window.appState.cachedComplaints.filter(c => c.status !== 'Resolved');

    if (!showMy) {
      complaints = complaints.filter(c => c.reporterName !== window.appState.currentUser.name);
    }
    if (!showNeigh) {
      complaints = complaints.filter(c => c.reporterName === window.appState.currentUser.name);
    }

    // Apply type checks
    complaints = complaints.filter(c => {
      const cat = c.category.toLowerCase();
      if (cat.includes('pothole') || cat.includes('road')) return this.mapTypeFilters.potholes;
      if (cat.includes(' streetlight') || cat.includes('lighting') || cat.includes('electrical')) return this.mapTypeFilters.lighting;
      if (cat.includes('water') || cat.includes('leak') || cat.includes('supply')) return this.mapTypeFilters.water;
      return this.mapTypeFilters.sanitation;
    });

    complaints.forEach(c => {
      let color = '#3b82f6';
      if (c.priority === 'Urgent') color = '#ef4444';
      else if (c.priority === 'Low') color = '#10b981';

      // Plot
      const lat = c.lat || 47.6062;
      const lng = c.lng || -122.3321;

      const m = L.circleMarker([lat, lng], {
        radius: 7,
        fillColor: color,
        color: '#ffffff',
        weight: 1.5,
        fillOpacity: 0.9
      }).addTo(this.portalMap).bindPopup(`<b>${c.id}</b><br/>${c.category}<br/>${c.address}`);
      
      this.portalMarkers.push(m);
    });
  },

  toggleTypeFilter(type) {
    this.mapTypeFilters[type] = !this.mapTypeFilters[type];
    
    // Toggle button style classes
    const btn = document.getElementById(`btn-filter-${type}`);
    if (btn) {
      if (this.mapTypeFilters[type]) {
        btn.className = "p-1.5 bg-secondary text-white rounded border border-secondary flex items-center justify-center gap-1";
      } else {
        btn.className = "p-1.5 bg-white text-on-surface-variant rounded border border-outline-variant flex items-center justify-center gap-1 hover:text-primary";
      }
    }

    this.plotPortalMarkers();
  },

  renderNearbyIssues() {
    const container = document.getElementById('res-nearby-issues-list');
    if (!container) return;

    const complaints = window.appState.cachedComplaints.filter(c => c.status !== 'Resolved');

    if (complaints.length === 0) {
      container.innerHTML = '<p class="text-center text-outline py-4 italic">No nearby issues found.</p>';
      return;
    }

    container.innerHTML = complaints.slice(0, 3).map(c => {
      let badge = 'bg-blue-100 text-blue-800';
      if (c.priority === 'Urgent') badge = 'bg-red-100 text-red-800';
      else if (c.priority === 'Moderate') badge = 'bg-amber-100 text-amber-800';

      return `
        <div class="p-3 bg-surface-container-low border border-outline-variant rounded-xl space-y-1">
          <div class="flex justify-between items-center text-[9px] font-bold uppercase">
            <span class="${badge} px-2 py-0.5 rounded">${c.priority}</span>
            <span class="text-outline font-mono">${c.status}</span>
          </div>
          <h4 class="font-sans font-bold text-xs text-primary leading-tight">${c.category}</h4>
          <p class="text-[11px] text-on-surface-variant leading-relaxed line-clamp-2">${c.description}</p>
          <div class="text-[9px] text-outline flex justify-between pt-1 border-t border-outline-variant/10">
            <span>📍 ${c.address}</span>
            <button onclick="OverviewTab.inspectDetails('${c.id}')" class="text-secondary font-bold hover:underline">Details</button>
          </div>
        </div>
      `;
    }).join('');
  },

  // 4. Citizen Analytics Chart
  initCharts() {
    const ctx1 = document.getElementById('resAnalyticsCategoriesChart');
    const ctx2 = document.getElementById('resAnalyticsStatusChart');
    if (!ctx1 || !ctx2) return;

    if (this.categoriesChart) this.categoriesChart.destroy();
    if (this.statusChart) this.statusChart.destroy();

    // Counts category distributions
    const catCounts = { 'Water': 0, 'Roads': 0, 'Electrical': 0, 'Waste': 0 };
    window.appState.cachedComplaints.forEach(c => {
      if (c.category.includes('Water')) catCounts['Water']++;
      else if (c.category.includes('Road') || c.category.includes('Pothole')) catCounts['Roads']++;
      else if (c.category.includes('Streetlight') || c.category.includes('Electric')) catCounts['Electrical']++;
      else catCounts['Waste']++;
    });

    this.categoriesChart = new Chart(ctx1, {
      type: 'doughnut',
      data: {
        labels: ['Water', 'Roads', 'Electrical', 'Waste'],
        datasets: [{
          data: Object.values(catCounts),
          backgroundColor: ['#001334', '#006a61', '#89f5e7', '#aec6ff'],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false
      }
    });

    // Counts status ratio
    const stats = window.appState.cachedStats;
    const resolved = stats.statusCounts ? stats.statusCounts.Resolved : 12;
    const active = stats.totalActive || 3;

    this.statusChart = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: ['Active Issues', 'Resolved Issues'],
        datasets: [{
          data: [active, resolved],
          backgroundColor: ['#ba1a1a', '#0d9488']
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } }
      }
    });
  }
};

// Global bindings for Resident Portal elements
function switchResidentTab(tabId) {
  ResidentPortal.switchTab(tabId);
}

function toggleResidentIntakeMode(mode) {
  ResidentPortal.toggleIntakeMode(mode);
}

function useCitizenCurrentLocation() {
  ResidentPortal.useCitizenLocation();
}

function previewCitizenMedia(input) {
  ResidentPortal.previewMedia(input);
}

function submitResidentComplaint(e) {
  ResidentPortal.submitComplaint(e);
}

function generateResidentAIDraft() {
  ResidentPortal.generateAIDraft();
}

function submitResidentAIDraft() {
  ResidentPortal.submitAIDraft();
}

function toggleMapTypeFilter(type) {
  ResidentPortal.toggleTypeFilter(type);
}

function filterResidentMap() {
  ResidentPortal.plotPortalMarkers();
}

window.ResidentPortal = ResidentPortal;
window.switchResidentTab = switchResidentTab;
window.toggleResidentIntakeMode = toggleResidentIntakeMode;
window.useCitizenCurrentLocation = useCitizenCurrentLocation;
window.previewCitizenMedia = previewCitizenMedia;
window.submitResidentComplaint = submitResidentComplaint;
window.generateResidentAIDraft = generateResidentAIDraft;
window.submitResidentAIDraft = submitResidentAIDraft;
window.toggleMapTypeFilter = toggleMapTypeFilter;
window.filterResidentMap = filterResidentMap;
