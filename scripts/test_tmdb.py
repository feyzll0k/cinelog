"""
TMDB Entegrasyonunu Test Etme Scripti
Kullanım (Terminalden):
    python scripts/test_tmdb.py
"""
import sys
import os

# Proje ana dizinini Python yoluna ekle
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.services.tmdb import (
    search_movies,
    get_popular_movies,
    get_movie_details,
    get_movie_credits,
    build_image_url,
)


def main():
    print("=" * 60)
    print("🎬 CINELOG - TMDB ENTEGRASYON TESTİ")
    print("=" * 60)

    # 1. Popüler Filmleri Çekme Testi
    print("\n[1] Popüler Filmler Getiriliyor...")
    try:
        popular = get_popular_movies(page=1)
        results = popular.get("results", [])
        print(f"✅ Başarılı! Toplam {len(results)} popüler film listelendi.")
        for movie in results[:3]:
            print(f"   - {movie.get('title')} ({movie.get('release_date')}) | TMDB ID: {movie.get('id')}")
    except Exception as e:
        print(f"❌ Popüler filmler çekilirken hata oluştu: {e}")
        return

    # 2. Arama Testi
    query = "Interstellar"
    print(f"\n[2] '{query}' Arama Testi...")
    try:
        search_res = search_movies(query=query)
        results = search_res.get("results", [])
        print(f"✅ Başarılı! '{query}' için {len(results)} sonuç bulundu.")
        if results:
            first = results[0]
            print(f"   İlk Sonuç: {first.get('title')} (ID: {first.get('id')})")
            print(f"   Özet: {first.get('overview')[:100]}...")
            print(f"   Afiş URL: {build_image_url(first.get('poster_path'))}")
    except Exception as e:
        print(f"❌ Arama testi sırasında hata: {e}")

    # 3. Detay ve Kadro Testi
    tmdb_id = 157336  # Interstellar TMDB ID
    print(f"\n[3] Interstellar (ID: {tmdb_id}) Detay ve Kadro Testi...")
    try:
        details = get_movie_details(tmdb_id)
        credits = get_movie_credits(tmdb_id)
        print(f"✅ Film: {details.get('title')} ({details.get('release_date')})")
        print(f"   Süre: {details.get('runtime')} dakika")
        genres = [g['name'] for g in details.get('genres', [])]
        print(f"   Türler: {', '.join(genres)}")
        
        cast = credits.get("cast", [])[:5]
        print("   Oyuncu Kadrosu (İlk 5):")
        for actor in cast:
            print(f"     * {actor.get('name')} as '{actor.get('character')}'")
    except Exception as e:
        print(f"❌ Detay/Kadro çekilirken hata: {e}")

    print("\n" + "=" * 60)
    print("🎉 TMDB API Entegrasyon Testi Tamamlandı!")
    print("=" * 60)


if __name__ == "__main__":
    main()

