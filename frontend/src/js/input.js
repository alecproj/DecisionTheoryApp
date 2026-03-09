// ================================
// ⚙️ Конфигурация
// ================================

const MODE = window.APP_MODE || "real";
const API_BASE = window.API_BASE || "";

// ================================
// 🌐 Утилита fetch JSON
// ================================

async function getJSON(url) {
  const r = await fetch(url);

  if (!r.ok) {
    throw new Error(`HTTP ${r.status}: ${url}`);
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

  return await getJSON(`${API_BASE}/api/algorithms`);
}

// ================================
// 🎨 Отображение алгоритма
// ================================

function renderAlgorithm(a) {

  const nameEl = document.getElementById("algorithm-name");
  const descEl = document.getElementById("algorithm-description");

  const guideEl = document.getElementById("guide-link");
  const templateEl = document.getElementById("template-link");

  const videoEl = document.getElementById("guide-video");

  if (nameEl) nameEl.textContent = a.name;
  if (descEl) descEl.textContent = a.description;

  if (guideEl && a.guide_link) {
    guideEl.href = `${API_BASE}${a.guide_link}`;
  }

  if (templateEl && a.template_link) {
    templateEl.href = `${API_BASE}${a.template_link}`;
  }

  // ================================
  // 🎬 YouTube авто-встраивание
  // ================================

  if (videoEl && a.guide_link && a.guide_link.includes("youtube")) {

    const embed = a.guide_link
      .replace("watch?v=", "embed/")
      .replace("youtu.be/", "youtube.com/embed/");

    videoEl.innerHTML = `
      <iframe
        src="${embed}"
        allowfullscreen>
      </iframe>
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

    const sheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[sheetName];

    const csv = XLSX.utils.sheet_to_csv(worksheet);

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
    return await getJSON("./mocks/run_created.json");
  }

  const formData = new FormData();

  formData.append("report_name", report_name);
  formData.append("file", file);

  const r = await fetch(`${API_BASE}/api/runs/${algorithm_id}`, {
    method: "POST",
    body: formData,
  });

  if (!r.ok) {

    const body = await r.json().catch(() => ({}));

    throw new Error(body.error || `HTTP ${r.status}`);
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

  const algId = localStorage.getItem("algorithm_id") || "example";

  let selectedFile = null;

  // ================================
  // 📦 Загружаем алгоритм
  // ================================

  try {

    const data = await fetchAlgorithms();
    const algorithms = data.algorithms || [];

    const algorithm = algorithms.find(a => a.id === algId);

    if (algorithm) {
      renderAlgorithm(algorithm);
    }

  } catch (e) {

    const nameEl = document.getElementById("algorithm-name");

    if (nameEl) {
      nameEl.textContent = "Ошибка загрузки алгоритма";
    }
  }

  // ================================
  // 🔘 Обновление кнопки запуска
  // ================================

  function updateRunButton() {

    const hasFile = !!selectedFile;
    const hasName = reportNameInput.value.trim().length > 0;

    runButton.disabled = !(hasFile && hasName);
  }

  // ================================
  // 📂 Click по Drop zone
  // ================================

  dropZone.addEventListener("click", () => {
    fileInput.click();
  });

  // ================================
  // 📂 Выбор файла
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

    updateRunButton();
  });

  // ================================
  // ✏️ Ввод имени отчета
  // ================================

  reportNameInput.addEventListener("input", updateRunButton);

  // ================================
  // 🚀 Submit формы
  // ================================

  form.addEventListener("submit", async (ev) => {

    ev.preventDefault();

    if (!selectedFile) {

      message.textContent = "Выберите файл";
      message.className = "error";

      return;
    }

    const report_name = reportNameInput.value.trim();

    if (!report_name) {

      message.textContent = "Введите имя отчета";
      message.className = "error";

      return;
    }

    message.textContent = "Загружаю...";
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
// 🚀 Автозапуск
// ================================

initInput();
