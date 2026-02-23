// Common navigation and utility functions for HTMS

// Add consistent navigation to all pages
document.addEventListener("DOMContentLoaded", () => {
  // Add mobile menu toggle functionality
  const menuToggle = document.querySelector('.menu-toggle');
  if (menuToggle) {
    menuToggle.addEventListener('click', function() {
      document.querySelector('.sidebar').classList.toggle('collapsed');
      document.querySelector('.main-content').classList.toggle('sidebar-collapsed');
    });
  }

  // Set active class for current page
  const currentPage = window.location.pathname.split('/').pop();
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    if (link.getAttribute('href') === currentPage || 
        (currentPage === '' && link.getAttribute('href') === 'index.html')) {
      link.classList.add('active');
    }
  });

  updateAdminKeyStatus();
});

// Utility function to format timestamps
function formatTimestamp(timestamp) {
  if (!timestamp) return 'N/A';
  try {
    // Handle both Unix timestamps and ISO strings
    let date;
    if (typeof timestamp === 'number') {
      date = new Date(timestamp * 1000); // Unix timestamp
    } else {
      date = new Date(timestamp); // ISO string
    }
    return date.toLocaleString();
  } catch (e) {
    return timestamp;
  }
}

// Utility function to get status class
function getStatusClass(status) {
  switch (status) {
    case 'TRUSTED':
      return 'status-TRUSTED';
    case 'DEGRADED':
      return 'status-DEGRADED';
    case 'SUSPENDED':
      return 'status-SUSPENDED';
    case 'ACTIVE':
      return 'status-ACTIVE';
    case 'REVOKED':
      return 'status-REVOKED';
    case 'PENDING':
      return 'status-PENDING';
    case 'SYNCED':
      return 'status-SYNCED';
    case 'FAILED':
      return 'status-FAILED';
    case 'allow':
      return 'decision-allow';
    case 'block':
      return 'decision-block';
    default:
      return '';
  }
}

// Utility function to truncate long strings
function truncate(str, maxLength = 20) {
  if (!str) return '';
  return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}

// API base URL - Updated to local server
const API_BASE_URL = "http://127.0.0.1:8000";

// Make functions available globally if not already defined
window.formatTimestamp = window.formatTimestamp || formatTimestamp;
window.getStatusClass = window.getStatusClass || getStatusClass;
window.truncate = window.truncate || truncate;
window.API_BASE_URL = window.API_BASE_URL || API_BASE_URL;

// Admin API key helpers
function getAdminApiKey() {
  return localStorage.getItem('htms_admin_key') || '';
}

function adminHeaders() {
  const key = getAdminApiKey();
  return key ? { 'X-API-Key': key } : {};
}

window.getAdminApiKey = window.getAdminApiKey || getAdminApiKey;
window.adminHeaders = window.adminHeaders || adminHeaders;

function ensureAdminKeyIndicator() {
  const headerRight = document.querySelector('.header-right');
  if (!headerRight || document.getElementById('admin-key-indicator')) return;

  const indicator = document.createElement('a');
  indicator.href = 'admin-settings.html';
  indicator.id = 'admin-key-indicator';
  indicator.className = 'admin-key-indicator admin-key-unknown';
  indicator.title = 'Admin key status';
  indicator.innerHTML = '<i class="fas fa-user-shield"></i><span class="admin-key-label">Key: Unknown</span>';
  headerRight.prepend(indicator);
}

async function updateAdminKeyStatus() {
  ensureAdminKeyIndicator();
  const indicator = document.getElementById('admin-key-indicator');
  if (!indicator) return;

  try {
    const response = await fetch(`${window.API_BASE_URL}/system/status`, {
      headers: { ...window.adminHeaders() }
    });
    if (!response.ok) {
      indicator.className = 'admin-key-indicator admin-key-invalid';
      indicator.title = 'Admin key invalid or missing';
      return;
    }
    const data = await response.json();
    if (data.key_valid) {
      indicator.className = 'admin-key-indicator admin-key-valid';
      indicator.title = 'Admin key valid';
      const label = indicator.querySelector('.admin-key-label');
      if (label) label.textContent = 'Key: Valid';
    } else {
      indicator.className = 'admin-key-indicator admin-key-invalid';
      indicator.title = 'Admin key invalid or missing';
      const label = indicator.querySelector('.admin-key-label');
      if (label) label.textContent = 'Key: Invalid';
    }
  } catch (e) {
    indicator.className = 'admin-key-indicator admin-key-unknown';
    indicator.title = 'Admin key status unknown';
    const label = indicator.querySelector('.admin-key-label');
    if (label) label.textContent = 'Key: Unknown';
  }
}

window.updateAdminKeyStatus = window.updateAdminKeyStatus || updateAdminKeyStatus;

// Error handling wrapper
function handleApiError(error, context = '') {
  console.error(`API Error in ${context}:`, error);
  return { error: true, message: error.message };
}

// Format numbers with commas
function formatNumber(num) {
  if (typeof num !== 'number') return num;
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Show loading state
function showLoading(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-spinner fa-spin"></i>
        <p>Loading...</p>
      </div>
    `;
  }
}

// Show empty state
function showEmptyState(elementId, message = "No data available") {
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-inbox"></i>
        <p>${message}</p>
      </div>
    `;
  }
}
