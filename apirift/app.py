from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
from datetime import datetime

# Cargar configuración desde config.py
from config import DevelopmentConfig

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Inicializar extensiones
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ----------------------------
# Modelos de la base de datos
# ----------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    # Datos de LoL
    summoner_name = db.Column(db.String(150), nullable=True)
    tagline = db.Column(db.String(10), nullable=True)

class Puntos(db.Model):
    __tablename__ = "puntos"
    id_usuario = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    puntos = db.Column(db.Integer, default=100)
    user = db.relationship("User", backref="puntos", uselist=False)

class Apuesta(db.Model):
    __tablename__ = "apuestas"
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("users.id"))
    id_partida = db.Column(db.String, nullable=False)
    apuesta_tipo = db.Column(db.String, nullable=False)  # "ganar" o "perder"
    puntos_apostados = db.Column(db.Integer, nullable=False)
    resultado = db.Column(db.Boolean, default=None)  # True=acierta, False=falla
    procesada = db.Column(db.Boolean, default=False)
    user = db.relationship("User", backref="apuestas")

# ----------------------------
# Rutas principales
# ----------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        # Verificar si el usuario ya existe
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash("Ese usuario o email ya está registrado.", "error")
            return redirect(url_for('register'))

        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()

        flash("Registro exitoso, ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash("Inicio de sesión exitoso.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Correo o contraseña incorrectos.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Has cerrado sesión.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Debes iniciar sesión para acceder al dashboard.", "error")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)




@app.route('/apuestas')
def apuestas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Aquí irá la lógica de apuestas
    return render_template('apuestas.html')

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.summoner_name = request.form.get('summoner_name')
        user.tagline = request.form.get('tagline')
        db.session.commit()
        flash("Datos de invocador guardados correctamente.", "success")
        return redirect(url_for('dashboard'))

    return render_template('perfil.html', user=user)
import requests
from urllib.parse import quote
from config import DevelopmentConfig

# Obtener PUUID desde summoner_name + tagline
def get_puuid(summoner_name, tagline):
    """
    Devuelve el PUUID de un invocador a partir de su Riot ID.
    """
    region = "europe"  # routing value para EU
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(summoner_name)}/{tagline}"
    headers = {"X-Riot-Token": app.config["RIOT_API_KEY"]}

    print("➡️ Llamando a Riot API:", url)
    r = requests.get(url, headers=headers)
    print("➡️ Status:", r.status_code)

    if r.status_code == 200:
        data = r.json()
        print("✅ get_puuid result:", data)
        return data.get("puuid")
    else:
        try:
            print("❌ Error en get_puuid:", r.json())
        except:
            print("❌ Error en get_puuid (raw):", r.text)
        return None

def get_summoner_info(puuid):
    """
    Devuelve información del invocador (nivel, icono, etc.)
    a partir de su PUUID.
    """
    region = "euw1"  # plataforma, no routing
    url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": app.config["RIOT_API_KEY"]}

    print("➡️ Llamando a Summoner-V4:", url)
    r = requests.get(url, headers=headers)
    print("➡️ Status:", r.status_code)

    if r.status_code == 200:
        data = r.json()
        print("✅ get_summoner_info result:", data)
        return {
            "summonerLevel": data.get("summonerLevel"),
            "profileIconId": data.get("profileIconId"),
            "puuid": data.get("puuid")
        }
    else:
        try:
            print("❌ Error en get_summoner_info:", r.json())
        except:
            print("❌ Error en get_summoner_info (raw):", r.text)
        return None

@app.route('/search', methods=['GET', 'POST'])
def search():
    headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}
    region_routing = "europe"
    region_platform = "euw1"

    summoner_info = None
    elo_data = None
    match_details = []

    if request.method == 'POST':
        summoner_name = request.form.get('summoner_name')
        tagline = request.form.get('tagline')
        match_count = int(request.form.get('match_count', 5))

        print(f"➡️ Buscando {summoner_name}#{tagline}, últimas {match_count} partidas")

        # Paso 1: obtener puuid
        url_account = f"https://{region_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(summoner_name)}/{tagline}"
        r_account = requests.get(url_account, headers=headers)
        print(f"📡 Account-v1 URL: {url_account}")
        print(f"📡 Status: {r_account.status_code}, Response: {r_account.text}")
        if r_account.status_code != 200:
            flash("No se pudo obtener el PUUID de este invocador", "error")
            return render_template("search.html")

        puuid = r_account.json().get("puuid")

        # Paso 2: obtener datos de perfil
        url_summoner = f"https://{region_platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        r_summoner = requests.get(url_summoner, headers=headers)
        if r_summoner.status_code == 200:
            summoner_info = r_summoner.json()

        # Paso 3: obtener elo
        url_rank = f"https://{region_platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        r_rank = requests.get(url_rank, headers=headers)
        if r_rank.status_code == 200:
            entries = r_rank.json()
            entry = next((e for e in entries if e["queueType"] == "RANKED_SOLO_5x5"), None)
            if not entry and entries:
                entry = entries[0]
            if entry:
                wins = entry.get("wins", 0)
                losses = entry.get("losses", 0)
                total = wins + losses
                winrate = f"{int((wins / total) * 100)}%" if total > 0 else "-"
                elo_data = {
                    "tier": entry.get("tier"),
                    "rank": entry.get("rank"),
                    "lp": entry.get("leaguePoints"),
                    "wins": wins,
                    "losses": losses,
                    "winrate": winrate
                }

        # Paso 4: obtener últimas partidas
        url_matches = f"https://{region_routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={match_count}"
        r_matches = requests.get(url_matches, headers=headers)
        if r_matches.status_code == 200:
            match_ids = r_matches.json()
            for match_id in match_ids:
                url_match = f"https://{region_routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
                r_match = requests.get(url_match, headers=headers)
                if r_match.status_code == 200:
                    match_data = r_match.json()
                    participant = next((p for p in match_data["info"]["participants"] if p["puuid"] == puuid), None)
                    if participant:
                        match_details.append({
                            "result": "Victoria" if participant["win"] else "Derrota",
                            "champion": participant["championName"],
                            "kda": f"{participant['kills']}/{participant['deaths']}/{participant['assists']}",
                            "damage": participant["totalDamageDealtToChampions"],
                            "date": datetime.fromtimestamp(match_data['info']['gameStartTimestamp'] / 1000).strftime('%d/%m/%Y')
                        })

    return render_template("search.html",
                           summoner_info=summoner_info,
                           elo_data=elo_data,
                           match_details=match_details)


@app.route('/stats')
def stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    print(f"➡️ Entrando en /stats con usuario {user.username}")

    if not user.summoner_name or not user.tagline:
        flash("Este usuario no tiene Riot ID configurado", "error")
        return redirect(url_for("settings"))  # por si quieres mandar a settings

    summoner_name = user.summoner_name
    tagline = user.tagline
    region_routing = "europe"
    region_platform = "euw1"
    headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}

    # Paso 1: obtener PUUID
    url_account = f"https://{region_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(summoner_name)}/{tagline}"
    r_account = requests.get(url_account, headers=headers)
    print(f"📡 Account-v1 URL: {url_account}")
    print(f"📡 Status: {r_account.status_code}, Response: {r_account.text}")
    if r_account.status_code != 200:
        flash("No se pudo obtener el PUUID del invocador", "error")
        return redirect(url_for("dashboard"))
    puuid = r_account.json().get("puuid")
    print(f"✅ PUUID: {puuid}")

    # Paso 2: obtener datos de perfil
    url_summoner = f"https://{region_platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r_summoner = requests.get(url_summoner, headers=headers)
    print(f"📡 Summoner-v4 URL: {url_summoner}")
    print(f"📡 Status: {r_summoner.status_code}, Response: {r_summoner.text}")
    if r_summoner.status_code != 200:
        flash("No se pudo obtener info del invocador", "error")
        return redirect(url_for("dashboard"))
    summoner_info = r_summoner.json()
    print(f"✅ Summoner info: {summoner_info}")

    # Paso 3: obtener Elo
    url_rank = f"https://{region_platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    r_rank = requests.get(url_rank, headers=headers)
    print(f"📡 League-v4 URL: {url_rank}")
    print(f"📡 Status: {r_rank.status_code}, Response: {r_rank.text}")
    elo_data = None
    if r_rank.status_code == 200:
        entries = r_rank.json()
        entry = next((e for e in entries if e["queueType"] == "RANKED_SOLO_5x5"), None)
        if not entry and entries:
            entry = entries[0]
        if entry:
            wins = entry.get("wins", 0)
            losses = entry.get("losses", 0)
            total = wins + losses
            winrate = f"{int((wins / total) * 100)}%" if total > 0 else "-"
            elo_data = {
                "tier": entry.get("tier"),
                "rank": entry.get("rank"),
                "lp": entry.get("leaguePoints"),
                "wins": wins,
                "losses": losses,
                "winrate": winrate
            }
    print(f"✅ Elo data: {elo_data}")

    # Paso 4: obtener últimas partidas
    url_matches = f"https://{region_routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
    r_matches = requests.get(url_matches, headers=headers)
    print(f"📡 Matches-v5 URL: {url_matches}")
    print(f"📡 Status: {r_matches.status_code}, Response: {r_matches.text[:200]}...")
    match_details = []
    if r_matches.status_code == 200:
        match_ids = r_matches.json()
        print(f"✅ Match IDs: {match_ids}")
        for match_id in match_ids:
            url_match = f"https://{region_routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            r_match = requests.get(url_match, headers=headers)
            print(f"   📡 Match detail URL: {url_match}")
            if r_match.status_code == 200:
                match_data = r_match.json()
                participant = next((p for p in match_data["info"]["participants"] if p["puuid"] == puuid), None)
                if participant:
                    details = {
                        "result": "Victoria" if participant["win"] else "Derrota",
                        "champion": participant["championName"],
                        "kda": f"{participant['kills']}/{participant['deaths']}/{participant['assists']}",
                        "damage": participant["totalDamageDealtToChampions"],
                        "date": datetime.fromtimestamp(match_data['info']['gameStartTimestamp'] / 1000).strftime('%d/%m/%Y')
                    }
                    match_details.append(details)
                    print(f"   ✅ Match detail added: {details}")

    return render_template("stats.html",
                           summoner_info=summoner_info,
                           elo_data=elo_data,
                           match_details=match_details,
                           user=user)




@app.route('/ranking')
def ranking():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}
    region_routing = "europe"
    region_platform = "euw1"

    users = User.query.filter(User.summoner_name.isnot(None)).all()
    user_ranks = []

    for u in users:
        print(f"\n👤 Procesando {u.username} ({u.summoner_name}#{u.tagline})")

        # Paso 1: obtener puuid
        url_account = f"https://{region_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(u.summoner_name)}/{u.tagline}"
        r_account = requests.get(url_account, headers=headers)
        if r_account.status_code != 200:
            print(f"❌ Error account-v1: {r_account.text}")
            continue
        puuid = r_account.json().get("puuid")

        # Paso 2: obtener elo por puuid
        url_rank = f"https://{region_platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        r_rank = requests.get(url_rank, headers=headers)
        if r_rank.status_code != 200:
            print(f"❌ Error league-v4: {r_rank.text}")
            continue

        rank_data = r_rank.json()
        print("➡️ rank_data:", rank_data)

        # Buscar soloQ, si no existe tomar la primera
        entry = next((e for e in rank_data if e["queueType"] == "RANKED_SOLO_5x5"), None)
        if not entry and rank_data:
            entry = rank_data[0]

        if entry:
            wins = entry.get("wins", 0)
            losses = entry.get("losses", 0)
            total = wins + losses
            winrate = f"{int((wins / total) * 100)}%" if total > 0 else "-"
            user_ranks.append({
                "username": u.username,
                "summoner_name": u.summoner_name,
                "tagline": u.tagline,
                "tier": entry.get("tier", "Unranked"),
                "rank": entry.get("rank", ""),
                "lp": entry.get("leaguePoints", 0),
                "wins": wins,
                "losses": losses,
                "winrate": winrate
            })
        else:
            user_ranks.append({
                "username": u.username,
                "summoner_name": u.summoner_name,
                "tagline": u.tagline,
                "tier": "Unranked",
                "rank": "",
                "lp": 0,
                "wins": 0,
                "losses": 0,
                "winrate": "-"
            })

    # Ordenar por Elo (tier > rank > LP)
    tier_priority = {
        "CHALLENGER": 1, "GRANDMASTER": 2, "MASTER": 3,
        "DIAMOND": 4, "PLATINUM": 5, "GOLD": 6,
        "SILVER": 7, "BRONZE": 8, "IRON": 9, "Unranked": 10
    }
    rank_priority = {"I": 1, "II": 2, "III": 3, "IV": 4}

    user_ranks.sort(key=lambda x: (
        tier_priority.get(x["tier"], 99),
        rank_priority.get(x["rank"], 99),
        -x["lp"]
    ))

    return render_template("ranking.html", user_ranks=user_ranks)





def get_ranked_info(puuid):
    """
    Devuelve tier, rank, LP, wins, losses a partir del PUUID.
    """
    headers = {"X-Riot-Token": app.config["RIOT_API_KEY"]}

    # Paso 1: obtener summonerId desde Summoner-V4
    region_platform = "euw1"  # plataforma (EUW, NA1, etc.)
    url_summoner = f"https://{region_platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r = requests.get(url_summoner, headers=headers)

    if r.status_code != 200:
        print("❌ Error en get_ranked_info (summoner):", r.text)
        return None

    summoner_data = r.json()
    summoner_id = summoner_data.get("id")
    if not summoner_id:
        print("❌ No se encontró summonerId en summoner_data:", summoner_data)
        return None

    # Paso 2: obtener elo desde League-V4
    url_rank = f"https://{region_platform}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    r2 = requests.get(url_rank, headers=headers)

    if r2.status_code != 200:
        print("❌ Error en get_ranked_info (rank):", r2.text)
        return None

    rank_data = r2.json()
    if not rank_data:
        return {
            "tier": "Unranked",
            "rank": "",
            "lp": 0,
            "wins": 0,
            "losses": 0
        }

    # Normalmente el primer objeto es soloQ
    ranked = rank_data[0]
    return {
        "tier": ranked.get("tier", "Unranked"),
        "rank": ranked.get("rank", ""),
        "lp": ranked.get("leaguePoints", 0),
        "wins": ranked.get("wins", 0),
        "losses": ranked.get("losses", 0)
    }


# ----------------------------
# Ejecutar la app    source venv/bin/activate
# ----------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # crea las tablas si no existen
    app.run(debug=True, port=5001)
