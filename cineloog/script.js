//// --- CINE LOG: Dinamik JavaScript Altyapısı ---

// 1. Ekran Geçiş Yönetimi (Tab & Navigation)
function showScreen(screenId) {
    // Tüm ekranları gizle
    const screens = document.querySelectorAll('.screen-container');
    screens.forEach(el => {
        el.classList.remove('active');
    });

    // Tüm sekmelerin aktifliğini kaldır
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Hedef ekranı göster
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.classList.add('active');
    }
    
    // Üst test sekmelerini senkronize et
    tabs.forEach(btn => {
        const onclickAttr = btn.getAttribute('onclick');
        if (onclickAttr && onclickAttr.includes(screenId)) {
            btn.classList.add('active');
        }
    });

    // Sayfanın en üstüne yumuşak kaydırma
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 2. Dinamik Film Arama ve "Sonuç Bulunamadı" Kontrolü
function handleSearch(event) {
    if (event.key === 'Enter') {
        const query = event.target.value.trim().toLowerCase();
        if (query !== '') {
            // Arama sonuçları ekranına geçiş yap
            showScreen('screen-search');
            
            const searchHeading = document.querySelector('#screen-search h2');
            const movieGrid = document.querySelector('.movie-grid');
            
            // Simülasyon veritabanımızdaki örnek filmler
            const availableMovies = ['interstellar', 'inception', 'the martian'];
            
            // Aranan film listede var mı diye bakıyoruz
            const isFound = availableMovies.some(movie => movie.includes(query));
            
            if (isFound) {
                // Film bulunduysa normal grid listesini göster
                searchHeading.innerText = `"${event.target.value.trim()}" Arama Sonuçları`;
                movieGrid.style.display = 'grid';
                movieGrid.innerHTML = `
                    <div class="movie-card" onclick="showScreen('screen-detail')">
                        <div class="movie-poster">${event.target.value.trim()} Afis</div>
                        <div class="movie-info">
                            <div class="movie-title">${event.target.value.trim()}</div>
                            <div class="movie-year">2024 • Sci-Fi / Drama</div>
                        </div>
                    </div>
                `;
            } else {
                // SONUÇ BULUNAMADI DURUMU (Empty / Error State)
                searchHeading.innerText = `"${event.target.value.trim()}" için sonuç bulunamadı.`;
                movieGrid.style.display = 'block';
                movieGrid.innerHTML = `
                    <div style="text-align: center; padding: 3rem; color: var(--text-muted); background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                        <p style="font-size: 1.2rem; margin-bottom: 0.5rem;">🎬 Aradığınız kriterlere uygun film bulunamadı.</p>
                        <p style="font-size: 0.9rem;">Lütfen farklı bir anahtar kelime (Örn: Interstellar, Inception) deneyin.</p>
                    </div>
                `;
            }
        }
    }
}

// 3. Sayfa Yüklendiğinde Olay Dinleyicilerini Bağlama
document.addEventListener('DOMContentLoaded', () => {
    // Arama çubuğuna Enter tuşu dinleyicisi ekle
    const searchInput = document.querySelector('.search-bar');
    if (searchInput) {
        searchInput.addEventListener('keydown', handleSearch);
    }

    // Yıldız puanlama sistemine etkileşim ekle
    const stars = document.querySelectorAll('.stars');
    stars.forEach(starBox => {
        starBox.addEventListener('click', () => {
            starBox.innerText = '⭐⭐⭐⭐⭐';
            alert('Puanınız başarıyla kaydedildi! ⭐ 5/5');
        });
    });
});
    
