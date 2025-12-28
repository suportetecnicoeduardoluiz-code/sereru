from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
# Configuração exata do seu app.py original
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading', max_http_buffer_size=1000000000, ping_timeout=60, ping_interval=25)
FILA_ATENDIMENTO = []