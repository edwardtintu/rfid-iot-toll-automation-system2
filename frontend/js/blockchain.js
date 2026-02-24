// Load audit data
async function loadAuditData() {
  try {
    const response = await fetch(`${window.API_BASE_URL}/blockchain/audit`);
    
    if (response.ok) {
      const auditData = await response.json();
      const tbody = document.getElementById('audit-tbody');

      if (auditData.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center">
              <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No blockchain audit records found</p>
              </div>
            </td>
          </tr>
        `;
        return;
      }

      let html = '';
      auditData.forEach(item => {
        const statusClass = getStatusClass(item.status);
        html += `
          <tr>
            <td><code>${truncate(item.event_id, 12)}</code></td>
            <td class="${statusClass}">${item.status}</td>
            <td><span class="retry-count">${item.retry_count || 0}</span></td>
            <td><small>${formatTimestamp(item.last_attempt)}</small></td>
            <td><span class="status-ACTIVE">Queued</span></td>
          </tr>
        `;
      });

      tbody.innerHTML = html;
    } else {
      document.getElementById('audit-tbody').innerHTML = `
        <tr>
          <td colspan="5" class="text-center">
            <div class="empty-state">
              <i class="fas fa-exclamation-triangle"></i>
              <p>Error loading audit records</p>
            </div>
          </td>
        </tr>
      `;
    }
  } catch (error) {
    console.error("Error loading blockchain audit:", error);
    document.getElementById('audit-tbody').innerHTML = `
      <tr>
        <td colspan="5" class="text-center">
          <div class="empty-state">
            <i class="fas fa-exclamation-triangle"></i>
            <p>Error loading audit records</p>
          </div>
        </td>
      </tr>
    `;
  }
}

// Load once on page load
document.addEventListener("DOMContentLoaded", function() {
  loadAuditData();
});