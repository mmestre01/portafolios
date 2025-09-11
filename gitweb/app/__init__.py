
import flask

def create_app():
    app = Flask(__name__)

    # Registra blueprints
    from .routes.users import bp as users_bp
    from .routes.repos import bp as repos_bp
    from .routes.commits import bp as commits_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(repos_bp)
    app.register_blueprint(commits_bp)

    # Inicializa la BD (conectarla y crear tablas si no existen)
    init_db(app)

    return app
