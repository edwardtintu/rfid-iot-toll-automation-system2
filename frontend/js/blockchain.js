async function loadBlockchainAudit() {
  try {
    const res = await fetch(window.API_BASE_URL + "/blockchain/audit");
    const data = await res.json();

    const tbody = document.querySelector("#blockchain-table tbody");
    tbody.innerHTML = "";

    data.forEach(b => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><code>${truncate(b.event_id, 12)}</code></td>
        <td class="${getStatusClass(b.status)}">${b.status}</td>
        <td><span class="retry-count">${b.retry_count || 0}</span></td>
        <td><small>${formatTimestamp(b.last_attempt)}</small></td>
      `;
      tbody.appendChild(row);
    });
  } catch (error) {
    console.error("Error loading blockchain audit:", error);
    document.querySelector("#blockchain-table tbody").innerHTML =
      `<tr><td colspan="4">Error loading blockchain audit data</td></tr>`;
  }
}

loadBlockchainAudit();
setInterval(loadBlockchainAudit, 5000);