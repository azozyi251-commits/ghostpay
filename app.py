import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests

app = Flask(__name__)

# إعدادات أمان الجلسات والتشفير
app.secret_key = os.environ.get("SECRET_KEY", "ghostpay_super_secret_key_2026")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # تفعيل الأمان عبر HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
GOOGLE_CLIENT_ID = "906645015267-71r989vufuujrqf8itiak72sbpvnej6e.apps.googleusercontent.com"

# ذاكرة الحماية الزمنية ضد السكربتات البوتات (In-memory Rate Limiter)
USER_LAST_REWARD_TIME = {}
USER_LAST_AI_TIME = {}

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL variable is missing in Render!")
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                google_id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                name TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                balance_sar REAL DEFAULT 0.0
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("PostgreSQL Initialized Successfully.")
    except Exception as e:
        print("Database Init Error:", e)

init_db()

def get_user(google_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT google_id, email, name, points, balance_sar FROM users WHERE google_id = %s;", (google_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        print("Get User Error:", e)
        return None

def create_or_get_user(google_id, email, name):
    user = get_user(google_id)
    if not user:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (google_id, email, name, points, balance_sar) VALUES (%s, %s, %s, 0, 0.0);",
                (google_id, email, name)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return {"google_id": google_id, "email": email, "name": name, "points": 0, "balance_sar": 0.0}
        except Exception as e:
            print("Create User Error:", e)
    return user

def update_user_balance(google_id, added_points, added_sar):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET points = points + %s, balance_sar = balance_sar + %s WHERE google_id = %s;",
            (added_points, added_sar, google_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Update Balance Error:", e)

@app.route("/")
def index():
    user_data = None
    if "user_id" in session:
        user_data = get_user(session["user_id"])
    return render_template("index.html", user=user_data, google_client_id=GOOGLE_CLIENT_ID)

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
        return jsonify({"success": False, "message": "يرجى تسجيل الدخول أولاً لحفظ نقاطك"})

    google_id = session["user_id"]
    current_time = time.time()

    # حماية ضد البوتات والتكرار السريع (منع إرسال طلبات قبل مرور 3 ثوانٍ)
    last_time = USER_LAST_REWARD_TIME.get(google_id, 0)
    if current_time - last_time < 3.0:
        return jsonify({
            "success": False, 
            "message": "تم اكتشاف طلبات سريعة جداً! يرجى الانتظار 3 ثوانٍ بين كل تفاعل."
        }), 429

    USER_LAST_REWARD_TIME[google_id] = current_time

    update_user_balance(google_id, added_points=50, added_sar=0.50)
    updated_user = get_user(google_id)

    return jsonify({
        "success": True,
        "new_points": updated_user["points"],
        "new_balance": float(updated_user["balance_sar"])
    })

@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "يرجى تسجيل الدخول أولاً"})

    data = request.get_json() or {}
    try:
        amount_sar = float(data.get("amount_sar", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "المبلغ المدخل غير صالح"})

    method = data.get("method", "").strip()
    account_info = data.get("account_info", "").strip()

    if amount_sar <= 0 or not method or not account_info:
        return jsonify({"success": False, "message": "يرجى إدخال جميع بيانات السحب بشكل صحيح"})

    google_id = session["user_id"]
    user = get_user(google_id)

    if not user or float(user["balance_sar"]) < amount_sar:
        return jsonify({"success": False, "message": "رصيدك غير كافي للسحب"})

    deduct_points = int(amount_sar * 100)
    update_user_balance(google_id, added_points=-deduct_points, added_sar=-amount_sar)
    updated_user = get_user(google_id)

    return jsonify({
        "success": True,
        "message": f"تم استلام طلب سحب {amount_sar} ريال عبر {method} بنجاح! سيتم التحويل إلى ({account_info}) قريباً.",
        "new_points": updated_user["points"],
        "new_balance": float(updated_user["balance_sar"])
    })

@app.route("/api/ai-guide", methods=["POST"])
def ai_guide():
    if "user_id" in session:
        google_id = session["user_id"]
        current_time = time.time()
        last_ai = USER_LAST_AI_TIME.get(google_id, 0)
        if current_time - last_ai < 10.0:
            return jsonify({
                "success": False,
                "message": "يرجى الانتظار 10 ثوانٍ قبل إرسال سؤال آخر للذكاء الاصطناعي."
            }), 429
        USER_LAST_AI_TIME[google_id] = current_time

    data = request.get_json() or {}
    user_question = data.get("question", "").strip()

    if not user_question:
        return jsonify({"success": False, "message": "يرجى كتابة سؤال أولاً"})

    if not GEMINI_API_KEY:
        return jsonify({
            "success": False,
            "message": "مفتاح API غير معرف في Environment Variables."
        })

    system_prompt = "أنت مساعد ذكي خاص بموقع GhostPay. وظيفتك فقط توضيح وشرح فائدة الموقع للزوار: الموقع يقدم مكافآت وأرباح فورية عند التفاعل والضغط كل 3 ثواني، ويمكن تحويل النقاط إلى STC Pay أو UrPay. اشرح بأسلوب سايبر حماسي ومختصر جداً وبدون خروج عن هذا الموضوع."

    models_to_try = ["gemini-3.8-flash", "gemini-1.5-flash"]
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\nسؤال الزائر: {user_question}"}]
            }
        ]
    }

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
            res_data = res.json()

            if "candidates" in res_data and len(res_data["candidates"]) > 0:
                reply = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"success": True, "reply": reply})
        except Exception as e:
            print(f"Error trying model {model}:", e)

    return jsonify({
        "success": False,
        "message": "السيرفر يواجه ضغطاً عالياً حالياً، يرجى المحاولة بعد بضع ثوانٍ."
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
