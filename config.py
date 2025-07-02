import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_that_you_should_change'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///whois_history.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False