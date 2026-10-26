# Cinelog

Film keşfetme ve inceleme platformu. Kullanıcılar film arar, puanlar, inceleme yazar, izleme ve özel listeler oluşturur, diğer kullanıcıları takip eder ve akıştan aktiviteleri görür. Moderatör ve yönetici paneli ile şikayet yönetimi vardır.

Yazılım Mühendisliği dersi dönem projesi (2026/27 Güz).

## Teknolojiler
- Backend: Python, Flask
- Veritabanı: PostgreSQL
- Film verisi: TMDB API
- Arayüz: HTML, CSS, JavaScript (Jinja2 şablonları)
- Proje yönetimi: Jira (Scrum)

## Gereksinimler
- Python 3.9 veya üzeri
- PostgreSQL 15 veya üzeri
- Git
- TMDB API anahtarı (themoviedb.org'da ücretsiz hesapla alınır)

## Kurulum
1. Repoyu klonla ve klasöre gir:
   ```bash
   git clone https://github.com/feyzll0k/cinelog.git
   cd REPO
   ```
2. Sanal ortam oluştur ve etkinleştir:
   - Mac/Linux: `python3 -m venv .venv` ve `source .venv/bin/activate`
   - Windows: `python -m venv .venv` ve `.venv\Scripts\activate`
3. Bağımlılıkları kur:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. `.env.example` dosyasını `.env` olarak kopyala ve değerleri doldur:
   - Mac/Linux: `cp .env.example .env`
   - Windows: `copy .env.example .env`
5. PostgreSQL'de veritabanı oluştur ve şemayı yükle:
   ```bash
   psql -U KULLANICI -d VERITABANI -f database/schema.sql
   ```
6. Uygulamayı başlat:
   ```bash
   flask --app backend/app run --debug
   ```
7. Tarayıcıda `http://localhost:5000` adresini aç.

## Klasör yapısı
```
backend/     Flask uygulaması ve iş mantığı
frontend/    HTML şablonları (templates) ve statik dosyalar (static)
database/    schema.sql (tablolar) ve seed.sql (örnek veri)
docs/        Diyagramlar, raporlar ve API listesi
```

## Çalışma kuralları
- `main` dalı her zaman çalışır durumda olmalı. Doğrudan `main`'e yazılmaz.
- Her görev için ayrı dal açılır. Dal adı Jira görev numarasını içerir: `feature/SCRUM-12-giris-kayit`
- Commit mesajı görev numarasıyla başlar: `SCRUM-12: kayıt ve giriş eklendi`
- İş bitince Pull Request açılır, bir ekip arkadaşı bakıp birleştirir.
- `.env` dosyası ve API anahtarları repoya girmez. Yeni ayar eklenirse `.env.example` güncellenir.
- Veritabanı şeması sadece `database/schema.sql` üzerinden değişir. Şema değişikliği isteği Jira'ya yazılır.

## Ekip
| Rol | Kişi |
|---|---|
| Proje Yöneticisi / Sistem Analisti | Feyzanur Lök |
| Veritabanı Geliştiricisi | Muratcan Asarkaya |
| Backend Geliştirici A | Sidrah Süleyman  |
| Backend Geliştirici B | |
| Arayüz Tasarımcısı / Web Geliştirici | Bilal Hoser |
| Test Uzmanı | Doğukan Karakışlak |