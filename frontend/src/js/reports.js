// ================================
// ⚙️ Конфигурация
// ================================

const MODE = window.APP_MODE || "real";
const API_BASE = window.API_BASE || "/api";

const DEFAULT_PAGE = 1;
const DEFAULT_PAGE_SIZE = 50;

// ================================
// 🌐 Fetch helper
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
// 📦 Получение списка отчетов
// ================================

async function fetchReports(page = DEFAULT_PAGE, pageSize = DEFAULT_PAGE_SIZE) {

  if (MODE === "mock") {

    return await getJSON("./mocks/reports.json");

  }

  const url =
    `${API_BASE}/reports?page=${page}&page_size=${pageSize}`;

  return await getJSON(url);
}

// ================================
// 🎨 Отображение списка отчетов
// ================================

function renderReports(data) {

  const container = document.getElementById("reports-list");

  const items = data.items || [];

  if (items.length === 0) {

    container.innerHTML = "<p>Отчётов пока нет</p>";

    return;
  }

  container.innerHTML = "";

  const ul = document.createElement("ul");
  ul.className = "reports-ul";

  for (const r of items) {

    const li = document.createElement("li");

    const btn = document.createElement("button");

    btn.className = "report-button";

    btn.textContent = r.report_name;

    btn.onclick = () => {

      localStorage.setItem("run_id", r.run_id);

      window.location.href = "./report.html";
    };

    li.appendChild(btn);
    ul.appendChild(li);
  }

  container.appendChild(ul);

  // информация о количестве
  const info = document.createElement("p");

  info.className = "reports-info";

  info.textContent =
    `Всего отчётов: ${data.total}`;

  container.appendChild(info);
}

// ================================
// 🚀 init
// ================================

async function initReports() {

  const el = document.getElementById("reports-list");

  if (!el) return;

  el.textContent = "Загружаю отчёты...";

  try {

    const data = await fetchReports();

    renderReports(data);

  } catch (e) {

    el.innerHTML =
      `<p class="error">Ошибка загрузки отчётов: ${e.message}</p>`;
  }
}

initReports();
