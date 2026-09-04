import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import time
import urllib.parse

import websockets
import requests

SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:5000')
RASPBERRY_TOKEN = os.environ.get('RASPBERRY_TOKEN', 'change_me')
ALSA_DEVICE = os.environ.get('ALSA_DEVICE', 'default')
DOWNLOAD_DIR = pathlib.Path(__file__).resolve().parent / 'downloads'
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_ws_url():
    parsed = urllib.parse.urlparse(SERVER_URL)
    scheme = 'wss' if parsed.scheme == 'https' else 'ws'
    return urllib.parse.urlunparse((scheme, parsed.netloc, '/ws/digame', '', f'token={urllib.parse.quote(RASPBERRY_TOKEN)}', ''))


def download_audio(url):
    local_name = DOWNLOAD_DIR / pathlib.Path(urllib.parse.urlparse(url).path).name
    print(f'Descargando audio a {local_name}')
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(local_name, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return str(local_name)


def play_audio(path):
    print(f'Reproduciendo audio desde {path} en {ALSA_DEVICE}')
    if shutil.which('ffmpeg') and shutil.which('aplay'):
        wav_path = str(pathlib.Path(path).with_suffix('.wav'))
        decoder = subprocess.run(
            [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-y',
                '-i', path,
                '-ar', '48000',
                wav_path,
            ],
            stderr=subprocess.PIPE,
            text=True,
        )
        if decoder.returncode != 0:
            raise RuntimeError(f'ffmpeg falló ({decoder.returncode}): {decoder.stderr.strip()}')
        player = subprocess.run(
            ['aplay', '-D', ALSA_DEVICE, wav_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if player.returncode != 0:
            raise RuntimeError(f'aplay falló ({player.returncode}): {player.stderr.strip()}')
    elif shutil.which('ffplay'):
        result = subprocess.run(
            ['ffplay', '-nodisp', '-autoexit', path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f'ffplay falló ({result.returncode}): {result.stderr.strip()}')
    elif shutil.which('aplay'):
        result = subprocess.run(
            ['aplay', '-D', ALSA_DEVICE, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f'aplay falló ({result.returncode}): {result.stderr.strip()}')
    else:
        print('No se encontró reproductor local. Simulando reproducción durante 4 segundos...')
        time.sleep(4)


async def consume():
    ws_url = get_ws_url()
    while True:
        try:
            print(f'Conectando a {ws_url}')
            async with websockets.connect(ws_url) as ws:
                print('Conectado al servidor Digame.')
                while True:
                    message = await ws.recv()
                    payload = json.loads(message)
                    print('Recibido:', payload)
                    if payload.get('type') == 'play':
                        audio_url = payload.get('audioUrl')
                        audio_id = payload.get('id')
                        try:
                            path = download_audio(audio_url)
                            play_audio(path)
                            await ws.send(json.dumps({'type': 'played', 'id': audio_id}))
                            print('Reproducción confirmada.')
                        except Exception as exc:
                            await ws.send(json.dumps({'type': 'error', 'id': audio_id, 'message': str(exc)}))
                            print('Error en reproducción:', exc)
                    else:
                        print('Evento no reconocido:', payload)
        except Exception as exc:
            print('Conexión perdida. Reintentando en 5 segundos...', exc)
            await asyncio.sleep(5)


if __name__ == '__main__':
    asyncio.run(consume())
