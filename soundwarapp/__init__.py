#first open init beside the template folder which is the top root init.
# after the init inside the template next is config.py not in instance
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from soundwarapp.utils.email import mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from soundwarapp import config

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
jwt = JWTManager()
csrf = CSRFProtect()
limiter = Limiter(get_remote_address, default_limits=["200 per day", "50 per hour"])

def create_app(config_name="production", *args, **kwargs):
    app = Flask(__name__, instance_relative_config=True)

    if config_name == "testing":
        app.config.from_object(config.TestingConfig)

    elif config_name == "development":
        app.config.from_object(config.DevelopmentConfig)
        
    else:
        app.config.from_object(config.ProductionConfig)

    app.config.from_pyfile("config.py", silent=True)

    """folders"""
    app.config['UPLOAD_FOLDER'] = '/soundwarapp/static/images/artist/'
    app.config['UPLOAD_FOLDER2'] = '/soundwarapp/static/images/user/'

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    CORS(
        app,
        # resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
        origins=[app.config['FRONTEND_URL'],'http://localhost:5173', 'http://localhost:3000'], 
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Import blueprints
    from soundwarapp.myroutes.admin import admin_bp
    from soundwarapp.myroutes.artists import artists_bp
    from soundwarapp.myroutes.auth import auth_bp
    from soundwarapp.myroutes.leaderboard import leaderboard_bp
    from soundwarapp.myroutes.payments import payments_bp
    from soundwarapp.myroutes.songs import songs_bp
    from soundwarapp.myroutes.votes import votes_bp

    # Register blueprints
    app.register_blueprint(admin_bp)
    app.register_blueprint(artists_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(songs_bp)
    app.register_blueprint(votes_bp)
   

    #load blacklist model for jwt token revocation
    from soundwarapp import utils

    # load models
    from soundwarapp import models

    from soundwarapp import myroutes
    
    return app