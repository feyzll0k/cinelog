from datetime import datetime
from backend.db import get_db_cursor
from backend.services.tmdb import (
    get_movie_details,
    get_movie_credits,
    build_image_url,
)


def get_movie_by_tmdb_id(tmdb_id: int):
    """Veritabanında tmdb_id'ye sahip kayıtlı filmi ve ortalama puanını döndürür."""
    query = """
        SELECT m.*,
               s.rating_count,
               s.average_score
        FROM movies m
        LEFT JOIN movie_rating_stats s ON s.movie_id = m.movie_id
        WHERE m.tmdb_id = %s;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (tmdb_id,))
        return cursor.fetchone()


def get_movie_by_id(movie_id: int):
    """Yerel veritabanı ID'sine (movie_id) göre film detayını getirir."""
    query = """
        SELECT m.*,
               s.rating_count,
               s.average_score
        FROM movies m
        LEFT JOIN movie_rating_stats s ON s.movie_id = m.movie_id
        WHERE m.movie_id = %s;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (movie_id,))
        return cursor.fetchone()


def get_movie_genres(movie_id: int) -> list:
    """Bir filme ait türleri listeler."""
    query = """
        SELECT g.genre_id, g.tmdb_id, g.name
        FROM genres g
        JOIN movie_genres mg ON mg.genre_id = g.genre_id
        WHERE mg.movie_id = %s
        ORDER BY g.name;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (movie_id,))
        return cursor.fetchall()


def get_movie_cast(movie_id: int, limit: int = 15) -> list:
    """Bir filmin oyuncu kadrosunu listeler."""
    query = """
        SELECT a.actor_id, a.tmdb_id, a.name, a.profile_path,
               mc.character_name, mc.cast_order
        FROM movie_cast mc
        JOIN actors a ON a.actor_id = mc.actor_id
        WHERE mc.movie_id = %s
        ORDER BY mc.cast_order ASC
        LIMIT %s;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (movie_id, limit))
        cast = cursor.fetchall()
        for member in cast:
            member["profile_url"] = build_image_url(member["profile_path"], size="w185")
        return cast


def sync_movie_to_db(tmdb_id: int) -> int:
    """
    TMDB'den film detaylarını ve oyuncu kadrosunu çekerek yerel PostgreSQL veritabanına kaydeder/günceller.
    Başarılı olursa yerel `movie_id` değerini döndürür.
    """
    details = get_movie_details(tmdb_id)
    if not details:
        raise ValueError(f"TMDB üzerinde {tmdb_id} ID'li film bulunamadı.")

    credits = get_movie_credits(tmdb_id) or {}

    # Alanları şema kısıtlarına (constraints) uygun şekilde temizle
    title = (details.get("title") or details.get("original_title") or "İsimsiz").strip()
    original_title = details.get("original_title")
    overview = details.get("overview") or None
    
    release_date_str = details.get("release_date")
    release_date = release_date_str if release_date_str else None

    runtime = details.get("runtime")
    runtime_minutes = runtime if (runtime and runtime > 0) else None

    original_language = details.get("original_language")
    poster_path = details.get("poster_path")
    
    vote_avg = details.get("vote_average")
    tmdb_vote_average = min(max(vote_avg, 0.0), 10.0) if vote_avg is not None else None
    
    vote_count = details.get("vote_count")
    tmdb_vote_count = max(vote_count, 0) if vote_count is not None else 0

    with get_db_cursor(commit=True) as cursor:
        # 1. movies tablosuna ekle ya da güncelle (Upsert)
        movie_upsert_query = """
            INSERT INTO movies (
                tmdb_id, title, original_title, overview,
                release_date, runtime_minutes, original_language,
                poster_path, tmdb_vote_average, tmdb_vote_count,
                tmdb_synced_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (tmdb_id) DO UPDATE SET
                title = EXCLUDED.title,
                original_title = EXCLUDED.original_title,
                overview = EXCLUDED.overview,
                release_date = EXCLUDED.release_date,
                runtime_minutes = EXCLUDED.runtime_minutes,
                original_language = EXCLUDED.original_language,
                poster_path = EXCLUDED.poster_path,
                tmdb_vote_average = EXCLUDED.tmdb_vote_average,
                tmdb_vote_count = EXCLUDED.tmdb_vote_count,
                tmdb_synced_at = CURRENT_TIMESTAMP
            RETURNING movie_id;
        """
        cursor.execute(
            movie_upsert_query,
            (
                tmdb_id,
                title,
                original_title,
                overview,
                release_date,
                runtime_minutes,
                original_language,
                poster_path,
                tmdb_vote_average,
                tmdb_vote_count,
            ),
        )
        movie_row = cursor.fetchone()
        movie_id = movie_row["movie_id"]

        # 2. Türleri (genres & movie_genres) eşitle
        genres_data = details.get("genres") or []
        for g in genres_data:
            g_tmdb_id = g.get("id")
            g_name = g.get("name")
            if not g_tmdb_id or not g_name:
                continue

            # Türü kaydet veya al
            genre_upsert = """
                INSERT INTO genres (tmdb_id, name)
                VALUES (%s, %s)
                ON CONFLICT (tmdb_id) DO UPDATE SET name = EXCLUDED.name
                RETURNING genre_id;
            """
            cursor.execute(genre_upsert, (g_tmdb_id, g_name.strip()))
            genre_row = cursor.fetchone()
            genre_id = genre_row["genre_id"]

            # Film ile türü ilişkilendir
            cursor.execute(
                """
                INSERT INTO movie_genres (movie_id, genre_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (movie_id, genre_id),
            )

        # 3. Oyuncuları (actors & movie_cast) eşitle (İlk 15 oyuncu)
        cast_list = (credits.get("cast") or [])[:15]
        for index, cast_member in enumerate(cast_list):
            actor_tmdb_id = cast_member.get("id")
            actor_name = cast_member.get("name")
            if not actor_tmdb_id or not actor_name:
                continue

            profile_path = cast_member.get("profile_path")
            credit_id = cast_member.get("credit_id")
            character_name = cast_member.get("character")

            # Aktörü kaydet veya al
            actor_upsert = """
                INSERT INTO actors (tmdb_id, name, profile_path)
                VALUES (%s, %s, %s)
                ON CONFLICT (tmdb_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    profile_path = COALESCE(EXCLUDED.profile_path, actors.profile_path)
                RETURNING actor_id;
            """
            cursor.execute(actor_upsert, (actor_tmdb_id, actor_name.strip(), profile_path))
            actor_row = cursor.fetchone()
            actor_id = actor_row["actor_id"]

            # Rol ilişkisi
            if credit_id:
                cursor.execute(
                    """
                    INSERT INTO movie_cast (movie_id, actor_id, tmdb_credit_id, character_name, cast_order)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (tmdb_credit_id) DO UPDATE SET
                        character_name = EXCLUDED.character_name,
                        cast_order = EXCLUDED.cast_order;
                    """,
                    (movie_id, actor_id, credit_id, character_name, index),
                )

    return movie_id


def get_or_sync_movie(tmdb_id: int):
    """
    Filmi veritabanında arar; varsa getirir, yoksa TMDB'den otomatik senkronize edip döndürür.
    Film detay sayfası ve inceleme yazma işlemleri için ana fonksiyondur.
    """
    movie = get_movie_by_tmdb_id(tmdb_id)
    if not movie:
        movie_id = sync_movie_to_db(tmdb_id)
        movie = get_movie_by_id(movie_id)

    if movie:
        movie["poster_url"] = build_image_url(movie.get("poster_path"), size="w500")
        movie["genres"] = get_movie_genres(movie["movie_id"])
        movie["cast"] = get_movie_cast(movie["movie_id"])

    return movie

