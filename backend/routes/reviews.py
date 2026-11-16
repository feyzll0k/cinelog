from flask import Blueprint, jsonify, request, session
from psycopg2.errors import UniqueViolation

from backend.db import get_db_cursor
from backend.routes.permissions import login_required
from backend.services.movie_sync import get_movie_by_tmdb_id, get_or_sync_movie

reviews_bp = Blueprint("reviews", __name__)


@reviews_bp.route("/movies/<int:tmdb_id>/rating", methods=["PUT"])
@login_required
def set_rating(tmdb_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    score = data.get("score")
    if isinstance(score, bool) or not isinstance(score, int) or not (1 <= score <= 10):
        return jsonify({"error": "Puan 1 ile 10 arasında bir tam sayı olmalıdır."}), 400

    try:
        movie = get_or_sync_movie(tmdb_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Film senkronize edilemedi: {exc}"}), 502

    movie_id = movie["movie_id"]
    user_id = session["user_id"]

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO ratings (user_id, movie_id, score)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, movie_id) DO UPDATE
                    SET score = EXCLUDED.score
                RETURNING user_id, movie_id, score, created_at, updated_at
                """,
                (user_id, movie_id, score),
            )
            rating = dict(cursor.fetchone())

            cursor.execute(
                """
                SELECT rating_count, average_score
                FROM movie_rating_stats
                WHERE movie_id = %s
                """,
                (movie_id,),
            )
            stats = cursor.fetchone()

        return jsonify({
            "message": "Puan kaydedildi.",
            "rating": rating,
            "rating_count": stats["rating_count"] if stats else 0,
            "average_score": float(stats["average_score"]) if stats and stats["average_score"] is not None else None,
        }), 200
    except Exception:
        return jsonify({"error": "Puan kaydedilemedi."}), 500


@reviews_bp.route("/movies/<int:tmdb_id>/rating", methods=["DELETE"])
@login_required
def delete_rating(tmdb_id):
    movie = get_movie_by_tmdb_id(tmdb_id)
    if not movie:
        return jsonify({"error": "Film bulunamadı."}), 404

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                DELETE FROM ratings
                WHERE user_id = %s AND movie_id = %s
                RETURNING movie_id
                """,
                (session["user_id"], movie["movie_id"]),
            )
            deleted = cursor.fetchone()

        if not deleted:
            return jsonify({"error": "Silinecek puan bulunamadı."}), 404

        return jsonify({"message": "Puan silindi."}), 200
    except Exception:
        return jsonify({"error": "Puan silinemedi."}), 500


@reviews_bp.route("/movies/<int:tmdb_id>/reviews", methods=["GET"])
def list_movie_reviews(tmdb_id):
    movie = get_movie_by_tmdb_id(tmdb_id)
    if not movie:
        return jsonify({"reviews": []}), 200

    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT r.review_id,
                       r.user_id,
                       u.username,
                       u.display_name,
                       u.avatar_url,
                       r.movie_id,
                       r.body,
                       r.contains_spoiler,
                       r.created_at,
                       r.updated_at,
                       rt.score AS user_score
                FROM reviews r
                JOIN users u ON u.user_id = r.user_id
                LEFT JOIN ratings rt ON rt.user_id = r.user_id AND rt.movie_id = r.movie_id
                WHERE r.movie_id = %s
                  AND r.status = 'published'
                ORDER BY r.created_at DESC
                """,
                (movie["movie_id"],),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        return jsonify({"reviews": rows}), 200
    except Exception:
        return jsonify({"error": "İncelemeler alınamadı."}), 500


@reviews_bp.route("/movies/<int:tmdb_id>/reviews", methods=["POST"])
@login_required
def create_review(tmdb_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    body = data.get("body", "")
    contains_spoiler = data.get("contains_spoiler", False)

    if not isinstance(body, str) or not body.strip():
        return jsonify({"error": "İnceleme metni boş olamaz."}), 400
    if len(body) > 10000:
        return jsonify({"error": "İnceleme en fazla 10000 karakter olabilir."}), 400
    if not isinstance(contains_spoiler, bool):
        return jsonify({"error": "contains_spoiler boolean olmalıdır."}), 400

    try:
        movie = get_or_sync_movie(tmdb_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Film senkronize edilemedi: {exc}"}), 502

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO reviews (user_id, movie_id, body, contains_spoiler)
                VALUES (%s, %s, %s, %s)
                RETURNING review_id, user_id, movie_id, body, contains_spoiler, status, created_at, updated_at
                """,
                (session["user_id"], movie["movie_id"], body, contains_spoiler),
            )
            review = dict(cursor.fetchone())

        return jsonify({
            "message": "İnceleme yayınlandı.",
            "review": review,
        }), 201
    except UniqueViolation:
        return jsonify({"error": "Bu film için zaten bir incelemeniz bulunuyor."}), 409
    except Exception:
        return jsonify({"error": "İnceleme kaydedilemedi."}), 500


@reviews_bp.route("/reviews/<int:review_id>", methods=["PUT"])
@login_required
def update_review(review_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    body = data.get("body")
    contains_spoiler = data.get("contains_spoiler")

    if body is None and contains_spoiler is None:
        return jsonify({"error": "Güncellenecek alan belirtilmelidir."}), 400

    if body is not None:
        if not isinstance(body, str) or not body.strip():
            return jsonify({"error": "İnceleme metni boş olamaz."}), 400
        if len(body) > 10000:
            return jsonify({"error": "İnceleme en fazla 10000 karakter olabilir."}), 400

    if contains_spoiler is not None and not isinstance(contains_spoiler, bool):
        return jsonify({"error": "contains_spoiler boolean olmalıdır."}), 400

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT user_id, body, contains_spoiler FROM reviews WHERE review_id = %s",
                (review_id,),
            )
            existing = cursor.fetchone()
            if not existing:
                return jsonify({"error": "İnceleme bulunamadı."}), 404
            if existing["user_id"] != session["user_id"]:
                return jsonify({"error": "Yalnızca kendi incelemenizi düzenleyebilirsiniz."}), 403

            new_body = body if body is not None else existing["body"]
            new_spoiler = contains_spoiler if contains_spoiler is not None else existing["contains_spoiler"]

            cursor.execute(
                """
                UPDATE reviews
                SET body = %s,
                    contains_spoiler = %s
                WHERE review_id = %s
                RETURNING review_id, user_id, movie_id, body, contains_spoiler, status, created_at, updated_at
                """,
                (new_body, new_spoiler, review_id),
            )
            updated = dict(cursor.fetchone())

        return jsonify({
            "message": "İnceleme güncellendi.",
            "review": updated,
        }), 200
    except Exception:
        return jsonify({"error": "İnceleme güncellenemedi."}), 500


@reviews_bp.route("/reviews/<int:review_id>", methods=["DELETE"])
@login_required
def delete_review(review_id):
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT user_id FROM reviews WHERE review_id = %s",
                (review_id,),
            )
            existing = cursor.fetchone()
            if not existing:
                return jsonify({"error": "İnceleme bulunamadı."}), 404
            if existing["user_id"] != session["user_id"]:
                return jsonify({"error": "Yalnızca kendi incelemenizi silebilirsiniz."}), 403

            cursor.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))

        return jsonify({"message": "İnceleme silindi."}), 200
    except Exception:
        return jsonify({"error": "İnceleme silinemedi."}), 500

