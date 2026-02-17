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
async function fetchAlgorithms() {
  if (MODE === "mock") return await getJSON("./mocks/algorithms.json");
  return await getJSON(`${API_BASE}/api/algorithms`);
}

async function createRun(algorithm_id, input) {
  if (MODE === "mock") return await getJSON("./mocks/run_created.json");

  const r = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ algorithm_id, input }),
  });

  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${r.status}`);
  }
  return await r.json();
}

async function fetchReport(run_id) {
  if (MODE === "mock") return await getJSON("./mocks/report.json");
  return await getJSON(`${API_BASE}/api/reports/${run_id}`);
}

// -------- Pages --------

// index.html: показываем список алгоритмов и переход на input.html
async function initIndex() {
  const listEl = document.getElementById("algorithms");
  if (!listEl) return;

  try {
    const data = await fetchAlgorithms();
    const algorithms = data.algorithms || [];

    listEl.innerHTML = "";
    for (const a of algorithms) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.textContent = `${a.name} (${a.id})`;
      btn.onclick = () => {
        localStorage.setItem("algorithm_id", a.id);
        window.location.href = "./input.html";
      };
      li.appendChild(btn);
      listEl.appendChild(li);
    }
  } catch (e) {
    listEl.innerHTML = `<li>Ошибка: ${e.message}</li>`;
  }
}

// Авто-инициализация по наличию элементов на странице
initIndex();
