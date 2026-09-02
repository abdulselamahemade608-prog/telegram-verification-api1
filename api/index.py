import os
import hmac
import hashlib
import urllib.parse
import json
import time

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)


# ==================================================
# TELEGRAM INIT DATA VALIDATION
# ==================================================

def validate_init_data(init_data):

    bot_token = os.environ.get("BOT_TOKEN", "").strip()

    # BOT TOKEN NOT FOUND
    if not bot_token:
        return None, "BOT_TOKEN is not configured on Vercel."

    if not init_data:
        return None, "Telegram initData is empty."

    try:

        # ------------------------------------------
        # Parse Telegram initData
        # ------------------------------------------

        parsed = urllib.parse.parse_qsl(
            init_data,
            keep_blank_values=True
        )

        data = dict(parsed)

        # ------------------------------------------
        # Get Telegram hash
        # ------------------------------------------

        received_hash = data.pop("hash", None)

        if not received_hash:
            return None, "Telegram hash is missing."

        # ------------------------------------------
        # Create data-check-string
        # ------------------------------------------

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        # ------------------------------------------
        # Telegram secret key
        # ------------------------------------------

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        # ------------------------------------------
        # Calculate hash
        # ------------------------------------------

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        # ------------------------------------------
        # Compare
        # ------------------------------------------

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None, "Telegram hash validation failed."

        # ------------------------------------------
        # Optional auth_date check
        # ------------------------------------------

        auth_date = data.get("auth_date")

        if auth_date:

            try:

                auth_time = int(auth_date)

                # Reject data older than 1 hour
                if time.time() - auth_time > 3600:
                    return None, "Telegram verification data has expired."

            except ValueError:

                return None, "Invalid auth_date."

        return data, None

    except Exception as error:

        print("VALIDATION ERROR:", error)

        return None, "Server validation error."


# ==================================================
# HOME
# ==================================================

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


# ==================================================
# API STATUS
# ==================================================

@app.route("/api/status", methods=["GET"])
def api_status():

    bot_token_exists = bool(
        os.environ.get("BOT_TOKEN", "").strip()
    )

    return jsonify({
        "service": "Telegram Verification API",
        "status": "online",
        "bot_token_configured": bot_token_exists
    })


# ==================================================
# VERIFY
# ==================================================

@app.route("/api/verify", methods=["POST"])
def verify():

    try:

        body = request.get_json(
            silent=True
        )

        if not body:

            return jsonify({
                "success": False,
                "status": "FAIL",
                "message": "Request body is missing."
            }), 400

        init_data = body.get(
            "initData",
            ""
        )

        # ------------------------------------------
        # Validate
        # ------------------------------------------

        telegram_data, error = validate_init_data(
            init_data
        )

        if telegram_data is None:

            return jsonify({
                "success": False,
                "status": "FAIL",
                "message": error
            }), 403

        # ------------------------------------------
        # Get user
        # ------------------------------------------

        user_data = {}

        if "user" in telegram_data:

            try:

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

        # ------------------------------------------
        # SUCCESS
        # ------------------------------------------

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

    except Exception as error:

        print("VERIFY ERROR:", error)

        return jsonify({

            "success": False,

            "status": "FAIL",

            "message": "Internal server error."

        }), 500


# ==================================================
# RUN LOCAL
# ==================================================

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
