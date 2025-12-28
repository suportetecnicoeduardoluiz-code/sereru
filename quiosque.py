import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import requests, os
from config import URL_SERVIDOR, PASTA_ICONES, CONFIG_DATABIT

class QuiosqueFrame(tk.Frame):
    def __init__(self, parent, usuario_setores, tema_dict):
        super().__init__(parent, bg=tema_dict["bg_container"])
        self.parent = parent
        self.setores = usuario_setores
        self.tema = tema_dict
        
        # Configuração do Scroll
        self.canvas = tk.Canvas(self, bg=self.tema["bg_container"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.tema["bg_container"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.carregar_atalhos()

    def carregar_atalhos(self):
        try:
            r = requests.get(f"{URL_SERVIDOR}/api/get_config", timeout=3)
            dados = r.json()
            atalhos = dados.get('atalhos', [])
            
            # Atualiza config Databit globalmente se necessário
            if 'databit' in dados:
                CONFIG_DATABIT.update(dados['databit'])

            self.desenhar_grade(atalhos)
        except Exception as e:
            tk.Label(self.scrollable_frame, text=f"Erro ao carregar: {e}", bg="red", fg="white").pack()

    def desenhar_grade(self, atalhos_raw):
        # Limpa
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Filtra atalhos permitidos
        atalhos_filtrados = []
        for item in atalhos_raw:
            setores_atalho = [s.strip() for s in item.get('setores', 'Livre').split(',')]
            
            # Lógica de permissão
            eh_livre = 'Livre' in setores_atalho
            tem_permissao = 'TODOS' in self.setores or any(s in self.setores for s in setores_atalho)
            
            if eh_livre or tem_permissao:
                # Prioridade 0 = Setor específico (aparece primeiro), 1 = Livre
                item['prioridade'] = 0 if tem_permissao and not eh_livre else 1
                atalhos_filtrados.append(item)
        
        atalhos_filtrados.sort(key=lambda x: x['prioridade'])

        if not atalhos_filtrados:
            tk.Label(self.scrollable_frame, text="Nenhum atalho disponível.", bg=self.tema["bg_container"], fg=self.tema["fg_texto"]).pack(pady=20)
            return

        # Grid system
        row, col = 0, 0
        max_cols = 3  # Colunas por linha na sidebar
        
        for i in atalhos_filtrados:
            f = tk.Frame(self.scrollable_frame, bg=self.tema["bg_container"], padx=5, pady=5)
            f.grid(row=row, column=col, sticky="nsew")
            
            img = None
            if i.get('icone'):
                pth = os.path.join(PASTA_ICONES, i['icone'])
                # Se não existir local, tenta baixar (simplificado)
                if not os.path.exists(pth):
                    self.baixar_icone(i['icone'])
                
                if os.path.exists(pth):
                    try:
                        pil_img = Image.open(pth).resize((40, 40), Image.Resampling.LANCZOS)
                        img = ImageTk.PhotoImage(pil_img)
                    except: pass
            
            nome = i['nome']
            if len(nome) > 12: nome = nome[:10] + ".."
            
            # Cria o botão
            if img:
                b = tk.Button(f, text=nome, image=img, compound="top", font=("Segoe UI", 8, "bold"), 
                              bg="#e9ecef", bd=0, relief="raised")
                b.image = img # Mantém referência para não sumir
                b.config(height=65, width=80)
            else:
                ic = "💻" if i['tipo']=='programa' else "🌐"
                b = tk.Button(f, text=f"{ic}\n{nome}", font=("Segoe UI", 8, "bold"), 
                              bg="#e9ecef", bd=0, relief="raised", height=4, width=12)
            
            b.config(command=lambda c=i['comando'], t=i['tipo']: self.exec_atalho(c, t))
            b.pack()

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def baixar_icone(self, nome_arquivo):
        try:
            r = requests.get(f"{URL_SERVIDOR}/api/icon/{nome_arquivo}", timeout=2)
            if r.status_code == 200:
                with open(os.path.join(PASTA_ICONES, nome_arquivo), 'wb') as f:
                    f.write(r.content)
        except: pass

    def exec_atalho(self, comando, tipo):
        try:
            os.startfile(comando)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir:\n{comando}\n\nErro: {e}")