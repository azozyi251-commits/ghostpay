def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL variable is missing in Render!")
    
    # إصلاح البادئة وتفعيل تشفير SSL الإجباري للبيانات
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if "?" not in url:
        url += "?sslmode=require"
    else:
        url += "&sslmode=require"
        
    return psycopg2.connect(url)
