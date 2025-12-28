from .extensions import db
from datetime import datetime

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    senha_engrenagem = db.Column(db.String(50), default="admin")
    senha_mestre = db.Column(db.String(50), default="admin")
    
    # --- Wallpapers ---
    wallpaper_login = db.Column(db.String(200), default="default_login.jpg")
    wallpaper_desktop = db.Column(db.String(200), default="default_desktop.jpg")
    wallpaper_chat = db.Column(db.String(200), default="default_chat.jpg")
    
    # --- ADICIONE ESTA LINHA AQUI ---
    wall_quiosque = db.Column(db.String(200), nullable=True)
    # --------------------------------

    logo_atual = db.Column(db.String(200), nullable=True)
    databit_nome = db.Column(db.String(50), default="DataBit")
    databit_comando = db.Column(db.String(300), default="")
    databit_tipo = db.Column(db.String(20), default="site")
    caminho_cofre_global = db.Column(db.String(300), default="C:\\Cofres")
    caminho_datinet_global = db.Column(db.String(300), default="C:\\Datinet")
    caminho_drive_z = db.Column(db.String(300), default="C:\\DriveZ")
    icon_chrome = db.Column(db.String(200), nullable=True)
    icon_firefox = db.Column(db.String(200), nullable=True)
    icon_edge = db.Column(db.String(200), nullable=True)
    termos_ativo = db.Column(db.Boolean, default=False)
    termos_texto = db.Column(db.Text, default="Ao utilizar este computador, você concorda com as regras de uso.")
    chat_saudacao = db.Column(db.Text, default="Olá! Em que posso ajudar?")
    
    # Créditos
    dev_linha1 = db.Column(db.String(200), default="Desenvolvido Por Eng Eduardo Luiz Da Costa")
    dev_linha2 = db.Column(db.String(200), default="Programador Guilherme Gonsalves")
    dev_linha3 = db.Column(db.String(50), default="2026")

    # Limite de Upload
    max_upload_size_mb = db.Column(db.Integer, default=2048)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50))

class Setor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    sobrenome = db.Column(db.String(100))
    usuario = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50))
    setor = db.Column(db.String(300))
    sem_restricao = db.Column(db.Boolean, default=False)

class Impressora(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_exibicao = db.Column(db.String(100)) 
    caminho_rede = db.Column(db.String(300))
    setores_permitidos = db.Column(db.String(300), default="Todos")

class Computador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20))
    usuario_atual = db.Column(db.String(50), nullable=True)
    ultimo_visto = db.Column(db.DateTime, default=datetime.now)

class Restricao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20))
    alvo = db.Column(db.String(200))

class Atalho(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50))
    comando = db.Column(db.String(300))
    tipo = db.Column(db.String(20))
    icone = db.Column(db.String(200), nullable=True)
    setores = db.Column(db.String(300), default="Livre") 

class Ramal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    setor = db.Column(db.String(100))
    numero = db.Column(db.String(20))

class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100))
    usuario_real = db.Column(db.String(100))
    remetente = db.Column(db.String(50))
    mensagem = db.Column(db.Text)
    data_hora = db.Column(db.DateTime, default=datetime.now)

class ChatHistorico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    computador = db.Column(db.String(100))
    usuario = db.Column(db.String(100))
    conversa_completa = db.Column(db.Text)
    data_fim = db.Column(db.DateTime, default=datetime.now)

class LogAcesso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    computador = db.Column(db.String(100))
    usuario = db.Column(db.String(100))
    acao = db.Column(db.String(20))
    data_hora = db.Column(db.DateTime, default=datetime.now)

class LogArquivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, default=datetime.now)
    hostname = db.Column(db.String(100))
    usuario = db.Column(db.String(100))
    acao = db.Column(db.String(50))
    arquivo = db.Column(db.String(300))

class PastaSetor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_exibicao = db.Column(db.String(100))
    caminho_rede = db.Column(db.String(300))
    setores_permitidos = db.Column(db.String(300), default="Todos")
    permite_escrita = db.Column(db.Boolean, default=True)

class LogPasta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, default=datetime.now)
    hostname = db.Column(db.String(100))
    usuario = db.Column(db.String(100))
    pasta_aberta = db.Column(db.String(150))

class ArquivoIcone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    extensao = db.Column(db.String(20), unique=True)
    nome_arquivo = db.Column(db.String(200))