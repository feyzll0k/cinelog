from flask import Blueprint, jsonify, request, session

from backend.db import get_db_cursor
from backend.routes.permissions import role_required

moderation_bp = Blueprint("moderation", __name__)


# Açık şikâyetleri görüntüleme
@moderation_bp.route("/reports", methods=["GET"])
@role_required("moderator", "admin")
def get_reports():
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    report_id,
                    reporter_id,
                    review_id,
                    list_id,
                    reason,
                    details,
                    status,
                    created_at
                FROM reports
                WHERE status = 'open'
                ORDER BY created_at ASC
                """
            )

            reports = cursor.fetchall()

        return jsonify({
            "reports": [dict(report) for report in reports]
        }), 200

    except Exception:
        return jsonify({
            "error": "Şikâyetler alınamadı."
        }), 500


# Şikâyeti sonuçlandırma veya reddetme
@moderation_bp.route("/reports/<int:report_id>/resolve", methods=["PUT"])
@role_required("moderator", "admin")
def resolve_report(report_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Geçersiz istek."
        }), 400

    status = data.get("status")

    if not isinstance(status, str) or status not in ("resolved", "dismissed"):
        return jsonify({
            "error": "Durum resolved veya dismissed olmalıdır."
        }), 400

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE reports
                SET status = %s,
                    resolved_by = %s,
                    resolved_at = CURRENT_TIMESTAMP
                WHERE report_id = %s
                  AND status = 'open'
                RETURNING report_id, status, resolved_by, resolved_at
                """,
                (status, session["user_id"], report_id),
            )

            report = cursor.fetchone()

        if report is None:
            return jsonify({
                "error": "Şikâyet bulunamadı veya daha önce sonuçlandırıldı."
            }), 404

        return jsonify({
            "message": "Şikâyet başarıyla sonuçlandırıldı.",
            "report": dict(report)
        }), 200

    except Exception:
        return jsonify({
            "error": "Şikâyet sonuçlandırılırken hata oluştu."
        }), 500