from flask import Flask
from flask_cors import CORS
from app.routes.users import bp as users_bp
from app.routes.repos import bp2 as repos_bp
from app.routes.commits import bp3 as commits_bp
from app.routes.files import bp4 as files_bp
from app.database import init_db  # Asegúrate que contenga SCHEMA_SQL
from app.routes.branches import bp_branches
app = Flask(__name__)
CORS(app)

# Registrar blueprints
app.register_blueprint(users_bp, url_prefix="/api/users")
app.register_blueprint(repos_bp, url_prefix="/api/repos")
app.register_blueprint(commits_bp,url_prefix="/api/commits")
app.register_blueprint(files_bp, url_prefix="/api/files")
app.register_blueprint(bp_branches,url_prefix="/api/branches")

# Inicializar la base de datos con todas las tablas
init_db(app)
@app.route("/")
def index():
    return "Bienvenido a mi app Flask 🚀"
if __name__ == '__main__':
    for rule in app.url_map.iter_rules():
        print(rule)
    app.run(debug=True)
