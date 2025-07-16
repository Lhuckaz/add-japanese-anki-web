import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret')
    DEBUG = False
    TESTING = False
    ENV = 'production'

class DevelopmentConfig(Config):
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    ENV = 'production'

config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig
)
