import os, sys

def get_app_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_PATH = get_app_path()
ARQUIVO_IP = os.path.join(APP_PATH, "config_ip.txt")
BANCO_CACHE = os.path.join(APP_PATH, "cache_cliente.db")
PASTA_ICONES = os.path.join(APP_PATH, "cache_icones")
PASTA_TEMP_EDIT = os.path.join(os.getenv('TEMP'), "SeveroEditCache") 

# Imagens locais
IMG_LOGIN = os.path.join(APP_PATH, "img_login.jpg")
IMG_DESKTOP = os.path.join(APP_PATH, "img_desktop.jpg")
IMG_CHAT = os.path.join(APP_PATH, "img_chat.jpg")
LOGO_CACHE = os.path.join(APP_PATH, "logo_cache.png")

# Globais de Configuração
CONFIG_DATABIT = {'nome': 'DataBit', 'comando': 'https://google.com', 'tipo': 'site'}
SENHA_ENGRENAGEM = "admin"
CAMINHO_DATINET_LOCAL = "C:\\Datinet"
CAMINHO_DRIVE_Z_LOCAL = "C:\\DriveZ"

for p in [PASTA_ICONES, PASTA_TEMP_EDIT]:
    if not os.path.exists(p): os.makedirs(p)
if not os.path.exists(CAMINHO_DATINET_LOCAL): 
    try: os.makedirs(CAMINHO_DATINET_LOCAL)
    except: pass

def ler_url_servidor():
    if os.path.exists(ARQUIVO_IP):
        with open(ARQUIVO_IP, "r") as f:
            ip = f.read().strip()
            if ip: return f"http://{ip}"
    return 'http://127.0.0.1:5000'

def salvar_url_servidor(ip_bruto):
    with open(ARQUIVO_IP, "w") as f: 
        f.write(ip_bruto.replace("http://", "").replace("/", ""))

URL_SERVIDOR = ler_url_servidor()