from flask import Flask
from .extensions import db, socketio, FILA_ATENDIMENTO
from .routes import bp
from .events import *
import os, threading, time
from datetime import datetime, timedelta
from .models import Computador, Config

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave_datisevero_msg_system'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///datisevero.db'

# Configuração Padrão Inicial (Será sobrescrita pelo banco)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024 

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'wallpapers')
app.config['ICONS_FOLDER'] = os.path.join(app.root_path, 'static', 'icons')
app.config['LOGOS_FOLDER'] = os.path.join(app.root_path, 'static', 'logos')

for folder in [app.config['UPLOAD_FOLDER'], app.config['ICONS_FOLDER'], app.config['LOGOS_FOLDER']]:
    if not os.path.exists(folder): os.makedirs(folder)

db.init_app(app)
socketio.init_app(app)
app.register_blueprint(bp)

def monitorar_offline():
    while True:
        time.sleep(10)
        with app.app_context():
            try:
                limite = datetime.now() - timedelta(seconds=45)
                pcs = Computador.query.filter(Computador.ultimo_visto < limite, Computador.status != 'offline').all()
                for pc in pcs:
                    pc.status = 'offline'
                    pc.usuario_atual = ''
                    if pc.hostname in FILA_ATENDIMENTO:
                        FILA_ATENDIMENTO.remove(pc.hostname)
                    socketio.emit('update_painel', {'id': pc.id, 'status': 'offline', 'user': ''}, to='admins')
                if pcs: db.session.commit()
            except: pass

if __name__ == '__main__':
    threading.Thread(target=monitorar_offline, daemon=True).start()
    with app.app_context():
        try:
            # --- MIGRATIONS (ATUALIZAÇÃO DE BANCO) ---
            inspector = db.inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('config')]
            
            if 'caminho_drive_z' not in columns:
                db.session.execute(db.text('ALTER TABLE config ADD COLUMN caminho_drive_z VARCHAR(300) DEFAULT "C:\\DriveZ"'))
            
            if 'dev_linha1' not in columns:
                db.session.execute(db.text('ALTER TABLE config ADD COLUMN dev_linha1 VARCHAR(200) DEFAULT "Desenvolvido Por Eng Eduardo Luiz Da Costa"'))
                db.session.execute(db.text('ALTER TABLE config ADD COLUMN dev_linha2 VARCHAR(200) DEFAULT "Programador Guilherme Gonsalves"'))
                db.session.execute(db.text('ALTER TABLE config ADD COLUMN dev_linha3 VARCHAR(50) DEFAULT "2026"'))
            
            # --- CRIA A COLUNA PARA O PAPEL DE PAREDE DO QUIOSQUE ---
            if 'wall_quiosque' not in columns:
                print("Atualizando BD: Criando coluna wallpaper quiosque...")
                db.session.execute(db.text('ALTER TABLE config ADD COLUMN wall_quiosque VARCHAR(100)'))
            
            # Nova coluna para limite de upload
            if 'max_upload_size_mb' not in columns:
                print("Atualizando BD: Criando limite de upload...")
                db.session.execute(db.text('ALTER TABLE config ADD COLUMN max_upload_size_mb INTEGER DEFAULT 2048'))
                
            db.session.commit()
        except Exception as e: print(f"Erro Migração: {e}")
        
        db.create_all()
        
        # --- APLICA A CONFIGURAÇÃO DE TAMANHO MÁXIMO AO INICIAR ---
        try:
            conf = Config.query.first()
            if conf and conf.max_upload_size_mb:
                # Converte MB para Bytes
                app.config['MAX_CONTENT_LENGTH'] = conf.max_upload_size_mb * 1024 * 1024
                print(f"Limite de Upload definido para: {conf.max_upload_size_mb} MB")
        except: pass

    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)