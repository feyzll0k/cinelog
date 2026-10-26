from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)


@app.route("/")
def index():
    return render_template("index.html")
