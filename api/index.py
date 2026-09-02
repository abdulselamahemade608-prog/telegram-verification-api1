import os
import hmac
import hashlib
import urllib.parse
import time

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)


# ==========================================
# TELEGRAM INIT DATA VALIDATION
# ==========================================

def validate_init_data(init_data):

    bot_token = os.environ.get("BOT_TOKEN")

    if not bot_token:
        return None

    try:

        parsed_data = urllib.parse.parse_qsl(
            init_data,
            keep_blank_values=True
        )

        data = dict(parsed_data)

        received_hash = data.pop("hash", None)

        if not received_hash:
            return None

        # --------------------------------------
        # Check auth_date
        # --------------------------------------

        auth_date = data.get("auth_date")

        if auth_date:

            try:
                auth_time = int(auth_date)

                # Data older than 1 hour is rejected
                if time.time() - auth_time > 3600:
                    return None

            except Exception:
                return None

        # --------------------------------------
        # Create data-check-string
        # --------------------------------------

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        # --------------------------------------
        # Create secret key
        # --------------------------------------

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # --------------------------------------
        # Calculate hash
        # --------------------------------------

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # --------------------------------------
        # Compare hashes
        # --------------------------------------

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        return data

    except Exception:
        return None


# ==========================================
# HOME / MINI APP
# ==========================================

@app.route("/", methods=["GET"])
def home():

    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    return send_from_directory(
        base_dir,
        "index.html"
    )


# ==========================================
# API STATUS
# ==========================================

@app.route("/api/status", methods=["GET"])
def status():

    return jsonify({
        "service": "Telegram Verification API",
        "status": "online"
    })


# ==========================================
# VERIFY
# ==========================================

@app.route("/api/verify", methods=["POST"])
def verify():

    try:

        body = request.get_json(
            silent=True
        ) or {}

        init_data = body.get(
            "initData",
            ""
        )

        # --------------------------------------
        # Missing Telegram data
        # --------------------------------------

        if not init_data:

            return jsonify({
                "success": False,
                "status": "FAIL",
                "message": "Telegram data is missing."
            }), 400

        # --------------------------------------
        # Validate Telegram data
        # --------------------------------------

        telegram_data = validate_init_data(
            init_data
        )

        if telegram_data is None:

            return jsonify({
                "success": False,
                "status": "FAIL",
                "message": "Invalid Telegram verification data."
            }), 403

        # --------------------------------------
        # Get Telegram user
        # --------------------------------------

        user_data = {}

        if "user" in telegram_data:

            try:

                import json

                user_data = json.loads(
                    telegram_data["user"]
                )

            except Exception:
                user_data = {}

        user_id = user_data.get(
            "id"
        )

        first_name = user_data.get(
            "first_name",
            "User"
        )

        username = user_data.get(
            "username",
            ""
        )

        # --------------------------------------
        # SUCCESS
        # --------------------------------------

        return jsonify({

            "success": True,

            "status": "PASS",

            "message": "Verification successful.",

            "user": {
                "id": user_id,
                "first_name": first_name,
                "username": username
            }

        }), 200

    except Exception as e:

        return jsonify({

            "success": False,

            "status": "FAIL",

            "message": "Server error."

        }), 500


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
                )
