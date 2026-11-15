import os
from flask import Flask, render_template, session
from dotenv import load_dotenv

from backend.routes.auth import auth_bp
from backend.routes.moderation import moderation_bp
load_dotenv()

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)
app.secret_key = os.getenv("SECRET_KEY")
# Kullanıcı kayıt ve giriş işlemleri
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(moderation_bp, url_prefix="/api/moderation")

@app.route("/")
def index():
    return render_template("index.html")