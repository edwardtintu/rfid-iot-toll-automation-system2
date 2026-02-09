const API_BASE_URL = "http://127.0.0.1:8000";

async function loadDecisions() {
  try {
    const res = await fetch(API_BASE_URL + "/decisions");
    const data = await res.json();

    const tbody = document.querySelector("#decision-table tbody");
    tbody.innerHTML = "";

    data.forEach(d => {
      const row = document.createElement("tr");

      row.innerHTML = `
        <td class="small">${d.timestamp ? new Date(d.timestamp).toLocaleString() : 'N/A'}</td>
        <td>${d.event_id || 'N/A'}</td>
        <td>${d.reader_id}</td>
        <td class="decision-${d.decision.toLowerCase()}">${d.decision}</td>
        <td>${d.trust_score || 'N/A'}</td>
        <td class="small">A:${d.ml_a ? d.ml_a.toFixed(3) : 'N/A'} | B:${d.ml_b ? d.ml_b.toFixed(3) : 'N/A'}</td>
        <td>${d.reason || 'N/A'}</td>
      `;

      tbody.appendChild(row);
    });
  } catch (error) {
    console.error("Error loading decisions:", error);
    document.querySelector("#decision-table tbody").innerHTML = 
      `<tr><td colspan="7">Error loading decision data</td></tr>`;
  }
}

loadDecisions();
setInterval(loadDecisions, 5000);