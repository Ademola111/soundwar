import os

#the config that is not inside instance
class Config(object):
    DATABASE_URI="kg968nbfkk876 "
    MERCHANT_ID="SAMPLE"



class ProductionConfig(Config):
    """connecting database"""
    # SQLALCHEMY_DATABASE_URI="mysql+mysqlconnector://styleitafrica:AdemolaStyle#1@styleitafrica.mysql.pythonanywhere-services.com/styleitafrica$styleit"
    SQLALCHEMY_DATABASE_URI="mysql+mysqlconnector://root@127.0.0.1/styleit"
    SQLALCHEMY_TRACK_MODIFICATIONS=True

    MERCHANT_ID="dg8765@hj#"

    """"configuring socketio notification"""
    DEVELOPMENT = True
    DEBUG = True
    # """integrating socketio"""
    # socketio_integration = os.environ.get('INTEGRATE_SOCKETIO')
    # if socketio_integration == 'true':
    #     INTEGRATE_SOCKETIO = True
    # else:
    #     INTEGRATE_SOCKETIO = False

class DevelopmentConfig(Config):
    """connecting database"""
    SQLALCHEMY_DATABASE_URI="Development DB URI here"
    SQLALCHEMY_TRACK_MODIFICATIONS=True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"