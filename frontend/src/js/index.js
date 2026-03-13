const MODE = window.APP_MODE || "real";
const API_BASE = window.API_BASE || "/api";

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${url}`);
  return await r.json();
}

async function fetchAlgorithms() {
  if (MODE === "mock") {
    return await getJSON("./mocks/algorithms.json");
  }
  return await getJSON(`${API_BASE}/algorithms`);
}

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

initIndex();
