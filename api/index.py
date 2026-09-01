import os
import hmac
import hashlib
import urllib.parse

from flask import Flask, request, jsonify

app = Flask(__name__)


def validate_init_data(init_data):

    bot_token = os.environ.get("BOT_TOKEN")

    if not bot_token:
        return None

    try:
        parsed = urllib.parse.parse_qsl(
            init_data,
            keep_blank_values=True
        )

        data = dict(parsed)

        received_hash = data.pop("hash", None)

        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        return data

    except Exception:
        return None


@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "status": "online",
        "service": "Telegram Verification API"
    })


@app.route("/api/verify", methods=["POST"])
def verify():

    body = request.get_json(silent=True) or {}

    init_data = body.get("initData", "")

    if not init_data:

        return jsonify({
            "success": False,
            "status": "FAIL",
            "message": "Telegram data is missing."
        }), 400


    telegram_data = validate_init_data(init_data)

    if telegram_data is None:

        return jsonify({
            "success": False,
            "status": "FAIL",
            "message": "Invalid Telegram verification data."
        }), 403


    return jsonify({
        "success": True,
        "status": "PASS",
        "message": "Verification successful."
    })
