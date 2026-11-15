import re
from backend.routes.permissions import login_required, role_required
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.errors import UniqueViolation


from backend.db import get_db_cursor

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")

    if not isinstance(username, str) or not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Geçersiz bilgi gönderildi."}), 400

    username = username.strip().lower()
    email = email.strip().lower()

    if not username or not email or not password:
        return jsonify({"error": "Tüm alanları doldurmalısınız."}), 400

    if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
        return jsonify({
            "error": "Kullanıcı adı 3-30 karakter olmalı; küçük harf, rakam ve alt çizgi içermelidir."
        }), 400

    if "@" not in email or len(email) < 3:
        return jsonify({"error": "Geçerli bir e-posta adresi giriniz."}), 400

    if len(password) < 8:
        return jsonify({"error": "Şifre en az 8 karakter olmalıdır."}), 400

    password_hash = generate_password_hash(password)

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING user_id, username, email, role
                """,
                (username, email, password_hash),
            )

            user = cursor.fetchone()

        return jsonify({
            "message": "Hesap başarıyla oluşturuldu.",
            "user": dict(user)
        }), 201

    except UniqueViolation:
        return jsonify({
            "error": "Bu kullanıcı adı veya e-posta zaten kullanılıyor."
        }), 409

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    identifier = data.get("identifier", "")
    password = data.get("password", "")

    if not isinstance(identifier, str) or not isinstance(password, str):
        return jsonify({"error": "Geçersiz bilgi gönderildi."}), 400

    identifier = identifier.strip().lower()

    if not identifier or not password:
        return jsonify({"error": "Kullanıcı adı/e-posta ve şifre gereklidir."}), 400

    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, email, password_hash, role
                FROM users
                WHERE username = %s OR email = %s
                """,
                (identifier, identifier),
            )
            user = cursor.fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Kullanıcı adı veya şifre hatalı."}), 401
        session.clear()
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        return jsonify({
            "message": "Giriş başarılı.",
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
            }
        }), 200

    except Exception:
        return jsonify({"error": "Giriş sırasında bir hata oluştu."}), 500

@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "message": "Başarıyla çıkış yapıldı."
    }), 200

@auth_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    if "user_id" not in session:
        return jsonify({"error": "Giriş yapmalısınız."}), 401

    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, email, display_name,
                       bio, avatar_url, role, created_at
                FROM users
                WHERE user_id = %s
                """,
                (session["user_id"],),
            )

            user = cursor.fetchone()

        if user is None:
            session.clear()
            return jsonify({"error": "Kullanıcı bulunamadı."}), 404

        return jsonify({"user": dict(user)}), 200

    except Exception:
        return jsonify({"error": "Profil bilgileri alınamadı."}), 500

@auth_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    if "user_id" not in session:
        return jsonify({"error": "Giriş yapmalısınız."}), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Geçersiz istek."}), 400

    display_name = data.get("display_name")
    bio = data.get("bio")

    if display_name is not None and not isinstance(display_name, str):
        return jsonify({"error": "Görünen ad metin olmalıdır."}), 400

    if bio is not None and not isinstance(bio, str):
        return jsonify({"error": "Biyografi metin olmalıdır."}), 400

    if display_name is not None and len(display_name) > 100:
        return jsonify({"error": "Görünen ad en fazla 100 karakter olabilir."}), 400

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE users
                SET display_name = COALESCE(%s, display_name),
                    bio = COALESCE(%s, bio),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                RETURNING user_id, username, email, display_name, bio, role
                """,
                (display_name, bio, session["user_id"]),
            )

            user = cursor.fetchone()

        if user is None:
            return jsonify({"error": "Kullanıcı bulunamadı."}), 404

        return jsonify({
            "message": "Profil başarıyla güncellendi.",
            "user": dict(user)
        }), 200

    except Exception:
        return jsonify({"error": "Profil güncellenemedi."}), 500    

@auth_bp.route("/admin-test", methods=["GET"])
@role_required("admin")
def admin_test():
    return jsonify({
        "message": "Yönetici erişimi başarılı."
    }), 200