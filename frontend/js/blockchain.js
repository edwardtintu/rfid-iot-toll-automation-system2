const API_BASE_URL = "https://htms-backend.onrender.com";

async function loadBlockchainAudit() {
  try {
    const res = await fetch(API_BASE_URL + "/blockchain/audit");
    const data = await res.json();

    const tbody = document.querySelector("#blockchain-table tbody");
    tbody.innerHTML = "";

    data.forEach(b => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${b.event_id}</td>
        <td class="status-${b.status.toLowerCase()}">${b.status}</td>
        <td>${b.retry_count || 0}</td>
        <td>${b.last_attempt ? new Date(b.last_attempt).toLocaleString() : 'N/A'}</td>
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