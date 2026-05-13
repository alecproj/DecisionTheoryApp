// ================================
// Конфигурация
// ================================
const MODE = window.APP_MODE || "real";
const API_BASE = window.API_BASE || "/api";

// Если нужна работа Mermaid без интернета:
// 1. Скачай mermaid.esm.min.mjs
// 2. Положи, например, в /vendor/mermaid.esm.min.mjs
// 3. До подключения report.js задай:
//    window.MERMAID_SRC = "/vendor/mermaid.esm.min.mjs";
const MERMAID_SRC =
    window.MERMAID_SRC ||
    "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

let mermaidPromise = null;

// ================================
// Fetch JSON
// ================================
async function getJSON(url) {
    const response = await fetch(url);

    if (!response.ok) {
        let body;

        try {
            body = await response.json();
        } catch {
            throw new Error(`HTTP ${response.status}`);
        }

        if (body && body.error) {
            throw new Error(`${body.error} (${body.code})`);
        }

        throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
}

// ================================
// Получение отчёта
// ================================
async function fetchReport(runId) {
    if (MODE === "mock") {
        return await getJSON("./mocks/report.json");
    }

    return await getJSON(`${API_BASE}/reports/${runId}`);
}

// ================================
// Безопасное экранирование HTML
// ================================
function escapeHTML(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

// ================================
// Inline Markdown
// ================================
function inlineMarkdown(text) {
    let html = escapeHTML(text);

    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    return html;
}

// ================================
// Markdown-таблицы
// ================================
function isTableLine(line) {
    const trimmed = line.trim();

    return trimmed.startsWith("|") && trimmed.includes("|");
}

function isTableSeparator(line) {
    const trimmed = line.trim();

    if (!isTableLine(trimmed)) {
        return false;
    }

    return /^(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(trimmed);
}

function splitTableRow(line) {
    let trimmed = line.trim();

    if (trimmed.startsWith("|")) {
        trimmed = trimmed.slice(1);
    }

    if (trimmed.endsWith("|")) {
        trimmed = trimmed.slice(0, -1);
    }

    return trimmed.split("|").map((cell) => cell.trim());
}

function renderTable(lines) {
    const usefulLines = lines.filter((line) => !isTableSeparator(line));

    if (usefulLines.length === 0) {
        return "";
    }

    const headerCells = splitTableRow(usefulLines[0]);
    const bodyLines = usefulLines.slice(1);

    let html = '<div class="table-wrapper"><table><thead><tr>';

    for (const cell of headerCells) {
        html += `<th>${inlineMarkdown(cell)}</th>`;
    }

    html += "</tr></thead><tbody>";

    for (const line of bodyLines) {
        const cells = splitTableRow(line);

        html += "<tr>";

        for (const cell of cells) {
            html += `<td>${inlineMarkdown(cell)}</td>`;
        }

        html += "</tr>";
    }

    html += "</tbody></table></div>";

    return html;
}

// ================================
// Обычные блоки кода
// ================================
function renderCodeBlock(code, language) {
    const langClass = language ? ` language-${escapeHTML(language)}` : "";

    return `
        <pre class="code-block"><code class="${langClass}">${escapeHTML(code)}</code></pre>
    `;
}

// ================================
// Mermaid-блок
// ================================
function renderMermaidBlock(code) {
    return `
        <div class="mermaid-block">
            <div class="mermaid-toolbar">
                <div class="mermaid-toolbar-left">
                    <button type="button" class="mermaid-btn mermaid-zoom-out" title="Уменьшить">−</button>
                    <button type="button" class="mermaid-btn mermaid-zoom-reset" title="Сбросить масштаб">100%</button>
                    <button type="button" class="mermaid-btn mermaid-zoom-in" title="Увеличить">+</button>
                </div>

                <div class="mermaid-toolbar-right">
                    <button type="button" class="mermaid-btn copy-mermaid-btn">
                        Скопировать код
                    </button>
                    <span class="mermaid-status">
                        Схема ещё не построена
                    </span>
                </div>
            </div>

            <div class="mermaid-help">
                Масштаб: кнопки +/− или Ctrl + колесо мыши. Перемещение: зажми левую кнопку мыши и двигай схему.
            </div>

            <div class="mermaid-preview">
                <div class="mermaid-canvas">
                    <div class="mermaid-placeholder">
                        Загрузка схемы...
                    </div>
                </div>
            </div>

            <details class="mermaid-source-details">
                <summary>Исходный Mermaid-код для ручного копирования</summary>
                <pre><code class="mermaid-source">${escapeHTML(code)}</code></pre>
            </details>
        </div>
    `;
}

// ================================
// Markdown → HTML
// Поддерживает:
// - #, ##, ###
// - **жирный**
// - `inline code`
// - таблицы
// - fenced code blocks
// - ```mermaid
// ================================
function simpleMarkdown(markdown) {
    const lines = String(markdown || "").replaceAll("\r\n", "\n").split("\n");
    const htmlParts = [];

    let i = 0;

    while (i < lines.length) {
        const line = lines[i];
        const trimmed = line.trim();

        if (trimmed === "") {
            i += 1;
            continue;
        }

        // fenced code block
        if (trimmed.startsWith("```")) {
            const language = trimmed.slice(3).trim().toLowerCase();
            const codeLines = [];

            i += 1;

            while (i < lines.length && !lines[i].trim().startsWith("```")) {
                codeLines.push(lines[i]);
                i += 1;
            }

            if (i < lines.length && lines[i].trim().startsWith("```")) {
                i += 1;
            }

            const code = codeLines.join("\n");

            if (language === "mermaid") {
                htmlParts.push(renderMermaidBlock(code));
            } else {
                htmlParts.push(renderCodeBlock(code, language));
            }

            continue;
        }

        // таблица
        if (isTableLine(line)) {
            const tableLines = [];

            while (i < lines.length && isTableLine(lines[i])) {
                tableLines.push(lines[i]);
                i += 1;
            }

            htmlParts.push(renderTable(tableLines));
            continue;
        }

        // заголовки
        if (trimmed.startsWith("### ")) {
            htmlParts.push(`<h3>${inlineMarkdown(trimmed.slice(4))}</h3>`);
            i += 1;
            continue;
        }

        if (trimmed.startsWith("## ")) {
            htmlParts.push(`<h2>${inlineMarkdown(trimmed.slice(3))}</h2>`);
            i += 1;
            continue;
        }

        if (trimmed.startsWith("# ")) {
            htmlParts.push(`<h1>${inlineMarkdown(trimmed.slice(2))}</h1>`);
            i += 1;
            continue;
        }

        // обычный абзац
        htmlParts.push(`<p>${inlineMarkdown(line)}</p>`);
        i += 1;
    }

    return htmlParts.join("\n");
}

// ================================
// Копирование текста
// ================================
async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
    }

    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "-9999px";

    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    document.execCommand("copy");
    textarea.remove();
}

function setupMermaidCopyButtons(root) {
    const buttons = root.querySelectorAll(".copy-mermaid-btn");

    buttons.forEach((button) => {
        button.addEventListener("click", async () => {
            const block = button.closest(".mermaid-block");
            const source = block?.querySelector(".mermaid-source");

            if (!source) {
                return;
            }

            const originalText = button.textContent;

            try {
                await copyText(source.textContent || "");
                button.textContent = "Скопировано";

                setTimeout(() => {
                    button.textContent = originalText;
                }, 1500);
            } catch {
                button.textContent = "Ошибка копирования";

                setTimeout(() => {
                    button.textContent = originalText;
                }, 1500);
            }
        });
    });
}

// ================================
// Загрузка Mermaid
// ================================
async function loadMermaid() {
    if (window.mermaid) {
        return window.mermaid;
    }

    if (!mermaidPromise) {
        mermaidPromise = import(MERMAID_SRC).then((module) => {
            const mermaid = module.default || module;

            mermaid.initialize({
                startOnLoad: false,
                securityLevel: "strict",
                theme: "default",
                flowchart: {
                    useMaxWidth: false,
                    htmlLabels: true,
                    curve: "basis",
                    nodeSpacing: 35,
                    rankSpacing: 55,
                },
            });

            window.mermaid = mermaid;

            return mermaid;
        });
    }

    return await mermaidPromise;
}

// ================================
// Нормализация SVG после Mermaid
// ================================
function normalizeMermaidSvg(canvas) {
    const svg = canvas.querySelector("svg");

    if (!svg) {
        return;
    }

    svg.style.maxWidth = "none";
    svg.style.display = "block";

    const viewBox = svg.getAttribute("viewBox");

    if (viewBox) {
        const parts = viewBox.split(/\s+/).map(Number);

        if (parts.length === 4 && parts.every((part) => !Number.isNaN(part))) {
            const width = Math.ceil(parts[2]);
            const height = Math.ceil(parts[3]);

            svg.removeAttribute("width");
            svg.removeAttribute("height");

            svg.style.width = `${width}px`;
            svg.style.height = `${height}px`;
        }
    }
}

// ================================
// Зум и перемещение Mermaid-схемы
// ================================
function setupMermaidZoom(block) {
    const preview = block.querySelector(".mermaid-preview");
    const canvas = block.querySelector(".mermaid-canvas");
    const zoomInBtn = block.querySelector(".mermaid-zoom-in");
    const zoomOutBtn = block.querySelector(".mermaid-zoom-out");
    const resetBtn = block.querySelector(".mermaid-zoom-reset");

    if (!preview || !canvas || !zoomInBtn || !zoomOutBtn || !resetBtn) {
        return;
    }

    let scale = 1;
    let translateX = 0;
    let translateY = 0;

    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let startTranslateX = 0;
    let startTranslateY = 0;

    function clampScale(value) {
        return Math.min(5, Math.max(0.25, value));
    }

    function applyTransform() {
        canvas.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
        canvas.style.transformOrigin = "0 0";
        resetBtn.textContent = `${Math.round(scale * 100)}%`;
    }

    function fitToWidth() {
        const contentWidth = canvas.scrollWidth;
        const availableWidth = preview.clientWidth - 48;

        if (contentWidth <= 0 || availableWidth <= 0) {
            applyTransform();
            return;
        }

        const fittedScale = clampScale(Math.min(1, availableWidth / contentWidth));

        scale = fittedScale;
        translateX = 0;
        translateY = 0;

        applyTransform();
    }

    zoomInBtn.addEventListener("click", () => {
        scale = clampScale(scale + 0.15);
        applyTransform();
    });

    zoomOutBtn.addEventListener("click", () => {
        scale = clampScale(scale - 0.15);
        applyTransform();
    });

    resetBtn.addEventListener("click", () => {
        fitToWidth();
    });

    preview.addEventListener(
        "wheel",
        (event) => {
            if (!event.ctrlKey && !event.metaKey) {
                return;
            }

            event.preventDefault();

            const oldScale = scale;
            const delta = event.deltaY < 0 ? 0.12 : -0.12;
            const newScale = clampScale(scale + delta);

            if (newScale === oldScale) {
                return;
            }

            const rect = preview.getBoundingClientRect();
            const mouseX = event.clientX - rect.left;
            const mouseY = event.clientY - rect.top;

            const contentX = (mouseX - translateX) / oldScale;
            const contentY = (mouseY - translateY) / oldScale;

            scale = newScale;
            translateX = mouseX - contentX * scale;
            translateY = mouseY - contentY * scale;

            applyTransform();
        },
        { passive: false }
    );

    preview.addEventListener("mousedown", (event) => {
        if (event.button !== 0) {
            return;
        }

        isDragging = true;
        startX = event.clientX;
        startY = event.clientY;
        startTranslateX = translateX;
        startTranslateY = translateY;

        preview.classList.add("is-dragging");
    });

    window.addEventListener("mousemove", (event) => {
        if (!isDragging) {
            return;
        }

        translateX = startTranslateX + event.clientX - startX;
        translateY = startTranslateY + event.clientY - startY;

        applyTransform();
    });

    window.addEventListener("mouseup", () => {
        isDragging = false;
        preview.classList.remove("is-dragging");
    });

    requestAnimationFrame(fitToWidth);
}

// ================================
// Рендер Mermaid-блоков
// ================================
async function renderMermaidBlocks(root) {
    const blocks = Array.from(root.querySelectorAll(".mermaid-block"));

    if (blocks.length === 0) {
        return;
    }

    let mermaid;

    try {
        mermaid = await loadMermaid();
    } catch (error) {
        blocks.forEach((block) => {
            const canvas = block.querySelector(".mermaid-canvas");
            const status = block.querySelector(".mermaid-status");

            if (status) {
                status.textContent =
                    "Mermaid не загрузился. Код можно скопировать вручную.";
            }

            if (canvas) {
                canvas.innerHTML = `
                    <div class="mermaid-error">
                        Схему не удалось построить автоматически.
                        Вероятно, нет интернета или библиотека Mermaid недоступна.
                        Ниже оставлен исходный код для ручного копирования.
                    </div>
                `;
            }
        });

        console.error("Ошибка загрузки Mermaid:", error);
        return;
    }

    for (let index = 0; index < blocks.length; index += 1) {
        const block = blocks[index];
        const source = block.querySelector(".mermaid-source");
        const preview = block.querySelector(".mermaid-preview");
        const canvas = block.querySelector(".mermaid-canvas");
        const status = block.querySelector(".mermaid-status");

        if (!source || !preview || !canvas) {
            continue;
        }

        const diagramCode = source.textContent || "";
        const diagramId = `mermaid-diagram-${Date.now()}-${index}`;

        try {
            const result = await mermaid.render(diagramId, diagramCode);

            canvas.innerHTML = result.svg;
            normalizeMermaidSvg(canvas);

            if (typeof result.bindFunctions === "function") {
                result.bindFunctions(canvas);
            }

            setupMermaidZoom(block);

            if (status) {
                status.textContent = "Схема построена";
            }
        } catch (error) {
            canvas.innerHTML = `
                <div class="mermaid-error">
                    Не удалось построить схему. Проверь исходный Mermaid-код ниже.
                </div>
            `;

            if (status) {
                status.textContent = "Ошибка построения схемы";
            }

            console.error("Ошибка Mermaid:", error);
        }
    }
}

// ================================
// Инициализация страницы отчёта
// ================================
async function initReport() {
    const out = document.getElementById("report");

    if (!out) {
        return;
    }

    const runId = localStorage.getItem("run_id");

    if (!runId) {
        out.innerHTML = `
            <div class="error">
                Нет run_id. Сначала запустите алгоритм.
            </div>
        `;
        return;
    }

    out.textContent = "Загружаю отчёт...";

    try {
        const report = await fetchReport(runId);

        const title = document.createElement("h2");
        title.textContent = report.report_name || "Отчёт";

        const body = document.createElement("div");
        body.className = "report-body";
        body.innerHTML = simpleMarkdown(report.markdown || "");

        out.innerHTML = "";
        out.appendChild(title);
        out.appendChild(body);

        setupMermaidCopyButtons(body);
        await renderMermaidBlocks(body);
    } catch (error) {
        out.innerHTML = `
            <div class="error">
                Ошибка загрузки отчёта: ${escapeHTML(error.message)}
            </div>
        `;
    }
}

// ================================
// Запуск
// ================================
initReport();
