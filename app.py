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

    # رابط الموديل الجديد المعتمد
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
