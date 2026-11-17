# CineLog — Kalite Güvence (QA), Test Planı ve Sonuç Raporu

Bu doküman CineLog projesi kapsamında belirlenen Fonksiyonel Olmayan Gereksinimleri (`SCRUM-29`), Bug İş Akışı ve Sprint 1 Test Senaryolarını (`SCRUM-23`) ve Test Yürütme Sonuçlarını (`SCRUM-32`) içermektedir.

---

## 1. Fonksiyonel Olmayan Gereksinimler (NFR) ve Kabul Kriterleri (`SCRUM-29`)

### A. Performans ve Hız
* **Sayfa ve API Yanıt Süresi:** Film listeleme, detay görüntüleme (`movies`, `movie_cast`, `genres`) ve arama sorguları normal ağ koşullarında **2 saniyenin** altında yanıt vermelidir.
* **TMDB Senkronizasyonu:** TMDB üzerinden çekilen film verilerinin (`tmdb_id`, `tmdb_synced_at`) veritabanına aktarımı sırasında kullanıcı arayüzü kilitlenmemeli, senkronizasyon arka planda veya sayfalama ile yönetilmelidir.
* **Veritabanı Sorgu Verimliliği:** Puanlama (`ratings`), inceleme (`reviews`) ve sosyal akış (`follows`) sorgularında PK/FK indeksleri kullanılarak gecikme önlenmelidir.

### B. Güvenlik ve Erişim Kontrolü
* **Parola Güvenliği:** Kullanıcı şifreleri `users.password_hash` alanında güvenli hash algoritmaları (bcrypt/Argon2) ile saklanmalıdır.
* **Rol Tabanlı Yetkilendirme (RBAC):** `users.role` ve `users.account_status` alanları doğrultusunda; aktif olmayan hesaplar işlem yapamamalı, inceleme moderasyonu (`reviews.moderated_by`) ve şikayet çözme (`reports.resolved_by`) uç noktalarına yalnızca yetkili roller erişebilmelidir.
* **Veri Doğrulama:** `username` (maks. 30 karakter), `email` (maks. 254 karakter) ve puanlama aralığı (`ratings.score`) hem frontend hem de backend tarafında doğrulanmalıdır.
* **Gizlilik Kontrolü:** Özel olarak işaretlenen kullanıcı listeleri (`user_lists.visibility`) liste sahibi dışındaki kullanıcılar tarafından görüntülenememelidir.

### C. Kullanılabilirlik
* **Spoiler Koruması:** `reviews.contains_spoiler` değeri `true` olan incelemeler arayüzde varsayılan olarak gizli/bulanık gösterilmelidir.
* **Tutarlı Hata Mesajları:** Geçersiz giriş veya mükerrer kayıt durumlarında anlaşılır bilgilendirme mesajları gösterilmelidir.
* **Çoklu Cihaz Uyumluluğu:** Tüm ekranlar masaüstü ve mobil tarayıcılarda tasarım bozulması olmadan çalışmalıdır.

### D. Genel Kabul Kriterleri (Definition of Done)
1. Özelliğe ait tüm fonksiyonel gereksinimler eksiksiz çalışıyor olmalıdır.
2. Yapılan işlemler veritabanındaki ilgili tablolara (`NOT NULL` ve FK kısıtlamalarına uygun şekilde) hatasız kaydedilmelidir.
3. Tarayıcı konsolunda ve backend loglarında kritik (`500 Internal Server Error` vb.) hata bulunmamalıdır.
4. İlgili test senaryoları başarıyla geçmiş ve açıkta `Critical` veya `High` seviyesinde hata kalmamış olmalıdır.
5. Kodlar/dokümanlar feature dalından Pull Request açılarak `main` dalına birleştirilmiş olmalıdır.

---

## 2. Bug İş Akışı, Etiketleme ve Sprint 1 Test Senaryoları (`SCRUM-23`)

### A. Bug Yaşam Döngüsü
1. **Yapılacaklar (To Do):** Test uzmanı hatayı tekrar edilebilir adımlarla Jira'da `Bug` türünde açar ve ilgili geliştiriciye atar.
2. **Devam Ediyor (In Progress):** Geliştirici hatayı inceler ve ilgili branch üzerinde düzeltmeye başlar.
3. **İncelemede (In Review):** Geliştirici düzeltmeyi tamamladığında bileti tekrar Test Uzmanına atar.
4. **Tamamlandı (Done) / Yeniden Açıldı:** Hata çözülmüşse kapatılır; devam ediyorsa ekran görüntüsü eklenerek tekrar açılır.

### B. Öncelik Seviyeleri ve Modül Etiketleri
* **Öncelikler:** `Highest (Blocker)`, `High (Critical)`, `Medium (Major)`, `Low (Minor)`
* **Etiketler:** `module-auth`, `module-movies-tmdb`, `module-reviews-ratings`, `module-lists-social`, `frontend`, `backend`, `database`
* **Zorunlu Kayıt Formatı:** Özet Başlık, Ön Koşul, Adım Adım Tekrar Etme, Beklenen Sonuç, Gerçekleşen Sonuç + Ekran Görüntüsü/Log.

---

## 3. Test Yürütme Tablosu ve Mevcut Durum (`SCRUM-32`)

| Test ID | İlgili Görev / Modül | Test Senaryosu | Test Katmanı | Beklenen Sonuç | Gerçekleşen Durum | Statü |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `SCRUM-5` / Veritabanı | Tablo şemaları, PK/FK ilişkileri ve `NOT NULL` kısıtlamalarının doğrulanması | Database | Tüm tablolar (`users`, `movies`, `ratings`, `reviews`, `user_lists`, `reports`) şemaya uygun oluşturulmalı. | Veritabanı şeması ve bağlantı havuzu (`db.py`) hatasız doğrulandı. | **PASS** |
| **TC-02** | `SCRUM-5` / TMDB Sync | TMDB API üzerinden film, tür ve oyuncu verilerinin senkronize edilmesi | Backend / Script | Film verileri `tmdb_id` ile çekilip `movies`, `genres`, `actors` tablolarına kaydedilmeli. | Senkronizasyon betikleri ve veritabanı eşleşmesi başarıyla çalıştı. | **PASS** |
| **TC-03** | `SCRUM-20` / Film Rotaları | Film listeleme, arama ve detay uç noktalarının (`routes`) yanıt kontrolü | Backend API | Geçerli film ID veya arama sorgusunda HTTP 200 ve eksiksiz JSON verisi dönmeli. | Film rotaları beklenen JSON yapısını ve HTTP 200 yanıtını döndürdü. | **PASS** |
| **TC-04** | `SCRUM-21` / Puanlama | Kullanıcının bir filme puan (`ratings.score`) vermesi ve mevcut puanını güncellemesi | Backend API | Yeni puan eklenmeli; aynı kullanıcı tekrar puan verdiğinde güncelleme yapılmalı. | Puan ekleme ve güncelleme uç noktaları veri bütünlüğünü koruyarak çalıştı. | **PASS** |
| **TC-05** | `SCRUM-21` / İnceleme | Spoiler bayrağı (`contains_spoiler`) ile film incelemesi (`reviews`) oluşturulması | Backend API | İnceleme metni (`body`) ve spoiler durumu `reviews` tablosuna doğru kaydedilmeli. | İnceleme kaydı ve `contains_spoiler` alanı veritabanına doğru işlendi. | **PASS** |
| **TC-06** | `SCRUM-21` / Listeler | İzleme listesi (`watchlist`) ve özel kullanıcı listesi (`user_lists`) işlemleri | Backend API | Kullanıcı listeye film ekleyebilmeli ve `visibility` ayarı saklanabilmeli. | Liste oluşturma ve öğe ekleme uç noktaları beklenen şekilde çalıştı. | **PASS** |
| **TC-07** | Auth / Güvenlik | Geçersiz veri, eksik zorunlu alan ve yetkisiz erişim denemeleri | Backend API | Hatalı isteklerde sistem çökmeden HTTP 400/401/403 durum kodları dönmeli. | Hata yakalama ve doğrulama kontrolleri başarıyla doğrulandı. | **PASS** |
| **TC-08** | Frontend Entegrasyonu | Kullanıcı arayüzü üzerinden kayıt, giriş, film puanlama ve spoiler gizleme akışı | End-to-End (UI) | Arayüz ekranları backend API'leri ile uçtan uca hatasız haberleşmeli. | `frontend` geliştirme süreci devam ettiği için arayüz testleri sıradaki sprinte planlandı. | **PENDING** |

### Açık Hata (Bug) Kapatma Özeti
Mevcut sprint kapsamında Jira panosunda açıkta bekleyen bir `Bug` kaydı bulunmamaktadır. Frontend geliştirmeleri tamamlandığında `TC-08` ve devamındaki uçtan uca arayüz testleri yürütülecektir.
