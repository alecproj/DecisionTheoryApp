// Режим: "mock" (Pages) или "real" (локально с Flask)
const MODE = window.APP_MODE || "real";

// База для API. В docker обычно фронт и бэк на одном хосте, поэтому пусто.
const API_BASE = window.API_BASE || "";

// Утилита: fetch JSON
async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${url}`);
  return await r.json();
}

// Источники данных
async function fetchReport(run_id) {
  if (MODE === "mock") return await getJSON("./mocks/report.json");
  return await getJSON(`${API_BASE}/api/reports/${run_id}`);
}



// report.html: показываем markdown как текст (без markdown-рендера для простоты)
function simpleMarkdown(md) {
  let html = md;

  // Заголовки
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

  // Таблица (очень простой парсер)
  if (html.includes("|")) {
    const lines = html.split("\n");
    let inTable = false;
    let tableHTML = "";

    for (let line of lines) {
      if (line.startsWith("|")) {
        if (!inTable) {
          tableHTML += "<table><tbody>";
          inTable = true;
        }

        if (!line.includes("---")) {
          const cells = line.split("|").filter(c => c.trim() !== "");
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
        tableHTML += `<p>${line}</p>`;
      }
    }

    if (inTable) tableHTML += "</tbody></table>";
    html = tableHTML;
  }

  return html;
}

async function initReport() {
  const out = document.getElementById("report");
  if (!out) return;

  const runId = localStorage.getItem("run_id");
  if (!runId) {
    out.textContent = "Нет run_id. Сначала запустите алгоритм.";
    return;
  }

  out.textContent = "Загружаю отчёт...";

  try {
    const rep = await fetchReport(runId);
    out.innerHTML = simpleMarkdown(rep.markdown || "(пусто)");
  } catch (e) {
    out.innerHTML = `<p class="error">Ошибка: ${e.message}</p>`;
  }
}

// Авто-инициализация по наличию элементов на странице
initReport();
