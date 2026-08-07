// CivicPulse Frontend Routing and Core Application Manager

// Global State
window.appState = {
  currentTab: 'dashboard',
  currentUser: {
    name: 'Er. S. Deshmukh',
    role: 'MUNICIPAL_OFFICER',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD515AtUq2E1m4mcI6b5VyCh-W7zz6lC79mIUq-mDkFburR79roClHrt_1d-RlYbBYwOynOCRGpp0UulXyi8PFxw_QmnkLT5YNQNpf8qt437pNyfOu4H2MJ8SXCAGcSoV5eVA1h6eAYFtGSbJAneSnDUCYoyAFmnu67qdTDfxo5MhDDCTTLiZsHS32zP0nXyRmnc0XiRjkVEyJPNhCy4_bIvrIQvU8g3u0IMntaW7KUmJApDh6VUzFs'
  },
  isPrivacyMaskActive: true,
  notifications: [
    { id: 1, text: "High priority water leak report INC-2026-0412 assigned to Ward 12 Water Repair Unit.", time: "2 hours ago" },
    { id: 2, text: "District streetlight inspection flagged CP-4731 for bulb replacement work.", time: "1 day ago" }
  ],
  cachedComplaints: [],
  cachedStats: {}
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  // Load session from localStorage
  const savedUser = localStorage.getItem('civic_user');
  if (!savedUser) {
    window.location.href = '/login.html';
    return;
  }

  try {
    window.appState.currentUser = JSON.parse(savedUser);
  } catch (e) {
    console.error('Error parsing saved session', e);
  }

  // Update UI profile elements
  updateProfileUI();

  // Load notifications
  renderNotificationsList();

  // Bind click outside dropdowns
  window.addEventListener('click', (e) => {
    if (!e.target.closest('#user-dropdown') && !e.target.closest('img') && !e.target.closest('#res-avatar') && !e.target.closest('#res-user-dropdown')) {
      const d1 = document.getElementById('user-dropdown');
      if (d1) d1.classList.add('hidden');
      const d2 = document.getElementById('res-user-dropdown');
      if (d2) d2.classList.add('hidden');
    }
    if (!e.target.closest('#notif-dropdown') && !e.target.closest('button')) {
      document.getElementById('notif-dropdown').classList.add('hidden');
    }
  });

  // Load and apply masking state
  applyPrivacyMaskingUI();

  // Check role and initialize correct portal layout
  if (window.appState.currentUser.role === 'RESIDENT') {
    if (window.ResidentPortal) {
      await window.ResidentPortal.init();
    }
  } else {
    // Switch to initial Officer tab
    switchTab(window.appState.currentTab);
  }
});

// Tab Router
function switchTab(tabId) {
  window.appState.currentTab = tabId;

  // Toggle active styling on sidebar items
  const menuButtons = document.querySelectorAll('#sidebar-menu button');
  menuButtons.forEach(btn => {
    if (btn.id === `btn-tab-${tabId}`) {
      btn.className = "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-primary bg-surface-container-low border-l-4 border-secondary transition-all";
    } else {
      btn.className = "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-on-surface-variant hover:text-primary hover:bg-surface-container-low transition-all";
    }
  });

  // Toggle tab visibility
  const tabs = document.querySelectorAll('.tab-content');
  tabs.forEach(tab => {
    if (tab.id === `tab-${tabId}`) {
      tab.classList.remove('hidden');
    } else {
      tab.classList.add('hidden');
    }
  });

  // Toggle Header Badges depending on tab
  const engineStatus = document.getElementById('engine-status-badge');
  if (tabId === 'simulations') {
    engineStatus.classList.remove('hidden');
    engineStatus.classList.add('flex');
  } else {
    engineStatus.classList.add('hidden');
    engineStatus.classList.remove('flex');
  }

  // Page Specific Inits
  if (tabId === 'dashboard') {
    if (window.OverviewTab && typeof window.OverviewTab.init === 'function') {
      window.OverviewTab.init();
    }
  } else if (tabId === 'active-tasks') {
    if (window.ActiveTasksTab && typeof window.ActiveTasksTab.init === 'function') {
      window.ActiveTasksTab.init();
    }
  } else if (tabId === 'duplicates') {
    if (window.DuplicatesTab && typeof window.DuplicatesTab.init === 'function') {
      window.DuplicatesTab.init();
    }
  } else if (tabId === 'map') {
    if (window.MapViewTab && typeof window.MapViewTab.init === 'function') {
      window.MapViewTab.init();
    }
  } else if (tabId === 'simulations') {
    if (window.SimulationTab && typeof window.SimulationTab.init === 'function') {
      window.SimulationTab.init();
    }
  } else if (tabId === 'analytics') {
    if (window.ReportsTab && typeof window.ReportsTab.init === 'function') {
      window.ReportsTab.init();
    }
  } else if (tabId === 'sql-explorer') {
    if (window.SQLExplorerTab && typeof window.SQLExplorerTab.init === 'function') {
      window.SQLExplorerTab.init();
    }
  }
}

// Global UI Profile updater
function updateProfileUI() {
  const user = window.appState.currentUser;
  
  // Set resident avatar initials if it exists
  const resAvatar = document.getElementById('res-avatar');
  if (resAvatar && user.name) {
    resAvatar.textContent = user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }
  
  const dropdownUser = document.getElementById('dropdown-username');
  if (dropdownUser) {
    dropdownUser.textContent = user.name + (user.role === 'OPERATOR' ? ' (Admin)' : '');
  }

  const resDropdownUser = document.getElementById('res-dropdown-username');
  if (resDropdownUser) {
    resDropdownUser.textContent = user.name;
  }
  
  // Set avatar text/image for officer sidebar
  const avatar = document.getElementById('sidebar-avatar');
  if (avatar) {
    if (user.role === 'OPERATOR') {
      avatar.textContent = 'OA';
      avatar.className = 'w-10 h-10 rounded-full bg-slate-900 text-amber-400 flex items-center justify-center font-bold text-sm shadow-sm border border-slate-700';
      document.getElementById('sidebar-user-name').textContent = 'Admin Operator';
    } else if (user.role === 'RESIDENT') {
      avatar.textContent = 'RE';
      avatar.className = 'w-10 h-10 rounded-full bg-emerald-700 text-white flex items-center justify-center font-bold text-sm shadow-sm';
      document.getElementById('sidebar-user-name').textContent = 'Resident Portal';
    } else {
      // Municipal Officer
      avatar.textContent = 'OP';
      avatar.className = 'w-10 h-10 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-bold text-sm shadow-sm';
      document.getElementById('sidebar-user-name').textContent = 'Officer Portal';
    }
  }

  // Pre-fill user settings dropdown option
  const select = document.getElementById('settings-user-role');
  if (select) select.value = user.role;
}

// Notifications toggle
function toggleNotifications(event) {
  if (event) event.stopPropagation();
  const notif = document.getElementById('notif-dropdown');
  notif.classList.toggle('hidden');
}

function renderNotificationsList() {
  const container = document.getElementById('notif-list');
  const badge = document.getElementById('notif-badge');
  
  if (window.appState.notifications.length === 0) {
    container.innerHTML = '<p class="text-center text-outline py-4 italic">No notifications.</p>';
    badge.classList.add('hidden');
    return;
  }
  
  badge.classList.remove('hidden');
  container.innerHTML = window.appState.notifications.map(n => `
    <div class="p-2 border border-outline-variant rounded-lg bg-surface hover:bg-surface-container transition-all flex items-start gap-2">
      <span class="material-symbols-outlined text-secondary text-base mt-0.5">info</span>
      <div class="flex-grow">
        <p class="leading-relaxed text-[11px]">${n.text}</p>
        <span class="text-[9px] text-outline block mt-0.5">${n.time}</span>
      </div>
    </div>
  `).join('');
}

// User Profile drop downs
function toggleUserDropdown(event) {
  if (event) event.stopPropagation();
  const isResident = window.appState.currentUser && window.appState.currentUser.role === 'RESIDENT';
  const dropdownId = isResident ? 'res-user-dropdown' : 'user-dropdown';
  const dropdown = document.getElementById(dropdownId);
  if (dropdown) {
    dropdown.classList.toggle('hidden');
  }
}

function logoutSession() {
  localStorage.removeItem('civic_user');
  showToast("Logged out of session.", "info");
  setTimeout(() => {
    window.location.href = '/login.html';
  }, 500);
}

// Settings modal
function openSettingsModal() {
  document.getElementById('settings-modal').classList.remove('hidden');
}

function closeSettingsModal() {
  document.getElementById('settings-modal').classList.add('hidden');
}

function changeSessionUser() {
  const select = document.getElementById('settings-user-role');
  const role = select.value;
  let user = {};

  if (role === 'OPERATOR') {
    user = { name: 'Municipal Admin Operator', role: 'OPERATOR' };
  } else if (role === 'RESIDENT') {
    user = { name: 'Ramesh Kumar', role: 'RESIDENT' };
  } else {
    user = { name: 'Er. S. Deshmukh', role: 'MUNICIPAL_OFFICER' };
  }

  window.appState.currentUser = user;
  localStorage.setItem('civic_user', JSON.stringify(user));
  updateProfileUI();
  closeSettingsModal();
  showToast(`Switched session to ${user.name}`, "success");
  
  // Reload current tab view to re-apply role privileges
  switchTab(window.appState.currentTab);
}

// PII Privacy Masking Toggle
function togglePrivacyMasking() {
  window.appState.isPrivacyMaskActive = !window.appState.isPrivacyMaskActive;
  applyPrivacyMaskingUI();
  showToast(`PII Masking ${window.appState.isPrivacyMaskActive ? 'Enabled' : 'Disabled'}`, "info");
}

function applyPrivacyMaskingUI() {
  const active = window.appState.isPrivacyMaskActive;
  const elements = document.querySelectorAll('.pii-masked');
  
  elements.forEach(el => {
    if (active) {
      el.classList.remove('revealed');
    } else {
      el.classList.add('revealed');
    }
  });

  const icon = document.getElementById('privacy-mask-icon');
  const btn = document.getElementById('privacy-mask-btn');
  
  if (icon && btn) {
    if (active) {
      icon.textContent = 'visibility_off';
      btn.classList.add('bg-surface-container-low');
    } else {
      icon.textContent = 'visibility';
      btn.classList.remove('bg-surface-container-low');
    }
  }
}

// Global Toast Popup Helper
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  let bgClass = 'bg-[#001334] text-white border-slate-700';
  let icon = 'info';

  if (type === 'success') {
    bgClass = 'bg-emerald-800 text-white border-emerald-600';
    icon = 'check_circle';
  } else if (type === 'error') {
    bgClass = 'bg-red-800 text-white border-red-600';
    icon = 'error';
  }

  toast.className = `flex items-center gap-2 px-4 py-2.5 rounded-lg border shadow-lg text-xs transition-all duration-300 opacity-0 translate-y-2 ${bgClass}`;
  toast.innerHTML = `
    <span class="material-symbols-outlined text-base">${icon}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);

  // Trigger animations
  setTimeout(() => {
    toast.classList.remove('opacity-0', 'translate-y-2');
  }, 10);

  // Fade out and remove
  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4000);
}

// Global Exports
window.switchTab = switchTab;
window.toggleNotifications = toggleNotifications;
window.toggleUserDropdown = toggleUserDropdown;
window.logoutSession = logoutSession;
window.openSettingsModal = openSettingsModal;
window.closeSettingsModal = closeSettingsModal;
window.changeSessionUser = changeSessionUser;
window.togglePrivacyMasking = togglePrivacyMasking;
window.applyPrivacyMaskingUI = applyPrivacyMaskingUI;
window.showToast = showToast;
