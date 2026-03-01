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

async function fileToCSV(file) {
  const name = file.name.toLowerCase();

  // Если уже CSV — просто вернуть
  if (name.endsWith(".csv")) {
    return file;
  }

  // Excel → CSV
  if (name.endsWith(".xlsx") || name.endsWith(".xls")) {
    const data = await file.arrayBuffer();
    const workbook = XLSX.read(data);

    // берём первый лист
    const sheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[sheetName];

    const csv = XLSX.utils.sheet_to_csv(worksheet);

    // превращаем строку в File
    return new File([csv], file.name.replace(/\.(xlsx|xls)$/i, ".csv"), {
      type: "text/csv",
    });
  }

  throw new Error("Поддерживаются только CSV или Excel файлы");
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

async function createRunWithFile(algorithm_id, file) {
  if (MODE === "mock") return await getJSON("./mocks/run_created.json");

  const formData = new FormData();
  formData.append("algorithm_id", algorithm_id);
  formData.append("file", file);

  const r = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    body: formData,
  });

  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${r.status}`);
  }
  return await r.json();
}

async function initInput() {
  const form = document.getElementById("input-form");
  if (!form) return;

  const fileInput = document.getElementById("file-input");
  const dropZone = document.getElementById("drop-zone");

  const algEl = document.getElementById("algorithm-id");
  const algId = localStorage.getItem("algorithm_id") || "example";
  if (algEl) algEl.textContent = algId;

  let selectedFile = null;

  // =========================
  // 📂 Click по drop zone
  // =========================
  dropZone.addEventListener("click", () => fileInput.click());

  // =========================
  // 📂 Выбор через input
  // =========================
  fileInput.addEventListener("change", () => {
    selectedFile = fileInput.files[0];
    const btn = document.getElementById("file-button");

    if (selectedFile) {
      dropZone.textContent = `Выбран файл: ${selectedFile.name}`;
      if (btn) btn.textContent = `✓ ${selectedFile.name}`;
    }
  });

  // =========================
  // 🖱 Drag & Drop
  // =========================
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    const file = e.dataTransfer.files[0];
    if (!file) return;

    const name = file.name.toLowerCase();
    if (
      !name.endsWith(".csv") &&
      !name.endsWith(".xlsx") &&
      !name.endsWith(".xls")
    ) {
      alert("Нужен CSV или Excel файл");
      return;
    }

    selectedFile = file;
    fileInput.files = e.dataTransfer.files;
    dropZone.textContent = `Выбран файл: ${file.name}`;
  });

  // =========================
  // 🚀 Submit
  // =========================
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();

    const msg = document.getElementById("message");

    if (!selectedFile) {
      msg.textContent = "Выберите CSV файл";
      msg.className = "error";
      return;
    }

    msg.textContent = "Загружаю...";
    msg.className = "";

    try {
      const csvFile = await fileToCSV(selectedFile);
      const run = await createRunWithFile(algId, csvFile);
      localStorage.setItem("run_id", run.run_id);
      window.location.href = "./report.html";
    } catch (e) {
      msg.textContent = `Ошибка: ${e.message}`;
      msg.className = "error";
    }
  });
}

// Авто-инициализация
initInput();
