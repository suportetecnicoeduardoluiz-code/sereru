import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests, os, threading, time, math
from PIL import Image, ImageTk
from datetime import datetime

# Tenta importar configurações
try:
    from config import URL_SERVIDOR, PASTA_TEMP_EDIT, PASTA_ICONES
except ImportError:
    from ..config import URL_SERVIDOR, PASTA_TEMP_EDIT, PASTA_ICONES

# --- ÍCONES DO WINDOWS ---
try:
    import win32ui, win32gui, win32con, win32api
    TEM_WIN32 = True
except ImportError:
    TEM_WIN32 = False
    print("AVISO: 'pywin32' ausente. Ícones do Windows desativados.")

try:
    import windnd 
    TEM_DRAG_DROP = True
except ImportError:
    TEM_DRAG_DROP = False

TEMAS = {
    "claro": { "bg_janela": "#ffffff", "bg_container": "#ffffff", "fg_texto": "#202020", "top_bg": "#f9f9f9", "select_bg": "#e5f3ff", "select_fg": "#000000", "entry_bg": "#ffffff", "entry_fg": "#000000", "sidebar_bg": "#f3f3f3", "btn_bg": "#e0e0e0", "btn_fg": "#000000" },
    "escuro": { "bg_janela": "#202020", "bg_container": "#2b2b2b", "fg_texto": "#ffffff", "top_bg": "#1a1a1a", "select_bg": "#4a4a4a", "select_fg": "#ffffff", "entry_bg": "#333333", "entry_fg": "#ffffff", "sidebar_bg": "#252525", "btn_bg": "#333333", "btn_fg": "#ffffff" }
}

# --- CLASSE AUXILIAR PARA UPLOAD COM PROGRESSO ---
class ArquivoComCallback:
    def __init__(self, path, callback):
        self.f = open(path, 'rb')
        self.len = os.path.getsize(path)
        self.callback = callback
        self.read_so_far = 0
        self.start_time = time.time()

    def read(self, size=-1):
        chunk = self.f.read(size)
        self.read_so_far += len(chunk)
        self.callback(self.read_so_far, self.len, self.start_time)
        return chunk

    def tell(self): return self.f.tell()
    def seek(self, *args): return self.f.seek(*args)
    def close(self): self.f.close()
    def fileno(self): return self.f.fileno()

# --- JANELA DE POPUP DE TRANSFERÊNCIA ---
class PopupTransferencia:
    def __init__(self, parent, titulo="Copiando..."):
        self.top = tk.Toplevel(parent)
        self.top.title(titulo)
        self.top.geometry("400x180")
        self.top.resizable(False, False)
        self.top.attributes('-topmost', True)
        self.top.protocol("WM_DELETE_WINDOW", lambda: None) 
        
        ws = self.top.winfo_screenwidth(); hs = self.top.winfo_screenheight()
        x = (ws/2) - (400/2); y = (hs/2) - (180/2)
        self.top.geometry('%dx%d+%d+%d' % (400, 180, x, y))

        f = tk.Frame(self.top, padx=20, pady=20)
        f.pack(fill="both", expand=True)

        self.lbl_arquivo = tk.Label(f, text="Iniciando...", font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_arquivo.pack(fill="x")

        self.lbl_detalhes = tk.Label(f, text="Calculando...", font=("Segoe UI", 9), fg="#666", anchor="w")
        self.lbl_detalhes.pack(fill="x", pady=(5, 10))

        self.progress = ttk.Progressbar(f, orient="horizontal", length=100, mode="determinate")
        self.progress.pack(fill="x", pady=10)

        self.lbl_tempo = tk.Label(f, text="Tempo restante: Calculando...", font=("Segoe UI", 9), anchor="e")
        self.lbl_tempo.pack(fill="x")

    def atualizar(self, lido, total, inicio):
        if total == 0: total = 1
        perc = (lido / total) * 100
        self.progress['value'] = perc
        
        decorrido = time.time() - inicio
        if decorrido > 0 and lido > 0:
            velocidade = lido / decorrido 
            restante = total - lido
            tempo_rest = restante / velocidade if velocidade > 0 else 0
            
            mb_total = total / (1024*1024)
            mb_lido = lido / (1024*1024)
            vel_fmt = f"{velocidade/(1024*1024):.2f} MB/s"
            
            mins, segs = divmod(int(tempo_rest), 60)
            if mins > 60:
                horas, mins = divmod(mins, 60)
                txt_tempo = f"{horas}h {mins}m restantes"
            else:
                txt_tempo = f"{mins:02d}:{segs:02d} restantes"

            self.lbl_detalhes.config(text=f"{mb_lido:.1f} MB de {mb_total:.1f} MB ({vel_fmt})")
            self.lbl_tempo.config(text=f"Tempo estimado: {txt_tempo}")
            self.lbl_arquivo.config(text=f"{int(perc)}% Concluído")
        
        self.top.update_idletasks()

    def fechar(self):
        self.top.destroy()

# --- PROVIDER DE ÍCONES ---
class ServerIconProvider:
    def __init__(self):
        self.cache = {}
        self.mapa_extensoes = {} 
        self.carregar_mapa()
        self.default_file = self.gerar_icone_padrao("📄")
        self.default_folder = self.gerar_icone_padrao("📁")

    def gerar_icone_padrao(self, texto):
        img = Image.new('RGBA', (32, 32), (0,0,0,0)) 
        return ImageTk.PhotoImage(img)

    def carregar_mapa(self):
        try:
            r = requests.get(f"{URL_SERVIDOR}/api/get_file_icons_map", timeout=2)
            if r.status_code == 200: self.mapa_extensoes = r.json()
        except: pass

    def get_icon(self, nome_arquivo, eh_pasta):
        if eh_pasta: return self.default_folder
        ext = os.path.splitext(nome_arquivo)[1].lower()
        if ext in self.mapa_extensoes:
            nome_img = self.mapa_extensoes[ext]
            local_path = os.path.join(PASTA_ICONES, nome_img)
            if nome_img in self.cache: return self.cache[nome_img]
            if not os.path.exists(local_path):
                try:
                    r = requests.get(f"{URL_SERVIDOR}/api/icon/{nome_img}", timeout=5)
                    if r.status_code == 200:
                        with open(local_path, 'wb') as f: f.write(r.content)
                except: pass
            if os.path.exists(local_path):
                try:
                    img_pil = Image.open(local_path).resize((32, 32), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(img_pil)
                    self.cache[nome_img] = img_tk
                    return img_tk
                except: pass
        return self.default_file

class MonitorArquivo(threading.Thread):
    def __init__(self, caminho_local, upload_callback, stop_event):
        super().__init__()
        self.caminho = caminho_local; self.upload_callback = upload_callback; self.stop_event = stop_event
        self.last_mtime = os.path.getmtime(caminho_local) if os.path.exists(caminho_local) else 0
    def run(self):
        while not self.stop_event.is_set():
            time.sleep(1) 
            if os.path.exists(self.caminho):
                try:
                    current_mtime = os.path.getmtime(self.caminho)
                    if current_mtime != self.last_mtime:
                        self.last_mtime = current_mtime; time.sleep(1); self.upload_callback(self.caminho)
                except: pass
            else: break 

# --- CLASSE PRINCIPAL ---
class JanelaArquivos:
    def __init__(self, root_app, hostname, user, setores):
        self.top = tk.Toplevel(root_app); self.top.title(f"Severo Cloud - {user}")
        self.top.geometry("1100x700"); self.top.minsize(800, 500); self.top.attributes('-topmost', False); self.top.focus_force()
        self.hostname = hostname; self.user = user; self.setores = ",".join(setores)
        self.current_root_id = None; self.current_root_type = None; self.current_path = ""; self.can_write = False
        self.monitores = []; self.stop_event = threading.Event(); self.all_items = []; self.history = []; self.history_index = -1; self.is_navigating = False 
        self.tema_atual = "claro"; self.menu_contexto = tk.Menu(self.top, tearoff=0)
        self.icon_provider = ServerIconProvider()
        
        # LIMITE DE UPLOAD (Padrão 2GB se falhar conexão)
        self.limite_upload_mb = 2048 
        self.atualizar_limite_upload()
        
        self.top.protocol("WM_DELETE_WINDOW", self.on_close)
        if TEM_DRAG_DROP:
            try: windnd.hook_dropfiles(self.top, func=self.on_drop_files_in)
            except: pass
        self.construir_layout(); self.aplicar_tema(self.tema_atual); self.roots_data = []; self.carregar_raizes(); self.timer_refresh()

    def atualizar_limite_upload(self):
        # Busca o limite configurado no servidor em uma thread para não travar
        def _fetch():
            try:
                r = requests.get(f"{URL_SERVIDOR}/api/get_config", timeout=3)
                if r.status_code == 200:
                    d = r.json()
                    if 'max_upload_size_mb' in d:
                        self.limite_upload_mb = int(d['max_upload_size_mb'])
            except: pass
        threading.Thread(target=_fetch, daemon=True).start()

    def aplicar_tema(self, nome_tema):
        self.tema_atual = nome_tema; T = TEMAS[nome_tema]; style = ttk.Style(); style.theme_use('clam')
        style.configure("Treeview", background=T["bg_janela"], foreground=T["fg_texto"], fieldbackground=T["bg_janela"], font=("Segoe UI", 11), borderwidth=0, rowheight=50)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=T["top_bg"], foreground=T["fg_texto"], relief="flat")
        style.map("Treeview", background=[('selected', T["select_bg"])], foreground=[('selected', T["select_fg"])])
        self.top.configure(bg=T["bg_janela"]); self.sidebar.configure(bg=T["sidebar_bg"]); self.listbox_roots.configure(bg=T["sidebar_bg"], fg=T["fg_texto"])
        self.main_area.configure(bg=T["bg_janela"]); self.toolbar.configure(bg=T["top_bg"]); self.content_frame.configure(bg=T["bg_janela"])
        self.frame_tree.configure(bg=T["bg_janela"]); self.lbl_path.configure(bg=T["top_bg"], fg=T["fg_texto"]); self.lbl_acesso.configure(bg=T["sidebar_bg"], fg=T["fg_texto"])
        for btn in [self.btn_back, self.btn_fwd, self.btn_upload, self.btn_theme]: btn.configure(bg=T["btn_bg"], fg=T["btn_fg"])
        self.ent_search.configure(background=T["entry_bg"], foreground=T["entry_fg"])

    def alternar_tema(self): novo = "escuro" if self.tema_atual == "claro" else "claro"; self.aplicar_tema(novo)
    
    def construir_layout(self):
        self.sidebar = tk.Frame(self.top, width=250); self.sidebar.pack(side="left", fill="y"); self.sidebar.pack_propagate(False)
        self.lbl_acesso = tk.Label(self.sidebar, text="Acesso Rápido", font=("Segoe UI", 9, "bold"), pady=15, padx=15, anchor="w"); self.lbl_acesso.pack(fill="x")
        self.listbox_roots = tk.Listbox(self.sidebar, bd=0, font=("Segoe UI", 10), selectmode=tk.SINGLE, highlightthickness=0, activestyle="none", cursor="hand2"); self.listbox_roots.pack(fill="both", expand=True, padx=10, pady=5); self.listbox_roots.bind("<<ListboxSelect>>", self.on_select_root)
        self.btn_theme = tk.Button(self.sidebar, text="🌗 Tema", command=self.alternar_tema, font=("Segoe UI", 9), bd=0, pady=5); self.btn_theme.pack(side="bottom", fill="x", padx=10, pady=10)
        self.main_area = tk.Frame(self.top); self.main_area.pack(side="right", fill="both", expand=True)
        self.toolbar = tk.Frame(self.main_area, height=60, bd=0); self.toolbar.pack(fill="x", side="top", padx=20, pady=10)
        self.btn_back = tk.Button(self.toolbar, text="⬅", command=self.go_back, font=("Segoe UI", 12), bd=0, cursor="hand2", state="disabled"); self.btn_back.pack(side="left", padx=(0, 5))
        self.btn_fwd = tk.Button(self.toolbar, text="➡", command=self.go_forward, font=("Segoe UI", 12), bd=0, cursor="hand2", state="disabled"); self.btn_fwd.pack(side="left", padx=(0, 10))
        self.lbl_path = tk.Label(self.toolbar, text="Início", font=("Segoe UI", 12, "bold")); self.lbl_path.pack(side="left")
        frame_tools = tk.Frame(self.toolbar); frame_tools.pack(side="right")
        self.ent_search = ttk.Entry(frame_tools, width=25); self.ent_search.pack(side="left", padx=10); self.ent_search.bind("<KeyRelease>", self.filtrar_itens); self.ent_search.insert(0, "Buscar..."); self.ent_search.bind("<FocusIn>", lambda e: self.ent_search.delete(0, tk.END) if "Buscar" in self.ent_search.get() else None)
        self.btn_upload = tk.Button(frame_tools, text="➕ Novo", command=self.fazer_upload_manual, font=("Segoe UI", 9, "bold"), bd=0, padx=15, pady=6, cursor="hand2", state="disabled"); self.btn_upload.pack(side="left", padx=5)
        self.content_frame = tk.Frame(self.main_area); self.content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.frame_tree = tk.Frame(self.content_frame); self.frame_tree.pack(fill="both", expand=True)
        
        # Treeview Config
        cols = ('tamanho', 'tipo', 'data')
        self.tree = ttk.Treeview(self.frame_tree, columns=cols, selectmode='browse')
        self.tree.heading('#0', text='Nome', anchor='w'); self.tree.column('#0', width=450, anchor='w')
        self.tree.heading('tamanho', text='Tamanho', anchor='e'); self.tree.column('tamanho', width=100, anchor='e')
        self.tree.heading('tipo', text='Tipo', anchor='center'); self.tree.column('tipo', width=120, anchor='center')
        self.tree.heading('data', text='Modificação', anchor='w'); self.tree.column('data', width=150, anchor='w')
        sc = ttk.Scrollbar(self.frame_tree, orient="vertical", command=self.tree.yview); self.tree.configure(yscroll=sc.set); self.tree.pack(side="left", fill="both", expand=True); sc.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.on_double_click); self.tree.bind("<Button-3>", self.mostrar_menu_contexto)

    def update_nav_buttons(self):
        self.btn_back.config(state="normal" if self.history_index > 0 else "disabled")
        self.btn_fwd.config(state="normal" if self.history_index < len(self.history) - 1 else "disabled")
    def go_back(self):
        if self.history_index > 0: self.history_index -= 1; self.is_navigating = True; self.current_path = self.history[self.history_index]; self.carregar_conteudo(); self.is_navigating = False
    def go_forward(self):
        if self.history_index < len(self.history) - 1: self.history_index += 1; self.is_navigating = True; self.current_path = self.history[self.history_index]; self.carregar_conteudo(); self.is_navigating = False
    def add_to_history(self, path):
        if self.is_navigating: return
        self.history = self.history[:self.history_index+1]; self.history.append(path); self.history_index += 1; self.update_nav_buttons()
    
    def mostrar_toast_global(self, mensagem):
        try:
            toast = tk.Toplevel(); toast.overrideredirect(True); toast.attributes('-topmost', True); ws = toast.winfo_screenwidth(); hs = toast.winfo_screenheight()
            w = 280; h = 50; x = ws - w - 20; y = hs - h - 60; toast.geometry(f"{w}x{h}+{x}+{y}"); toast.configure(bg="#107c10")
            f = tk.Frame(toast, bg="#107c10", padx=15); f.pack(fill="both", expand=True)
            tk.Label(f, text="✔ Severo Cloud", bg="#107c10", fg="white", font=("Segoe UI", 10, "bold")).pack(side="top", anchor="w")
            tk.Label(f, text=mensagem, bg="#107c10", fg="#e6f4ea", font=("Segoe UI", 9)).pack(side="top", anchor="w")
            toast.after(3000, lambda: toast.destroy())
        except: pass

    def carregar_conteudo(self, silent=False):
        if not self.current_root_id: return
        try:
            pl = {'user': self.user, 'tipo': self.current_root_type, 'id_origem': self.current_root_id, 'caminho': self.current_path}; r = requests.post(f"{URL_SERVIDOR}/api/fm/conteudo", json=pl, timeout=5)
            if r.status_code == 200:
                d = r.json()
                if 'error' in d: 
                    if "Pasta removida" in d['error']: self.current_path=""; self.carregar_raizes()
                    return
                self.all_items = d; self.render_list(d); self.lbl_path.config(text="Início" if not self.current_path else self.current_path)
                if not self.history or self.history[self.history_index] != self.current_path: self.add_to_history(self.current_path)
                self.update_nav_buttons()
        except: pass
    
    def filtrar_itens(self, event=None):
        termo = self.ent_search.get().lower(); itens_filtrados = []
        if "Buscar" in termo: termo = ""
        for i in self.all_items:
            if termo in i['nome'].lower() or (i.get('date') and termo in i.get('date').lower()): itens_filtrados.append(i)
        self.render_list(itens_filtrados)
    
    def render_list(self, items):
        self.tree.delete(*self.tree.get_children())
        for i in items:
            sz_s = f"{i['tamanho']/1024:.1f} KB" if i['tipo']=='arquivo' else ""
            dt = i.get('date', '-')
            eh_pasta = (i['tipo'] == 'pasta')
            icon_img = self.icon_provider.get_icon(i['nome'], eh_pasta)
            if icon_img:
                self.tree.insert("", "end", text=f"  {i['nome']}", image=icon_img, values=(sz_s, i['tipo'], dt))
            else:
                ic = "📁" if eh_pasta else "📄"
                self.tree.insert("", "end", text=f"{ic}  {i['nome']}", values=(sz_s, i['tipo'], dt))

    def mostrar_menu_contexto(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid); self.menu_contexto = tk.Menu(self.top, tearoff=0, bg="white", fg="black", font=("Segoe UI", 9)); st = "normal" if self.can_write else "disabled"
            self.menu_contexto.add_command(label="📂 Abrir", command=self.on_double_click); self.menu_contexto.add_command(label="💾 Baixar uma Cópia", command=self.exportar_arquivo); self.menu_contexto.add_separator(); self.menu_contexto.add_command(label="🗑 Excluir", command=self.excluir_item, state=st); self.menu_contexto.post(event.x_root, event.y_root)
    
    def abrir_e_monitorar(self, nome_arquivo):
        tmp_d = os.path.join(PASTA_TEMP_EDIT, f"sessao_{int(time.time())}"); os.makedirs(tmp_d, exist_ok=True); local_p = os.path.join(tmp_d, nome_arquivo); local_p = os.path.abspath(local_p)
        self.top.config(cursor="watch"); self.top.update()
        try:
            pl = {'user': self.user, 'tipo': self.current_root_type, 'id_origem': self.current_root_id, 'caminho': self.current_path, 'arquivo': nome_arquivo}
            r = requests.post(f"{URL_SERVIDOR}/api/fm/download", json=pl)
            if r.status_code == 200:
                with open(local_p, 'wb') as f: f.write(r.content)
                if os.path.exists(local_p) and os.path.getsize(local_p) > 0:
                    os.startfile(local_p)
                    if self.can_write:
                        def cb_sync(path):
                            try: self.upload_individual(path, show_popup=False)
                            except: pass
                        m = MonitorArquivo(local_p, cb_sync, self.stop_event); m.daemon=True; m.start(); self.monitores.append(m)
                else: messagebox.showerror("Erro", "Arquivo vazio.")
            else: messagebox.showerror("Erro", "Falha ao baixar.")
        except Exception as e: messagebox.showerror("Erro", str(e))
        finally: self.top.config(cursor="")

    # --- UPLOAD COM POPUP E VERIFICAÇÃO DE LIMITE ---
    def fazer_upload_manual(self):
        if not self.can_write: return
        fs = filedialog.askopenfilenames()
        if fs:
            threading.Thread(target=self.iniciar_upload_lista, args=(fs,), daemon=True).start()

    def on_drop_files_in(self, filenames):
        if not self.can_write: messagebox.showwarning("Aviso", "Apenas Leitura"); return
        arquivos_finais = []
        for f_bytes in filenames:
            f_path = f_bytes.decode('utf-8', errors='ignore') if isinstance(f_bytes, bytes) else f_bytes
            if os.path.isfile(f_path): arquivos_finais.append(f_path)
            elif os.path.isdir(f_path): pass 
        if arquivos_finais:
            threading.Thread(target=self.iniciar_upload_lista, args=(arquivos_finais,), daemon=True).start()

    def iniciar_upload_lista(self, lista_arquivos):
        for arq in lista_arquivos:
            self.upload_individual(arq, show_popup=True)
        self.top.after(0, self.carregar_conteudo)

    def upload_individual(self, caminho_arquivo, show_popup=True):
        nome_arq = os.path.basename(caminho_arquivo)
        
        # --- VERIFICAÇÃO DE TAMANHO PRÉVIA ---
        try:
            tamanho_arquivo = os.path.getsize(caminho_arquivo)
            limite_bytes = self.limite_upload_mb * 1024 * 1024
            if tamanho_arquivo > limite_bytes:
                msg = f"Arquivo '{nome_arq}' muito grande!\n\nLimite: {self.limite_upload_mb} MB\nArquivo: {tamanho_arquivo/(1024*1024):.1f} MB"
                self.top.after(0, lambda: messagebox.showwarning("Arquivo Recusado", msg))
                return # Cancela o envio
        except: pass
        # --------------------------------------

        popup = None
        if show_popup:
            res = [None]
            def criar_popup(): res[0] = PopupTransferencia(self.top, f"Enviando {nome_arq}")
            self.top.after(0, criar_popup)
            while res[0] is None: time.sleep(0.05)
            popup = res[0]

        try:
            def callback_progresso(lido, total, inicio):
                if popup:
                    self.top.after(0, lambda: popup.atualizar(lido, total, inicio))

            arquivo_wrap = ArquivoComCallback(caminho_arquivo, callback_progresso)
            
            files = {'files': (nome_arq, arquivo_wrap, 'application/octet-stream')}
            data = {
                'user': self.user, 
                'tipo': self.current_root_type, 
                'id_origem': self.current_root_id, 
                'caminho': self.current_path
            }
            
            requests.post(f"{URL_SERVIDOR}/api/fm/upload", data=data, files=files)
            arquivo_wrap.close()
            
            if show_popup: self.top.after(0, lambda: self.mostrar_toast_global(f"Enviado: {nome_arq}"))

        except Exception as e:
            if show_popup: self.top.after(0, lambda: messagebox.showerror("Erro", f"Falha ao enviar {nome_arq}"))
        finally:
            if popup: self.top.after(0, popup.fechar)

    def on_double_click(self, event=None):
        sel = self.tree.selection(); 
        if not sel: return
        item_id = sel[0]
        item_dict = self.tree.item(item_id)
        nm = item_dict['text'].strip()
        vals = item_dict['values']
        tp = vals[1]
        if tp == 'pasta': self.current_path = os.path.join(self.current_path, nm); self.carregar_conteudo()
        else: self.abrir_e_monitorar(nm)
    
    def exportar_arquivo(self):
        sel = self.tree.selection(); 
        if not sel: return
        item_dict = self.tree.item(sel[0])
        nm = item_dict['text'].strip()
        save_p = filedialog.asksaveasfilename(initialfile=nm, title="Baixar uma cópia em...")
        if save_p:
            try:
                r = requests.post(f"{URL_SERVIDOR}/api/fm/download", json={'user': self.user, 'tipo': self.current_root_type, 'id_origem': self.current_root_id, 'caminho': self.current_path, 'arquivo': nm}, stream=True)
                with open(save_p, 'wb') as f: 
                    for c in r.iter_content(chunk_size=8192): f.write(c)
                self.mostrar_toast_global("Arquivo exportado!"); os.startfile(os.path.dirname(save_p))
            except Exception as e: messagebox.showerror("Erro", str(e))
    def excluir_item(self):
        if not self.can_write: return
        sel = self.tree.selection(); 
        if not sel: return
        item_dict = self.tree.item(sel[0])
        nm = item_dict['text'].strip()
        if messagebox.askyesno("Excluir", f"Apagar '{nm}'?"):
            try:
                r = requests.post(f"{URL_SERVIDOR}/api/fm/excluir", json={'user': self.user, 'tipo': self.current_root_type, 'id_origem': self.current_root_id, 'caminho': self.current_path, 'nome': nm})
                if r.json().get('status')=='ok': self.carregar_conteudo(); self.mostrar_toast_global("Item excluído")
                else: messagebox.showerror("Erro", "Erro ao excluir.")
            except: pass
    def timer_refresh(self):
        if self.top.winfo_exists():
            if self.current_root_id: self.carregar_conteudo(silent=True)
            self.carregar_raizes(silent=True)
            self.top.after(5000, self.timer_refresh)
    def carregar_raizes(self, silent=False):
        try:
            r = requests.post(f"{URL_SERVIDOR}/api/fm/listar_raizes", json={'user': self.user, 'setores': self.setores}, timeout=2)
            if r.status_code == 200:
                new = r.json(); cur = [x['nome'] for x in self.roots_data]
                if cur != [x['nome'] for x in new]:
                    self.roots_data = new; self.listbox_roots.delete(0, tk.END)
                    for i in self.roots_data:
                        ic = "🔒" if i['tipo']=='pessoal' else "📂"; pm = "" if i['pode_escrever'] else " (Leitura)"
                        self.listbox_roots.insert(tk.END, f"{ic} {i['nome']}{pm}")
                    if not self.current_root_id and self.roots_data: self.listbox_roots.selection_set(0); self.on_select_root(None)
        except: pass
    def on_select_root(self, event):
        sel = self.listbox_roots.curselection(); 
        if not sel: return
        d = self.roots_data[sel[0]]; self.current_root_id = d['id']; self.current_root_type = d['tipo']; self.can_write = d['pode_escrever']
        self.current_path = ""; self.history = []; self.history_index = -1; self.btn_upload.config(state="normal" if self.can_write else "disabled"); self.carregar_conteudo()
    def on_close(self): self.stop_event.set(); self.top.destroy()