import os
import hmac
import hashlib
import urllib.parse
import json
import time
import urllib.request

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

BOT_USERNAME = os.environ.get(
    "BOT_USERNAME",
    "YOUR_BOT_USERNAME"
).strip().lstrip("@")

MIN_WITHDRAW = 10.0


# =========================================================
# SIMPLE DATABASE
# =========================================================
# WARNING:
# This database is stored in RAM.
# Restarting Flask will reset the data.
# =========================================================

users = {}


def get_user(user_id, first_name="User", username=""):
    """
    Create user if not exists.
    """

    user_id = str(user_id)

    if user_id not in users:

        users[user_id] = {
            "id": user_id,
            "first_name": first_name or "User",
            "username": username or "",
            "balance": 0.0,
            "wallet": "",
            "referrals": 0,
            "referred_by": None,
            "withdrawals": []
        }

    else:

        users[user_id]["first_name"] = (
            first_name or users[user_id]["first_name"]
        )

        users[user_id]["username"] = (
            username or users[user_id]["username"]
        )

    return users[user_id]


# =========================================================
# TELEGRAM INIT DATA VALIDATION
# =========================================================

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
            return None, "Telegram hash validation failed."

        auth_date = data.get("auth_date")

        if auth_date:

            try:

                auth_time = int(auth_date)

                if time.time() - auth_time > 3600:
                    return None, "Verification data expired."

            except ValueError:

                return None, "Invalid auth_date."

        return data, None

    except Exception as error:

        print(
            "VALIDATION ERROR:",
            repr(error)
        )

        return None, "Validation error."


# =========================================================
# TELEGRAM API
# =========================================================

def telegram_request(method, payload):

    if not BOT_TOKEN:
        return False, {
            "description": "BOT_TOKEN is missing."
        }

    telegram_url = (
        "https://api.telegram.org/bot"
        + BOT_TOKEN
        + "/"
        + method
    )

    try:

        body = json.dumps(
            payload
        ).encode("utf-8")

        req = urllib.request.Request(

            telegram_url,

            data=body,

            headers={
                "Content-Type": "application/json"
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

        result_json = json.loads(result)

        return (
            result_json.get("ok", False),
            result_json
        )

    except Exception as error:

        print(
            "TELEGRAM API ERROR:",
            repr(error)
        )

        return False, {
            "description": str(error)
        }


# =========================================================
# MAIN MENU
# =========================================================

def send_main_menu(chat_id, first_name):

    SELAM_EMOJI = "5859691201250201986"

    main_text = (

        f"<tg-emoji emoji-id='{SELAM_EMOJI}'>👋</tg-emoji> "

        f"<b>ሰላም {first_name}!</b>\n\n"

        "🎉 <b>እንኳን ወደ ቦቱ "
        "በሰላም መጣህ!</b>\n\n"

        "💰 <b>Balance:</b> 0 Birr\n"

        "💎 <b>TON:</b> 0.0000 TON\n\n"

        "👇 <b>ከታች ያሉትን options ተጠቀም።</b>"
    )

    keyboard = {

        "keyboard": [

            [
                {
                    "text": "💰 Balance"
                    "icon_custom_emoji_id":MONEY_EMOJI
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

    ok, result = telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": main_text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }
    )

    print(
        "MAIN MENU:",
        result
    )

    return ok


# =========================================================
# AUTHENTICATE MINI APP USER
# =========================================================

def authenticate_user():

    body = request.get_json(
        silent=True
    )

    if not body:
        return None, (
            jsonify({
                "success": False,
                "message": "Request body is missing."
            }),
            400
        )

    init_data = body.get(
        "initData",
        ""
    )

    telegram_data, error = validate_init_data(
        init_data
    )

    if telegram_data is None:

        return None, (
            jsonify({
                "success": False,
                "message": error
            }),
            403
        )

    user_data = {}

    if "user" in telegram_data:

        try:

            user_data = json.loads(
                telegram_data["user"]
            )

        except Exception:

            return None, (
                jsonify({
                    "success": False,
                    "message": "Invalid Telegram user data."
                }),
                400
            )

    user_id = user_data.get("id")

    if not user_id:

        return None, (
            jsonify({
                "success": False,
                "message": "Telegram user ID not found."
            }),
            400
        )

    first_name = user_data.get(
        "first_name",
        "User"
    )

    username = user_data.get(
        "username",
        ""
    )

    user = get_user(
        user_id,
        first_name,
        username
    )

    return user, None


# =========================================================
# HOME
# =========================================================

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


# =========================================================
# STATUS
# =========================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def status():

    return jsonify({

        "service":
            "Telegram Mini App API",

        "status":
            "online",

        "bot_token_configured":
            bool(BOT_TOKEN),

        "users":
            len(users)

    })


# =========================================================
# VERIFY
# =========================================================

@app.route(
    "/api/verify",
    methods=["POST"]
)
def verify():

    user, error_response = authenticate_user()

    if user is None:
        return error_response

    sent = send_main_menu(
        user["id"],
        user["first_name"]
    )

    if not sent:

        return jsonify({

            "success": False,

            "status": "FAIL",

            "message":
                "Verification passed but Main Menu could not be sent."

        }), 500

    return jsonify({

        "success": True,

        "status": "PASS",

        "message":
            "Verification successful.",

        "user": user

    })


# =========================================================
# BALANCE
# =========================================================

@app.route(
    "/api/balance",
    methods=["POST"]
)
def balance():

    user, error_response = authenticate_user()

    if user is None:
        return error_response

    return jsonify({

        "success": True,

        "balance": user["balance"],

        "wallet": user["wallet"],

        "referrals": user["referrals"]

    })


# =========================================================
# SET WALLET
# =========================================================

@app.route(
    "/api/wallet",
    methods=["POST"]
)
def set_wallet():

    user, error_response = authenticate_user()

    if user is None:
        return error_response

    body = request.get_json(
        silent=True
    ) or {}

    wallet = str(
        body.get(
            "wallet",
            ""
        )
    ).strip()

    if not wallet:

        return jsonify({

            "success": False,

            "message":
                "Wallet address is required."

        }), 400

    if len(wallet) < 10:

        return jsonify({

            "success": False,

            "message":
                "Wallet address is too short."

        }), 400

    user["wallet"] = wallet

    return jsonify({

        "success": True,

        "message":
            "Wallet saved successfully.",

        "wallet":
            wallet

    })


# =========================================================
# WITHDRAW
# =========================================================

@app.route(
    "/api/withdraw",
    methods=["POST"]
)
def withdraw():

    user, error_response = authenticate_user()

    if user is None:
        return error_response

    body = request.get_json(
        silent=True
    ) or {}

    try:

        amount = float(
            body.get(
                "amount",
                0
            )
        )

    except Exception:

        return jsonify({

            "success": False,

            "message":
                "Invalid amount."

        }), 400

    if amount <= 0:

        return jsonify({

            "success": False,

            "message":
                "Amount must be greater than 0."

        }), 400

    if amount < MIN_WITHDRAW:

        return jsonify({

            "success": False,

            "message":
                f"Minimum withdrawal is {MIN_WITHDRAW} Birr."

        }), 400

    if amount > user["balance"]:

        return jsonify({

            "success": False,

            "message":
                "Insufficient balance."

        }), 400

    if not user["wallet"]:

        return jsonify({

            "success": False,

            "message":
                "Please set your wallet first."

        }), 400

    withdrawal = {

        "amount": amount,

        "wallet": user["wallet"],

        "status": "PENDING",

        "created_at": int(time.time())

    }

    user["balance"] -= amount

    user["withdrawals"].append(
        withdrawal
    )

    return jsonify({

        "success": True,

        "message":
            "Withdrawal request submitted.",

        "withdrawal":
            withdrawal,

        "remaining_balance":
            user["balance"]

    })


# =========================================================
# LEADERBOARD
# =========================================================

@app.route(
    "/api/leaderboard",
    methods=["POST"]
)
def leaderboard():

    user, error_response = authenticate_user()

    if user is None:
        return error_response

    sorted_users = sorted(

        users.values(),

        key=lambda x: (
            x["balance"],
            x["referrals"]
        ),

        reverse=True
    )

    top_users = []

    for index, item in enumerate(
        sorted_users[:10],
        start=1
    ):

        top_users.append({

            "rank":
                index,

            "first_name":
                item["first_name"],

            "username":
                item["username"],

            "balance":
                item["balance"],

            "referrals":
                item["referrals"]

        })

    user_rank = None

    for index, item in enumerate(
        sorted_users,
        start=1
    ):

        if item["id"] == user["id"]:

            user_rank = index
            break

    return jsonify({

        "success": True,

        "leaderboard":
            top_users,

        "your_rank":
            user_rank

    })


# =========================================================
# INVITE
# =========================================================

@app.route(
    "/api/invite",
    methods=["POST"]
)
def invite():

    user, error_response = authenticate_user()

    if user is None:
        return error_response

    referral_link = (
        f"https://t.me/{BOT_USERNAME}"
        f"?start=ref_{user['id']}"
    )

    return jsonify({

        "success": True,

        "referrals":
            user["referrals"],

        "referral_link":
            referral_link

    })


# =========================================================
# USER INFO
# =========================================================

@app.route(
    "/api/me",
    methods=["POST"]
)
def me():

    user, error_response = authenticate_user()

    if user is None:
        return error_response

    return jsonify({

        "success": True,

        "user": user

    })


# =========================================================
# LOCAL SERVER
# =========================================================

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
