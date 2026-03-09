// ================================
// ⚙️ Конфигурация
// ================================

const MODE = window.APP_MODE || "real";
const API_BASE = window.API_BASE || "";

// ================================
// 🌐 fetch helper
// ================================

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${url}`);
  return await r.json();
}

// ================================
// 📦 Получение списка отчетов
// ================================

async function fetchReports() {

  if (MODE === "mock") {

    // mock режим — один отчет
    const rep = await getJSON("./mocks/report.json");

    return {
      items: [
        {
          run_id: rep.run_id,
          report_name: rep.markdown
            .split("\n")[0]
            .replace("#", "")
            .trim()
        }
      ]
    };
  }

  return await getJSON(`${API_BASE}/api/reports`);
}

// ================================
// 🎨 Отображение списка
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

    btn.textContent = r.report_name || r.run_id;

    btn.onclick = () => {

      localStorage.setItem("run_id", r.run_id);

      window.location.href = "./report.html";
    };

    li.appendChild(btn);
    ul.appendChild(li);
  }

  container.appendChild(ul);
}

// ================================
// 🚀 init
// ================================

async function initReports() {

  const el = document.getElementById("reports-list");a

  if (!el) return;

  el.textContent = "Загружаю отчёты...";

  try {

    const data = await fetchReports();

    renderReports(data);

  } catch (e) {

    el.innerHTML = `<p class="error">Ошибка: ${e.message}</p>`;
  }
}

initReports();
