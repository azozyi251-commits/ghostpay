import os
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

# جلب المفتاح من متغيرات البيئة لحمايته من GitHub Secret Scanning
GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY", "AQ.Ab8RN6JmCkC38JnNOzZdLdRv9pHMqWVubYs2JBm3TS8SXAKCzw"
)

# ضَع هنا الـ Client ID الحقيقي المأخوذ من Google Cloud Console
# مثال: "1234567890-abc123def456.apps.googleusercontent.com"
GOOGLE_CLIENT_ID = "906645015267-71r989vufuujrqf8itiak72sbpvnej6e.apps.googleusercontent.com
"


@app.route("/")
def index():
    user_data = None  # بيانات المستخدم إذا كان مسجلاً دخول
    return render_template(
        "index.html", user=user_data, google_client_id=GOOGLE_CLIENT_ID
    )


# --- API المسارات الخاصة بالموقع ---


@app.route("/api/auth/google", methods=["POST"])
def auth_google():
    return jsonify({"success": True})


@app.route("/api/ads/reward", methods=["POST"])
def ads_reward():
    return jsonify({"success": True, "new_points": 50, "new_balance": 5.00})


@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    return jsonify({
        "success": True,
        "message": "تم إرسال طلب السحب بنجاح!",
        "new_points": 0,
        "new_balance": 0.00,
    })


# --- مسار المساعد الذكي (Ghost AI Guide) ---
@app.route("/api/ai-guide", methods=["POST"])
def ai_guide():
    data = request.get_json()
    user_question = data.get("question", "")

    system_prompt = "أنت مساعد ذكي خاص بموقع GhostPay. وظيفتك فقط توضيح وشرح فائدة الموقع للزوار: الموقع يقدم مكافآت وأرباح فورية عند التفاعل والضغط كل 3 ثواني، ويمكن تحويل النقاط إلى STC Pay أو UrPay. اشرح بأسلوب سايبر حماسي ومختصر جداً وبدون خروج عن هذا الموضوع."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {"parts": [{"text": system_prompt + "\nسؤال الزائر: " + user_question}]}
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
            return jsonify({
                "success": False,
                "message": "عذراً، لم أستطع معالجة الإجابة حالياً.",
            })

    except Exception as e:
        print("Error in AI Guide:", e)
        return jsonify({
            "success": False,
            "message": "تعذر الاتصال بالذكاء الاصطناعي.",
        })


if __name__ == "__main__":
    app.run(debug=True)
