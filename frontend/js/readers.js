const API_BASE_URL = "https://htms-backend.onrender.com";

async function loadReaders() {
  try {
    const res = await fetch(API_BASE_URL + "/readers");
    const readers = await res.json();

    const tbody = document.querySelector("#reader-table tbody");
    tbody.innerHTML = "";

    readers.forEach(r => {
      const row = document.createElement("tr");

      row.innerHTML = `
        <td>${r.reader_id}</td>
        <td>
          ${r.trust_score}
          <div class="trust-bar">
            <div class="trust-bar-fill" style="width:${r.trust_score}%"></div>
          </div>
        </td>
        <td class="status-${r.status}">${r.status}</td>
        <td>${r.last_updated || 'N/A'}</td>
      `;

      tbody.appendChild(row);
    });
  } catch (error) {
    console.error("Error loading readers:", error);
    document.querySelector("#reader-table tbody").innerHTML = 
      `<tr><td colspan="3">Error loading reader data</td></tr>`;
  }
}

loadReaders();
setInterval(loadReaders, 5000);