#first open init beside the template folder which is the top root init.
# after the init inside the template next is config.py not in instance
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from styleitapp import config

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
    app.config['UPLOAD_FOLDER'] = '/home/styleitafrica/styleit/styleitapp/static/images/profile/customer/'
    app.config['UPLOAD_FOLDER2'] = '/home/styleitafrica/styleit/styleitapp/static/images/profile/designer/'
    app.config['POST_IMAGE'] = '/home/styleitafrica/styleit/styleitapp/static/images/postpic/'
    app.config['COMPLETE_TASK'] = "/home/styleitafrica/styleit/styleitapp/static/images/completed_task/"
    app.config['desveri_pic'] = "/home/styleitafrica/styleit/styleitapp/static/images/profile/designer/vpic/"
    app.config['cusveri_pic'] = "/home/styleitafrica/styleit/styleitapp/static/images/profile/customer/vpic/"

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173", "https://styleit2-0.vercel.app"]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Import blueprints
    from styleitapp.myroutes.adminroutes import admin_bp
    from styleitapp.myroutes.adminroutes_api import admin_api_bp
    from styleitapp.myroutes.userroutes import user_bp
    from styleitapp.myroutes.userroutes_api import user_api_bp

    # Register blueprints
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(user_api_bp)
    
    #load blacklist model for jwt token revocation
    from styleitapp.blacklist import TokenBlocklist

    # load models
    from styleitapp import models

    #Load forms
    from styleitapp import forms

    """Loading serializers"""
    from styleitapp import serializers

    return app