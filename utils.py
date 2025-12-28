import os, sys, subprocess, ctypes, threading
from tkinter import messagebox
from config import CAMINHO_DATINET_LOCAL, CAMINHO_DRIVE_Z_LOCAL

try: import win32com.client; import keyboard
except ImportError: win32com = None; keyboard = None

def criar_atalho_inicializacao():
    try:
        if not win32com: return
        startup = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        path_app = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        path_lnk = os.path.join(startup, "SeveroClient.lnk")
        if not os.path.exists(path_lnk):
            s = win32com.client.Dispatch("WScript.Shell")
            lnk = s.CreateShortCut(path_lnk)
            lnk.TargetPath = path_app
            lnk.WorkingDirectory = os.path.dirname(path_app)
            lnk.save()
    except: pass

def bloquear_teclas():
    if keyboard: 
        try: keyboard.block_key('windows'); keyboard.block_key('alt')
        except: pass

def desbloquear_teclas():
    if keyboard: 
        try: keyboard.unhook_all()
        except: pass

def montar_drive_z(usuario):
    try:
        os.system("subst Z: /D >nul 2>&1")
        usuario_safe = "".join([c for c in usuario if c.isalnum() or c in (' ', '.', '_')]).strip()
        base_z = CAMINHO_DRIVE_Z_LOCAL
        if not base_z: base_z = "C:\\DriveZ"
        pasta_z = os.path.join(base_z, usuario_safe)
        if not os.path.exists(pasta_z): os.makedirs(pasta_z, exist_ok=True)
        subprocess.run(f'subst Z: "{pasta_z}"', shell=True)
    except: pass

def desmontar_drive_z():
    try: os.system("subst Z: /D")
    except: pass

def obter_caminho_navegador(nome):
    caminhos_comuns = []
    if nome == "Chrome":
        caminhos_comuns = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")]
    elif nome == "Edge":
        caminhos_comuns = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    elif nome == "Firefox":
        caminhos_comuns = [r"C:\Program Files\Mozilla Firefox\firefox.exe", r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe", os.path.expanduser(r"~\AppData\Local\Mozilla Firefox\firefox.exe")]
    for caminho in caminhos_comuns:
        if os.path.exists(caminho): return caminho
    return {"Chrome": "chrome.exe", "Edge": "msedge.exe", "Firefox": "firefox.exe"}.get(nome, nome)

def lancar_navegador_seguro(navegador, usuario):
    if not usuario: messagebox.showerror("Erro", "Usuário não identificado."); return
    usuario_safe = "".join([c for c in usuario if c.isalnum() or c in (' ', '.', '_')]).strip()
    perfil_path = os.path.join(CAMINHO_DATINET_LOCAL, usuario_safe, navegador)
    if not os.path.exists(perfil_path):
        try: os.makedirs(perfil_path)
        except: pass
    exe_path = obter_caminho_navegador(navegador)
    cmd = []
    try:
        if navegador == "Chrome": cmd = [exe_path, f"--user-data-dir={perfil_path}", "--no-first-run", "--no-default-browser-check"]
        elif navegador == "Edge": cmd = [exe_path, f"--user-data-dir={perfil_path}", "--no-first-run"]
        elif navegador == "Firefox": cmd = [exe_path, "-profile", perfil_path, "-no-remote"]
        subprocess.Popen(cmd)
    except Exception as e: messagebox.showerror("Erro ao Lançar", f"Falha ao abrir {navegador}.\nVerifique se está instalado.\nErro: {str(e)}")