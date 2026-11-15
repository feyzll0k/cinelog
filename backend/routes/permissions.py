from functools import wraps

from flask import session, jsonify


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "error": "Bu işlem için giriş yapmalısınız."
            }), 401

        return func(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({
                    "error": "Giriş yapmalısınız."
                }), 401

            user_role = session.get("role")

            if user_role not in allowed_roles:
                return jsonify({
                    "error": "Bu işlem için yetkiniz bulunmuyor."
                }), 403

            return func(*args, **kwargs)

        return wrapper

    return decorator