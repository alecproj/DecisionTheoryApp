// ================================
// ⚙️ Конфигурация
// ================================

const MODE = window.APP_MODE || "real";
const API_BASE = window.API_BASE || "/api";

// ================================
// 🌐 Fetch JSON
// ================================

async function getJSON(url) {

  const r = await fetch(url);

  if (!r.ok) {
    throw new Error(`HTTP ${r.status}`);
  }

  return await r.json();
}

// ================================
// 📦 Получение алгоритмов
// ================================

async function fetchAlgorithms() {

  if (MODE === "mock") {
    return await getJSON("./mocks/algorithms.json");
  }

  return await getJSON(`${API_BASE}/algorithms`);
}

// ================================
// 🎨 Отображение алгоритма
// ================================

function renderAlgorithm(a) {

  document.getElementById("algorithm-name").textContent = a.name;
  document.getElementById("algorithm-description").textContent = a.description;

  const guideEl = document.getElementById("guide-link");
  const templateEl = document.getElementById("template-link");
  const videoEl = document.getElementById("guide-video");

  if (a.guide_link) {
    guideEl.href = `${a.guide_link}`;
  }

  if (a.template_link) {
    templateEl.href = `${a.template_link}`;
  }

  // YouTube embed
  if (videoEl && a.guide_link && a.guide_link.includes("youtube")) {

    const embed = a.guide_link
      .replace("watch?v=", "embed/")
      .replace("youtu.be/", "youtube.com/embed/");

    videoEl.innerHTML = `
      <iframe src="${embed}" allowfullscreen></iframe>
    `;
  }
}

// ================================
// 📄 Excel → CSV
// ================================

async function fileToCSV(file) {

  const name = file.name.toLowerCase();

  if (name.endsWith(".csv")) {
    return file;
  }

  if (name.endsWith(".xlsx") || name.endsWith(".xls")) {

    const data = await file.arrayBuffer();

    const workbook = XLSX.read(data);

    const sheet = workbook.Sheets[workbook.SheetNames[0]];

    const csv = XLSX.utils.sheet_to_csv(sheet);

    return new File(
      [csv],
      file.name.replace(/\.(xlsx|xls)$/i, ".csv"),
      { type: "text/csv" }
    );
  }

  throw new Error("Поддерживаются только CSV или Excel файлы");
}

// ================================
// 🚀 Создание run
// ================================

async function createRunWithFile(algorithm_id, report_name, file) {

  if (MODE === "mock") {

    const mock = await getJSON("./mocks/run_created.json");

    return {
      ...mock,
      algorithm_id,
      report_name
    };
  }

  const formData = new FormData();

  formData.append("report_name", report_name);
  formData.append("file", file);

  const r = await fetch(`${API_BASE}/runs/${algorithm_id}`, {
    method: "POST",
    body: formData
  });

  if (r.status !== 201) {

    const body = await r.json().catch(() => ({}));

    throw new Error(
      body.error
        ? `${body.error} (${body.code})`
        : `HTTP ${r.status}`
    );
  }

  return await r.json();
}

// ================================
// 📥 Инициализация страницы
// ================================

async function initInput() {

  const form = document.getElementById("input-form");
  if (!form) return;

  const reportNameInput = document.getElementById("report-name");
  const fileInput = document.getElementById("file-input");

  const dropZone = document.getElementById("drop-zone");
  const runButton = document.getElementById("run-button");

  const message = document.getElementById("message");

  const algId = localStorage.getItem("algorithm_id") || "ahp";

  let selectedFile = null;

  // ================================
  // 📦 Загружаем алгоритм
  // ================================

  try {

    const data = await fetchAlgorithms();

    const algorithm = data.algorithms.find(a => a.id === algId);

    if (algorithm) {
      renderAlgorithm(algorithm);
    }

  } catch {

    document.getElementById("algorithm-name").textContent =
      "Ошибка загрузки алгоритма";
  }

  // ================================
  // 🔘 Кнопка запуска
  // ================================

  function updateRunButton() {

    const hasName = reportNameInput.value.trim().length > 0;
    const hasFile = !!selectedFile;

    runButton.disabled = !(hasName && hasFile);
  }

  // ================================
  // 📂 click по зоне
  // ================================

  dropZone.addEventListener("click", () => {
    fileInput.click();
  });

  // ================================
  // 📂 выбор файла
  // ================================

  fileInput.addEventListener("change", () => {

    selectedFile = fileInput.files[0];

    if (selectedFile) {
      dropZone.textContent = `Выбран файл: ${selectedFile.name}`;
    }

    updateRunButton();
  });

  // ================================
  // 🖱 Drag & Drop
  // ================================

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

    if (!name.endsWith(".csv") &&
        !name.endsWith(".xlsx") &&
        !name.endsWith(".xls")) {

      alert("Нужен CSV или Excel файл");
      return;
    }

    selectedFile = file;
    fileInput.files = e.dataTransfer.files;

    dropZone.textContent = `Выбран файл: ${file.name}`;

    updateRunButton();
  });

  // ================================
  // ✏️ имя отчета
  // ================================

  reportNameInput.addEventListener("input", updateRunButton);

  // ================================
  // 🚀 submit
  // ================================

  form.addEventListener("submit", async (e) => {

    e.preventDefault();

    if (!selectedFile) {

      message.textContent = "Выберите файл";
      message.className = "error";
      return;
    }

    if (selectedFile.size === 0) {

      message.textContent = "Файл пустой";
      message.className = "error";
      return;
    }

    const report_name = reportNameInput.value.trim();

    if (!report_name) {

      message.textContent = "Введите имя отчета";
      message.className = "error";
      return;
    }

    message.textContent = "Загрузка...";
    message.className = "";

    try {

      const csvFile = await fileToCSV(selectedFile);

      const run = await createRunWithFile(
        algId,
        report_name,
        csvFile
      );

      localStorage.setItem("run_id", run.run_id);

      window.location.href = "./report.html";

    } catch (e) {

      message.textContent = `Ошибка: ${e.message}`;
      message.className = "error";
    }
  });
}

// ================================
// 🚀 Старт
// ================================

initInput();
