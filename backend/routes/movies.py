from flask import Blueprint, jsonify, request, session

from backend.db import get_db_cursor
from backend.services.movie_sync import get_or_sync_movie
from backend.services.tmdb import (
    build_image_url,
    get_genres,
    get_popular_movies,
    get_top_rated_movies,
    search_movies,
)

movies_bp = Blueprint("movies", __name__)


def _parse_page(raw_page):
    try:
        page = int(raw_page)
        return page if page >= 1 else 1
    except (TypeError, ValueError):
        return 1


def _format_tmdb_list(data):
    results = []
    for item in (data or {}).get("results", []):
        results.append({
            "tmdb_id": item.get("id"),
            "title": item.get("title"),
            "original_title": item.get("original_title"),
            "overview": item.get("overview"),
            "release_date": item.get("release_date"),
            "poster_path": item.get("poster_path"),
            "poster_url": build_image_url(item.get("poster_path"), size="w500"),
            "tmdb_vote_average": item.get("vote_average"),
            "tmdb_vote_count": item.get("vote_count"),
            "genre_ids": item.get("genre_ids", []),
        })
    return {
        "page": (data or {}).get("page", 1),
        "total_pages": (data or {}).get("total_pages", 0),
        "total_results": (data or {}).get("total_results", 0),
        "results": results,
    }


@movies_bp.route("/search", methods=["GET"])
def search():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"error": "Arama terimi (q) gereklidir."}), 400

    page = _parse_page(request.args.get("page", 1))
    try:
        data = search_movies(query=query, page=page)
        return jsonify(_format_tmdb_list(data)), 200
    except Exception as exc:
        return jsonify({"error": f"Film araması başarısız: {exc}"}), 502


@movies_bp.route("/popular", methods=["GET"])
def popular():
    page = _parse_page(request.args.get("page", 1))
    try:
        data = get_popular_movies(page=page)
        return jsonify(_format_tmdb_list(data)), 200
    except Exception as exc:
        return jsonify({"error": f"Popüler filmler alınamadı: {exc}"}), 502


@movies_bp.route("/top-rated", methods=["GET"])
def top_rated():
    page = _parse_page(request.args.get("page", 1))
    try:
        data = get_top_rated_movies(page=page)
        return jsonify(_format_tmdb_list(data)), 200
    except Exception as exc:
        return jsonify({"error": f"En yüksek puanlı filmler alınamadı: {exc}"}), 502


@movies_bp.route("/genres", methods=["GET"])
def genres():
    try:
        return jsonify({"genres": get_genres()}), 200
    except Exception as exc:
        return jsonify({"error": f"Film türleri alınamadı: {exc}"}), 502


@movies_bp.route("/<int:tmdb_id>", methods=["GET"])
def detail(tmdb_id):
    if tmdb_id <= 0:
        return jsonify({"error": "Geçersiz film ID."}), 400

    try:
        movie = get_or_sync_movie(tmdb_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Film detayları alınamadı: {exc}"}), 502

    if not movie:
        return jsonify({"error": "Film bulunamadı."}), 404

    movie_data = dict(movie)
    if movie_data.get("average_score") is not None:
        movie_data["average_score"] = float(movie_data["average_score"])
    if movie_data.get("tmdb_vote_average") is not None:
        movie_data["tmdb_vote_average"] = float(movie_data["tmdb_vote_average"])

    user_id = session.get("user_id")
    movie_data["user_rating"] = None
    movie_data["in_watchlist"] = False

    if user_id:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT score FROM ratings WHERE user_id = %s AND movie_id = %s",
                (user_id, movie_data["movie_id"]),
            )
            rating_row = cursor.fetchone()
            if rating_row:
                movie_data["user_rating"] = rating_row["score"]

            cursor.execute(
                "SELECT 1 FROM watchlist WHERE user_id = %s AND movie_id = %s",
                (user_id, movie_data["movie_id"]),
            )
            movie_data["in_watchlist"] = cursor.fetchone() is not None

    return jsonify({"movie": movie_data}), 200

