from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_from_directory, send_file, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import os, time, shutil, hashlib

from .extensions import db, socketio, FILA_ATENDIMENTO
from .models import *

bp = Blueprint('main', __name__)

def calcular_md5(caminho_arquivo):
    if not os.path.exists(caminho_arquivo): return None
    try:
        hash_md5 = hashlib.md5()
        with open(caminho_arquivo, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""): hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except: return None

def validar_caminho(base, subcaminho):
    if not base or not os.path.exists(base): return None
    caminho_real = os.path.abspath(os.path.join(base, subcaminho))
    if not caminho_real.startswith(os.path.abspath(base)): return None
    return caminho_real

@bp.route('/login', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        user = request.form['usuario']; senha = request.form['senha']
        admin = Admin.query.filter_by(usuario=user, senha=senha).first()
        if (user == "admin" and senha == "admin") or admin: session['admin_logado'] = True; return redirect(url_for('main.index'))
        return render_template('login_admin.html', erro="Dados incorretos")
    return render_template('login_admin.html')

@bp.route('/')
def index():
    if 'admin_logado' not in session: return redirect(url_for('main.login_admin'))
    computadores = Computador.query.all()
    usuarios = Usuario.query.all()
    logs = LogAcesso.query.order_by(LogAcesso.id.desc()).limit(50).all()
    logs_arquivos = LogArquivo.query.order_by(LogArquivo.id.desc()).limit(100).all()
    chats_finalizados = ChatHistorico.query.order_by(ChatHistorico.id.desc()).limit(50).all()
    restricoes = Restricao.query.all()
    atalhos = Atalho.query.all()
    ramais = Ramal.query.all()
    setores = Setor.query.all()
    impressoras = Impressora.query.all()
    pastas_setor = PastaSetor.query.all()
    logs_pastas = LogPasta.query.order_by(LogPasta.id.desc()).limit(100).all()
    icones_arquivos = ArquivoIcone.query.all()
    
    if not setores: db.session.add(Setor(nome="Geral")); db.session.commit(); setores = Setor.query.all()
    conf = Config.query.first()
    if not conf: conf = Config(); db.session.add(conf); db.session.commit()
    
    return render_template('painel.html', computadores=computadores, usuarios=usuarios, logs=logs, logs_arquivos=logs_arquivos, chats_finalizados=chats_finalizados, restricoes=restricoes, config=conf, atalhos=atalhos, ramais=ramais, setores=setores, impressoras=impressoras, pastas_setor=pastas_setor, logs_pastas=logs_pastas, arquivos_icones=icones_arquivos)

@bp.route('/acao/add_pasta', methods=['POST'])
def add_pasta():
    lista = request.form.getlist('setores_pasta')
    str_s = "Todos" if 'Todos' in lista or not lista else ",".join(lista)
    pode_escrever = True if 'pode_escrever' in request.form else False
    db.session.add(PastaSetor(nome_exibicao=request.form['nome'], caminho_rede=request.form['caminho'], setores_permitidos=str_s, permite_escrita=pode_escrever))
    db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/acao/del_pasta/<int:id>')
def del_pasta(id): PastaSetor.query.filter_by(id=id).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/edit_pasta', methods=['POST'])
def edit_pasta():
    p = PastaSetor.query.get(request.form['id_pasta'])
    if p:
        p.nome_exibicao = request.form['nome']
        p.caminho_rede = request.form['caminho']
        lista = request.form.getlist('setores_pasta')
        p.setores_permitidos = "Todos" if 'Todos' in lista or not lista else ",".join(lista)
        p.permite_escrita = True if 'pode_escrever' in request.form else False
        db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/acao/limpar_logs_pastas')
def limpar_logs_pastas(): db.session.query(LogPasta).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/configurar', methods=['POST'])
def configurar():
    conf = Config.query.first()
    if not conf: conf = Config(); db.session.add(conf)
    if 'senha_unica' in request.form and request.form['senha_unica'].strip():
        nova_senha = request.form['senha_unica'].strip()
        conf.senha_engrenagem = nova_senha; conf.senha_mestre = nova_senha
    if 'chat_saudacao' in request.form: conf.chat_saudacao = request.form['chat_saudacao']
    
    conf.databit_nome = request.form.get('databit_nome', 'DataBit')
    conf.databit_comando = request.form.get('databit_comando', '')
    conf.databit_tipo = request.form.get('databit_tipo', 'site')
    
    if 'caminho_cofre_global' in request.form: conf.caminho_cofre_global = request.form['caminho_cofre_global']
    if 'caminho_datinet_global' in request.form: conf.caminho_datinet_global = request.form['caminho_datinet_global']
    if 'caminho_drive_z' in request.form: conf.caminho_drive_z = request.form['caminho_drive_z']

    if 'dev_linha1' in request.form: conf.dev_linha1 = request.form['dev_linha1']
    if 'dev_linha2' in request.form: conf.dev_linha2 = request.form['dev_linha2']
    if 'dev_linha3' in request.form: conf.dev_linha3 = request.form['dev_linha3']

    # --- LIMITE UPLOAD ---
    if 'max_upload_size_mb' in request.form:
        try:
            tamanho_mb = int(request.form['max_upload_size_mb'])
            conf.max_upload_size_mb = tamanho_mb
            # Aplica no app rodando agora
            current_app.config['MAX_CONTENT_LENGTH'] = tamanho_mb * 1024 * 1024
        except: pass

    conf.termos_ativo = 'termos_ativo' in request.form; conf.termos_texto = request.form.get('termos_texto', '')
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    logos_folder = current_app.config['LOGOS_FOLDER']
    icons_folder = current_app.config['ICONS_FOLDER']

    # --- ATUALIZADO: Inclui 'file_quiosque' na lista de processamento ---
    for file_key, conf_key in [
        ('file_login', 'wallpaper_login'), 
        ('file_desktop', 'wallpaper_desktop'), 
        ('file_chat', 'wallpaper_chat'),
        ('file_quiosque', 'wall_quiosque')
    ]:
        if file_key in request.files:
            f = request.files[file_key]
            if f.filename != '': 
                nome = f"wall_{conf_key}_{int(time.time())}.jpg"
                f.save(os.path.join(upload_folder, nome))
                setattr(conf, conf_key, nome)
    
    if 'logo_img' in request.files:
        f = request.files['logo_img']
        if f.filename != '': nome_logo = "logo_cliente.png"; f.save(os.path.join(logos_folder, nome_logo)); conf.logo_atual = nome_logo
    for file_key, conf_key in [('icon_chrome', 'icon_chrome'), ('icon_firefox', 'icon_firefox'), ('icon_edge', 'icon_edge')]:
        if file_key in request.files:
            f = request.files[file_key]
            if f.filename != '': ext = f.filename.split('.')[-1]; nome = f"datinet_{conf_key}_{int(time.time())}.{ext}"; f.save(os.path.join(icons_folder, nome)); setattr(conf, conf_key, nome)
    
    db.session.commit()
    socketio.emit('comando_sistema', {'acao': 'atualizar_wallpaper'}); socketio.emit('comando_sistema', {'acao': 'atualizar_config'}); 
    return redirect(url_for('main.index'))

@bp.route('/acao/add_setor', methods=['POST'])
def add_setor():
    nome = request.form['nome'].strip()
    if nome and not Setor.query.filter_by(nome=nome).first(): db.session.add(Setor(nome=nome)); db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/acao/del_setor/<int:id>')
def del_setor(id): Setor.query.filter_by(id=id).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/add_usuario', methods=['POST'])
def add_usuario():
    lista = request.form.getlist('setores_lista'); str_s = ",".join(lista) if lista else "Geral"; sem = 'sem_restricao' in request.form
    db.session.add(Usuario(nome=request.form['nome'], sobrenome=request.form['sobrenome'], usuario=request.form['usuario'], senha=request.form['senha'], setor=str_s, sem_restricao=sem)); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/edit_usuario', methods=['POST'])
def edit_usuario():
    u = Usuario.query.get(request.form['id_usuario'])
    if u: u.nome=request.form['nome']; u.sobrenome=request.form['sobrenome']; u.usuario=request.form['usuario']; u.senha=request.form['senha']; u.setor=",".join(request.form.getlist('setores_lista')); u.sem_restricao='sem_restricao' in request.form; db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/acao/del_usuario/<int:id>')
def del_usuario(id): Usuario.query.filter_by(id=id).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/add_impressora', methods=['POST'])
def add_impressora():
    lista = request.form.getlist('setores_impressora'); str_s = "Todos" if 'Todos' in lista or not lista else ",".join(lista)
    db.session.add(Impressora(nome_exibicao=request.form['nome_exibicao'], caminho_rede=request.form['caminho_rede'], setores_permitidos=str_s)); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/del_impressora/<int:id>')
def del_impressora(id): Impressora.query.filter_by(id=id).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/add_atalho', methods=['POST'])
def add_atalho():
    icone_nome = None
    if 'arquivo_icone' in request.files: 
        f = request.files['arquivo_icone']
        if f.filename!='': 
            ext=f.filename.split('.')[-1]; icone_nome=f"icon_{int(time.time())}.{ext}"
            f.save(os.path.join(current_app.config['ICONS_FOLDER'], icone_nome))
    lista = request.form.getlist('setores_atalho'); str_s = "Livre" if 'Livre' in lista or not lista else ",".join(lista)
    db.session.add(Atalho(nome=request.form['nome'], comando=request.form['comando'], tipo=request.form['tipo'], icone=icone_nome, setores=str_s)); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/edit_atalho', methods=['POST'])
def edit_atalho():
    a = Atalho.query.get(request.form['id_atalho'])
    if a:
        a.nome=request.form['nome']; a.comando=request.form['comando']; a.tipo=request.form['tipo']; lista=request.form.getlist('setores_atalho'); a.setores="Livre" if 'Livre' in lista or not lista else ",".join(lista)
        if 'arquivo_icone' in request.files: 
            f=request.files['arquivo_icone']
            if f.filename!='': 
                ext=f.filename.split('.')[-1]; icone_nome=f"icon_{int(time.time())}.{ext}"
                f.save(os.path.join(current_app.config['ICONS_FOLDER'], icone_nome)); a.icone=icone_nome
        db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/del_atalho/<int:id>')
def del_atalho(id): Atalho.query.filter_by(id=id).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/add_ramal', methods=['POST'])
def add_ramal(): db.session.add(Ramal(nome=request.form['nome'], setor=request.form['setor'], numero=request.form['numero'])); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/del_ramal/<int:id>')
def del_ramal(id): Ramal.query.filter_by(id=id).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/del_computador/<int:id>')
def del_computador(id): Computador.query.filter_by(id=id).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/comando_remoto/<int:id>/<comando>')
def comando_remoto(id, comando): 
    pc = Computador.query.get(id)
    if pc: socketio.emit('comando_remoto', {'acao': comando}, to=pc.hostname)
    return redirect(url_for('main.index'))

@bp.route('/acao/add_restricao', methods=['POST'])
def add_restricao(): db.session.add(Restricao(tipo=request.form['tipo'], alvo=request.form['alvo'])); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/del_restricao/<int:id>')
def del_restricao(id): Restricao.query.filter_by(id=id).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/limpar_chat_tudo')
def limpar_chat_tudo(): db.session.query(ChatLog).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/limpar_logs_acesso')
def limpar_logs_acesso(): db.session.query(LogAcesso).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/limpar_logs_arquivos')
def limpar_logs_arquivos(): db.session.query(LogArquivo).delete(); db.session.commit(); return redirect(url_for('main.index'))

@bp.route('/acao/add_arquivo_icone', methods=['POST'])
def add_arquivo_icone():
    ext = request.form['extensao'].strip().lower()
    if not ext.startswith('.'): ext = f".{ext}"
    if 'arquivo_imagem' in request.files:
        f = request.files['arquivo_imagem']
        if f.filename != '':
            antigo = ArquivoIcone.query.filter_by(extensao=ext).first()
            if antigo:
                try: os.remove(os.path.join(current_app.config['ICONS_FOLDER'], antigo.nome_arquivo))
                except: pass
                db.session.delete(antigo)
            nome_final = f"file_icon_{ext.replace('.','')}_{int(time.time())}.png"
            f.save(os.path.join(current_app.config['ICONS_FOLDER'], nome_final))
            novo = ArquivoIcone(extensao=ext, nome_arquivo=nome_final)
            db.session.add(novo)
            db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/acao/del_arquivo_icone/<int:id>')
def del_arquivo_icone(id):
    icon = ArquivoIcone.query.get(id)
    if icon:
        try: os.remove(os.path.join(current_app.config['ICONS_FOLDER'], icon.nome_arquivo))
        except: pass
        db.session.delete(icon)
        db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/api/get_file_icons_map', methods=['GET'])
def get_file_icons_map():
    icons = ArquivoIcone.query.all()
    mapa = {}
    for i in icons:
        mapa[i.extensao] = i.nome_arquivo
    return jsonify(mapa)

@bp.route('/api/login_cliente', methods=['POST'])
def api_login():
    d = request.json
    if d['user'] == 'admin' and d['pass'] == 'admin': 
        db.session.add(LogAcesso(computador=d['hostname'], usuario='SUPER ADMIN', acao="Entrou"))
        db.session.commit()
        return jsonify({'status': 'ok', 'setores': 'TODOS', 'sem_restricao': True, 'nome_real': 'Administrador'})
    
    u = Usuario.query.filter_by(usuario=d['user'], senha=d['pass']).first()
    if not u: return jsonify({'status': 'erro'})
    
    db.session.add(LogAcesso(computador=d['hostname'], usuario=d['user'], acao="Entrou"))
    db.session.commit()
    
    return jsonify({
        'status': 'ok', 
        'setores': u.setor, 
        'sem_restricao': u.sem_restricao,
        'nome_real': f"{u.nome} {u.sobrenome}"
    })

@bp.route('/api/check_master', methods=['POST'])
def api_check_master():
    d = request.json; conf = Config.query.first(); senha = d.get('senha')
    if not conf: conf = Config(); db.session.add(conf); db.session.commit()
    if conf.senha_mestre == senha: db.session.add(LogAcesso(computador=d['hostname'], usuario='ADMIN_MASTER', acao="Desbloqueio Mestre")); db.session.commit(); return jsonify({'status': 'ok'})
    return jsonify({'status': 'erro'})

@bp.route('/api/logout_cliente', methods=['POST'])
def api_logout(): 
    d = request.json
    if d['hostname'] in FILA_ATENDIMENTO: FILA_ATENDIMENTO.remove(d['hostname'])
    db.session.add(LogAcesso(computador=d['hostname'], usuario=d.get('user',''), acao="Saiu")); db.session.commit(); return jsonify({'status': 'ok'})

@bp.route('/api/get_config', methods=['GET'])
def get_config():
    c = Config.query.first()
    if not c: c = Config(); db.session.add(c); db.session.commit()
    progs = [r.alvo for r in Restricao.query.filter_by(tipo='programa').all()]
    sites = [r.alvo for r in Restricao.query.filter_by(tipo='site').all()]
    lista_atalhos = []
    
    icons_folder = current_app.config['ICONS_FOLDER']
    upload_folder = current_app.config['UPLOAD_FOLDER']
    logos_folder = current_app.config['LOGOS_FOLDER']

    for a in Atalho.query.all():
        hash_icone = None
        if a.icone: path_icon = os.path.join(icons_folder, a.icone); hash_icone = calcular_md5(path_icon)
        lista_atalhos.append({'id': a.id, 'nome': a.nome, 'comando': a.comando, 'tipo': a.tipo, 'icone': a.icone, 'setores': a.setores, 'hash_icone': hash_icone})

    hashes_ativos = {
        'wall_login': calcular_md5(os.path.join(upload_folder, c.wallpaper_login)) if c.wallpaper_login else None,
        'wall_desktop': calcular_md5(os.path.join(upload_folder, c.wallpaper_desktop)) if c.wallpaper_desktop else None,
        'wall_chat': calcular_md5(os.path.join(upload_folder, c.wallpaper_chat)) if c.wallpaper_chat else None,
        # --- ATUALIZADO: HASH DO WALLPAPER DO QUIOSQUE ---
        'wall_quiosque': calcular_md5(os.path.join(upload_folder, c.wall_quiosque)) if getattr(c, 'wall_quiosque', None) else None,
        # -------------------------------------------------
        'logo': calcular_md5(os.path.join(logos_folder, c.logo_atual)) if c.logo_atual else None,
        'icon_chrome': calcular_md5(os.path.join(icons_folder, c.icon_chrome)) if c.icon_chrome else None,
        'icon_firefox': calcular_md5(os.path.join(icons_folder, c.icon_firefox)) if c.icon_firefox else None,
        'icon_edge': calcular_md5(os.path.join(icons_folder, c.icon_edge)) if c.icon_edge else None,
    }

    return jsonify({
        'senha_engrenagem': c.senha_engrenagem, 
        'wall_login': c.wallpaper_login, 
        'wall_desktop': c.wallpaper_desktop, 
        'wall_chat': c.wallpaper_chat, 
        # --- ATUALIZADO: ENVIA O NOME DO ARQUIVO PARA O CLIENTE ---
        'wall_quiosque': getattr(c, 'wall_quiosque', None),
        # ----------------------------------------------------------
        'logo': c.logo_atual, 
        'hashes': hashes_ativos, 
        'databit': {'nome': c.databit_nome, 'comando': c.databit_comando, 'tipo': c.databit_tipo}, 
        'caminho_cofre': c.caminho_cofre_global, 
        'caminho_datinet': c.caminho_datinet_global, 
        'caminho_drive_z': c.caminho_drive_z,
        'datinet_icons': {'chrome': c.icon_chrome, 'firefox': c.icon_firefox, 'edge': c.icon_edge}, 
        'termos': {'ativo': c.termos_ativo, 'texto': c.termos_texto}, 
        'creditos': {
            'l1': c.dev_linha1,
            'l2': c.dev_linha2,
            'l3': c.dev_linha3
        },
        'bloqueio_programas': progs, 
        'bloqueio_sites': sites, 
        'atalhos': lista_atalhos
    })

@bp.route('/api/get_impressoras', methods=['POST'])
def api_get_impressoras():
    d = request.json; user_setores = d.get('setores', 'TODOS').split(',')
    imps = Impressora.query.all(); resultado = []
    for imp in imps:
        imp_setores = imp.setores_permitidos.split(',')
        if 'Todos' in imp_setores or 'TODOS' in user_setores or any(s.strip() in user_setores for s in imp_setores):
            resultado.append({'nome': imp.nome_exibicao, 'caminho': imp.caminho_rede})
    return jsonify(resultado)

@bp.route('/api/get_ramais', methods=['GET'])
def get_ramais(): return jsonify([{'nome': r.nome, 'setor': r.setor, 'numero': r.numero} for r in Ramal.query.all()])

@bp.route('/api/wallpaper/<filename>')
def serve_wallpaper(filename): return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
@bp.route('/api/icon/<filename>')
def serve_icon(filename): return send_from_directory(current_app.config['ICONS_FOLDER'], filename)
@bp.route('/api/logo/<filename>')
def serve_logo(filename): return send_from_directory(current_app.config['LOGOS_FOLDER'], filename)
@bp.route('/api/get_chat_history/<hostname>')
def get_chat(hostname): msgs = ChatLog.query.filter_by(hostname=hostname).all(); return jsonify([{'remetente': m.remetente, 'msg': m.mensagem, 'usuario_real': m.usuario_real} for m in msgs])

@bp.route('/api/fm/listar_raizes', methods=['POST'])
def api_fm_raizes():
    d = request.json
    usuario = d.get('user')
    setores_user = d.get('setores', []).split(',')
    raizes = []
    conf = Config.query.first()
    path_cofre = conf.caminho_cofre_global if conf else "C:\\Cofres"
    path_user = os.path.join(path_cofre, f"Cofre_{usuario}")
    if not os.path.exists(path_user): os.makedirs(path_user)
    raizes.append({'id': 'cofre', 'nome': '🔐 Meu Cofre Pessoal', 'tipo': 'pessoal', 'pode_escrever': True})
    pastas = PastaSetor.query.all()
    for p in pastas:
        p_setores = p.setores_permitidos.split(',')
        permitido = False
        if 'Todos' in p_setores or 'TODOS' in setores_user: permitido = True
        else:
            for s in setores_user:
                if s.strip() in p_setores: permitido = True; break
        if permitido:
            raizes.append({'id': p.id, 'nome': f"📂 {p.nome_exibicao}", 'tipo': 'setor', 'pode_escrever': p.permite_escrita})
    return jsonify(raizes)

@bp.route('/api/fm/conteudo', methods=['POST'])
def api_fm_conteudo():
    d = request.json
    usuario = d.get('user'); tipo = d.get('tipo'); id_origem = d.get('id_origem'); subcaminho = d.get('caminho', '')
    base_path = ""
    if tipo == 'pessoal':
        conf = Config.query.first(); base_path = os.path.join(conf.caminho_cofre_global, f"Cofre_{usuario}")
    else:
        p = PastaSetor.query.get(id_origem)
        if not p: return jsonify({'error': 'Pasta removida'})
        base_path = p.caminho_rede
    caminho_final = validar_caminho(base_path, subcaminho)
    if not caminho_final or not os.path.exists(caminho_final): return jsonify({'error': 'Caminho inválido'})
    itens = []
    try:
        with os.scandir(caminho_final) as it:
            for entry in it:
                if entry.name.startswith('.'): continue
                tipo_item = 'pasta' if entry.is_dir() else 'arquivo'
                tamanho = entry.stat().st_size if entry.is_file() else 0
                itens.append({'nome': entry.name, 'tipo': tipo_item, 'tamanho': tamanho})
    except Exception as e: return jsonify({'error': str(e)})
    itens.sort(key=lambda x: (x['tipo'] != 'pasta', x['nome'].lower()))
    return jsonify(itens)

@bp.route('/api/fm/upload', methods=['POST'])
def api_fm_upload():
    user = request.form['user']
    tipo = request.form['tipo']
    id_origem = request.form['id_origem']
    subcaminho = request.form['caminho']
    base_path = ""
    if tipo == 'pessoal':
        conf = Config.query.first(); base_path = os.path.join(conf.caminho_cofre_global, f"Cofre_{user}")
    else:
        p = PastaSetor.query.get(id_origem)
        if not p: return jsonify({'status': 'erro', 'msg': 'Pasta não existe'})
        if not p.permite_escrita: return jsonify({'status': 'erro', 'msg': 'Apenas Leitura!'})
        base_path = p.caminho_rede
    dest_dir = validar_caminho(base_path, subcaminho)
    if not dest_dir: return jsonify({'status': 'erro'})
    if not os.path.exists(dest_dir):
        try: os.makedirs(dest_dir, exist_ok=True)
        except Exception as e: return jsonify({'status': 'erro', 'msg': f'Erro ao criar pasta: {str(e)}'})
    files = request.files.getlist('files')
    count = 0
    for f in files:
        if f.filename:
            fn = secure_filename(f.filename)
            f.save(os.path.join(dest_dir, fn))
            db.session.add(LogArquivo(hostname="WEB-FM", usuario=user, acao="UPLOAD", arquivo=f"{tipo}:{fn}"))
            count += 1
    db.session.commit()
    return jsonify({'status': 'ok', 'count': count})

@bp.route('/api/fm/download', methods=['POST'])
def api_fm_download():
    d = request.json
    tipo = d.get('tipo'); id_origem = d.get('id_origem'); subcaminho = d.get('caminho'); arquivo = d.get('arquivo')
    base_path = ""
    if tipo == 'pessoal':
        conf = Config.query.first(); base_path = os.path.join(conf.caminho_cofre_global, f"Cofre_{d.get('user')}")
    else:
        p = PastaSetor.query.get(id_origem); base_path = p.caminho_rede if p else ""
    path_file = validar_caminho(base_path, os.path.join(subcaminho, arquivo))
    if path_file and os.path.exists(path_file):
        db.session.add(LogArquivo(hostname="WEB-FM", usuario=d.get('user'), acao="DOWNLOAD", arquivo=arquivo))
        db.session.commit()
        return send_file(path_file, as_attachment=True)
    return "Erro", 404

@bp.route('/api/fm/excluir', methods=['POST'])
def api_fm_excluir():
    d = request.json
    tipo = d.get('tipo'); id_origem = d.get('id_origem')
    base_path = ""
    if tipo == 'pessoal':
        conf = Config.query.first(); base_path = os.path.join(conf.caminho_cofre_global, f"Cofre_{d.get('user')}")
    else:
        p = PastaSetor.query.get(id_origem)
        if not p.permite_escrita: return jsonify({'status': 'erro', 'msg': 'Sem permissão'})
        base_path = p.caminho_rede
    alvo = validar_caminho(base_path, os.path.join(d.get('caminho'), d.get('nome')))
    if alvo and os.path.exists(alvo):
        try:
            if os.path.isdir(alvo): shutil.rmtree(alvo)
            else: os.remove(alvo)
            db.session.add(LogArquivo(hostname="WEB-FM", usuario=d.get('user'), acao="EXCLUIU", arquivo=d.get('nome')))
            db.session.commit()
            return jsonify({'status': 'ok'})
        except Exception as e: return jsonify({'status': 'erro', 'msg': str(e)})
    return jsonify({'status': 'erro'})