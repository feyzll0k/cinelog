from flask import Blueprint, jsonify, request, session

from backend.db import get_db_cursor
from backend.routes.permissions import login_required
from backend.services.movie_sync import get_movie_by_tmdb_id, get_or_sync_movie
from backend.services.tmdb import build_image_url

lists_bp = Blueprint("lists", __name__)


# --- İzleme Listesi (Watchlist) ---

@lists_bp.route("/watchlist", methods=["GET"])
@login_required
def get_watchlist():
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT m.movie_id, m.tmdb_id, m.title, m.original_title,
                       m.release_date, m.poster_path, m.tmdb_vote_average,
                       w.added_at
                FROM watchlist w
                JOIN movies m ON m.movie_id = w.movie_id
                WHERE w.user_id = %s
                ORDER BY w.added_at DESC
                """,
                (session["user_id"],),
            )
            items = []
            for row in cursor.fetchall():
                item = dict(row)
                item["poster_url"] = build_image_url(item.get("poster_path"), size="w500")
                if item.get("tmdb_vote_average") is not None:
                    item["tmdb_vote_average"] = float(item["tmdb_vote_average"])
                items.append(item)

        return jsonify({"watchlist": items}), 200
    except Exception:
        return jsonify({"error": "İzleme listesi alınamadı."}), 500


@lists_bp.route("/watchlist/<int:tmdb_id>", methods=["POST"])
@login_required
def add_to_watchlist(tmdb_id):
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
                INSERT INTO watchlist (user_id, movie_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, movie_id) DO NOTHING
                """,
                (session["user_id"], movie["movie_id"]),
            )
        return jsonify({"message": "Film izleme listesine eklendi."}), 201
    except Exception:
        return jsonify({"error": "Film izleme listesine eklenemedi."}), 500


@lists_bp.route("/watchlist/<int:tmdb_id>", methods=["DELETE"])
@login_required
def remove_from_watchlist(tmdb_id):
    movie = get_movie_by_tmdb_id(tmdb_id)
    if not movie:
        return jsonify({"error": "Film bulunamadı."}), 404

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                DELETE FROM watchlist
                WHERE user_id = %s AND movie_id = %s
                RETURNING movie_id
                """,
                (session["user_id"], movie["movie_id"]),
            )
            deleted = cursor.fetchone()

        if not deleted:
            return jsonify({"error": "Film izleme listenizde değil."}), 404

        return jsonify({"message": "Film izleme listesinden çıkarıldı."}), 200
    except Exception:
        return jsonify({"error": "Film izleme listesinden çıkarılamadı."}), 500


# --- Özel Listeler (User Lists) ---

@lists_bp.route("/lists", methods=["GET"])
@login_required
def get_my_lists():
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT l.list_id, l.user_id, l.name, l.description,
                       l.visibility, l.created_at, l.updated_at,
                       COUNT(li.movie_id) AS movie_count
                FROM user_lists l
                LEFT JOIN list_items li ON li.list_id = l.list_id
                WHERE l.user_id = %s
                GROUP BY l.list_id
                ORDER BY l.updated_at DESC
                """,
                (session["user_id"],),
            )
            lists = [dict(row) for row in cursor.fetchall()]

        return jsonify({"lists": lists}), 200
    except Exception:
        return jsonify({"error": "Listeler alınamadı."}), 500


@lists_bp.route("/lists", methods=["POST"])
@login_required
def create_list():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    name = data.get("name", "")
    description = data.get("description")
    visibility = data.get("visibility", "private")

    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Liste adı boş olamaz."}), 400
    name = name.strip()
    if len(name) > 100:
        return jsonify({"error": "Liste adı en fazla 100 karakter olabilir."}), 400

    if description is not None and not isinstance(description, str):
        return jsonify({"error": "Geçersiz açıklama."}), 400

    if visibility not in ("public", "private"):
        return jsonify({"error": "Görünürlük 'public' veya 'private' olmalıdır."}), 400

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO user_lists (user_id, name, description, visibility)
                VALUES (%s, %s, %s, %s)
                RETURNING list_id, user_id, name, description, visibility, created_at, updated_at
                """,
                (session["user_id"], name, description, visibility),
            )
            created = dict(cursor.fetchone())

        return jsonify({
            "message": "Liste oluşturuldu.",
            "list": created,
        }), 201
    except Exception:
        return jsonify({"error": "Liste oluşturulamadı."}), 500


@lists_bp.route("/lists/<int:list_id>", methods=["GET"])
def get_list_detail(list_id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT l.list_id, l.user_id, u.username, l.name, l.description,
                       l.visibility, l.created_at, l.updated_at
                FROM user_lists l
                JOIN users u ON u.user_id = l.user_id
                WHERE l.list_id = %s
                """,
                (list_id,),
            )
            lst = cursor.fetchone()
            if not lst:
                return jsonify({"error": "Liste bulunamadı."}), 404

            if lst["visibility"] == "private" and session.get("user_id") != lst["user_id"]:
                return jsonify({"error": "Bu listeyi görüntüleme yetkiniz yok."}), 403

            cursor.execute(
                """
                SELECT m.movie_id, m.tmdb_id, m.title, m.release_date,
                       m.poster_path, m.tmdb_vote_average, li.added_at
                FROM list_items li
                JOIN movies m ON m.movie_id = li.movie_id
                WHERE li.list_id = %s
                ORDER BY li.added_at DESC
                """,
                (list_id,),
            )
            movies = []
            for row in cursor.fetchall():
                item = dict(row)
                item["poster_url"] = build_image_url(item.get("poster_path"), size="w500")
                if item.get("tmdb_vote_average") is not None:
                    item["tmdb_vote_average"] = float(item["tmdb_vote_average"])
                movies.append(item)

        list_data = dict(lst)
        list_data["movies"] = movies
        return jsonify({"list": list_data}), 200
    except Exception:
        return jsonify({"error": "Liste detayı alınamadı."}), 500


@lists_bp.route("/lists/<int:list_id>", methods=["PUT"])
@login_required
def update_list(list_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT user_id, name, description, visibility FROM user_lists WHERE list_id = %s",
                (list_id,),
            )
            existing = cursor.fetchone()
            if not existing:
                return jsonify({"error": "Liste bulunamadı."}), 404
            if existing["user_id"] != session["user_id"]:
                return jsonify({"error": "Yalnızca kendi listenizi düzenleyebilirsiniz."}), 403

            name = data.get("name", existing["name"])
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
                return jsonify({"error": "Liste adı 1-100 karakter arasında olmalıdır."}), 400

            description = data.get("description", existing["description"])
            if description is not None and not isinstance(description, str):
                return jsonify({"error": "Geçersiz açıklama."}), 400

            visibility = data.get("visibility", existing["visibility"])
            if visibility not in ("public", "private"):
                return jsonify({"error": "Görünürlük 'public' veya 'private' olmalıdır."}), 400

            cursor.execute(
                """
                UPDATE user_lists
                SET name = %s,
                    description = %s,
                    visibility = %s
                WHERE list_id = %s
                RETURNING list_id, user_id, name, description, visibility, created_at, updated_at
                """,
                (name.strip(), description, visibility, list_id),
            )
            updated = dict(cursor.fetchone())

        return jsonify({
            "message": "Liste güncellendi.",
            "list": updated,
        }), 200
    except Exception:
        return jsonify({"error": "Liste güncellenemedi."}), 500


@lists_bp.route("/lists/<int:list_id>", methods=["DELETE"])
@login_required
def delete_list(list_id):
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("SELECT user_id FROM user_lists WHERE list_id = %s", (list_id,))
            existing = cursor.fetchone()
            if not existing:
                return jsonify({"error": "Liste bulunamadı."}), 404
            if existing["user_id"] != session["user_id"]:
                return jsonify({"error": "Yalnızca kendi listenizi silebilirsiniz."}), 403

            cursor.execute("DELETE FROM user_lists WHERE list_id = %s", (list_id,))

        return jsonify({"message": "Liste silindi."}), 200
    except Exception:
        return jsonify({"error": "Liste silinemedi."}), 500


@lists_bp.route("/lists/<int:list_id>/movies", methods=["POST"])
@login_required
def add_movie_to_list(list_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    tmdb_id = data.get("tmdb_id")
    if isinstance(tmdb_id, bool) or not isinstance(tmdb_id, int) or tmdb_id <= 0:
        return jsonify({"error": "Geçerli bir tmdb_id belirtilmelidir."}), 400

    with get_db_cursor() as cursor:
        cursor.execute("SELECT user_id FROM user_lists WHERE list_id = %s", (list_id,))
        lst = cursor.fetchone()
        if not lst:
            return jsonify({"error": "Liste bulunamadı."}), 404
        if lst["user_id"] != session["user_id"]:
            return jsonify({"error": "Yalnızca kendi listenize film ekleyebilirsiniz."}), 403

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
                INSERT INTO list_items (list_id, movie_id)
                VALUES (%s, %s)
                ON CONFLICT (list_id, movie_id) DO NOTHING
                """,
                (list_id, movie["movie_id"]),
            )
        return jsonify({"message": "Film listeye eklendi."}), 201
    except Exception:
        return jsonify({"error": "Film listeye eklenemedi."}), 500


@lists_bp.route("/lists/<int:list_id>/movies/<int:tmdb_id>", methods=["DELETE"])
@login_required
def remove_movie_from_list(list_id, tmdb_id):
    with get_db_cursor() as cursor:
        cursor.execute("SELECT user_id FROM user_lists WHERE list_id = %s", (list_id,))
        lst = cursor.fetchone()
        if not lst:
            return jsonify({"error": "Liste bulunamadı."}), 404
        if lst["user_id"] != session["user_id"]:
            return jsonify({"error": "Yalnızca kendi listenizden film çıkarabilirsiniz."}), 403

    movie = get_movie_by_tmdb_id(tmdb_id)
    if not movie:
        return jsonify({"error": "Film bulunamadı."}), 404

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                DELETE FROM list_items
                WHERE list_id = %s AND movie_id = %s
                RETURNING movie_id
                """,
                (list_id, movie["movie_id"]),
            )
            deleted = cursor.fetchone()

        if not deleted:
            return jsonify({"error": "Film bu listede değil."}), 404

        return jsonify({"message": "Film listeden çıkarıldı."}), 200
    except Exception:
        return jsonify({"error": "Film listeden çıkarılamadı."}), 500

