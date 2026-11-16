"""
Tüm Backend API Rotalarını UI Olmadan Test Etme Scripti

Kullanım (sanal ortam aktifken):
    python scripts/test_api.py

Not: Flask'ın yerleşik test_client() özelliğini kullanır, ayrı bir sunucu
başlatmanıza gerek yoktur. Gerçek PostgreSQL ve TMDB API'sine bağlanır,
test sonunda oluşturduğu geçici test kullanıcılarını veritabanından temizler.
"""
import os
import sys
import uuid

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app import app
from backend.db import get_db_cursor

TEST_TMDB_ID = 27205  # Inception


def assert_status(resp, expected, label):
    if resp.status_code != expected:
        print(f"❌ {label} -> Beklenen: {expected}, Gelen: {resp.status_code}")
        print(f"   Yanıt: {resp.get_json()}")
        sys.exit(1)
    print(f"✅ {label} ({resp.status_code})")
    return resp.get_json()


def cleanup_users(usernames):
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM users WHERE username = ANY(%s)",
            (usernames,),
        )


def main():
    suffix = uuid.uuid4().hex[:6]
    u1_name = f"test1_{suffix}"
    u2_name = f"test2_{suffix}"
    password = "TestPassword123"

    client = app.test_client()

    print("=" * 60)
    print("🧪 CINELOG - END-TO-END API TESTİ")
    print("=" * 60)

    try:
        # 1. Kayıt ve Giriş
        print("\n[1] Auth (Kayıt & Giriş)")
        r = client.post("/api/auth/register", json={
            "username": u1_name,
            "email": f"{u1_name}@example.com",
            "password": password,
        })
        u1_id = assert_status(r, 201, "Kullanıcı 1 kayıt")["user"]["user_id"]

        r = client.post("/api/auth/register", json={
            "username": u2_name,
            "email": f"{u2_name}@example.com",
            "password": password,
        })
        u2_id = assert_status(r, 201, "Kullanıcı 2 kayıt")["user"]["user_id"]

        r = client.post("/api/auth/login", json={
            "identifier": u1_name,
            "password": password,
        })
        assert_status(r, 200, "Kullanıcı 1 giriş")

        # 2. Filmler (TMDB)
        print("\n[2] Filmler & TMDB")
        r = client.get("/api/movies/search?q=Inception")
        search_data = assert_status(r, 200, "Film arama")
        print(f"   Bulunan sonuç sayısı: {len(search_data.get('results', []))}")

        r = client.get("/api/movies/popular")
        assert_status(r, 200, "Popüler filmler")

        r = client.get(f"/api/movies/{TEST_TMDB_ID}")
        movie_data = assert_status(r, 200, f"Film detay + DB senkronizasyonu ({TEST_TMDB_ID})")
        print(f"   Film: {movie_data['movie']['title']} | Yerel movie_id: {movie_data['movie']['movie_id']}")

        # 3. Puanlama & İnceleme
        print("\n[3] Puanlama & İncelemeler")
        r = client.put(f"/api/movies/{TEST_TMDB_ID}/rating", json={"score": 9})
        rating_data = assert_status(r, 200, "Puan verme (9/10)")
        print(f"   Ortalama puan: {rating_data['average_score']} ({rating_data['rating_count']} oy)")

        r = client.post(f"/api/movies/{TEST_TMDB_ID}/reviews", json={
            "body": "Kurgu ve müzikler muhteşem.",
            "contains_spoiler": False,
        })
        review_id = assert_status(r, 201, "İnceleme ekleme")["review"]["review_id"]

        r = client.get(f"/api/movies/{TEST_TMDB_ID}/reviews")
        reviews_data = assert_status(r, 200, "İncelemeleri listeleme")
        print(f"   Toplam yayınlanan inceleme: {len(reviews_data['reviews'])}")

        r = client.put(f"/api/reviews/{review_id}", json={
            "body": "Kurgu, oyunculuklar ve müzikler muhteşem.",
            "contains_spoiler": False,
        })
        assert_status(r, 200, "İnceleme güncelleme")

        # 4. Watchlist & Özel Listeler
        print("\n[4] İzleme Listesi & Özel Listeler")
        r = client.post(f"/api/watchlist/{TEST_TMDB_ID}")
        assert_status(r, 201, "Watchlist'e ekleme")

        r = client.get("/api/watchlist")
        wl_data = assert_status(r, 200, "Watchlist görüntüleme")
        print(f"   Watchlist film sayısı: {len(wl_data['watchlist'])}")

        r = client.post("/api/lists", json={
            "name": "Bilim Kurgu Favorileri",
            "description": "En iyi bilim kurgu filmleri",
            "visibility": "public",
        })
        list_id = assert_status(r, 201, "Özel liste oluşturma")["list"]["list_id"]

        r = client.post(f"/api/lists/{list_id}/movies", json={"tmdb_id": TEST_TMDB_ID})
        assert_status(r, 201, "Listeye film ekleme")

        r = client.get(f"/api/lists/{list_id}")
        list_detail = assert_status(r, 200, "Liste detayı")
        print(f"   Liste: {list_detail['list']['name']} ({len(list_detail['list']['movies'])} film)")

        # 5. Takip & Aktivite Akışı (Kullanıcı 2 ile)
        print("\n[5] Takip & Aktivite Akışı")
        client.post("/api/auth/logout")
        r = client.post("/api/auth/login", json={
            "identifier": u2_name,
            "password": password,
        })
        assert_status(r, 200, "Kullanıcı 2 giriş")

        r = client.post(f"/api/social/follow/{u1_id}")
        assert_status(r, 201, "Kullanıcı 1'i takip etme")

        r = client.get(f"/api/social/users/{u1_id}/followers")
        followers_data = assert_status(r, 200, "Takipçileri listeleme")
        print(f"   Kullanıcı 1 takipçi sayısı: {len(followers_data['followers'])}")

        r = client.get("/api/social/feed")
        feed_data = assert_status(r, 200, "Aktivite akışı (feed)")
        print(f"   Akışta görünen aktivite sayısı: {len(feed_data['feed'])}")
        for ev in feed_data["feed"]:
            print(f"     • {ev['actor_username']} -> {ev['event_type']}")

        print("\n" + "=" * 60)
        print("🎉 TÜM BACKEND API TESTLERİ BAŞARIYLA GEÇTİ!")
        print("=" * 60)
    finally:
        cleanup_users([u1_name, u2_name])
        print("🧹 Geçici test kullanıcıları temizlendi.")


if __name__ == "__main__":
    main()

