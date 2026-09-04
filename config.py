import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Clave para sesiones, flashes, etc.
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")

    # Si tienes DATABASE_URL en variables de entorno (por ejemplo Postgres en producción),
    # la usará. Si no, usa un SQLite local.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "sqlite:///" + os.path.join(basedir, "app.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Modo desarrollo por defecto
    DEBUG = True

    # DIGAME configuration
    DIGAME_ENABLED = os.environ.get("DIGAME_ENABLED", "true").lower() == "true"
    DIGAME_ADMIN_KEY = os.environ.get("DIGAME_ADMIN_KEY", "change_me")
    RASPBERRY_TOKEN = os.environ.get("RASPBERRY_TOKEN", "change_me")
    DIGAME_MOCK_RASPBERRY = os.environ.get("DIGAME_MOCK_RASPBERRY", "true").lower() == "true"
    DIGAME_MAX_SECONDS = int(os.environ.get("DIGAME_MAX_SECONDS", 10))
    DIGAME_MAX_FILE_MB = int(os.environ.get("DIGAME_MAX_FILE_MB", 3))
    DIGAME_MAX_QUEUE = int(os.environ.get("DIGAME_MAX_QUEUE", 10))
    DIGAME_ALLOWED_MIMES = ["audio/webm", "audio/ogg", "audio/mpeg", "audio/wav"]


class ProductionConfig(Config):
    DEBUG = False
    # Aquí podrías añadir cosas específicas de producción,
    # como cookies seguras, etc. si quieres más adelante.

