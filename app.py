import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

app = Flask(__name__)
app.secret_key = "SUPER_SECRET_KEY_CHANGE_THIS"

GOOGLE_CLIENT_ID = "906645015267-71r989vufuujrqf8itiak72sbpvnej6e.apps.googleusercontent.com"
CONVERSION_RATE = 10 

users_db = {}

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user, google_client_id=GOOGLE_CLIENT_ID)

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.get_json()
    token = data.get('token')

    try:
        id_info = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        user_id = id_info['sub']
        email = id_info['email']
        name = id_info.get('name', 'User')

        if user_id not in users_db:
            users_db[user_id] = {
                'name': name,
                'email': email,
                'points': 0,
                'balance_sar': 0.0
            }

        session['user_id'] = user_id
        session['user'] = users_db[user_id]

        return jsonify({'success': True, 'user': users_db[user_id]})

    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid Google token'}), 400

@app.route('/api/ads/reward', methods=['POST'])
def reward_user():
    user_id = session.get('user_id')
    if not user_id or user_id not in users_db:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    reward_points = 50
    users_db[user_id]['points'] += reward_points
    users_db[user_id]['balance_sar'] = users_db[user_id]['points'] / CONVERSION_RATE
    session['user'] = users_db[user_id]

    return jsonify({
        'success': True,
        'added_points': reward_points,
        'new_points': users_db[user_id]['points'],
        'new_balance': users_db[user_id]['balance_sar']
    })

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    user_id = session.get('user_id')
    if not user_id or user_id not in users_db:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json()
    amount_sar = float(data.get('amount_sar', 0))
    method = data.get('method')
    account_info = data.get('account_info')

    needed_points = amount_sar * CONVERSION_RATE
    current_points = users_db[user_id]['points']

    if current_points < needed_points:
        return jsonify({'success': False, 'message': 'Insufficient points balance'}), 400

    users_db[user_id]['points'] -= needed_points
    users_db[user_id]['balance_sar'] = users_db[user_id]['points'] / CONVERSION_RATE
    session['user'] = users_db[user_id]

    print(f"[WITHDRAW REQUEST] User: {users_db[user_id]['email']} | Amount: {amount_sar} SAR | Method: {method} | Details: {account_info}")

    return jsonify({
        'success': True,
        'message': f'Withdrawal request for {amount_sar} SAR submitted successfully.',
        'new_points': users_db[user_id]['points'],
        'new_balance': users_db[user_id]['balance_sar']
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)