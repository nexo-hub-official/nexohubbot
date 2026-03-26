"""Simple Flask web companion for the NexoHub bot.

Run locally:
    export FLASK_APP=web_app.py
    flask run --host=0.0.0.0 --port=8000
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import Flask, jsonify

APP_NAME = "NexoHub Bot Web"


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index() -> dict[str, str]:
        return {
            "app": APP_NAME,
            "status": "online",
            "message": "NexoHub bot now includes a Flask web app.",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/config")
    def config() -> tuple[object, int]:
        token_present = bool(os.getenv("DISCORD_BOT_TOKEN"))
        return jsonify({"discord_token_configured": token_present}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
