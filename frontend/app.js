const API_BASE = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    loadStats();

    document.getElementById("search-form").addEventListener("submit", (e) => {
        e.preventDefault();
        performSearch();
    });

    document.getElementById("btn-scrape").addEventListener("click", () => {
        triggerScrape();
    });
});

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) throw new Error("API Error");
        const stats = await res.json();
        
        document.getElementById("stat-repos").textContent = stats.total_repos.toLocaleString();
        document.getElementById("stat-langs").textContent = stats.languages;
        document.getElementById("stat-max").textContent = stats.stars_max.toLocaleString();
        document.getElementById("stat-avg").textContent = Math.round(stats.stars_avg).toLocaleString();
    } catch (err) {
        console.error("No se pudo cargar estadisticas", err);
    }
}

async function performSearch() {
    const q = document.getElementById("input-q").value.trim();
    const lang = document.getElementById("input-lang").value.trim();
    const limit = document.getElementById("input-limit").value;

    if (!q) return;

    const resultsCard = document.getElementById("results-card");
    const loading = document.getElementById("loading");
    const tbody = document.getElementById("results-body");

    resultsCard.classList.add("hide");
    loading.classList.remove("hide");
    tbody.innerHTML = "";

    try {
        let url = `${API_BASE}/search?q=${encodeURIComponent(q)}&limit=${limit}`;
        if (lang) url += `&language=${encodeURIComponent(lang)}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error("API Error");
        const data = await res.json();

        data.repos.forEach(repo => {
            const tr = document.createElement("tr");
            
            const tdName = document.createElement("td");
            tdName.innerHTML = `<a href="${repo.url}" target="_blank"><strong>${repo.owner}/${repo.name}</strong></a>`;
            
            const tdStars = document.createElement("td");
            tdStars.textContent = "⭐ " + repo.stars.toLocaleString();
            
            const tdLang = document.createElement("td");
            tdLang.textContent = repo.language || "-";
            
            const tdDesc = document.createElement("td");
            tdDesc.className = "text-wrap";
            tdDesc.textContent = repo.description || "-";

            tr.appendChild(tdName);
            tr.appendChild(tdStars);
            tr.appendChild(tdLang);
            tr.appendChild(tdDesc);
            tbody.appendChild(tr);
        });

        resultsCard.classList.remove("hide");
    } catch (err) {
        alert("Error al buscar: " + err.message);
    } finally {
        loading.classList.add("hide");
    }
}

async function triggerScrape() {
    try {
        const res = await fetch(`${API_BASE}/scrape?min_stars=500`, { method: "POST" });
        if (!res.ok) throw new Error("Error en API");
        const data = await res.json();
        alert("Scraping iniciado en background: " + data.message);
    } catch(err) {
        alert("Error: " + err.message);
    }
}
