from datetime import timedelta
import os

JWT_TOKEN_LOCATION = ["headers", "cookies"]
JWT_HEADER_NAME = "Authorization"
JWT_HEADER_TYPE = "Bearer"
JWT_COOKIE_SECURE = False
JWT_COOKIE_HTTPONLY = True
JWT_COOKIE_CSRF_PROTECT = True
JWT_COOKIE_SAMESITE = "Lax"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=1)
BCRYPT_LOG_ROUNDS = 13
WTF_CSRF_ENABLED = True
DEBUG_TB_ENABLED = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

# Frontend URL
FRONTEND_URL = "http://localhost:8080"
CORS_ORIGINS = [
    FRONTEND_URL,
    "http://127.0.0.1:8080",
    "http://localhost:8080",
]

# File uploads
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
UPLOAD_FOLDER2 = os.environ.get('UPLOAD_FOLDER2', 'uploads')
MAX_CONTENT_LENGTH = 15 * 1024 * 1024  # 15MB
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}

# Contest settings
ARTIST_REGISTRATION_FEE = int(os.environ.get('ARTIST_REGISTRATION_FEE', 15000))
WINNER_BLOCK_MONTHS = 24
REPARTICIPATION_REMINDER_INTERVAL_HOURS = int(os.environ.get('REPARTICIPATION_REMINDER_INTERVAL_HOURS', 24))


# Mail settings
MAIL_SERVER='smtp.gmail.com'
MAIL_PORT=465
MAIL_USE_SSL=True
MAIL_USE_TLS=False

# mail account
MAIL_DEFAULT_SENDER = ['Soundwar HQ', 'noreply@soundwar.com.ng']
