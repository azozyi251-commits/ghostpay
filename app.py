import os
import sqlite3
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests

# إعلان تطبيق Flask الرئيسي
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ghostpay_super_secret_key_2026")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GOOGLE_CLIENT_ID = (
    "906645015267-71r989vufuujrqf8itiak72sbpvnej6e.apps.googleusercontent.com"
)

DB_FILE = "ghostpay.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            google_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            balance_sar REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()


init_db()


def get_user(google_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT google_id, email, name, points, balance_sar FROM users WHERE google_id = ?",
        (google_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "google_id": row[0],
            "email": row[1],
            "name": row[2],
            "points": row[3],
            "balance_sar": row[4],
        }
    return None


def create_or_get_user(google_id, email, name):
    user = get_user(google_id)
    if not user:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (google_id, email, name, points, balance_sar) VALUES (?, ?, ?, 0, 0.0)",
            (google_id, email, name),
        )
        conn.commit()
        conn.close()
        return {
            "google_id": google_id,
            "email": email,
            "name": name,
            "points": 0,
            "balance_sar": 0.0,
        }
    return user


def update_user_balance(google_id, added_points, added_sar):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET points = points + ?, balance_sar = balance_sar + ? WHERE google_id = ?",
        (added_points, added_sar, google_id),
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    user_data = None
    if "user_id" in session:
        user_data = get_user(session["user_id"])
    return render_template(
        "index.html", user=user_data, google_client_id=GOOGLE_CLIENT_ID
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/auth/google", methods=["POST"])
def auth_google():
    data = request.get_json() or {}
    token = data.get("token")
    if not token:
        return jsonify({"success": False, "message": "No token provided"})

    try:
        id_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        google_id = id_info["sub"]
        email = id_info.get("email", "")
        name = id_info.get("name", "User")

        user = create_or_get_user(google_id, email, name)
        session["user_id"] = user["google_id"]
        return jsonify({"success": True})
    except Exception as e:
        print("Auth error:", e)
        return jsonify({"success": False, "message": "Invalid token"})


@app.route("/api/ads/reward", methods=["POST"])
def ads_reward():
    if "user_id" not in session:
        return jsonify(
            {"success": False, "message": "يرجى تسجيل الدخول أولاً لحفظ نقاطك"}
        )

    google_id = session["user_id"]
    update_user_balance(google_id, added_points=50, added_sar=0.50)
    updated_user = get_user(google_id)

    return jsonify({
        "success": True,
        "new_points": updated_user["points"],
        "new_balance": updated_user["balance_sar"],
    })


@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "يرجى تسجيل الدخول أولاً"})

    data = request.get_json() or {}
    amount_sar = float(data.get("amount_sar", 0))
    method = data.get("method", "")
    account_info = data.get("account_info", "")

    google_id = session["user_id"]
    user = get_user(google_id)

    if user["balance_sar"] < amount_sar:
        return jsonify({"success": False, "message": "رصيدك غير كافي للسحب"})

    deduct_points = int(amount_sar * 100)
    update_user_balance(google_id, added_points=-deduct_points, added_sar=-amount_sar)
    updated_user = get_user(google_id)

    return jsonify({
        "success": True,
        "message": f"تم استلام طلب سحب {amount_sar} ريال عبر {method} بنجاح! سيتم التحويل إلى ({account_info}) قريباً.",
        "new_points": updated_user["points"],
        "new_balance": updated_user["balance_sar"],
    })


@app.route("/api/ai-guide", methods=["POST"])
def ai_guide():
    data = request.get_json() or {}
    user_question = data.get("question", "")

    if not GEMINI_API_KEY:
        return jsonify({
            "success": False,
            "message": "مفتاح API غير معرف في Environment Variables.",
        })

    system_prompt = "أنت مساعد ذكي خاص بموقع GhostPay. وظيفتك فقط توضيح وشرح فائدة الموقع للزوار: الموقع يقدم مكافآت وأرباح فورية عند التفاعل والضغط كل 3 ثواني، ويمكن تحويل النقاط إلى STC Pay أو UrPay. اشرح بأسلوب سايبر حماسي ومختصر جداً وبدون خروج عن هذا الموضوع."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\nسؤال الزائر: {user_question}"}]
            }
        ]
    }

    try:
        res = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}
        )
        res_data = res.json()

        if "candidates" in res_data and len(res_data["candidates"]) > 0:
            reply = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return jsonify({"success": True, "reply": reply})
        else:
            error_msg = res_data.get("error", {}).get("message", "استجابة غير متوقعة من API")
            print("Gemini API Error Detail:", res_data)
            return jsonify({
                "success": False,
                "message": f"خطأ من سيرفر الذكاء الاصطناعي: {error_msg}",
            })

    except Exception as e:
        print("Error in AI Guide:", e)
        return jsonify({
            "success": False,
            "message": "تعذر الاتصال بالذكاء الاصطناعي.",
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
