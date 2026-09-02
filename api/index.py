import os
import hmac
import hashlib
import urllib.parse
import json
import time

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)


# ==========================================
# CONFIGURATION
# ==========================================

BOT_TOKEN = os.environ.get(
    "BOT_TOKEN",
    ""
).strip()

# Verification data lifetime
VERIFY_MAX_AGE = 3600


# ==========================================
# IN-MEMORY VERIFICATION STORE
# ==========================================
#
# NOTE:
# This is temporary storage.
# Vercel Serverless Functions are stateless,
# so for permanent verification status use
# a database later.
#

verified_users = set()


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

        received_hash = data.pop(
            "hash",
            None
        )

        if not received_hash:
            return None, "Telegram hash is missing."

        # Telegram data-check-string
        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(
                data.items()
            )
        )

        # Secret key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        # Calculated hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Compare hashes
        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None, "Invalid Telegram verification data."

        # ======================================
        # AUTH DATE
        # ======================================

        auth_date = data.get(
            "auth_date"
        )

        if not auth_date:
            return None, "auth_date is missing."

        try:

            auth_time = int(
                auth_date
            )

        except ValueError:

            return None, "Invalid auth_date."

        # Expired?
        if time.time() - auth_time > VERIFY_MAX_AGE:

            return None, (
                "Telegram verification data expired."
            )

        return data, None

    except Exception as error:

        print(
            "VALIDATION ERROR:",
            repr(error)
        )

        return None, "Verification validation error."


# ==========================================
# GET TELEGRAM USER
# ==========================================

def get_telegram_user(data):

    if not data:
        return None

    user_string = data.get(
        "user"
    )

    if not user_string:
        return None

    try:

        return json.loads(
            user_string
        )

    except Exception as error:

        print(
            "USER JSON ERROR:",
            repr(error)
        )

        return None


# ==========================================
# HOME
# ==========================================

@app.route(
    "/",
    methods=["GET"]
)
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

@app.route(
    "/api/status",
    methods=["GET"]
)
def api_status():

    return jsonify({

        "service":
            "Telegram Verification API",

        "status":
            "online",

        "bot_token_configured":
            bool(BOT_TOKEN)

    })


# ==========================================
# VERIFY
# ==========================================

@app.route(
    "/api/verify",
    methods=["POST"]
)
def verify():

    try:

        body = request.get_json(
            silent=True
        )

        if not body:

            return jsonify({

                "success":
                    False,

                "status":
                    "FAIL",

                "message":
                    "Request body is missing."

            }), 400


        init_data = body.get(
            "initData",
            ""
        )


        # ==================================
        # VALIDATE TELEGRAM DATA
        # ==================================

        telegram_data, error = (
            validate_init_data(
                init_data
            )
        )


        if telegram_data is None:

            return jsonify({

                "success":
                    False,

                "status":
                    "FAIL",

                "message":
                    error

            }), 403


        # ==================================
        # GET USER
        # ==================================

        user = get_telegram_user(
            telegram_data
        )


        if not user:

            return jsonify({

                "success":
                    False,

                "status":
                    "FAIL",

                "message":
                    "Telegram user data not found."

            }), 400


        user_id = user.get(
            "id"
        )


        first_name = user.get(
            "first_name",
            "User"
        )


        username = user.get(
            "username",
            ""
        )


        if not user_id:

            return jsonify({

                "success":
                    False,

                "status":
                    "FAIL",

                "message":
                    "Telegram user ID not found."

            }), 400


        # ==================================
        # SUCCESS
        # ==================================

        verified_users.add(
            int(user_id)
        )


        print(
            "VERIFICATION PASS:",
            user_id
        )


        return jsonify({

            "success":
                True,

            "status":
                "PASS",

            "message":
                "Verification successful.",

            "user": {

                "id":
                    user_id,

                "first_name":
                    first_name,

                "username":
                    username

            }

        }), 200


    except Exception as error:

        print(
            "VERIFY ERROR:",
            repr(error)
        )


        return jsonify({

            "success":
                False,

            "status":
                "FAIL",

            "message":
                "Internal server error."

        }), 500


# ==========================================
# CHECK VERIFICATION
# ==========================================

@app.route(
    "/api/check",
    methods=["GET"]
)
def check_verification():

    user_id = request.args.get(
        "user_id",
        ""
    )

    if not user_id:

        return jsonify({

            "success":
                False,

            "verified":
                False,

            "message":
                "user_id is required."

        }), 400


    try:

        user_id = int(
            user_id
        )

    except ValueError:

        return jsonify({

            "success":
                False,

            "verified":
                False,

            "message":
                "Invalid user_id."

        }), 400


    return jsonify({

        "success":
            True,

        "verified":
            user_id in verified_users

    })


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
