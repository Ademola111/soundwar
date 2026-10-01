import os

#the config that is not inside instance
class Config(object):
    DATABASE_URI = os.environ.get("DATABASE_URI")
    MERCHANT_ID="SAMPLE"
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT")
    ADMIN_SETUP_KEY = os.environ.get("ADMIN_SETUP_KEY")
    FLUTTERWAVE_SECRET_KEY = os.environ.get("FLUTTERWAVE_SECRET_KEY")
    FLUTTERWAVE_PUBLIC_KEY = os.environ.get("FLUTTERWAVE_PUBLIC_KEY")
    FLUTTERWAVE_ENCRYPTION_KEY = os.environ.get("FLUTTERWAVE_ENCRYPTION_KEY")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")



class ProductionConfig(Config):
    """connecting database"""
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+mysqlconnector://root@127.0.0.1/soundwars"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MERCHANT_ID = os.environ.get("MERCHANT_ID")
    PRODUCTION = True
    DEBUG = False

    # """"configuring socketio notification"""
    # """integrating socketio"""
    # socketio_integration = os.environ.get('INTEGRATE_SOCKETIO')
    # if socketio_integration == 'true':
    #     INTEGRATE_SOCKETIO = True
    # else:
    #     INTEGRATE_SOCKETIO = False

class DevelopmentConfig(Config):
    """connecting database"""
    DEVELOPMENT = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_SQLALCHEMY_DATABASE_URI",
        "mysql+mysqlconnector://root@127.0.0.1/soundwars_dev"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only-secret-key"
    JWT_SECRET_KEY = "test-only-jwt-signing-key-32-bytes"
    MAIL_SUPPRESS_SEND = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_SQLALCHEMY_DATABASE_URI",
        "sqlite:///:memory:"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# config = {
#     'development': DevelopmentConfig,
#     'production': ProductionConfig,
#     'testing': TestingConfig,
#     'default': ProductionConfig
# }