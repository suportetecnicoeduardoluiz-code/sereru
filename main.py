import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, font
import sqlite3, os, sys, socket, requests, threading, time, subprocess, ctypes, base64
import shutil # Importante para copiar arquivos locais
from io import BytesIO
from PIL import Image, ImageTk
from datetime import datetime

# Imports Locais (Tratamento de erro para execução direta)
try:
    from config import *
    from services.network import sio, conectar, enviar_heartbeat
    from gui.arquivos import JanelaArquivos
    from gui.quiosque import QuiosqueFrame
    from utils import criar_atalho_inicializacao, bloquear_teclas, desbloquear_teclas, montar_drive_z, desmontar_drive_z, lancar_navegador_seguro
except ImportError:
    try:
        from .config import *
        from .services.network import sio, conectar, enviar_heartbeat
        from .gui.arquivos import JanelaArquivos
        from .gui.quiosque import QuiosqueFrame
        from .utils import criar_atalho_inicializacao, bloquear_teclas, desbloquear_teclas, montar_drive_z, desmontar_drive_z, lancar_navegador_seguro
    except: pass

try: import pyautogui; pyautogui.FAILSAFE = False 
except: pyautogui = None
try: import keyboard
except: keyboard = None
try: from screeninfo import get_monitors
except ImportError: get_monitors = None

# --- 1. DEFINIÇÃO INTELIGENTE DE PASTAS ---
DIRETORIO_ATUAL = os.getcwd()

# Se existir uma pasta 'cliente' dentro da atual, assume que estamos na raiz do projeto
# e que os arquivos devem ser salvos lá dentro.
if os.path.exists(os.path.join(DIRETORIO_ATUAL, "cliente")):
    BASE_DIR = os.path.join(DIRETORIO_ATUAL, "cliente")
else:
    BASE_DIR = DIRETORIO_ATUAL

if 'PASTA_CACHE' not in globals():
    PASTA_CACHE = os.path.join(BASE_DIR, "cache")
    if not os.path.exists(PASTA_CACHE):
        try: os.makedirs(PASTA_CACHE)
        except: pass

if 'PASTA_ICONES' not in globals():
    PASTA_ICONES = os.path.join(PASTA_CACHE, "icones")
    if not os.path.exists(PASTA_ICONES):
        try: os.makedirs(PASTA_ICONES)
        except: pass

# --- Pastas do Servidor (Para cópia local em modo desenvolvimento) ---
caminho_pai = os.path.dirname(BASE_DIR) 
PASTA_SERVIDOR_WALLPAPERS = os.path.join(caminho_pai, "servidor", "static", "wallpapers")
PASTA_SERVIDOR_LOGOS = os.path.join(caminho_pai, "servidor", "static", "logos")
PASTA_SERVIDOR_ICONES = os.path.join(caminho_pai, "servidor", "static", "icons")

# --- CONSTANTES ---
# Arquivo local de backup (ex: logo da empresa antiga)
IMG_LOGO_CACHE_WALLPAPER = os.path.join(BASE_DIR, 'logo_cache.png')

# Arquivo baixado do servidor (TEM PRIORIDADE)
IMG_QUIOSQUE_BG = os.path.join(PASTA_CACHE, 'quiosque_wall.jpg')

# Logo do topo
LOGO_CACHE = os.path.join(PASTA_CACHE, 'logo.png') 
# Fallback antigo
IMG_QUIOSQUE_LOGO = os.path.join(PASTA_CACHE, 'quiosque_logo.png')

IMG_LOGIN = os.path.join(PASTA_CACHE, 'login_wall.jpg')
IMG_DESKTOP = os.path.join(PASTA_CACHE, 'desktop_wall.jpg')
IMG_CHAT = os.path.join(PASTA_CACHE, 'chat_bg.jpg')
BANCO_CACHE = os.path.join(PASTA_CACHE, 'sistema.db')

# Variáveis Globais
app_instance = None
LISTA_BLOQUEIO_PROG = []
LISTA_BLOQUEIO_SITES = []
COMPARTILHANDO_TELA = False
USER_SEM_RESTRICAO = False
CONFIG_DATINET_ICONS = {'chrome': None, 'firefox': None, 'edge': None}
CONFIG_DATABIT = {}
SENHA_ENGRENAGEM = "admin"

# Cores
TEMAS = {
    "claro": { 
        "bg_janela": "#f0f2f5", "bg_container": "#ffffff", "fg_texto": "#202020", 
        "header_bg": "#ffffff", "btn_header_fg": "#5f6368", "btn_header_hover": "#e8eaed"
    },
    "escuro": { 
        "bg_janela": "#202124", "bg_container": "#303134", "fg_texto": "#ffffff", 
        "header_bg": "#292a2d", "btn_header_fg": "#e8eaed", "btn_header_hover": "#3c4043"
    }
}

# --- CACHE ---
def init_cache():
    try:
        c = sqlite3.connect(BANCO_CACHE); cur = c.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS atalhos (id INTEGER PRIMARY KEY, nome TEXT, comando TEXT, tipo TEXT, icone TEXT, setores TEXT, hash_icone TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS configs (chave TEXT PRIMARY KEY, valor TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS users_cache (usuario TEXT PRIMARY KEY, senha TEXT, ultimo_login DATETIME)")
        c.commit(); c.close()
    except: pass
init_cache()

def salvar_cache(dados):
    try:
        c = sqlite3.connect(BANCO_CACHE); cur = c.cursor()
        cur.execute("DELETE FROM atalhos")
        for a in dados.get('atalhos', []): 
            cur.execute("INSERT INTO atalhos (nome, comando, tipo, icone, setores, hash_icone) VALUES (?,?,?,?,?,?)", (a['nome'], a['comando'], a['tipo'], a.get('icone',''), a.get('setores', 'Livre'), a.get('hash_icone')))
        import json
        cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('databit', json.dumps(dados.get('databit',{}))))
        cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('datinet_icons', json.dumps(dados.get('datinet_icons',{}))))
        if 'caminho_datinet' in dados: cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('caminho_datinet', json.dumps(dados.get('caminho_datinet', 'C:\\Datinet'))))
        if 'caminho_drive_z' in dados: cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('caminho_drive_z', json.dumps(dados.get('caminho_drive_z', 'C:\\DriveZ'))))
        cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('termos', json.dumps(dados.get('termos',{}))))
        cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('creditos', json.dumps(dados.get('creditos',{}))))
        cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('bloqueio_programas', json.dumps(dados.get('bloqueio_programas',[]))))
        cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('bloqueio_sites', json.dumps(dados.get('bloqueio_sites',[]))))
        cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('senha_engrenagem', json.dumps(dados.get('senha_engrenagem', 'admin'))))
        cur.execute("INSERT OR REPLACE INTO configs (chave, valor) VALUES (?,?)", ('hashes', json.dumps(dados.get('hashes', {}))))
        c.commit(); c.close()
    except: pass

def carregar_cache():
    d = {'atalhos':[], 'databit':{}, 'datinet_icons':{}, 'bloqueio_programas':[], 'bloqueio_sites':[], 'termos':{'ativo':False,'texto':''}, 'creditos': {}, 'senha_engrenagem': 'admin', 'caminho_cofre': 'C:\\Cofres', 'caminho_datinet': 'C:\\Datinet', 'caminho_drive_z': 'C:\\DriveZ', 'hashes': {}}
    try:
        c = sqlite3.connect(BANCO_CACHE); cur = c.cursor()
        cur.execute("SELECT nome, comando, tipo, icone, setores, hash_icone FROM atalhos")
        for l in cur.fetchall(): d['atalhos'].append({'nome':l[0], 'comando':l[1], 'tipo':l[2], 'icone':l[3], 'setores':l[4], 'hash_icone': l[5]})
        import json
        cur.execute("SELECT chave, valor FROM configs")
        for k,v in cur.fetchall(): 
            if k in d: d[k] = json.loads(v)
        c.close()
    except: pass
    return d

def cache_user(u, s):
    try:
        c = sqlite3.connect(BANCO_CACHE)
        c.execute("INSERT OR REPLACE INTO users_cache (usuario, senha, ultimo_login) VALUES (?,?,?)", (u, s, datetime.now().strftime("%Y-%m-%d")))
        c.commit(); c.close()
    except: pass

def check_login_offline(u, s):
    try:
        c = sqlite3.connect(BANCO_CACHE)
        res = c.execute("SELECT senha FROM users_cache WHERE usuario=?", (u,)).fetchone()
        c.close()
        return res and res[0] == s
    except: return False

def calcular_md5_local(caminho):
    if not os.path.exists(caminho): return None
    try:
        import hashlib
        hash_md5 = hashlib.md5()
        with open(caminho, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""): hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except: return None

# --- NOVA FUNÇÃO: BUSCA ARQUIVO NA PASTA DO SERVIDOR (LOCAL) ---
def buscar_arquivo_local_servidor(nome_arquivo, pasta_destino, tipo="wallpaper"):
    pasta_origem = None
    if tipo == "wallpaper": pasta_origem = PASTA_SERVIDOR_WALLPAPERS
    elif tipo == "logo": pasta_origem = PASTA_SERVIDOR_LOGOS
    elif tipo == "icon": pasta_origem = PASTA_SERVIDOR_ICONES
    
    if pasta_origem and os.path.exists(pasta_origem):
        caminho_origem = os.path.join(pasta_origem, nome_arquivo)
        if os.path.exists(caminho_origem):
            try:
                shutil.copy2(caminho_origem, pasta_destino)
                return True
            except: pass
    return False

def baixar_arquivo_inteligente(url, caminho_destino, hash_servidor, nome_arquivo_original=None, tipo="wallpaper"):
    # 1. Tenta copiar da pasta local do servidor (se existir)
    if nome_arquivo_original:
        if buscar_arquivo_local_servidor(nome_arquivo_original, caminho_destino, tipo):
            return True

    # 2. Se não achou local, verifica se precisa baixar da rede
    precisa_baixar = False
    if not os.path.exists(caminho_destino): precisa_baixar = True
    elif hash_servidor:
        hash_local = calcular_md5_local(caminho_destino)
        if hash_local != hash_servidor: precisa_baixar = True
    
    # 3. Baixa da rede
    if precisa_baixar:
        try:
            r = requests.get(url, timeout=20) 
            if r.status_code == 200:
                with open(caminho_destino, 'wb') as f: f.write(r.content)
                return True
        except: return False
    return False

# --- FUNÇÃO DE DOWNLOAD CORRIGIDA ---
def processar_downloads_ativos(dados):
    hashes = dados.get('hashes', {})
    
    # Lista com 4 elementos: Chave, CaminhoDestino, RotaAPI, Tipo(para busca local)
    lista_midia = [
        ('wall_login', IMG_LOGIN, '/api/wallpaper/', 'wallpaper'),
        ('wall_desktop', IMG_DESKTOP, '/api/wallpaper/', 'wallpaper'),
        ('wall_chat', IMG_CHAT, '/api/wallpaper/', 'wallpaper'),
        ('wall_quiosque', IMG_QUIOSQUE_BG, '/api/wallpaper/', 'wallpaper'),
        ('logo', LOGO_CACHE, '/api/logo/', 'logo')
    ]
    
    alteracao_visual = False
    
    for chave_json, caminho_local, api_base, tipo_midia in lista_midia:
        nome_arquivo = dados.get(chave_json)
        hash_srv = hashes.get(chave_json)
        
        if nome_arquivo: 
            # Passa o nome original e o tipo para tentar copiar localmente
            baixou = baixar_arquivo_inteligente(
                f"{URL_SERVIDOR}{api_base}{nome_arquivo}", 
                caminho_local, 
                hash_srv, 
                nome_arquivo, 
                tipo_midia
            )
            if baixou: alteracao_visual = True
    
    # Ícones Navegadores
    icones_datinet = dados.get('datinet_icons', {})
    for nav, nome_arquivo in icones_datinet.items():
        if nome_arquivo: 
            baixar_arquivo_inteligente(f"{URL_SERVIDOR}/api/icon/{nome_arquivo}", os.path.join(PASTA_ICONES, nome_arquivo), hashes.get(f"icon_{nav}"), nome_arquivo, 'icon')
            
    # Ícones Atalhos
    for atalho in dados.get('atalhos', []):
        nome_icon = atalho.get('icone')
        if nome_icon: 
            baixar_arquivo_inteligente(f"{URL_SERVIDOR}/api/icon/{nome_icon}", os.path.join(PASTA_ICONES, nome_icon), atalho.get('hash_icone'), nome_icon, 'icon')
    
    # Atualiza a tela se algo mudou
    if alteracao_visual and app_instance: 
        try: app_instance.root.after(100, app_instance.update_bg)
        except: pass 

def iniciar_sincronizacao_thread():
    threading.Thread(target=_sincronizar_logica_pesada, daemon=True).start()

def _sincronizar_logica_pesada():
    global LISTA_BLOQUEIO_PROG, LISTA_BLOQUEIO_SITES, CONFIG_DATABIT, SENHA_ENGRENAGEM, CONFIG_DATINET_ICONS
    dados = None
    try:
        r = requests.get(f"{URL_SERVIDOR}/api/get_config", timeout=10)
        if r.status_code == 200: 
            dados = r.json()
            salvar_cache(dados)
            processar_downloads_ativos(dados) 
    except: pass
    
    if not dados: dados = carregar_cache()
    
    LISTA_BLOQUEIO_PROG = [p.lower() for p in dados.get('bloqueio_programas',[])]
    LISTA_BLOQUEIO_SITES = [s.lower() for s in dados.get('bloqueio_sites',[])]
    if 'databit' in dados: CONFIG_DATABIT.update(dados['databit'])
    if 'datinet_icons' in dados: CONFIG_DATINET_ICONS = dados['datinet_icons']
    if 'senha_engrenagem' in dados: 
        globals()['SENHA_ENGRENAGEM'] = dados['senha_engrenagem']
    
    if app_instance:
        app_instance.root.after(100, app_instance.update_bg)

class SistemaApp:
    def __init__(self, root):
        self.root = root; self.root.title("Sistema Severo"); self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        criar_atalho_inicializacao(); bloquear_teclas(); self.extras = []; self.user = None; self.hostname = socket.gethostname(); self.janela_chat_aberta = False; self.chat_canvas = None; self.chat_y_pos = 10; 
        
        self.tema = "escuro" 
        
        self.usuario_setores = []; self.nome_exibicao = ""; global app_instance; app_instance = self; self.img_bg = None; self.img_tablet_bg = None; self.img_logo_quiosque = None; self.icones_cache_tk = []; 
        
        iniciar_sincronizacao_thread()
        self.tela_login()
    
    def cobrir_secundarios(self):
        if not get_monitors: return
        for w in self.extras: 
            try: w.destroy() 
            except: pass
        self.extras = []
        try:
            for m in get_monitors():
                if m.x == 0 and m.y == 0: continue
                t = tk.Toplevel(self.root); t.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}"); t.overrideredirect(True); t.attributes('-topmost', True); t.configure(bg="black")
                if self.img_bg: tk.Label(t, image=self.img_bg, bg="black").place(x=0, y=0, relwidth=1, relheight=1)
                self.extras.append(t)
        except: pass
    
    def enviar_heartbeat(self): enviar_heartbeat(self.hostname, self.user)
    
    def show_alert(self, msg):
        try:
            t = tk.Toplevel(self.root); w,h = 500,250; ws,hs = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            t.geometry(f'{w}x{h}+{int((ws/2)-(w/2))}+{int((hs/2)-(h/2))}'); t.overrideredirect(True); t.attributes('-topmost',True); t.configure(bg="#212529")
            tk.Label(t, text="⚠ AVISO", font=("Segoe UI", 14, "bold"), bg="#dc3545", fg="white", pady=10).pack(fill="x")
            tk.Label(t, text=msg, font=("Segoe UI", 16), bg="#212529", fg="white", wraplength=450).pack(expand=True)
            self.root.after(5000, t.destroy)
        except: pass
    
    def update_bg(self):
        # 1. Login
        try:
            if getattr(self, 'bg_canvas', None) and self.bg_canvas.winfo_exists():
                if os.path.exists(IMG_LOGIN):
                    i = Image.open(IMG_LOGIN).resize((self.root.winfo_screenwidth(), self.root.winfo_screenheight()), Image.Resampling.LANCZOS)
                    self.img_bg = ImageTk.PhotoImage(i)
                    self.bg_canvas.delete("bg_img")
                    self.bg_canvas.create_image(0, 0, image=self.img_bg, anchor="nw", tags="bg_img")
                    self.bg_canvas.tag_lower("bg_img") 
        except Exception: pass 
        
        # 2. Chat
        try:
            if getattr(self, 'chat_canvas', None) and self.chat_canvas.winfo_exists():
                if os.path.exists(IMG_CHAT):
                    w = 420; h = 600
                    img_pil = Image.open(IMG_CHAT).resize((w, h), Image.Resampling.LANCZOS)
                    self.bg_chat_img = ImageTk.PhotoImage(img_pil) 
                    self.chat_canvas.delete("bg_chat_img")
                    self.chat_canvas.create_image(0, 0, image=self.bg_chat_img, anchor="nw", tags="bg_chat_img")
                    self.chat_canvas.tag_lower("bg_chat_img")
        except Exception: pass
        
        # 3. Quiosque (Tablet)
        try:
             if getattr(self, 'tablet_canvas', None) and self.tablet_canvas.winfo_exists():
                 self.tablet_canvas.delete("tablet_bg")
                 
                 imagem_fundo_path = None
                 
                 # --- PRIORIDADE: Cache Servidor (IMG_QUIOSQUE_BG) PRIMEIRO ---
                 # Agora IMG_QUIOSQUE_BG aponta para a pasta correta (cliente/cache/...)
                 if os.path.exists(IMG_QUIOSQUE_BG):
                     imagem_fundo_path = IMG_QUIOSQUE_BG
                 elif os.path.exists(IMG_LOGO_CACHE_WALLPAPER):
                     imagem_fundo_path = IMG_LOGO_CACHE_WALLPAPER
                 
                 if imagem_fundo_path:
                     largura_tela = self.root.winfo_screenwidth()
                     altura_tela = self.root.winfo_screenheight()
                     i = Image.open(imagem_fundo_path).resize((largura_tela, altura_tela), Image.Resampling.LANCZOS)
                     self.img_tablet_bg = ImageTk.PhotoImage(i)
                     self.tablet_canvas.create_image(0, 0, image=self.img_tablet_bg, anchor="nw", tags="tablet_bg")
                 else:
                     self.tablet_canvas.config(bg="#202124")
                 
                 self.tablet_canvas.tag_lower("tablet_bg")
                 self.load_atalhos_canvas()
        except Exception: pass

        # 4. Logo Quiosque
        try:
            if getattr(self, 'sb', None) and self.sb.winfo_exists():
                if getattr(self, 'frame_logo_quiosque', None) and self.frame_logo_quiosque.winfo_exists():
                     for widget in self.frame_logo_quiosque.winfo_children(): 
                         try: widget.destroy()
                         except: pass
                     self.load_logo(self.frame_logo_quiosque, TEMAS[self.tema]["btn_header_fg"])
        except Exception: pass

    def tela_login(self):
        self.user = None; global USER_SEM_RESTRICAO; USER_SEM_RESTRICAO = False; bloquear_teclas(); 
        self.root.deiconify()
        self.root.overrideredirect(True) 
        self.root.attributes('-topmost', False)
        self.root.state('zoomed') 
        self.root.configure(bg="black")
        for w in self.root.winfo_children(): w.destroy()
        
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0, bg="black"); self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.update_bg(); self.root.after(1000, self.cobrir_secundarios)
        cw, ch = 400, 480 
        cv = tk.Canvas(self.root, width=cw, height=ch, bg="black", highlightthickness=0); cv.place(relx=0.5, rely=0.5, anchor="center"); cv.create_rectangle(10, 10, cw-10, ch-10, fill="white", outline="") 
        f = tk.Frame(cv, bg="white"); f.place(relx=0.5, rely=0.5, anchor="center", width=300, height=440)
        tk.Label(f, text="ACESSO RESTRITO", font=("Segoe UI", 18, "bold"), bg="white", fg="#333").pack(pady=(10,5))
        self.e_u = self.mk_input(f, "USUÁRIO"); self.e_u.bind('<Return>', lambda e: self.e_p.focus())
        self.e_p = self.mk_input(f, "SENHA", "*"); self.e_p.bind('<Return>', lambda e: self.login())
        tk.Button(f, text="ENTRAR", font=("Segoe UI", 11, "bold"), bg="#0d6efd", fg="white", relief="flat", command=self.login).pack(fill="x", pady=(20,10), ipady=5)
        tk.Button(f, text="🔓 LIBERAR MASTER", font=("Segoe UI", 9, "bold"), bg="#555", fg="white", relief="flat", command=self.login_mestre).pack(fill="x", pady=5, ipady=3)
        ws = self.root.winfo_screenwidth(); hs = self.root.winfo_screenheight()
        self.id_gear = self.bg_canvas.create_text(ws-35, hs-35, text="⚙️", font=("Arial", 24), fill="#888", anchor="center")
        def on_enter_gear(e): self.bg_canvas.itemconfig(self.id_gear, fill="white"); self.bg_canvas.config(cursor="hand2")
        def on_leave_gear(e): self.bg_canvas.itemconfig(self.id_gear, fill="#888"); self.bg_canvas.config(cursor="arrow")
        self.bg_canvas.tag_bind(self.id_gear, "<Button-1>", lambda e: self.config()); self.bg_canvas.tag_bind(self.id_gear, "<Enter>", on_enter_gear); self.bg_canvas.tag_bind(self.id_gear, "<Leave>", on_leave_gear)
        dados = carregar_cache(); creds = dados.get('creditos', {})
        tk.Label(f, text="", bg="white", height=1).pack()
        tk.Label(f, text=creds.get('l1', "Desenvolvido Por Eng Eduardo Luiz Da Costa"), font=("Segoe UI", 8, "bold"), bg="white", fg="#777").pack()
        tk.Label(f, text=creds.get('l2', "Programador Guilherme Gonsalves"), font=("Segoe UI", 7), bg="white", fg="#888").pack()
        tk.Label(f, text=creds.get('l3', "2026"), font=("Segoe UI", 7), bg="white", fg="#999").pack()
    
    def mk_input(self, p, ph, show=None):
        f = tk.Frame(p, bg="white"); f.pack(pady=5, fill="x"); tk.Label(f, text=ph, font=("Segoe UI", 8, "bold"), bg="white", fg="#555", anchor="w").pack(fill="x"); e = tk.Entry(f, font=("Segoe UI", 12), bg="#f2f2f2", fg="#333", relief="flat"); 
        if show: e.config(show=show)
        e.pack(fill="x", ipady=5); return e
    
    def login(self):
        u = self.e_u.get(); p = self.e_p.get(); ok = False; setores_str = ""; global USER_SEM_RESTRICAO
        try:
            r = requests.post(f"{URL_SERVIDOR}/api/login_cliente", json={'hostname': self.hostname, 'user': u, 'pass': p}, timeout=3); data = r.json()
            if r.status_code == 200 and data.get('status') == 'ok': ok = True; cache_user(u, p); setores_str = data.get('setores', 'Livre'); USER_SEM_RESTRICAO = data.get('sem_restricao', False); self.nome_exibicao = data.get('nome_real', u) 
        except:
            if u == "admin" and p == "admin": ok = True; setores_str = "TODOS"; USER_SEM_RESTRICAO = True; self.nome_exibicao = "Administrador"
            elif check_login_offline(u, p): ok = True; setores_str = "Livre"; USER_SEM_RESTRICAO = False; self.nome_exibicao = u 
            else: messagebox.showwarning("Erro", "Falha no login.")
        if ok: self.usuario_setores = [s.strip() for s in setores_str.split(',')]; self.entrar(u) if u == "admin" else self.termos(u)
        else: messagebox.showerror("Erro", "Login inválido.")
    
    def login_mestre(self):
        desbloquear_teclas(); s = simpledialog.askstring("Master", "Senha Mestre de Desbloqueio:", show="*", parent=self.root)
        if not s: bloquear_teclas(); return
        try:
            r = requests.post(f"{URL_SERVIDOR}/api/check_master", json={'hostname': self.hostname, 'senha': s}, timeout=3)
            if r.status_code == 200 and r.json().get('status') == 'ok':
                global USER_SEM_RESTRICAO; USER_SEM_RESTRICAO = True; self.usuario_setores = ["TODOS"]; self.nome_exibicao = "Mestre"; self.entrar("ADMIN_MASTER")
            else: messagebox.showerror("Erro", "Senha Mestre Incorreta!"); bloquear_teclas()
        except:
            if s == "admin":
                if messagebox.askyesno("Servidor Offline", "Apenas desbloquear?"): self.root.destroy()
                else: USER_SEM_RESTRICAO=True; self.usuario_setores=["TODOS"]; self.entrar("ADMIN_LOCAL_OFFLINE")
            else: messagebox.showerror("Erro", "Não foi possível conectar ao servidor."); bloquear_teclas()
    
    def termos(self, u):
        d = carregar_cache(); t = d.get('termos', {})
        if not t.get('ativo'): self.entrar(u); return
        win = tk.Toplevel(self.root); w,h=600,500; ws,hs=self.root.winfo_screenwidth(), self.root.winfo_screenheight(); win.geometry(f'{w}x{h}+{int((ws/2)-(w/2))}+{int((hs/2)-(h/2))}'); win.overrideredirect(True); win.attributes('-topmost',True)
        tk.Label(win, text="TERMOS DE USO", font=("Segoe UI", 16, "bold")).pack(pady=20)
        txt = tk.Text(win, font=("Segoe UI", 11), height=10); txt.insert("1.0", t.get('texto','')); txt.config(state="disabled"); txt.pack(padx=20, pady=10)
        f = tk.Frame(win, pady=20); f.pack(fill="x")
        tk.Button(f, text="❌ NÃO CONCORDO", bg="#dc3545", fg="white", command=lambda: [win.destroy(), messagebox.showinfo("Info","Necessário aceitar.")]).pack(side="left", padx=30)
        tk.Button(f, text="✅ CONCORDO", bg="#198754", fg="white", command=lambda: [win.destroy(), self.entrar(u)]).pack(side="right", padx=30)
    
    def entrar(self, u):
        self.user = u; desbloquear_teclas()
        for w in self.extras: w.destroy()
        self.extras = []; self.enviar_heartbeat(); montar_drive_z(u)
        if os.path.exists(IMG_DESKTOP): 
            try: ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath(IMG_DESKTOP), 3)
            except: pass
        self.modo_trab()
    
    def modo_trab(self):
        for w in self.root.winfo_children(): w.destroy()
        self.root.state('normal'); self.root.attributes('-fullscreen', False); self.root.overrideredirect(True); self.root.attributes('-topmost', False)
        ws = self.root.winfo_screenwidth()
        self.root.geometry(f"50x50+{ws-70}+10"); self.root.configure(bg="#0d6efd")
        tk.Button(self.root, text="☰", font=("Arial", 20, "bold"), bg="#0d6efd", fg="white", bd=0, activebackground="#0b5ed7", activeforeground="white", command=self.abrir_quiosque_tablet).pack(fill="both", expand=True)
        self.root.after(100, self.abrir_quiosque_tablet)
    
    def abrir_quiosque_tablet(self):
        self.root.withdraw()
        if getattr(self, 'sb', None) and self.sb.winfo_exists(): self.sb.destroy()
        
        C = TEMAS[self.tema]
        self.sb = tk.Toplevel(self.root)
        
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        self.sb.geometry(f"{ws}x{hs}+0+0")
        
        self.sb.overrideredirect(True)
        self.sb.attributes('-topmost', False)
        self.sb.configure(bg=C["bg_janela"])

        # --- CANVAS PRINCIPAL (FUNDO + ÍCONES) ---
        self.tablet_canvas = tk.Canvas(self.sb, highlightthickness=0, bg=C["bg_janela"])
        self.tablet_canvas.place(x=0, y=80, relwidth=1, relheight=1)
        
        vbar = tk.Scrollbar(self.sb, orient="vertical", command=self.tablet_canvas.yview)
        vbar.place(relx=0.985, y=80, relheight=0.9, width=20)
        self.tablet_canvas.configure(yscrollcommand=vbar.set)

        self.update_bg() 

        # --- HEADER ---
        frame_header = tk.Frame(self.sb, bg=C["header_bg"], height=80)
        frame_header.place(x=0, y=0, relwidth=1, height=80)
        
        self.frame_logo_quiosque = tk.Frame(frame_header, bg=C["header_bg"], padx=20)
        self.frame_logo_quiosque.pack(side="left", fill="y")
        self.load_logo(self.frame_logo_quiosque, C["btn_header_fg"])

        frame_actions = tk.Frame(frame_header, bg=C["header_bg"])
        frame_actions.pack(side="left", padx=(0, 20), fill="y")

        btn_font = ("Segoe UI", 12, "bold"); btn_bd = 0; btn_relief = "flat"
        
        def criar_btn_header(texto, icone_emoji, comando, bg_color=C["header_bg"], fg_color=C["btn_header_fg"]):
             txt_final = f"{icone_emoji}  {texto}"
             btn = tk.Button(frame_actions, text=txt_final, font=btn_font, bg=bg_color, fg=fg_color, bd=btn_bd, relief=btn_relief, activebackground=C["btn_header_hover"], padx=15, command=comando)
             btn.pack(side="left", fill="y", padx=5)
             return btn

        criar_btn_header("Arquivos", "🔐", self.abrir_gerenciador)
        criar_btn_header("Internet", "🌍", self.janela_escolha_navegador)
        criar_btn_header("Chat", "💬", self.chat)
        criar_btn_header("Ramal", "📞", self.ramais)
        criar_btn_header(f"{CONFIG_DATABIT.get('nome','DB')}", "🚀", self.databit)
        criar_btn_header("Tema", "🎨", self.troca_tema)

        if self.user == "admin" or self.user == "ADMIN_MASTER" or self.user == "ADMIN_LOCAL_OFFLINE":
             criar_btn_header("FECHAR SIS", "💀", self.root.destroy, bg_color="#8B0000", fg_color="white")
             
        criar_btn_header("Sair", "❌", self.logout)

        btn_minimizar = tk.Button(frame_header, text="◱", font=("Arial", 20), bg=C["header_bg"], fg=C["btn_header_fg"], bd=0, relief="flat", activebackground=C["btn_header_hover"], command=self.fechar_quiosque_tablet)
        btn_minimizar.pack(side="right", padx=20, fill="y")

        # Rodapé
        ff = tk.Frame(self.sb, bg=C["header_bg"], height=30)
        ff.pack(fill="x", side="bottom")
        tk.Label(ff, text=f"Usuario: {self.nome_exibicao}  |  Setor: {','.join(self.usuario_setores) if self.usuario_setores else 'Geral'}", font=("Segoe UI", 10), fg=C["btn_header_fg"], bg=C["header_bg"]).pack(side="left", padx=20)

    def fechar_quiosque_tablet(self):
        self.frame_logo_quiosque = None 
        self.tablet_canvas = None 
        if getattr(self, 'sb', None) and self.sb.winfo_exists():
            self.sb.destroy()
        self.sb = None
        self.root.deiconify()

    def abrir_gerenciador(self):
        if not self.user: return
        JanelaArquivos(self.root, self.hostname, self.user, self.usuario_setores)
    
    def janela_escolha_navegador(self):
        w, h = 500, 250
        ws, hs = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x, y = int((ws/2) - (w/2)), int((hs/2) - (h/2))
        top = tk.Toplevel(self.root); top.title("Internet"); top.geometry(f"{w}x{h}+{x}+{y}"); top.attributes('-topmost', True); top.configure(bg="#f0f0f0")
        tk.Label(top, text="Escolha seu Navegador", font=("Segoe UI", 14, "bold"), bg="#f0f0f0").pack(pady=(15, 20))
        f = tk.Frame(top, bg="#f0f0f0"); f.pack(fill="x", padx=20)
        def obter_imagem_icone(chave_config):
            nome_arquivo = CONFIG_DATINET_ICONS.get(chave_config)
            if nome_arquivo:
                caminho = os.path.join(PASTA_ICONES, nome_arquivo)
                if os.path.exists(caminho):
                    try: return ImageTk.PhotoImage(Image.open(caminho).resize((64, 64), Image.Resampling.LANCZOS))
                    except: pass
            return None
        self.img_chrome = obter_imagem_icone('chrome'); self.img_edge = obter_imagem_icone('edge'); self.img_firefox = obter_imagem_icone('firefox')
        estilo = {"font": ("Segoe UI", 10, "bold"), "bd": 0, "relief": "raised", "cursor": "hand2", "compound": "top", "height": 90, "width": 100}
        def criar_botao(pai, texto, imagem, cmd, cor_padrao):
            if imagem: b = tk.Button(pai, text=texto, image=imagem, bg="#fff", fg="#000", **estilo)
            else: b = tk.Button(pai, text=texto, bg=cor_padrao, fg="white", font=("Segoe UI", 10, "bold"), bd=0, relief="raised", height=4, width=15)
            b.config(command=cmd); b.pack(side="left", padx=10, fill="x", expand=True)
            return b
        criar_botao(f, "Chrome", self.img_chrome, lambda: [lancar_navegador_seguro("Chrome", self.user), top.destroy()], "#DB4437")
        criar_botao(f, "Edge", self.img_edge, lambda: [lancar_navegador_seguro("Edge", self.user), top.destroy()], "#0078D7")
        criar_botao(f, "Firefox", self.img_firefox, lambda: [lancar_navegador_seguro("Firefox", self.user), top.destroy()], "#FF7139")
        tk.Label(top, text="* Dados salvos no seu perfil.", font=("Segoe UI", 9), bg="#f0f0f0", fg="#666").pack(side="bottom", pady=15)
    
    def load_atalhos_canvas(self):
        canvas = self.tablet_canvas
        if not canvas or not canvas.winfo_exists(): return
        
        canvas.delete("atalho") 
        c = TEMAS[self.tema]
        
        d = carregar_cache()
        atalhos_raw = d.get('atalhos', []); atalhos_filtrados = []
        for item in atalhos_raw:
            setores_atalho = [s.strip() for s in item.get('setores', 'Livre').split(',')]
            if 'TODOS' in self.usuario_setores: item['prioridade'] = 1; atalhos_filtrados.append(item); continue
            eh_livre = 'Livre' in setores_atalho; tem_permissao = any(s in self.usuario_setores for s in setores_atalho)
            if eh_livre or tem_permissao: item['prioridade'] = 0 if tem_permissao and not eh_livre else 1; atalhos_filtrados.append(item)
        atalhos_filtrados.sort(key=lambda x: x['prioridade'])
        
        if not atalhos_filtrados: 
            canvas.create_text(self.root.winfo_screenwidth()/2, 200, text="Sem atalhos.", fill=c["fg_texto"], font=("Segoe UI", 16), tags="atalho")
            return

        start_x = 50; start_y = 50
        icon_w = 120; icon_h = 130
        gap_x = 30; gap_y = 30
        
        sw = self.root.winfo_screenwidth()
        cols = int((sw - 100) / (icon_w + gap_x))
        if cols < 1: cols = 1
        
        self.icones_cache_tk = [] 

        for idx, item in enumerate(atalhos_filtrados):
            row = idx // cols
            col = idx % cols
            x = start_x + col * (icon_w + gap_x)
            y = start_y + row * (icon_h + gap_y)
            
            img_tk = None
            if item.get('icone'):
                pth = os.path.join(PASTA_ICONES, item['icone'])
                if os.path.exists(pth):
                    try: 
                        img_pil = Image.open(pth).resize((64, 64), Image.Resampling.LANCZOS)
                        img_tk = ImageTk.PhotoImage(img_pil)
                        self.icones_cache_tk.append(img_tk)
                    except: pass
            
            if img_tk:
                canvas.create_image(x + icon_w/2, y + 40, image=img_tk, tags=("atalho", f"btn_{idx}"))
            else:
                canvas.create_text(x + icon_w/2, y + 40, text="🌐" if item['tipo']=='site' else "💻", font=("Segoe UI", 30), fill="white", tags=("atalho", f"btn_{idx}"))
            
            nome_curto = item['nome'][:15] + ".." if len(item['nome']) > 15 else item['nome']
            
            canvas.create_text(x + icon_w/2 + 1, y + 90 + 1, text=nome_curto, font=("Segoe UI", 10, "bold"), fill="black", width=icon_w, justify="center", tags=("atalho", f"btn_{idx}"))
            canvas.create_text(x + icon_w/2, y + 90, text=nome_curto, font=("Segoe UI", 10, "bold"), fill="white", width=icon_w, justify="center", tags=("atalho", f"btn_{idx}"))
            
            canvas.create_rectangle(x, y, x+icon_w, y+icon_h, fill="", outline="", tags=("atalho", f"btn_{idx}"))
            
            cmd = item['comando']; tipo = item['tipo']
            canvas.tag_bind(f"btn_{idx}", "<Button-1>", lambda e, c=cmd, t=tipo: self.exec_atalho(c, t))
            
            def on_enter(e): canvas.config(cursor="hand2")
            def on_leave(e): canvas.config(cursor="arrow")
            canvas.tag_bind(f"btn_{idx}", "<Enter>", on_enter)
            canvas.tag_bind(f"btn_{idx}", "<Leave>", on_leave)
        
        canvas.config(scrollregion=canvas.bbox("all"))

    def exec_atalho(self, c, t):
        try: os.startfile(c)
        except: messagebox.showerror("Erro", f"Erro ao abrir {c}")
    
    def load_logo(self, p, fg):
        if os.path.exists(LOGO_CACHE):
            try:
                i = Image.open(LOGO_CACHE)
                i.thumbnail((200, 60), Image.Resampling.LANCZOS)
                self.img_logo_quiosque = ImageTk.PhotoImage(i)
                tk.Label(p, image=self.img_logo_quiosque, bg=TEMAS[self.tema]["header_bg"]).pack(side="left", anchor="center")
                return
            except: pass
            
        if os.path.exists(IMG_QUIOSQUE_LOGO):
            try:
                i = Image.open(IMG_QUIOSQUE_LOGO)
                i.thumbnail((200, 60), Image.Resampling.LANCZOS)
                self.img_logo_quiosque = ImageTk.PhotoImage(i)
                tk.Label(p, image=self.img_logo_quiosque, bg=TEMAS[self.tema]["header_bg"]).pack(side="left", anchor="center")
                return
            except: pass
            
        tk.Label(p, text="SEVERO", font=("Arial Black", 16), fg=fg, bg=TEMAS[self.tema]["header_bg"]).pack(side="left", anchor="center")

    def troca_tema(self): 
        self.tema = "escuro" if self.tema == "claro" else "claro"
        self.abrir_quiosque_tablet()

    def databit(self): 
        c = CONFIG_DATABIT.get('comando'); t = CONFIG_DATABIT.get('tipo','site') 
        if c: self.exec_atalho(c, t)
    
    def ramais(self):
        try: r = requests.get(f"{URL_SERVIDOR}/api/get_ramais", timeout=3).json()
        except: messagebox.showerror("Erro", "Ramais indisponíveis"); return
        t = tk.Toplevel(self.root); w, h = 600, 500; ws, hs = self.root.winfo_screenwidth(), self.root.winfo_screenheight(); x, y = int((ws/2) - (w/2)), int((hs/2) - (h/2)); t.geometry(f"{w}x{h}+{x}+{y}"); t.attributes('-topmost', True)
        f = tk.Frame(t); f.pack(fill="x", padx=10, pady=10); tk.Label(f, text="Filtrar:").pack(side="left"); e = tk.Entry(f); e.pack(side="left", fill="x", expand=True, padx=10)
        tr = ttk.Treeview(t, columns=('Nome','Setor','Ramal'), show='headings'); tr.pack(fill="both", expand=True)
        for c in ('Nome','Setor','Ramal'): tr.heading(c, text=c)
        def p(x=""):
            tr.delete(*tr.get_children())
            for i in r: 
                if x.lower() in i['nome'].lower(): tr.insert("", "end", values=(i['nome'], i['setor'], i['numero']))
        e.bind("<KeyRelease>", lambda ev: p(e.get())); p()
    
    def logout(self):
        desmontar_drive_z()
        if not self.user: return
        try: requests.post(f"{URL_SERVIDOR}/api/logout_cliente", json={'hostname': self.hostname, 'user': self.user}, timeout=1)
        except: pass
        if getattr(self, 'sb', None): self.sb.destroy()
        if getattr(self, 't_chat', None): self.t_chat.destroy()
        self.t_chat = None; self.chat_canvas = None; self.janela_chat_aberta = False; self.tela_login()

    def chat(self):
        if self.janela_chat_aberta: 
            if getattr(self, 't_chat', None) and self.t_chat.winfo_exists(): 
                self.t_chat.deiconify() 
                self.t_chat.lift()      
                self.t_chat.focus_force()
                return
            else: 
                self.janela_chat_aberta = False
        
        self.janela_chat_aberta = True
        self.t_chat = tk.Toplevel(self.root)
        t = self.t_chat
        t.title(f"Suporte - {self.user}")
        
        w, h = 420, 600
        ws, hs = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x, y = int((ws/2)-(w/2)), int((hs/2)-(h/2))
        t.geometry(f"{w}x{h}+{x}+{y}")
        t.resizable(False, False)
        t.attributes('-topmost', True) 
        
        self.frame_topo_sys = tk.Frame(t, bg="#fff3cd", height=30)
        self.frame_topo_sys.pack_propagate(False)
        self.frame_topo_sys.place(relx=0, rely=0, relwidth=1, height=30)
        self.lbl_system_msg = tk.Label(self.frame_topo_sys, text="Chat Iniciado", bg="#fff3cd", fg="#856404", font=("Segoe UI", 8, "bold"))
        self.lbl_system_msg.pack(fill="both", expand=True)

        self.chat_canvas = tk.Canvas(t, bg="#efe7dd", highlightthickness=0)
        self.chat_canvas.place(relx=0, y=30, relwidth=1, relheight=0.80) 
        self.update_bg()
        
        vbar = tk.Scrollbar(t, orient="vertical", command=self.chat_canvas.yview)
        vbar.place(relx=0.96, y=30, relheight=0.80)
        self.chat_canvas.config(yscrollcommand=vbar.set)
        
        self.chat_y_pos = 10 

        t.protocol("WM_DELETE_WINDOW", lambda: [setattr(self, 'janela_chat_aberta', False), t.destroy()])
        
        self.frame_input = tk.Frame(t, bg="#f0f0f0", height=60)
        self.frame_input.place(relx=0, rely=0.88, relwidth=1, relheight=0.12)
        e = tk.Entry(self.frame_input, font=("Segoe UI", 11), bd=0, highlightthickness=1, highlightbackground="#ddd")
        e.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=12)
        
        def env(ev=None):
            m = e.get()
            if m.strip() and sio.connected: 
                sio.emit('chat_mensagem_cliente', {'hostname': self.hostname, 'user': self.user, 'msg': m})
                self.add_msg(m, 'me', self.user)
                e.delete(0, tk.END)
        
        tk.Button(self.frame_input, text="ENVIAR", command=env, bg="#25D366", fg="white", font=("Segoe UI", 9, "bold"), bd=0, relief="flat").pack(side="right", padx=(5, 10), pady=12, fill="y")
        e.bind("<Return>", env)
        
        if sio.connected: sio.emit('cliente_entrar_fila', {'hostname': self.hostname})
        try:
            r = requests.get(f"{URL_SERVIDOR}/api/get_chat_history/{self.hostname}", timeout=2)
            for m in r.json(): self.add_msg(m['msg'], 'me' if m['remetente']!='Admin' and m['remetente']!='Sistema' else 'admin', m['remetente'])
        except: pass

    def limpar_chat_visual(self):
        if self.chat_canvas and self.chat_canvas.winfo_exists():
            self.chat_canvas.delete("msg")
            self.chat_y_pos = 10
            if hasattr(self, 'lbl_system_msg') and self.lbl_system_msg.winfo_exists():
                self.lbl_system_msg.config(text="Chat Limpo pelo Suporte")
    
    def add_msg(self, m, origem, nome):
        if nome == 'Sistema':
            if hasattr(self, 'lbl_system_msg') and self.lbl_system_msg.winfo_exists():
                self.lbl_system_msg.config(text=m)
            return
        if not self.chat_canvas or not self.chat_canvas.winfo_exists(): return
        MAX_WIDTH = 250
        FONT_MSG = font.Font(family="Segoe UI", size=10)
        FONT_NOME = font.Font(family="Segoe UI", size=7, weight="bold")
        FONT_HORA = font.Font(family="Segoe UI", size=7)
        bg_color = "#dcf8c6" if origem == 'me' else "#ffffff"
        lines = []; words = m.split(); current_line = []
        for word in words:
            current_line.append(word)
            if FONT_MSG.measure(" ".join(current_line)) > MAX_WIDTH:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line: lines.append(" ".join(current_line))
        texto_final = "\n".join(lines)
        if not texto_final: texto_final = m 
        width_bubble = 0
        for lin in lines:
            w_l = FONT_MSG.measure(lin)
            if w_l > width_bubble: width_bubble = w_l
        width_bubble += 30
        if width_bubble < 100: width_bubble = 100
        height_bubble = (len(lines) * 20) + 30 
        canvas_width = 400 
        if self.chat_canvas.winfo_width() > 1: canvas_width = self.chat_canvas.winfo_width()
        if origem == 'me':
            x1 = canvas_width - width_bubble - 10
            x2 = canvas_width
        else:
            x1 = 10
            x2 = 10 + width_bubble
        y1 = self.chat_y_pos
        y2 = y1 + height_bubble
        self.chat_canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline="#ccc", tags="msg")
        hora = datetime.now().strftime('%H:%M')
        self.chat_canvas.create_text(x1+5, y1+5, text=nome, font=FONT_NOME, anchor="nw", fill="gray", tags="msg")
        self.chat_canvas.create_text(x1+5, y1+20, text=texto_final, font=FONT_MSG, anchor="nw", fill="black", tags="msg")
        self.chat_canvas.create_text(x2-5, y2-5, text=hora, font=FONT_HORA, anchor="se", fill="gray", tags="msg")
        self.chat_y_pos += height_bubble + 10
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        self.chat_canvas.yview_moveto(1)
    
    def config(self):
        desbloquear_teclas(); s = simpledialog.askstring("Admin", "Senha de Configuração:", show="*", parent=self.root)
        if s == SENHA_ENGRENAGEM or s == "admin": 
            top = tk.Toplevel(self.root); top.attributes('-topmost',True); tk.Label(top, text="IP do Servidor:").pack(pady=5); e = tk.Entry(top); e.insert(0, URL_SERVIDOR.replace("http://","")); e.pack(padx=10)
            def salvar_ip(): salvar_url_servidor(e.get()); messagebox.showinfo("Sucesso", "IP salvo! Reinicie."); self.root.destroy()
            tk.Button(top, text="💾 Salvar IP", command=salvar_ip, bg="#198754", fg="white").pack(pady=10, fill='x', padx=10)
        else: messagebox.showerror("Erro", "Senha incorreta!"); bloquear_teclas()

# --- SOCKET EVENTS ---
@sio.event
def connect(): 
    if app_instance: app_instance.enviar_heartbeat()
    iniciar_sincronizacao_thread()

@sio.on('comando_remoto')
def on_cmd(d):
    a = d.get('acao')
    if a == 'reiniciar': os.system('shutdown /r /t 0')
    elif a == 'desligar': os.system('shutdown /s /t 0')
    elif a == 'deslogar' and app_instance: 
        app_instance.root.after(0, app_instance.logout)

@sio.on('comando_sistema')
def on_sys(d):
    if app_instance and d.get('acao') in ['atualizar_wallpaper', 'atualizar_config']: 
        iniciar_sincronizacao_thread()

@sio.on('chat_receber')
def on_chat(d):
    if app_instance:
        def _acao_chat():
            if not app_instance.janela_chat_aberta: app_instance.chat()
            elif hasattr(app_instance, 't_chat') and app_instance.t_chat.winfo_exists(): app_instance.t_chat.deiconify(); app_instance.t_chat.lift()
            app_instance.add_msg(d.get('msg'), 'admin', d.get('remetente','Suporte'))
        app_instance.root.after(0, _acao_chat)

@sio.on('chat_limpar')
def on_chat_limpar(d):
    if app_instance: app_instance.root.after(0, app_instance.limpar_chat_visual)

@sio.on('aviso_sistema')
def on_aviso(d):
    if app_instance: app_instance.root.after(0, lambda: app_instance.show_alert(d.get('msg')))

@sio.on('pedido_acesso_remoto')
def on_remoto(d):
    if app_instance:
        def _pedir_acesso():
            if not pyautogui: messagebox.showerror("Erro de Sistema", "O módulo de suporte remoto (pyautogui) não está instalado."); return
            resp = messagebox.askyesno("Suporte Técnico", "O Administrador está solicitando controle remoto da sua tela.\n\nDeseja PERMITIR?", parent=app_instance.root)
            if resp:
                global COMPARTILHANDO_TELA; COMPARTILHANDO_TELA = True; sio.emit('acesso_remoto_aceito', {'hostname': socket.gethostname()}); threading.Thread(target=enviar_tela, daemon=True).start()
        app_instance.root.after(0, _pedir_acesso)

def enviar_tela():
    global COMPARTILHANDO_TELA; QUALIDADE_JPEG = 80; SCALE = 0.8          
    while COMPARTILHANDO_TELA and pyautogui:
        try:
            img = pyautogui.screenshot(); w_original, h_original = img.size; novo_w = int(w_original * SCALE); novo_h = int(h_original * SCALE); img = img.resize((novo_w, novo_h), Image.Resampling.LANCZOS); buf = BytesIO(); img.save(buf, format="JPEG", quality=QUALIDADE_JPEG, optimize=True); b64 = base64.b64encode(buf.getvalue()).decode('utf-8'); sio.emit('frame_tela_cliente', {'hostname': socket.gethostname(), 'image': b64}); time.sleep(0.05)
        except Exception as e: print(f"Erro tela: {e}"); COMPARTILHANDO_TELA = False

@sio.on('executar_input_remoto')
def on_input(d):
    if not pyautogui: return
    try:
        if d['type'] == 'click': w, h = pyautogui.size(); pyautogui.click(int(d['x']*w), int(d['y']*h))
        elif d['type'] == 'key': pyautogui.press(d['key'])
    except: pass

def monitorar():
    while True:
        try:
            if int(time.time()) % 120 == 0: 
                iniciar_sincronizacao_thread()
            if USER_SEM_RESTRICAO: time.sleep(5); continue
            if LISTA_BLOQUEIO_PROG:
                procs = subprocess.check_output('tasklist /fo csv /nh', shell=True).decode('latin-1').lower()
                for p in LISTA_BLOQUEIO_PROG:
                    if p in procs: os.system(f'taskkill /f /im "{p}"')
            if LISTA_BLOQUEIO_SITES:
                cmd = 'powershell "Get-Process | Where-Object {$_.MainWindowTitle -ne \\"\\"} | Select-Object MainWindowTitle"'
                wins = subprocess.check_output(cmd, shell=True).decode('latin-1').lower()
                for site in LISTA_BLOQUEIO_SITES:
                    if site in wins: 
                        for browser in ['chrome.exe', 'msedge.exe', 'firefox.exe', 'opera.exe', 'brave.exe']: os.system(f'taskkill /f /im {browser}')
        except: pass
        time.sleep(3)
threading.Thread(target=monitorar, daemon=True).start()

def conn_keep():
    while True:
        try:
            if not sio.connected: sio.connect(URL_SERVIDOR)
            else: 
                if app_instance: app_instance.enviar_heartbeat()
        except: pass
        time.sleep(5)
threading.Thread(target=conn_keep, daemon=True).start()

if __name__ == "__main__":
    app_instance = None; root = tk.Tk(); app = SistemaApp(root); root.mainloop()