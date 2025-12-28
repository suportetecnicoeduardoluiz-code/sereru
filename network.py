import socketio
import requests
from config import URL_SERVIDOR

sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=1)

def conectar():
    if not sio.connected:
        try: sio.connect(URL_SERVIDOR)
        except: pass

def enviar_heartbeat(hostname, user):
    if sio.connected:
        try: sio.emit('status_update', {'hostname': hostname, 'status': 'logado' if user else 'livre', 'user': user or ''})
        except: pass