from flask import Blueprint, jsonify, request, session

from backend.db import get_db_cursor
from backend.routes.permissions import login_required
from backend.services.tmdb import build_image_url

social_bp = Blueprint("social", __name__)


@social_bp.route("/follow/<int:target_user_id>", methods=["POST"])
@login_required
def follow_user(target_user_id):
    follower_id = session["user_id"]
    if follower_id == target_user_id:
        return jsonify({"error": "Kendinizi takip edemezsiniz."}), 400

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT user_id FROM users WHERE user_id = %s AND account_status = 'active'",
                (target_user_id,),
            )
            if not cursor.fetchone():
                return jsonify({"error": "Kullanıcı bulunamadı."}), 404

            cursor.execute(
                """
                INSERT INTO follows (follower_id, followed_id)
                VALUES (%s, %s)
                ON CONFLICT (follower_id, followed_id) DO NOTHING
                """,
                (follower_id, target_user_id),
            )

        return jsonify({"message": "Kullanıcı takip edildi."}), 201
    except Exception:
        return jsonify({"error": "Takip işlemi başarısız oldu."}), 500


@social_bp.route("/follow/<int:target_user_id>", methods=["DELETE"])
@login_required
def unfollow_user(target_user_id):
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                DELETE FROM follows
                WHERE follower_id = %s AND followed_id = %s
                RETURNING followed_id
                """,
                (session["user_id"], target_user_id),
            )
            deleted = cursor.fetchone()

        if not deleted:
            return jsonify({"error": "Bu kullanıcıyı zaten takip etmiyorsunuz."}), 404

        return jsonify({"message": "Takipten çıkıldı."}), 200
    except Exception:
        return jsonify({"error": "Takipten çıkma işlemi başarısız oldu."}), 500


@social_bp.route("/users/<int:user_id>/followers", methods=["GET"])
def get_followers(user_id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT u.user_id, u.username, u.display_name, u.avatar_url, f.created_at AS followed_at
                FROM follows f
                JOIN users u ON u.user_id = f.follower_id
                WHERE f.followed_id = %s
                ORDER BY f.created_at DESC
                """,
                (user_id,),
            )
            followers = [dict(row) for row in cursor.fetchall()]

        return jsonify({"followers": followers}), 200
    except Exception:
        return jsonify({"error": "Takipçiler alınamadı."}), 500


@social_bp.route("/users/<int:user_id>/following", methods=["GET"])
def get_following(user_id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT u.user_id, u.username, u.display_name, u.avatar_url, f.created_at AS followed_at
                FROM follows f
                JOIN users u ON u.user_id = f.followed_id
                WHERE f.follower_id = %s
                ORDER BY f.created_at DESC
                """,
                (user_id,),
            )
            following = [dict(row) for row in cursor.fetchall()]

        return jsonify({"following": following}), 200
    except Exception:
        return jsonify({"error": "Takip edilenler alınamadı."}), 500


@social_bp.route("/feed", methods=["GET"])
@login_required
def get_activity_feed():
    try:
        limit = min(max(int(request.args.get("limit", 30)), 1), 100)
    except (TypeError, ValueError):
        limit = 30

    try:
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        offset = 0

    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT ae.event_id,
                       ae.event_type,
                       ae.actor_id,
                       actor.username AS actor_username,
                       actor.display_name AS actor_display_name,
                       actor.avatar_url AS actor_avatar_url,
                       ae.movie_id,
                       m.tmdb_id AS movie_tmdb_id,
                       m.title AS movie_title,
                       m.poster_path AS movie_poster_path,
                       ae.review_id,
                       ae.list_id,
                       ul.name AS list_name,
                       ae.target_user_id,
                       target_u.username AS target_username,
                       ae.score,
                       ae.occurred_at
                FROM activity_events ae
                JOIN follows f
                  ON f.followed_id = ae.actor_id
                 AND f.follower_id = %s
                JOIN users actor ON actor.user_id = ae.actor_id
                LEFT JOIN movies m ON m.movie_id = ae.movie_id
                LEFT JOIN user_lists ul ON ul.list_id = ae.list_id
                LEFT JOIN users target_u ON target_u.user_id = ae.target_user_id
                ORDER BY ae.occurred_at DESC
                LIMIT %s OFFSET %s
                """,
                (session["user_id"], limit, offset),
            )
            events = []
            for row in cursor.fetchall():
                item = dict(row)
                item["movie_poster_url"] = build_image_url(item.get("movie_poster_path"), size="w185")
                events.append(item)

        return jsonify({"feed": events, "limit": limit, "offset": offset}), 200
    except Exception:
        return jsonify({"error": "Aktivite akışı alınamadı."}), 500

