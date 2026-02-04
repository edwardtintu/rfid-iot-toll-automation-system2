const API_BASE_URL = "https://htms-backend.onrender.com";

// Load dashboard stats
async function loadDashboard() {
  try {
    const res = await fetch(API_BASE_URL + "/stats/summary");
    const data = await res.json();

    document.getElementById("backend-status").innerText = "Backend Connected ✅";
    document.getElementById("backend-status").className = "status-connected";

    document.getElementById("total-events").innerText = data.total_events;
    document.getElementById("allowed").innerText = data.allowed;
    document.getElementById("blocked").innerText = data.blocked;
    document.getElementById("active-readers").innerText = data.active_readers;
    document.getElementById("suspended-readers").innerText = data.suspended_readers;
    document.getElementById("blockchain-pending").innerText = data.pending_blockchain;

  } catch (e) {
    document.getElementById("backend-status").innerText = "Backend Not Reachable ❌";
    document.getElementById("backend-status").className = "status-disconnected";
  }
}

// Load additional data
async function loadAdditionalData() {
  // Load system status
  try {
    const response = await fetch(`${API_BASE_URL}/system/status`);
    if (response.ok) {
      const data = await response.json();
      document.getElementById("system-info").innerHTML = `
        Backend: ${data.backend}<br/>
        Database: ${data.database}<br/>
        Blockchain: ${data.blockchain}<br/>
        Simulation Mode: ${data.simulation_mode}
      `;
    } else {
      document.getElementById("system-info").innerHTML = "<p>Error loading system status.</p>";
    }
  } catch (err) {
    document.getElementById("system-info").innerHTML = `<p>Error: ${err.message}</p>`;
  }

  // Load reader trust status
  try {
    const response = await fetch(`${API_BASE_URL}/api/readers/trust`);
    if (response.ok) {
      const readers = await response.json();
      const container = document.getElementById("reader-trust-info");

      if (readers.length === 0) {
        container.innerHTML = "<p>No readers registered yet.</p>";
        return;
      }

      let html = '<div class="readers-list">';
      readers.forEach(reader => {
        const trustClass = reader.trust_score >= 80 ? 'trust-high' :
                          reader.trust_score >= 50 ? 'trust-medium' : 'trust-low';

        html += `
          <div class="reader-item">
            <strong>${reader.reader_id}</strong><br>
            <span class="${trustClass}">Trust: ${reader.trust_score} (${reader.trust_status})</span><br>
            <small>Last updated: ${reader.last_updated || 'N/A'}</small>
          </div>
        `;
      });
      html += '</div>';
      container.innerHTML = html;
    } else {
      document.getElementById("reader-trust-info").innerHTML = "<p>Error loading reader trust status.</p>";
    }
  } catch (err) {
    document.getElementById("reader-trust-info").innerHTML = `<p>Error: ${err.message}</p>`;
  }

  // Load recent transactions
  try {
    const response = await fetch(`${API_BASE_URL}/transactions/recent`);

    if (response.ok) {
      const data = await response.json();
      let html = '<div class="transactions-list">';

      if (data.length === 0) {
        html += "<p>No recent transactions.</p>";
      } else {
        data.forEach(tx => {
          html += `
            <div class="transaction-item">
              <strong>${tx.reader_id}</strong> → ${tx.decision}<br>
              <small>${tx.timestamp}</small>
            </div>
          `;
        });
      }

      html += '</div>';
      document.getElementById("recent-transactions").innerHTML = html;
    } else {
      document.getElementById("recent-transactions").innerHTML = "<p>Error loading recent transactions.</p>";
    }
  } catch (err) {
    document.getElementById("recent-transactions").innerHTML = `<p>Error: ${err.message}</p>`;
  }

  // Load blockchain status
  try {
    // Check if there are pending blockchain events
    const response = await fetch(`${API_BASE_URL}/api/events/pending/count`);

    if (response.ok) {
      const result = await response.json();
      const pendingCount = result.count || 0;

      let html = `
        <p><strong>Pending Events:</strong> ${pendingCount}</p>
        <p><strong>Status:</strong> ${pendingCount > 0 ? 'Sync in Progress' : 'All Synced'}</p>
      `;

      if (pendingCount > 0) {
        html += `<p><button onclick="triggerSync()">Sync Pending Events</button></p>`;
      }

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
    const response = await fetch(`${API_BASE_URL}/api/events/sync`, {
      method: 'POST'
    });

    if (response.ok) {
      alert('Sync triggered successfully!');
      // Reload the blockchain status after a short delay
      setTimeout(loadAdditionalData, 1000);
    } else {
      alert('Failed to trigger sync.');
    }
  } catch (err) {
    alert(`Error triggering sync: ${err.message}`);
  }
}

// Load immediately
loadDashboard();
loadAdditionalData();

// Auto-refresh dashboard stats every 5 seconds
setInterval(loadDashboard, 5000);

// Refresh additional data periodically (every 30 seconds)
setInterval(loadAdditionalData, 30000);