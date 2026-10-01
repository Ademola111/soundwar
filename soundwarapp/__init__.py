#first open init beside the template folder which is the top root init.
# after the init inside the template next is config.py not in instance
import flask
import flask_wtf.csrf
import flask_sqlalchemy
import flask_migrate
import flask_mail
from soundwarapp.utils.email import mail
import flask_jwt_extended
import flask_limiter
import flask_limiter.util
import flask_cors
from soundwarapp import config

db = flask_sqlalchemy.SQLAlchemy()
migrate = flask_migrate.Migrate()
mail = flask_mail.Mail()
jwt = flask_jwt_extended.JWTManager()
csrf = flask_wtf.csrf.CSRFProtect()
limiter = flask_limiter.Limiter(flask_limiter.util.get_remote_address, default_limits=["200 per day", "50 per hour"])

def create_app(config_name="production", *args, **kwargs):
    app = flask.Flask(__name__, instance_relative_config=True)

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

    cors_origins = app.config.get("CORS_ORIGINS", [])
    if isinstance(cors_origins, str):
        cors_origins = [cors_origins]

    frontend_url = app.config.get("FRONTEND_URL")
    if frontend_url:
        cors_origins.append(frontend_url)

    default_origins = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    allowed_origins = list(dict.fromkeys([origin for origin in [*cors_origins, *default_origins] if origin]))

    flask_cors.CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
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
    from soundwarapp.utils import blacklist
    
    #load the reparticipation scheduler
    from soundwarapp.utils.reparticipation import start_reparticipation_scheduler

    # load models
    from soundwarapp.models import User, Artist, Song, Vote, Contest, ContestWinner, Payment, TokenBlocklist

    from soundwarapp.myroutes import admin, artists, auth, leaderboard, payments, songs, votes

    # Start the background notification scheduler for past winners.
    # start_reparticipation_scheduler(app)
    
    __all__ = ["db", "migrate", "mail", "jwt", "csrf", "limiter", "create_app"]

    return app