const state = {
    user: null,
    discoverMode: "popular", // "popular" | "top-rated" | "search"
    searchQuery: "",
    page: 1,
    totalPages: 1,
    currentMovie: null,
    myLists: [],
};

// --- Helpers ---
async function api(url, options = {}) {
    const opts = {
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        ...options,
    };
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.error || `Hata (${res.status})`);
    }
    return data;
}

function toast(message, isError = false) {
    const container = document.getElementById("toast-container");
    const el = document.createElement("div");
    el.className = `toast${isError ? " error" : ""}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 3200);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

function formatDate(iso) {
    if (!iso) return "";
    return String(iso).slice(0, 10);
}

// --- Navigation & Views ---
function switchView(viewId) {
    document.querySelectorAll(".view-section").forEach((s) => s.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));

    const target = document.getElementById(`view-${viewId}`);
    if (target) target.classList.add("active");

    const navBtn = document.querySelector(`.nav-btn[data-view="${viewId}"]`);
    if (navBtn) navBtn.classList.add("active");

    if (viewId === "discover") loadDiscoverMovies();
    if (viewId === "feed") loadFeed();
    if (viewId === "lists") loadListsView();
    if (viewId === "profile") loadProfileView();
}

// --- Auth ---
async function checkSession() {
    try {
        const data = await api("/api/auth/profile");
        state.user = data.user;
    } catch {
        state.user = null;
    }
    renderAuthHeader();
}

function renderAuthHeader() {
    const area = document.getElementById("auth-area");
    if (state.user) {
        area.innerHTML = `
            <span class="user-pill">@${escapeHtml(state.user.username)}</span>
            <button class="btn-secondary" onclick="logout()">Çıkış</button>
        `;
    } else {
        area.innerHTML = `
            <button class="btn-primary" onclick="openAuthModal('login')">Giriş Yap</button>
        `;
    }
}

function openAuthModal(tab = "login") {
    document.getElementById("auth-modal").classList.add("open");
    switchAuthTab(tab);
}

function closeAuthModal() {
    document.getElementById("auth-modal").classList.remove("open");
}

function switchAuthTab(tab) {
    document.getElementById("tab-login").classList.toggle("active", tab === "login");
    document.getElementById("tab-register").classList.toggle("active", tab === "register");
    document.getElementById("login-form").style.display = tab === "login" ? "block" : "none";
    document.getElementById("register-form").style.display = tab === "register" ? "block" : "none";
}

async function handleLogin(e) {
    e.preventDefault();
    const identifier = document.getElementById("login-identifier").value.trim();
    const password = document.getElementById("login-password").value;
    try {
        const data = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ identifier, password }),
        });
        state.user = data.user;
        renderAuthHeader();
        closeAuthModal();
        toast(`Hoş geldin, @${data.user.username}`);
        loadDiscoverMovies();
    } catch (err) {
        toast(err.message, true);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById("reg-username").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;
    try {
        await api("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({ username, email, password }),
        });
        toast("Hesap oluşturuldu! Şimdi giriş yapabilirsiniz.");
        switchAuthTab("login");
        document.getElementById("login-identifier").value = username;
    } catch (err) {
        toast(err.message, true);
    }
}

async function logout() {
    try {
        await api("/api/auth/logout", { method: "POST" });
        state.user = null;
        renderAuthHeader();
        toast("Çıkış yapıldı.");
        switchView("discover");
    } catch (err) {
        toast(err.message, true);
    }
}

// --- Discover / Search ---
function setDiscoverMode(mode) {
    state.discoverMode = mode;
    state.page = 1;
    document.querySelectorAll("#discover-tabs .seg-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.mode === mode);
    });
    loadDiscoverMovies();
}

function handleSearch(e) {
    if (e) e.preventDefault();
    const q = document.getElementById("global-search-input").value.trim();
    if (!q) {
        setDiscoverMode("popular");
        switchView("discover");
        return;
    }
    state.searchQuery = q;
    state.discoverMode = "search";
    state.page = 1;
    document.querySelectorAll("#discover-tabs .seg-btn").forEach((b) => b.classList.remove("active"));
    switchView("discover");
}

async function loadDiscoverMovies() {
    const grid = document.getElementById("discover-grid");
    const subtitle = document.getElementById("discover-subtitle");
    grid.innerHTML = `<div class="empty-state">Yükleniyor...</div>`;

    let url = `/api/movies/popular?page=${state.page}`;
    subtitle.textContent = "TMDB üzerinde şu an en çok ilgi gören filmler";

    if (state.discoverMode === "top-rated") {
        url = `/api/movies/top-rated?page=${state.page}`;
        subtitle.textContent = "Tüm zamanların en yüksek puanlı yapımları";
    } else if (state.discoverMode === "search") {
        url = `/api/movies/search?q=${encodeURIComponent(state.searchQuery)}&page=${state.page}`;
        subtitle.textContent = `"${state.searchQuery}" için arama sonuçları`;
    }

    try {
        const data = await api(url);
        state.totalPages = data.total_pages || 1;
        renderMovieGrid(grid, data.results || []);
        document.getElementById("page-indicator").textContent = `Sayfa ${data.page || 1} / ${state.totalPages}`;
        document.getElementById("prev-page-btn").disabled = state.page <= 1;
        document.getElementById("next-page-btn").disabled = state.page >= state.totalPages;
    } catch (err) {
        grid.innerHTML = `<div class="empty-state"><h3>Bir hata oluştu</h3><p>${escapeHtml(err.message)}</p></div>`;
    }
}

function changePage(delta) {
    const next = state.page + delta;
    if (next < 1 || next > state.totalPages) return;
    state.page = next;
    loadDiscoverMovies();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderMovieGrid(container, movies) {
    if (!movies.length) {
        container.innerHTML = `<div class="empty-state"><h3>Sonuç bulunamadı</h3><p>Başka bir film adı deneyin.</p></div>`;
        return;
    }
    container.innerHTML = movies
        .map((m) => {
            const year = m.release_date ? String(m.release_date).slice(0, 4) : "—";
            const vote = m.tmdb_vote_average ? Number(m.tmdb_vote_average).toFixed(1) : "—";
            const poster = m.poster_url
                ? `<img src="${escapeHtml(m.poster_url)}" alt="${escapeHtml(m.title)}" loading="lazy">`
                : `<div class="poster-placeholder">${escapeHtml(m.title)}</div>`;
            return `
                <article class="movie-card" onclick="openMovieDetail(${m.tmdb_id})">
                    <div class="poster-wrap">
                        ${poster}
                        <span class="rating-badge">★ ${vote}</span>
                    </div>
                    <div class="movie-meta">
                        <div class="movie-title">${escapeHtml(m.title)}</div>
                        <div class="movie-year">${year}</div>
                    </div>
                </article>
            `;
        })
        .join("");
}

// --- Movie Detail Modal ---
async function openMovieDetail(tmdbId) {
    const modal = document.getElementById("detail-modal");
    const body = document.getElementById("detail-modal-body");
    modal.classList.add("open");
    body.innerHTML = `<div class="empty-state">Film bilgileri yükleniyor...</div>`;

    try {
        const [movieRes, reviewsRes] = await Promise.all([
            api(`/api/movies/${tmdbId}`),
            api(`/api/movies/${tmdbId}/reviews`),
        ]);
        const m = movieRes.movie;
        state.currentMovie = m;

        if (state.user) {
            try {
                const listsData = await api("/api/lists");
                state.myLists = listsData.lists || [];
            } catch {
                state.myLists = [];
            }
        }

        renderMovieDetail(m, reviewsRes.reviews || []);
    } catch (err) {
        body.innerHTML = `<div class="empty-state"><h3>Yüklenemedi</h3><p>${escapeHtml(err.message)}</p></div>`;
    }
}

function closeDetailModal() {
    document.getElementById("detail-modal").classList.remove("open");
}

function renderMovieDetail(m, reviews) {
    const body = document.getElementById("detail-modal-body");
    const year = m.release_date ? String(m.release_date).slice(0, 4) : "—";
    const runtime = m.runtime_minutes ? `${m.runtime_minutes} dk` : "Süre belirtilmemiş";
    const localAvg = m.average_score !== null && m.average_score !== undefined ? Number(m.average_score).toFixed(1) : "—";
    const tmdbAvg = m.tmdb_vote_average !== null && m.tmdb_vote_average !== undefined ? Number(m.tmdb_vote_average).toFixed(1) : "—";

    const genresHtml = (m.genres || [])
        .map((g) => `<span class="pill">${escapeHtml(g.name)}</span>`)
        .join("");

    const castHtml = (m.cast || []).length
        ? `<div class="cast-strip">
            ${m.cast
                .map(
                    (c) => `
                <div class="cast-item">
                    <img src="${escapeHtml(c.profile_url || "")}" onerror="this.style.opacity='0.2'" alt="${escapeHtml(c.name)}">
                    <div>${escapeHtml(c.name)}</div>
                    <div class="cast-char">${escapeHtml(c.character_name || "")}</div>
                </div>`
                )
                .join("")}
           </div>`
        : `<p style="color:var(--text-muted); font-size:0.86rem; margin-bottom:1.25rem;">Oyuncu bilgisi bulunamadı.</p>`;

    const ratingButtons = Array.from({ length: 10 }, (_, idx) => {
        const val = idx + 1;
        const selected = m.user_rating === val ? "selected" : "";
        return `<button class="rate-num ${selected}" onclick="rateMovie(${m.tmdb_id}, ${val})">${val}</button>`;
    }).join("");

    const listOptions = state.myLists
        .map((l) => `<option value="${l.list_id}">${escapeHtml(l.name)}</option>`)
        .join("");

    const userActions = state.user
        ? `
        <div style="margin: 1.25rem 0; display:flex; flex-direction:column; gap:1rem;">
            <div>
                <div style="font-size:0.82rem; color:var(--text-muted);">Puanın (1-10):</div>
                <div class="rating-bar">
                    ${ratingButtons}
                    ${m.user_rating ? `<button class="btn-danger" style="margin-left:0.4rem;" onclick="deleteRating(${m.tmdb_id})">Sil</button>` : ""}
                </div>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:0.6rem; align-items:center;">
                <button class="${m.in_watchlist ? "btn-primary" : "btn-secondary"}" onclick="toggleWatchlist(${m.tmdb_id}, ${Boolean(m.in_watchlist)})">
                    ${m.in_watchlist ? "✓ İzleme Listemde" : "+ İzleme Listeme Ekle"}
                </button>
                ${
                    state.myLists.length
                        ? `<div style="display:flex; gap:0.4rem; align-items:center;">
                            <select id="add-to-list-select">${listOptions}</select>
                            <button class="btn-secondary" onclick="addMovieToSelectedList(${m.tmdb_id})">Listeye Ekle</button>
                           </div>`
                        : ""
                }
            </div>
        </div>
        `
        : `<p style="margin:1rem 0; color:var(--text-muted); font-size:0.88rem;">Puan vermek, listeye eklemek ve inceleme yazmak için <a style="color:var(--accent); text-decoration:underline; cursor:pointer;" onclick="closeDetailModal(); openAuthModal('login')">giriş yapın</a>.</p>`;

    const reviewForm = state.user
        ? `
        <form onsubmit="submitReview(event, ${m.tmdb_id})" class="panel" style="margin-bottom:1.25rem;">
            <div class="form-group">
                <label>İnceleme Yaz</label>
                <textarea id="review-body-input" rows="3" placeholder="Film hakkındaki düşüncelerin..."></textarea>
            </div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:1rem;">
                <label style="display:flex; align-items:center; gap:0.45rem; font-size:0.84rem; color:var(--text-muted); cursor:pointer;">
                    <input type="checkbox" id="review-spoiler-input" style="width:auto;"> Spoiler içerir
                </label>
                <button type="submit" class="btn-primary">Yayınla</button>
            </div>
        </form>
        `
        : "";

    const reviewsHtml = reviews.length
        ? reviews
              .map((r) => {
                  const isMine = state.user && state.user.user_id === r.user_id;
                  const followBtn =
                      state.user && !isMine
                          ? `<button class="pill pear" style="cursor:pointer;" onclick="followUser(${r.user_id})">+ Takip Et</button>`
                          : "";
                  const deleteBtn = isMine
                      ? `<button class="btn-danger" onclick="deleteReview(${r.review_id}, ${m.tmdb_id})">Sil</button>`
                      : "";
                  const scoreBadge = r.user_score ? `<span class="pill pear">★ ${r.user_score}/10</span>` : "";
                  return `
                    <div class="review-card">
                        <div class="review-header">
                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                <strong>@${escapeHtml(r.username)}</strong>
                                ${scoreBadge}
                                ${followBtn}
                            </div>
                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                <span style="color:var(--text-muted); font-size:0.76rem;">${formatDate(r.created_at)}</span>
                                ${deleteBtn}
                            </div>
                        </div>
                        ${
                            r.contains_spoiler
                                ? `<div style="font-size:0.75rem; color:var(--danger); margin-bottom:0.35rem;">⚠ Spoiler uyarısı (görmek için tıkla)</div>
                                   <p class="spoiler-blur" onclick="this.classList.toggle('revealed')">${escapeHtml(r.body)}</p>`
                                : `<p>${escapeHtml(r.body)}</p>`
                        }
                    </div>
                  `;
              })
              .join("")
        : `<p style="color:var(--text-muted); font-size:0.88rem;">Henüz inceleme yazılmamış.</p>`;

    body.innerHTML = `
        <div class="detail-hero">
            <img class="detail-poster" src="${escapeHtml(m.poster_url || "")}" alt="${escapeHtml(m.title)}">
            <div>
                <h2 class="detail-title">${escapeHtml(m.title)}</h2>
                <div class="detail-sub">${escapeHtml(m.original_title || "")} · ${year} · ${runtime}</div>
                <div class="genre-tags">${genresHtml}</div>
                <div class="score-strip">
                    <div class="score-box">
                        <span>CineLog Puanı</span>
                        <strong>${localAvg} <small style="font-size:0.72rem; color:var(--text-muted);">(${m.rating_count || 0} oy)</small></strong>
                    </div>
                    <div class="score-box">
                        <span>TMDB Puanı</span>
                        <strong>★ ${tmdbAvg}</strong>
                    </div>
                </div>
                <p style="font-size:0.92rem; color:var(--text); opacity:0.9;">${escapeHtml(m.overview || "Özet bulunmuyor.")}</p>
                ${userActions}
            </div>
        </div>
        <h3 style="margin-bottom:0.75rem; font-size:1.05rem;">Oyuncu Kadrosu</h3>
        ${castHtml}
        <h3 style="margin-bottom:0.75rem; font-size:1.05rem;">İncelemeler (${reviews.length})</h3>
        ${reviewForm}
        ${reviewsHtml}
    `;
}

async function rateMovie(tmdbId, score) {
    try {
        await api(`/api/movies/${tmdbId}/rating`, {
            method: "PUT",
            body: JSON.stringify({ score }),
        });
        toast(`Puanınız kaydedildi: ${score}/10`);
        openMovieDetail(tmdbId);
    } catch (err) {
        toast(err.message, true);
    }
}

async function deleteRating(tmdbId) {
    try {
        await api(`/api/movies/${tmdbId}/rating`, { method: "DELETE" });
        toast("Puanınız silindi.");
        openMovieDetail(tmdbId);
    } catch (err) {
        toast(err.message, true);
    }
}

async function toggleWatchlist(tmdbId, currentlyIn) {
    try {
        await api(`/api/watchlist/${tmdbId}`, { method: currentlyIn ? "DELETE" : "POST" });
        toast(currentlyIn ? "İzleme listesinden çıkarıldı." : "İzleme listesine eklendi.");
        openMovieDetail(tmdbId);
    } catch (err) {
        toast(err.message, true);
    }
}

async function addMovieToSelectedList(tmdbId) {
    const select = document.getElementById("add-to-list-select");
    if (!select || !select.value) return;
    try {
        await api(`/api/lists/${select.value}/movies`, {
            method: "POST",
            body: JSON.stringify({ tmdb_id: tmdbId }),
        });
        toast("Film listeye eklendi.");
    } catch (err) {
        toast(err.message, true);
    }
}

async function submitReview(e, tmdbId) {
    e.preventDefault();
    const body = document.getElementById("review-body-input").value.trim();
    const contains_spoiler = document.getElementById("review-spoiler-input").checked;
    if (!body) {
        toast("İnceleme metni boş olamaz.", true);
        return;
    }
    try {
        await api(`/api/movies/${tmdbId}/reviews`, {
            method: "POST",
            body: JSON.stringify({ body, contains_spoiler }),
        });
        toast("İncelemeniz yayınlandı!");
        openMovieDetail(tmdbId);
    } catch (err) {
        toast(err.message, true);
    }
}

async function deleteReview(reviewId, tmdbId) {
    try {
        await api(`/api/reviews/${reviewId}`, { method: "DELETE" });
        toast("İnceleme silindi.");
        openMovieDetail(tmdbId);
    } catch (err) {
        toast(err.message, true);
    }
}

async function followUser(userId) {
    try {
        await api(`/api/social/follow/${userId}`, { method: "POST" });
        toast("Kullanıcı takip edildi.");
    } catch (err) {
        toast(err.message, true);
    }
}

// --- Lists & Watchlist View ---
async function loadListsView() {
    const container = document.getElementById("lists-content");
    if (!state.user) {
        container.innerHTML = `<div class="empty-state"><h3>Giriş Gerekli</h3><p>İzleme listenizi ve özel listelerinizi görmek için giriş yapın.</p></div>`;
        return;
    }
    container.innerHTML = `<div class="empty-state">Yükleniyor...</div>`;
    try {
        const [wlRes, listsRes] = await Promise.all([api("/api/watchlist"), api("/api/lists")]);
        const wl = wlRes.watchlist || [];
        const lists = listsRes.lists || [];

        const wlHtml = wl.length
            ? `<div class="movie-grid">${wl
                  .map(
                      (m) => `
                    <article class="movie-card" onclick="openMovieDetail(${m.tmdb_id})">
                        <div class="poster-wrap">
                            ${m.poster_url ? `<img src="${escapeHtml(m.poster_url)}" alt="${escapeHtml(m.title)}">` : `<div class="poster-placeholder">${escapeHtml(m.title)}</div>`}
                        </div>
                        <div class="movie-meta">
                            <div class="movie-title">${escapeHtml(m.title)}</div>
                            <div class="movie-year">${formatDate(m.release_date).slice(0, 4) || "—"}</div>
                        </div>
                    </article>`
                  )
                  .join("")}</div>`
            : `<div class="empty-state">İzleme listeniz henüz boş.</div>`;

        const listsHtml = lists.length
            ? `<div class="lists-grid">${lists
                  .map(
                      (l) => `
                    <div class="list-card" onclick="openListDetailModal(${l.list_id})">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong style="color:var(--white);">${escapeHtml(l.name)}</strong>
                            <span class="pill ${l.visibility === "public" ? "pear" : ""}">${l.visibility === "public" ? "Herkese Açık" : "Özel"}</span>
                        </div>
                        <p style="font-size:0.84rem; color:var(--text-muted);">${escapeHtml(l.description || "Açıklama yok.")}</p>
                        <div style="font-size:0.78rem; color:var(--accent); margin-top:auto;">${l.movie_count} film</div>
                    </div>`
                  )
                  .join("")}</div>`
            : `<div class="empty-state">Henüz özel liste oluşturmadınız.</div>`;

        container.innerHTML = `
            <div style="margin-bottom:2.5rem;">
                <h3 style="margin-bottom:1rem; font-size:1.15rem;">İzleme Listem (${wl.length})</h3>
                ${wlHtml}
            </div>
            <div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                    <h3 style="font-size:1.15rem;">Özel Listelerim (${lists.length})</h3>
                </div>
                ${listsHtml}
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><h3>Hata</h3><p>${escapeHtml(err.message)}</p></div>`;
    }
}

async function createCustomList(e) {
    e.preventDefault();
    if (!state.user) {
        openAuthModal("login");
        return;
    }
    const name = document.getElementById("new-list-name").value.trim();
    const description = document.getElementById("new-list-desc").value.trim();
    const visibility = document.getElementById("new-list-visibility").value;
    try {
        await api("/api/lists", {
            method: "POST",
            body: JSON.stringify({ name, description, visibility }),
        });
        toast("Liste oluşturuldu.");
        document.getElementById("new-list-form").reset();
        loadListsView();
    } catch (err) {
        toast(err.message, true);
    }
}

async function openListDetailModal(listId) {
    const modal = document.getElementById("detail-modal");
    const body = document.getElementById("detail-modal-body");
    modal.classList.add("open");
    body.innerHTML = `<div class="empty-state">Liste yükleniyor...</div>`;
    try {
        const data = await api(`/api/lists/${listId}`);
        const l = data.list;
        const moviesHtml = (l.movies || []).length
            ? `<div class="movie-grid">${l.movies
                  .map(
                      (m) => `
                    <article class="movie-card" onclick="openMovieDetail(${m.tmdb_id})">
                        <div class="poster-wrap">
                            ${m.poster_url ? `<img src="${escapeHtml(m.poster_url)}" alt="${escapeHtml(m.title)}">` : `<div class="poster-placeholder">${escapeHtml(m.title)}</div>`}
                        </div>
                        <div class="movie-meta">
                            <div class="movie-title">${escapeHtml(m.title)}</div>
                            <button class="btn-danger" style="margin-top:0.4rem;" onclick="event.stopPropagation(); removeFromCustomList(${l.list_id}, ${m.tmdb_id})">Listeden Çıkar</button>
                        </div>
                    </article>`
                  )
                  .join("")}</div>`
            : `<div class="empty-state">Bu listede henüz film yok.</div>`;

        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; margin-bottom:1.5rem; padding-right:2.5rem;">
                <div>
                    <h2 style="font-size:1.5rem; color:var(--white);">${escapeHtml(l.name)}</h2>
                    <p style="color:var(--text-muted); font-size:0.9rem;">${escapeHtml(l.description || "")}</p>
                </div>
                <button class="btn-danger" onclick="deleteCustomList(${l.list_id})">Listeyi Sil</button>
            </div>
            ${moviesHtml}
        `;
    } catch (err) {
        body.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
    }
}

async function removeFromCustomList(listId, tmdbId) {
    try {
        await api(`/api/lists/${listId}/movies/${tmdbId}`, { method: "DELETE" });
        toast("Film listeden çıkarıldı.");
        openListDetailModal(listId);
    } catch (err) {
        toast(err.message, true);
    }
}

async function deleteCustomList(listId) {
    try {
        await api(`/api/lists/${listId}`, { method: "DELETE" });
        toast("Liste silindi.");
        closeDetailModal();
        loadListsView();
    } catch (err) {
        toast(err.message, true);
    }
}

// --- Social Feed View ---
async function loadFeed() {
    const container = document.getElementById("feed-content");
    if (!state.user) {
        container.innerHTML = `<div class="empty-state"><h3>Giriş Gerekli</h3><p>Takip ettiğiniz kişilerin aktivitelerini görmek için giriş yapın.</p></div>`;
        return;
    }
    container.innerHTML = `<div class="empty-state">Akış yükleniyor...</div>`;
    try {
        const data = await api("/api/social/feed");
        const events = data.feed || [];
        if (!events.length) {
            container.innerHTML = `<div class="empty-state"><h3>Akışınız henüz sakin</h3><p>Film detaylarındaki inceleme yazarlarını takip ederek aktivitelerini burada görebilirsiniz.</p></div>`;
            return;
        }
        const labels = {
            movie_rated: "filme puan verdi",
            review_written: "film için inceleme yazdı",
            list_created: "yeni bir liste oluşturdu",
            movie_added_to_list: "listeye film ekledi",
            user_followed: "bir kullanıcıyı takip etti",
        };
        container.innerHTML = `<div class="feed-list">${events
            .map((ev) => {
                const actionText = labels[ev.event_type] || ev.event_type;
                const extra =
                    ev.event_type === "movie_rated" && ev.score
                        ? `<span class="pill pear">★ ${ev.score}/10</span>`
                        : ev.list_name
                        ? `<span class="pill">${escapeHtml(ev.list_name)}</span>`
                        : "";
                const poster = ev.movie_poster_url
                    ? `<img class="feed-poster" src="${escapeHtml(ev.movie_poster_url)}" alt="">`
                    : "";
                const clickAttr = ev.movie_tmdb_id ? `onclick="openMovieDetail(${ev.movie_tmdb_id})" style="cursor:pointer;"` : "";
                return `
                    <div class="feed-item" ${clickAttr}>
                        <div class="feed-left">
                            ${poster}
                            <div>
                                <div><strong>@${escapeHtml(ev.actor_username)}</strong> ${actionText} ${ev.movie_title ? `— <strong>${escapeHtml(ev.movie_title)}</strong>` : ""}</div>
                                <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.2rem;">${formatDate(ev.occurred_at)}</div>
                            </div>
                        </div>
                        ${extra}
                    </div>
                `;
            })
            .join("")}</div>`;
    } catch (err) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
    }
}

// --- Profile View ---
async function loadProfileView() {
    const container = document.getElementById("profile-content");
    if (!state.user) {
        container.innerHTML = `<div class="empty-state"><h3>Giriş Gerekli</h3><p>Profilinizi görüntülemek için giriş yapın.</p></div>`;
        return;
    }
    container.innerHTML = `<div class="empty-state">Profil yükleniyor...</div>`;
    try {
        const profRes = await api("/api/auth/profile");
        const u = profRes.user;
        state.user = u;
        const [followersRes, followingRes] = await Promise.all([
            api(`/api/social/users/${u.user_id}/followers`),
            api(`/api/social/users/${u.user_id}/following`),
        ]);
        const followers = followersRes.followers || [];
        const following = followingRes.following || [];

        container.innerHTML = `
            <div class="panel" style="max-width:640px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1rem; margin-bottom:1.5rem;">
                    <div>
                        <h3 style="font-size:1.35rem; color:var(--white);">@${escapeHtml(u.username)}</h3>
                        <p style="color:var(--text-muted); font-size:0.88rem;">${escapeHtml(u.email)} · <span class="pill pear">${escapeHtml(u.role)}</span></p>
                    </div>
                    <div style="display:flex; gap:1rem;">
                        <div class="score-box"><span>Takipçi</span><strong>${followers.length}</strong></div>
                        <div class="score-box"><span>Takip</span><strong>${following.length}</strong></div>
                    </div>
                </div>
                <form onsubmit="updateProfile(event)">
                    <div class="form-group">
                        <label>Görünen Ad</label>
                        <input type="text" id="prof-display-name" value="${escapeHtml(u.display_name || "")}" placeholder="Adınız Soyadınız">
                    </div>
                    <div class="form-group">
                        <label>Biyografi</label>
                        <textarea id="prof-bio" rows="3" placeholder="Sinema zevkinizden bahsedin...">${escapeHtml(u.bio || "")}</textarea>
                    </div>
                    <button type="submit" class="btn-primary">Profili Güncelle</button>
                </form>
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
    }
}

async function updateProfile(e) {
    e.preventDefault();
    const display_name = document.getElementById("prof-display-name").value.trim();
    const bio = document.getElementById("prof-bio").value.trim();
    try {
        const data = await api("/api/auth/profile", {
            method: "PUT",
            body: JSON.stringify({ display_name, bio }),
        });
        state.user = data.user;
        toast("Profil güncellendi.");
    } catch (err) {
        toast(err.message, true);
    }
}

// --- Boot ---
document.addEventListener("DOMContentLoaded", async () => {
    await checkSession();
    loadDiscoverMovies();
});
