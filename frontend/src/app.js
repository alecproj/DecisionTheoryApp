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

// input.html: отправляем input и переходим на report.html
async function initInput() {
  const form = document.getElementById("input-form");
  if (!form) return;

  const algEl = document.getElementById("algorithm-id");
  const algId = localStorage.getItem("algorithm_id") || "example";
  if (algEl) algEl.textContent = algId;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const a = Number(document.getElementById("a").value);
    const b = Number(document.getElementById("b").value);

    const msg = document.getElementById("message");
    msg.textContent = "Запускаю...";

    try {
      const run = await createRun(algId, { a, b });
      localStorage.setItem("run_id", run.run_id);
      window.location.href = "./report.html";
    } catch (e) {
      msg.textContent = `Ошибка: ${e.message}`;
    }
  });
}

// report.html: показываем markdown как текст (без markdown-рендера для простоты)
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
    out.textContent = rep.markdown || "(пусто)";
  } catch (e) {
    out.textContent = `Ошибка: ${e.message}`;
  }
}

// Авто-инициализация по наличию элементов на странице
initIndex();
initInput();
initReport();
