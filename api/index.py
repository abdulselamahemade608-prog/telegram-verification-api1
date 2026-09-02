import os
import hmac
import hashlib
import urllib.parse
import json
import time

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
MAX_AUTH_AGE = 3600


# ==========================================
# IN-MEMORY VERIFIED USERS
# ==========================================
# Important:
# Vercel serverless instances are not permanent.
# For production, replace this with Firebase/Supabase/etc.
verified_users = {}


# ==========================================
# TELEGRAM INIT DATA VALIDATION
# ==========================================

def validate_init_data(init_data):

    if not BOT_TOKEN:
        return None, "BOT_TOKEN is not configured."

    if not init_data:
        return None, "Telegram initData is empty."

    try:

        parsed = urllib.parse.parse_qsl(
            init_data,
            keep_blank_values=True
        )

        data = dict(parsed)

        received_hash = data.pop("hash", None)

        if not received_hash:
            return None, "Telegram hash is missing."

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None, "Telegram verification failed."

        auth_date = data.get("auth_date")

        if not auth_date:
            return None, "auth_date is missing."

        try:
            auth_time = int(auth_date)
        except ValueError:
            return None, "Invalid auth_date."

        age = time.time() - auth_time

        if age < 0:
            return None, "Invalid authentication time."

        if age > MAX_AUTH_AGE:
            return None, "Verification data expired."

        return data, None

    except Exception as error:

        print(
            "VALIDATION ERROR:",
            repr(error)
        )

        return None, "Validation error."


# ==========================================
# HOME
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
# STATUS
# ==========================================

@app.route("/api/status", methods=["GET"])
def status():

    return jsonify({
        "service": "Telegram Verification API",
        "status": "online",
        "bot_token_configured": bool(BOT_TOKEN)
    })


# ==========================================
# VERIFY
# ==========================================

@app.route("/api/verify", methods=["POST"])
def verify():

    try:

        body = request.get_json(silent=True)

        if not body:

            return jsonify({
                "success": False,
                "status": "FAIL",
                "verified": False,
                "message": "Request body is missing."
            }), 400

        init_data = body.get(
            "initData",
            ""
        )

        telegram_data, error = validate_init_data(
            init_data
        )

        if telegram_data is None:

            return jsonify({
                "success": False,
                "status": "FAIL",
                "verified": False,
                "message": error
            }), 403

        user_data = {}

        if "user" in telegram_data:

            try:

                user_data = json.loads(
                    telegram_data["user"]
                )

            except Exception:

                return jsonify({
                    "success": False,
                    "status": "FAIL",
                    "verified": False,
                    "message": "Invalid Telegram user data."
                }), 400

        user_id = user_data.get("id")

        first_name = user_data.get(
            "first_name",
            "User"
        )

        username = user_data.get(
            "username",
            ""
        )

        if not user_id:

            return jsonify({
                "success": False,
                "status": "FAIL",
                "verified": False,
                "message": "Telegram user ID not found."
            }), 400

        # ==========================================
        # SAVE VERIFIED USER
        # ==========================================

        verified_users[str(user_id)] = {
            "verified": True,
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "verified_at": int(time.time())
        }

        print(
            "VERIFIED USER:",
            user_id
        )

        # ==========================================
        # PASS
        # ==========================================

        return jsonify({
            "success": True,
            "status": "PASS",
            "verified": True,
            "message": "Verification successful.",
            "user": {
                "id": user_id,
                "first_name": first_name,
                "username": username
            }
        }), 200

    except Exception as error:

        print(
            "VERIFY ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "status": "FAIL",
            "verified": False,
            "message": "Internal server error."
        }), 500


# ==========================================
# CHECK VERIFICATION
# ==========================================

@app.route("/api/check", methods=["GET"])
def check_verification():

    user_id = request.args.get(
        "user_id",
        ""
    ).strip()

    if not user_id:

        return jsonify({
            "success": False,
            "verified": False,
            "message": "user_id is required."
        }), 400

    user = verified_users.get(
        str(user_id)
    )

    if not user:

        return jsonify({
            "success": True,
            "verified": False
        })

    return jsonify({
        "success": True,
        "verified": True,
        "user": user
    })


# ==========================================
# VERCEL
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
