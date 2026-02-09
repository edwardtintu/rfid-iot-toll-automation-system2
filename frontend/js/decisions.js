async function loadDecisions() {
  try {
    const res = await fetch(window.API_BASE_URL + "/decisions");
    const data = await res.json();

    const tbody = document.querySelector("#decision-table tbody");
    tbody.innerHTML = "";

    data.forEach(d => {
      const row = document.createElement("tr");

      row.innerHTML = `
        <td><small>${formatTimestamp(d.timestamp)}</small></td>
        <td><code>${truncate(d.event_id || 'N/A', 12)}</code></td>
        <td><strong>${d.reader_id}</strong></td>
        <td class="${getStatusClass(d.decision)}">${d.decision}</td>
        <td><span class="trust-indicator">${d.trust_score || 'N/A'}</span></td>
        <td class="ml-scores">
          <span class="ml-a">A:${d.ml_a ? d.ml_a.toFixed(3) : 'N/A'}</span> | 
          <span class="ml-b">B:${d.ml_b ? d.ml_b.toFixed(3) : 'N/A'}</span>
        </td>
        <td class="reason-cell">${truncate(d.reason || 'N/A', 25)}</td>
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