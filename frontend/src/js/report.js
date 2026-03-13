// ================================
// ⚙️ Конфигурация
// ================================

const MODE = window.APP_MODE || "real";
const API_BASE = window.API_BASE || "";

// ================================
// 🌐 Fetch JSON
// ================================

async function getJSON(url) {

  const r = await fetch(url);

  if (!r.ok) {

    let err;

    try {
      err = await r.json();
    } catch {
      throw new Error(`HTTP ${r.status}`);
    }

    if (err && err.error) {
      throw new Error(`${err.error} (${err.code})`);
    }

    throw new Error(`HTTP ${r.status}`);
  }

  return await r.json();
}

// ================================
// 📄 Получение отчета
// ================================

async function fetchReport(run_id) {

  if (MODE === "mock") {
    return await getJSON("./mocks/report.json");
  }

  return await getJSON(`${API_BASE}/api/reports/${run_id}`);
}

// ================================
// 📝 Очень простой Markdown → HTML
// ================================

function simpleMarkdown(md) {

  let html = md;

  // заголовки
  html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

  // таблицы (простейший парсер)
  if (html.includes("|")) {

    const lines = html.split("\n");

    let tableHTML = "";
    let inTable = false;

    for (let line of lines) {

      if (line.startsWith("|")) {

        if (!inTable) {
          tableHTML += "<table><tbody>";
          inTable = true;
        }

        if (!line.includes("---")) {

          const cells = line
            .split("|")
            .filter(c => c.trim() !== "");

          tableHTML += "<tr>";

          for (let c of cells) {
            tableHTML += `<td>${c.trim()}</td>`;
          }

          tableHTML += "</tr>";
        }

      } else {

        if (inTable) {
          tableHTML += "</tbody></table>";
          inTable = false;
        }

        if (line.trim() !== "") {
          tableHTML += `<p>${line}</p>`;
        }
      }
    }

    if (inTable) tableHTML += "</tbody></table>";

    html = tableHTML;
  }

  return html;
}

// ================================
// 🚀 Инициализация страницы
// ================================

async function initReport() {

  const out = document.getElementById("report");

  if (!out) return;

  const runId = localStorage.getItem("run_id");

  if (!runId) {

    out.innerHTML = `
      <p class="error">
        Нет run_id. Сначала запустите алгоритм.
      </p>
    `;

    return;
  }

  out.textContent = "Загружаю отчёт...";

  try {

    const rep = await fetchReport(runId);

    // заголовок отчета
    const title = document.createElement("h2");
    title.textContent = rep.report_name;

    const body = document.createElement("div");
    body.innerHTML = simpleMarkdown(rep.markdown || "");

    out.innerHTML = "";
    out.appendChild(title);
    out.appendChild(body);

  } catch (e) {

    out.innerHTML = `
      <p class="error">
        Ошибка загрузки отчета: ${e.message}
      </p>
    `;
  }
}

// ================================
// 🚀 запуск
// ================================

initReport();
