from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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

    # Relaciones
    puntos = db.relationship("Puntos", back_populates="user", uselist=False)
    apuestas = db.relationship("Apuesta", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"


class Puntos(db.Model):
    __tablename__ = "puntos"
    
    id_usuario = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    puntos = db.Column(db.Integer, default=100)

    user = db.relationship("User", back_populates="puntos")

    def __repr__(self):
        return f"<Puntos user_id={self.id_usuario} puntos={self.puntos}>"


class Apuesta(db.Model):
    __tablename__ = "apuestas"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    id_partida = db.Column(db.String, nullable=False)

    apuesta_tipo = db.Column(db.String(20), nullable=False)  # "ganar" o "perder"
    puntos_apostados = db.Column(db.Integer, nullable=False)

    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    resultado = db.Column(db.Boolean, default=None)  # True=acierta, False=falla
    procesada = db.Column(db.Boolean, default=False)

    user = db.relationship("User", back_populates="apuestas")

    def __repr__(self):
        return (f"<Apuesta id={self.id} user_id={self.id_usuario} "
                f"tipo={self.apuesta_tipo} puntos={self.puntos_apostados} "
                f"resultado={self.resultado} procesada={self.procesada}>")

class HistorialPuntos(db.Model):
    __tablename__ = "historial_puntos"
    
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    puntos = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="historial_puntos")

    def __repr__(self):
        return f"<Historial user={self.id_usuario} puntos={self.puntos} fecha={self.fecha}>"

# ----------------------------
# Rutas principales
# ----------------------------
@app.route('/apirift/')
def index():
    return render_template('index.html')
from datetime import datetime
import requests
from urllib.parse import quote

def get_ids_from_riot_id(game_name: str, tag_line: str, api_key: str):
    """Devuelve (puuid, summoner_id) usando account-v1 + summoner-v4(by-puuid). Incluye prints de depuración."""
    headers = {"X-Riot-Token": api_key}
    region_routing = "europe"
    region_platform = "euw1"

    # 1) Riot ID -> PUUID (account-v1)
    url_account = f"https://{region_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(game_name)}/{quote(tag_line)}"
    r_acc = requests.get(url_account, headers=headers)
    print(f"📡 account-v1 URL: {url_account}")
    print(f"   ↳ status: {r_acc.status_code}, resp: {r_acc.text}")
    if r_acc.status_code != 200:
        return None, None
    puuid = r_acc.json().get("puuid")

    # 2) PUUID -> Summoner (summoner-v4 by-puuid)  => necesitamos el 'id' (encryptedSummonerId)
    url_sum_by_puuid = f"https://{region_platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r_sum = requests.get(url_sum_by_puuid, headers=headers)
    print(f"📡 summoner-v4(by-puuid) URL: {url_sum_by_puuid}")
    print(f"   ↳ status: {r_sum.status_code}, resp: {r_sum.text}")
    if r_sum.status_code != 200:
        return puuid, None

    sum_payload = r_sum.json()
    summoner_id = sum_payload.get("id")  # <- ESTE es el que requiere spectator

    # Nota: con algunas keys de desarrollo, Riot puede devolver un payload "recortado"
    # sin 'id' ni 'name'. Si viene None, no podremos consultar spectator.
    if not summoner_id:
        print("⚠️ summoner-v4(by-puuid) ha devuelto un payload sin 'id'. "
              "Con algunas dev keys Riot oculta campos personales en EU. "
              "Soluciones: intentar otra key, o integrar RSO y usar /summoner/v4/summoners/me.")
    return puuid, summoner_id

def procesar_apuesta(apuesta, headers):
    """Verifica el resultado de la partida y actualiza puntos."""
    url_match = f"https://europe.api.riotgames.com/lol/match/v5/matches/{apuesta.id_partida}"
    r_match = requests.get(url_match, headers=headers)

    if r_match.status_code != 200:
        return

    match_data = r_match.json()
    if "info" not in match_data:
        return

    # Buscar al usuario
    puuid = apuesta.user.puntos.user.summoner_name
    participant = next((p for p in match_data["info"]["participants"] if p["puuid"] == puuid), None)
    if not participant:
        return

    win = participant.get("win", False)

    if (win and apuesta.apuesta_tipo == "ganar") or (not win and apuesta.apuesta_tipo == "perder"):
        apuesta.resultado = True
        apuesta.user.puntos.puntos += apuesta.puntos_apostados  # Ganó → duplica
    else:
        apuesta.resultado = False
        apuesta.user.puntos.puntos -= apuesta.puntos_apostados  # Perdió → resta

    apuesta.procesada = True
    db.session.commit()



@app.route('/apirift/apuestas')
def apuestas():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user.summoner_name or not user.tagline:
        flash("Configura tu Riot ID en Ajustes antes de apostar.", "error")
        return redirect(url_for('perfil'))

    headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}
    region_routing = "europe"
    region_platform = "euw1"

    # Ranking de puntos global
    ranking_puntos = (
        db.session.query(User.username, Puntos.puntos)
        .join(Puntos, User.id == Puntos.id_usuario)
        .order_by(Puntos.puntos.desc())
        .all()
    )

    # Historial de puntos del usuario
    historial = (
        Apuesta.query.filter_by(id_usuario=user.id)
        .order_by(Apuesta.fecha.asc())
        .all()
    )
    puntos_actuales = user.puntos.puntos if user.puntos else 0

    # 1) Riot ID -> PUUID
    url_account = f"https://{region_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(user.summoner_name)}/{quote(user.tagline)}"
    r_acc = requests.get(url_account, headers=headers)
    if r_acc.status_code != 200:
        # No bloqueamos, solo mostramos ranking
        return render_template("apuestas.html",
                               user=user,
                               puede_apostar=False,
                               ranking_puntos=ranking_puntos,
                               historial=historial,
                               puntos_actuales=puntos_actuales)

    puuid = r_acc.json().get("puuid")

    # 2) Spectator con PUUID
    url_active = f"https://{region_platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    r_active = requests.get(url_active, headers=headers)

    if r_active.status_code != 200:
        # No está en partida → mostrar ranking
        return render_template("apuestas.html",
                               user=user,
                               puede_apostar=False,
                               ranking_puntos=ranking_puntos,
                               historial=historial,
                               puntos_actuales=puntos_actuales)

    game_info = r_active.json()
    game_start_ms = game_info.get("gameStartTime")
    game_id = str(game_info.get("gameId"))

    # 3) comprobar tiempo de partida
    inicio = datetime.fromtimestamp(game_start_ms / 1000.0)
    minutos = (datetime.utcnow() - inicio).total_seconds() / 60.0
    puede_apostar = minutos <= 5

    return render_template("apuestas.html",
                           user=user,
                           puede_apostar=puede_apostar,
                           game_id=game_id,
                           ranking_puntos=ranking_puntos,
                           historial=historial,
                           puntos_actuales=puntos_actuales)


from urllib.parse import quote

def get_puuid_from_user(user, api_key):
    headers = {"X-Riot-Token": api_key}
    region_routing = "europe"
    url_account = f"https://{region_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(user.summoner_name)}/{quote(user.tagline)}"
    r = requests.get(url_account, headers=headers)
    print(f"[get_puuid] {url_account} -> {r.status_code}")
    if r.status_code != 200:
        print(f"[get_puuid] resp: {r.text}")
        return None
    return r.json().get("puuid")

def procesar_apuesta(apuesta, api_key):
    """
    Verifica el resultado de la partida donde se apostó y liquida la apuesta.
    - apuesta.id_partida = gameId NUMÉRICO de spectator
    - buscamos en match-v5 (por puuid) el match cuyo info.gameId == int(id_partida)
    - si ganó y apostó 'ganar' (o perdió y apostó 'perder') => sumamos 2x lo apostado (ya se restó al apostar)
    - si perdió => no hacemos nada más (el stake ya fue descontado)
    """
    if apuesta.procesada:
        return False  # ya hecha

    headers = {"X-Riot-Token": api_key}
    region_routing = "europe"

    user = apuesta.user
    puuid = get_puuid_from_user(user, api_key)
    if not puuid:
        print("[procesar_apuesta] No PUUID para user", user.username)
        return False

    # 1) ids recientes
    url_ids = f"https://{region_routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10"
    r_ids = requests.get(url_ids, headers=headers)
    print(f"[procesar_apuesta] {url_ids} -> {r_ids.status_code}")
    if r_ids.status_code != 200:
        print("[procesar_apuesta] resp:", r_ids.text)
        return False

    match_ids = r_ids.json() or []
    try:
        target_game_id = int(apuesta.id_partida)
    except (TypeError, ValueError):
        print("[procesar_apuesta] id_partida inválido:", apuesta.id_partida)
        return False

    found = None
    for mid in match_ids:
        url_match = f"https://{region_routing}.api.riotgames.com/lol/match/v5/matches/{mid}"
        r_match = requests.get(url_match, headers=headers)
        print(f"[procesar_apuesta] {url_match} -> {r_match.status_code}")
        if r_match.status_code != 200:
            continue
        data = r_match.json()
        info = data.get("info", {})
        if info.get("gameId") == target_game_id:
            found = info
            break

    if not found:
        print("[procesar_apuesta] No encontrado match con info.gameId =", target_game_id)
        return False

    # 2) localizar participante por PUUID y ver si ganó
    participant = next((p for p in found.get("participants", []) if p.get("puuid") == puuid), None)
    if not participant:
        print("[procesar_apuesta] No participant con ese puuid")
        return False

    gano = bool(participant.get("win", False))

    # 3) liquidación
    if (gano and apuesta.apuesta_tipo == "ganar") or ((not gano) and apuesta.apuesta_tipo == "perder"):
        # al apostar restamos 'puntos_apostados'; si gana, añadimos 2x => neto +1x
        apuesta.resultado = True
        if apuesta.user.puntos is None:
            # por si acaso
            apuesta.user.puntos = Puntos(id_usuario=apuesta.user.id, puntos=0)
        apuesta.user.puntos.puntos += (apuesta.puntos_apostados * 2)
    else:
        # perdió: no tocamos nada (el stake ya se restó al apostar)
        apuesta.resultado = False

    apuesta.procesada = True
    db.session.commit()
    return True

@app.route("/apirift/realizar_apuesta", methods=["POST"])
def realizar_apuesta():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    apuesta_tipo = request.form.get("apuesta_tipo")
    game_id = request.form.get("game_id")
    puntos_raw = request.form.get("puntos_apostados")

    if not game_id or not puntos_raw or not apuesta_tipo:
        flash("Datos de apuesta incompletos", "error")
        return redirect(url_for("apuestas"))

    puntos = int(puntos_raw)

    if not user.puntos or user.puntos.puntos < puntos:
        flash("No tienes suficientes puntos", "error")
        return redirect(url_for("apuestas"))

    # crear apuesta y descontar stake
    ap = Apuesta(
        id_usuario=user.id,
        id_partida=str(game_id),  # guardamos el gameId numérico de spectator
        apuesta_tipo=apuesta_tipo,
        puntos_apostados=puntos,
        procesada=False,
        resultado=None
    )
    user.puntos.puntos -= puntos

    db.session.add(ap)
    db.session.commit()

    flash("Apuesta registrada ✅", "success")
    return redirect(url_for("apuestas"))



from flask import jsonify

@app.route("/apirift/check_game_status")
def check_game_status():
    if "user_id" not in session:
        return jsonify({"error": "No logueado"})

    user = User.query.get(session["user_id"])
    headers = {"X-Riot-Token": app.config["RIOT_API_KEY"]}
    region_routing = "europe"
    region_platform = "euw1"

    # 1) PUUID
    url_account = f"https://{region_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(user.summoner_name)}/{quote(user.tagline)}"
    r_acc = requests.get(url_account, headers=headers)
    if r_acc.status_code != 200:
        return jsonify({"en_partida": False, "partida_finalizada": False})

    puuid = r_acc.json().get("puuid")

    # 2) Spectator
    url_active = f"https://{region_platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    r_active = requests.get(url_active, headers=headers)

    if r_active.status_code == 200:
        game_info = r_active.json()
        game_start_ms = game_info.get("gameStartTime")
        game_id = str(game_info.get("gameId"))
        inicio = datetime.fromtimestamp(game_start_ms / 1000.0)
        minutos = (datetime.utcnow() - inicio).total_seconds() / 60.0
        puede_apostar = minutos <= 5

        return jsonify({
            "en_partida": True,
            "puede_apostar": puede_apostar,
            "game_id": game_id,
            "partida_finalizada": False
        })

    # 3) No está en partida -> ¿hay apuestas pendientes que liquidar?
    apuestas_pendientes = Apuesta.query.filter_by(id_usuario=user.id, procesada=False).all()
    if not apuestas_pendientes:
        return jsonify({"en_partida": False, "partida_finalizada": False})

    algo_procesado = False
    for ap in apuestas_pendientes:
        try:
            ok = procesar_apuesta(ap, app.config["RIOT_API_KEY"])
            if ok:
                algo_procesado = True
        except Exception as e:
            print("[check_game_status] error procesando apuesta", ap.id, e)

    # Solo avisamos de finalización si había apuestas y conseguimos procesar algo
    return jsonify({
        "en_partida": False,
        "partida_finalizada": algo_procesado
    })


@app.route('/apirift/register', methods=['GET', 'POST'])
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
        

        # 🔹 Crear fila de puntos inicial
        user_points = Puntos(id_usuario=user.id, puntos=100)
        db.session.add(user_points)
        db.session.commit()

        flash("Registro exitoso, ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/apirift/login', methods=['GET', 'POST'])
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

@app.route('/apirift/logout')
def logout():
    session.pop('user_id', None)
    flash("Has cerrado sesión.", "info")
    return redirect(url_for('login'))

@app.route("/apirift/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    ultima_apuesta = None
    if user.apuestas:
        ultima_apuesta = Apuesta.query.filter_by(id_usuario=user.id).order_by(Apuesta.id.desc()).first()

    return render_template("dashboard.html", user=user, ultima_apuesta=ultima_apuesta)







@app.route('/apirift/perfil', methods=['GET', 'POST'])
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

@app.route('/apirift/search', methods=['GET', 'POST'])
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


@app.route('/apirift/stats')
def stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    print(f"➡️ Entrando en /stats con usuario {user.username}")

    if not user.summoner_name or not user.tagline:
        flash("Este usuario no tiene Riot ID configurado", "error")
        return redirect(url_for("perfil"))  # por si quieres mandar a settings

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




@app.route('/apirift/ranking')
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
