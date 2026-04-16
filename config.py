import os

class Config:
    SECRET_KEY = "medassist_secret_key"
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'medassist_db'
    # Ajout du chemin pour ffmpeg local
    FFMPEG_PATH = os.path.dirname(os.path.abspath(__file__))