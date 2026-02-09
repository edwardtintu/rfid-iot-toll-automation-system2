// Load dashboard stats
async function loadDashboard() {
  try {
    const res = await fetch(window.API_BASE_URL + "/stats/summary");
    const data = await res.json();

    document.getElementById("backend-status").innerText = "Backend Connected";
    document.getElementById("backend-status").className = "status-connected";

    document.getElementById("total-events").innerText = formatNumber(data.total_events);
    document.getElementById("allowed").innerText = formatNumber(data.allowed);
    document.getElementById("blocked").innerText = formatNumber(data.blocked);
    document.getElementById("active-readers").innerText = formatNumber(data.active_readers);
    document.getElementById("suspended-readers").innerText = formatNumber(data.suspended_readers);
    document.getElementById("blockchain-pending").innerText = formatNumber(data.pending_blockchain);

  } catch (e) {
    document.getElementById("backend-status").innerText = "Backend Not Reachable";
    document.getElementById("backend-status").className = "status-disconnected";
  }
}

// Load additional data
async function loadAdditionalData() {
  // Load system status
  try {
    const response = await fetch(`${window.API_BASE_URL}/system/status`);
    if (response.ok) {
      const data = await response.json();
      document.getElementById("system-info").innerHTML = `
        <div class="system-status-grid">
          <div class="status-item">
            <div class="status-icon">
              <i class="fas fa-server"></i>
            </div>
            <div class="status-details">
              <h4>Backend</h4>
              <p class="status-value status-${data.backend.toLowerCase()}">${data.backend}</p>
            </div>
          </div>
          <div class="status-item">
            <div class="status-icon">
              <i class="fas fa-database"></i>
            </div>
            <div class="status-details">
              <h4>Database</h4>
              <p class="status-value status-${data.database.toLowerCase()}">${data.database}</p>
            </div>
          </div>
          <div class="status-item">
            <div class="status-icon">
              <i class="fas fa-link"></i>
            </div>
            <div class="status-details">
              <h4>Blockchain</h4>
              <p class="status-value status-${data.blockchain.toLowerCase()}">${data.blockchain}</p>
            </div>
          </div>
          <div class="status-item">
            <div class="status-icon">
              <i class="fas fa-sliders-h"></i>
            </div>
            <div class="status-details">
              <h4>Simulation</h4>
              <p class="status-value">${data.simulation_mode ? 'Enabled' : 'Disabled'}</p>
            </div>
          </div>
        </div>
      `;
    } else {
      document.getElementById("system-info").innerHTML = "<p>Error loading system status.</p>";
    }
  } catch (err) {
    document.getElementById("system-info").innerHTML = `<p>Error: ${err.message}</p>`;
  }

  // Load reader trust status
  try {
    const response = await fetch(`${window.API_BASE_URL}/api/readers/trust`);
    if (response.ok) {
      const readers = await response.json();
      const container = document.getElementById("reader-trust-info");

      if (readers.length === 0) {
        showEmptyState("reader-trust-info", "No readers registered yet");
        return;
      }

      let html = '';
      readers.forEach(reader => {
        const statusClass = getStatusClass(reader.trust_status);
        const trustPercentage = reader.trust_score + '%';
        const cardClass = reader.trust_status;

        html += `
          <div class="reader-card ${cardClass}">
            <div class="reader-header">
              <strong>${reader.reader_id}</strong>
              <span class="${statusClass}">${reader.trust_status}</span>
            </div>
            <div class="trust-score">${reader.trust_score}/100</div>
            <div class="trust-bar">
              <div class="trust-bar-fill" style="width: ${trustPercentage};"></div>
            </div>
            <div class="reader-meta">
              <small>Last updated: ${formatTimestamp(reader.last_updated) || 'N/A'}</small>
            </div>
          </div>
        `;
      });
      container.innerHTML = html;
    } else {
      document.getElementById("reader-trust-info").innerHTML = "<p>Error loading reader trust status.</p>";
    }
  } catch (err) {
    document.getElementById("reader-trust-info").innerHTML = `<p>Error: ${err.message}</p>`;
  }

  // Load recent transactions
  try {
    const response = await fetch(`${window.API_BASE_URL}/transactions/recent`);

    if (response.ok) {
      const data = await response.json();
      let html = '';

      if (data.length === 0) {
        showEmptyState("recent-transactions", "No recent transactions");
      } else {
        data.forEach(tx => {
          const decisionClass = getStatusClass(tx.decision);
          html += `
            <div class="transaction-card">
              <div class="transaction-header">
                <strong>${tx.reader_id}</strong>
                <span class="${decisionClass}">${tx.decision}</span>
              </div>
              <div class="transaction-meta">
                <small>${formatTimestamp(tx.timestamp)}</small>
              </div>
            </div>
          `;
        });
        document.getElementById("recent-transactions").innerHTML = html;
      }
    } else {
      document.getElementById("recent-transactions").innerHTML = "<p>Error loading recent transactions.</p>";
    }
  } catch (err) {
    document.getElementById("recent-transactions").innerHTML = `<p>Error: ${err.message}</p>`;
  }

  // Load blockchain status
  try {
    // Check if there are pending blockchain events
    const response = await fetch(`${window.API_BASE_URL}/api/events/pending/count`);

    if (response.ok) {
      const result = await response.json();
      const pendingCount = result.count || 0;
      const syncStatus = pendingCount > 0 ? 'Pending' : 'Synced';
      const statusClass = pendingCount > 0 ? 'status-PENDING' : 'status-SYNCED';

      let html = `
        <div class="status-item">
          <h4>Pending Events</h4>
          <p class="status-value">${pendingCount}</p>
        </div>
        <div class="status-item">
          <h4>Status</h4>
          <p class="status-value ${statusClass}">${syncStatus}</p>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${Math.min(100, pendingCount * 10)}%;"></div>
        </div>
      `;

      document.getElementById("blockchain-status").innerHTML = html;
    } else {
      document.getElementById("blockchain-status").innerHTML = "<p>Blockchain status unavailable.</p>";
    }
  } catch (err) {
    document.getElementById("blockchain-status").innerHTML = `<p>Error: ${err.message}</p>`;
  }
}

// Trigger blockchain sync
async function triggerSync() {
  try {
    const response = await fetch(`${window.API_BASE_URL}/api/events/sync`, {
      method: 'POST'
    });

    if (response.ok) {
      // Show success notification
      showNotification('Sync triggered successfully!', 'success');
      // Reload the blockchain status after a short delay
      setTimeout(loadAdditionalData, 1000);
    } else {
      showNotification('Failed to trigger sync.', 'error');
    }
  } catch (err) {
    showNotification(`Error triggering sync: ${err.message}`, 'error');
  }
}

// Show notification
function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
    <span>${message}</span>
    <button class="close-notification">&times;</button>
  `;
  
  // Add to body
  document.body.appendChild(notification);
  
  // Auto remove after 3 seconds
  setTimeout(() => {
    notification.remove();
  }, 3000);
  
  // Add close functionality
  notification.querySelector('.close-notification').addEventListener('click', () => {
    notification.remove();
  });
}

// Load immediately
loadDashboard();
loadAdditionalData();

// Auto-refresh dashboard stats every 5 seconds
setInterval(loadDashboard, 5000);

// Refresh additional data periodically (every 30 seconds)
setInterval(loadAdditionalData, 30000);

// Add notification styles dynamically
const style = document.createElement('style');
style.textContent = `
  .notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 16px 20px;
    border-radius: 8px;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    display: flex;
    align-items: center;
    gap: 12px;
    z-index: 10000;
    animation: slideInRight 0.3s ease-out;
    border-left: 4px solid var(--primary);
  }
  
  .notification.notification-success {
    border-left-color: var(--success);
  }
  
  .notification.notification-error {
    border-left-color: var(--danger);
  }
  
  .notification i {
    font-size: 18px;
  }
  
  .notification.notification-success i {
    color: var(--success);
  }
  
  .notification.notification-error i {
    color: var(--danger);
  }
  
  .close-notification {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    color: var(--gray);
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`;
document.head.appendChild(style);