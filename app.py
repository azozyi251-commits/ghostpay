import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests

# تعريف التطبيق باسم app ليتعرف عليه Gunicorn تلقائياً
app = Flask(__name__)

# إعدادات أمان الجلسات والتشفير
app.secret_key = os.environ.get("SECRET_KEY", "ghostpay_super_secret_key_2026")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
GOOGLE_CLIENT_ID = "906645015267-71r989vufuujrqf8itiak72sbpvnej6e.apps.googleusercontent.com"

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL variable is missing in Render!")
    
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if "?" not in url:
        url += "?sslmode=require"
    else:
        url += "&sslmode=require"
        
    return psycopg2.connect(url)
