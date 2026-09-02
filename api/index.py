import os
import hmac
import hashlib
import urllib.parse
import json
import time
import urllib.request

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)


# ==========================================
# TELEGRAM INIT DATA VALIDATION
# ==========================================

def validate_init_data(init_data):

    bot_token = os.environ.get(
        "BOT_TOKEN",
        ""
    ).strip()

    if not bot_token:
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

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(
                data.items()
            )
        )

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode("utf-8"),
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
            return None, "Telegram hash validation failed."

        auth_date = data.get(
            "auth_date"
        )

        if auth_date:

            try:

                auth_time = int(
                    auth_date
                )

                if time.time() - auth_time > 3600:

                    return None, (
                        "Verification data expired."
                    )

            except ValueError:

                return None, "Invalid auth_date."

        return data, None

    except Exception as error:

        print(
            "VALIDATION ERROR:",
            repr(error)
        )

        return None, "Validation error."


# ==========================================
# SEND MAIN MENU
# ==========================================

def send_main_menu(
    chat_id,
    first_name
):

    bot_token = os.environ.get(
        "BOT_TOKEN",
        ""
    ).strip()

    if not bot_token:

        print(
            "BOT_TOKEN is missing."
        )

        return False


    # ======================================
    # PREMIUM EMOJI
    # ======================================

    SELAM_EMOJI = (
        "5859691201250201986"
    )

    MONEY_EMOJI = (
        "6190336264940559752"
    )

    LINK_EMOJI = (
        "5379742233853451967"
    )

    WITHDRAW_EMOJI = (
        "6053003027793578665"
    )


    # ======================================
    # MAIN MENU TEXT
    # ======================================

    main_text = (

        f"<tg-emoji emoji-id="
        f"'{SELAM_EMOJI}'>👋</tg-emoji> "

        f"<b>ሰላም {first_name}!</b>\n\n"

        "🎉 <b>እንኳን ወደ ቦቱ "
        "በሰላም መጣህ!</b>\n\n"

        "💰 <b>Balance:</b> 0 Birr\n"

        "💎 <b>TON:</b> 0.0000 TON\n\n"

        "👇 <b>ከታች ያሉትን "
        "options ተጠቀም።</b>"
    )


    # ======================================
    # REPLY KEYBOARD
    # ======================================

    keyboard = {

        "keyboard": [

            [
                {
                    "text": "💰 Balance"
                },
                {
                    "text": "💸 Withdraw"
                }
            ],

            [
                {
                    "text": "🏆 Leaderboard"
                },
                {
                    "text": "👛 Set Wallet"
                }
            ],

            [
                {
                    "text": "👥 Invite"
                }
            ]

        ],

        "resize_keyboard": True,

        "one_time_keyboard": False,

        "is_persistent": True

    }


    # ======================================
    # TELEGRAM BOT API
    # ======================================

    telegram_url = (

        "https://api.telegram.org/bot"

        + bot_token

        + "/sendMessage"
    )


    payload = {

        "chat_id": chat_id,

        "text": main_text,

        "parse_mode": "HTML",

        "reply_markup": keyboard

    }


    try:

        body = json.dumps(
            payload
        ).encode("utf-8")


        req = urllib.request.Request(

            telegram_url,

            data=body,

            headers={
                "Content-Type":
                    "application/json"
            },

            method="POST"

        )


        with urllib.request.urlopen(

            req,

            timeout=15

        ) as response:

            result = (
                response
                .read()
                .decode("utf-8")
            )


        print(
            "TELEGRAM RESPONSE:",
            result
        )


        result_json = json.loads(
            result
        )


        if result_json.get("ok"):

            return True


        print(
            "TELEGRAM ERROR:",
            result_json
        )

        return False


    except Exception as error:

        print(
            "SEND MAIN MENU ERROR:",
            repr(error)
        )

        return False


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
def status():

    token_exists = bool(

        os.environ.get(
            "BOT_TOKEN",
            ""
        ).strip()

    )

    return jsonify({

        "service":
            "Telegram Verification API",

        "status":
            "online",

        "bot_token_configured":
            token_exists

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
        # GET TELEGRAM USER
        # ==================================

        user_data = {}


        if "user" in telegram_data:

            try:

                user_data = json.loads(
                    telegram_data["user"]
                )

            except Exception as error:

                print(
                    "USER JSON ERROR:",
                    repr(error)
                )


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
        # SEND REPLY KEYBOARD MAIN MENU
        # ==================================

        sent = send_main_menu(

            user_id,

            first_name

        )


        if not sent:

            return jsonify({

                "success":
                    False,

                "status":
                    "FAIL",

                "message":
                    "Verification passed, "
                    "but Main Menu could not "
                    "be sent."

            }), 500


        # ==================================
        # SUCCESS
        # ==================================

        return jsonify({

            "success":
                True,

            "status":
                "PASS",

            "message":
                "Verification successful. "
                "Main Menu sent.",

            "user": {

                "id":
                    user_id,

                "first_name":
                    first_name,

                "username":
                    username

            }

        })


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
# LOCAL SERVER
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
