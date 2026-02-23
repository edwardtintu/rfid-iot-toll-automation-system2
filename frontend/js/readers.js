async function loadReaders() {
  try {
    const res = await fetch(window.API_BASE_URL + "/readers");
    const readers = await res.json();

    const tbody = document.querySelector("#reader-table tbody");
    tbody.innerHTML = "";

    readers.forEach(r => {
      const row = document.createElement("tr");

      row.innerHTML = `
        <td><strong>${r.reader_id}</strong></td>
        <td><span class="trust-score">${r.trust_score}/100</span></td>
        <td class="${getStatusClass(r.status)}">${r.status}</td>
        <td>
          <div class="trust-bar">
            <div class="trust-bar-fill" style="width:${r.trust_score}%"></div>
          </div>
        </td>
        <td><small>${formatTimestamp(r.last_updated)}</small></td>
      `;

      tbody.appendChild(row);
    });
  } catch (error) {
    console.error("Error loading readers:", error);
    document.querySelector("#reader-table tbody").innerHTML =
      `<tr><td colspan="5">Error loading reader data</td></tr>`;
  }
}

// Load once on page load
document.addEventListener("DOMContentLoaded", function() {
  loadReaders();
});