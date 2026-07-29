const API_BASE = window.location.origin && window.location.origin.startsWith("http") 
    ? window.location.origin 
    : "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    loadStats();

    document.getElementById("search-form").addEventListener("submit", (e) => {
        e.preventDefault();
        performSearch();
    });

    document.getElementById("btn-scrape").addEventListener("click", () => {
        triggerScrape();
    });
    
    // Stats skeleton loading
    showStatsLoading();
});

// Toast System
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    // Set ARIA role based on type: alert for errors, status for info/success
    toast.setAttribute("role", type === "error" ? "alert" : "status");
    
    const icon = type === "success" ? "✅" : "❌";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    
    container.appendChild(toast);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Show skeleton state for stat cards
function showStatsLoading() {
    const statIds = ["stat-repos", "stat-langs", "stat-max", "stat-avg"];
    statIds.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.textContent === "-") {
            el.innerHTML = `<div class="skeleton sk-badge" style="height:2rem;width:80px"></div>`;
        }
    });
}

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) throw new Error("API devuelta error: " + res.status);
        const stats = await res.json();
        
        document.getElementById("stat-repos").textContent = stats.total_repos.toLocaleString();
        document.getElementById("stat-langs").textContent = stats.languages;
        document.getElementById("stat-max").textContent = stats.stars_max.toLocaleString();
        document.getElementById("stat-avg").textContent = Math.round(stats.stars_avg).toLocaleString();
    } catch (err) {
        // Clear skeletons if they exist
        const statIds = ["stat-repos", "stat-langs", "stat-max", "stat-avg"];
        statIds.forEach(id => {
            const el = document.getElementById(id);
            if (el && el.children.length > 0) el.textContent = "-";
        });
        showToast("Error al cargar estadísticas: " + err.message, "error");
        console.error("Stats Error:", err);
    }
}

async function performSearch() {
    const q = document.getElementById("input-q").value.trim();
    const lang = document.getElementById("input-lang").value.trim();
    const limit = document.getElementById("input-limit").value;

    if (!q) return;

    const resultsCard = document.getElementById("results-card");
    const skeletonLoader = document.getElementById("loading-skeleton");
    const tbody = document.getElementById("results-body");

    // UI States
    resultsCard.classList.add("hide");
    skeletonLoader.classList.remove("hide");
    tbody.innerHTML = "";

    try {
        let url = `${API_BASE}/search?q=${encodeURIComponent(q)}&limit=${limit}`;
        if (lang) url += `&language=${encodeURIComponent(lang)}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error("Error en servidor");
        const data = await res.json();

        if (data.repos.length === 0) {
            showToast("No se encontraron resultados para tu búsqueda.", "error");
            skeletonLoader.classList.add("hide");
            return;
        }

        data.repos.forEach((repo, idx) => {
            const tr = document.createElement("tr");
            tr.setAttribute("data-testid", `result-row-${idx}`);
            
            // Name & URL
            const tdName = document.createElement("td");
            tdName.innerHTML = `<a href="${repo.url}" target="_blank" data-testid="repo-link-${idx}">${repo.owner}/${repo.name}</a>`;
            
            // Stars
            const tdStars = document.createElement("td");
            tdStars.innerHTML = `<span style="color: #fbbf24; font-weight: 600;">⭐ ${repo.stars.toLocaleString()}</span>`;
            
            // Language
            const tdLang = document.createElement("td");
            tdLang.innerHTML = repo.language ? `<span class="badge">${repo.language}</span>` : "-";
            
            // Description
            const tdDesc = document.createElement("td");
            tdDesc.textContent = repo.description || "Sin descripción";
            tdDesc.style.color = "var(--text-muted)";
            tdDesc.style.lineHeight = "1.5";

            tr.appendChild(tdName);
            tr.appendChild(tdStars);
            tr.appendChild(tdLang);
            tr.appendChild(tdDesc);
            tbody.appendChild(tr);
        });

        skeletonLoader.classList.add("hide");
        resultsCard.classList.remove("hide");
        
    } catch (err) {
        skeletonLoader.classList.add("hide");
        showToast("Error al buscar: " + err.message, "error");
    }
}

async function triggerScrape() {
    const btn = document.getElementById("btn-scrape");
    const btnText = document.getElementById("btn-scrape-text");
    const btnSpinner = document.getElementById("btn-scrape-spinner");
    
    // Disable button + show spinner
    btn.disabled = true;
    btn.style.opacity = "0.7";
    btnText.classList.add("hide");
    btnSpinner.classList.remove("hide");
    btn.setAttribute("aria-busy", "true");
    
    try {
        showToast("Iniciando scraper en background...", "success");
        const res = await fetch(`${API_BASE}/scrape?min_stars=500`, { method: "POST" });
        if (!res.ok) throw new Error("La API no pudo iniciar el scraper");
        const data = await res.json();
        showToast(data.message, "success");
    } catch(err) {
        showToast(err.message, "error");
    } finally {
        // Re-enable button
        btn.disabled = false;
        btn.style.opacity = "1";
        btnText.classList.remove("hide");
        btnSpinner.classList.add("hide");
        btn.removeAttribute("aria-busy");
    }
}
