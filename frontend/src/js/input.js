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

// Авто-инициализация по наличию элементов на странице
initInput();
