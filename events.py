from flask_socketio import emit, join_room, leave_room
from .extensions import db, socketio, FILA_ATENDIMENTO
from .models import Computador, ChatLog, ChatHistorico, Config
from datetime import datetime

@socketio.on('status_update')
def handle_status(data):
    h = data['hostname']
    # --- CORREÇÃO: Cliente entra na sala com seu próprio nome ---
    join_room(h)
    
    with db.session.no_autoflush:
        pc = Computador.query.filter_by(hostname=h).first()
        if not pc: 
            pc = Computador(hostname=h)
            db.session.add(pc)
        pc.status = data['status']
        pc.usuario_atual = data.get('user', '')
        pc.ultimo_visto = datetime.now()
        db.session.commit()
        # Avisa apenas os admins sobre a atualização
        emit('update_painel', {'id': pc.id, 'status': pc.status, 'user': pc.usuario_atual}, to='admins')

@socketio.on('admin_entrar_painel')
def handle_admin_entrar():
    # --- CORREÇÃO: Admin entra na sala global 'admins' ---
    join_room('admins') 

@socketio.on('cliente_entrar_fila')
def handle_entrar_fila(data):
    hostname = data['hostname']
    join_room(hostname) # Garante sala
    
    if hostname not in FILA_ATENDIMENTO: FILA_ATENDIMENTO.append(hostname)
    pos = FILA_ATENDIMENTO.index(hostname)
    
    # Tenta buscar configuração de saudação
    saudacao = "Olá! Em que posso ajudar?"
    try:
        conf = Config.query.first()
        if conf and conf.chat_saudacao: saudacao = conf.chat_saudacao
    except: pass

    if pos == 0: emit('chat_receber', {'msg': f"📢 {saudacao}", 'remetente': 'Sistema'}, to=hostname)
    else: emit('chat_receber', {'msg': f"⏳ Você é o número {pos} da fila de espera.", 'remetente': 'Sistema'}, to=hostname)

@socketio.on('admin_finalizar_atendimento')
def handle_finalizar_fila(data):
    hostname = data['hostname']
    msgs = ChatLog.query.filter_by(hostname=hostname).all()
    if msgs:
        texto_completo = ""
        usuario_nome = "Desconhecido"
        for m in msgs: 
            hora = m.data_hora.strftime("%H:%M")
            texto_completo += f"[{hora}] {m.remetente}: {m.mensagem}\n"
            if m.usuario_real: usuario_nome = m.usuario_real
        hist = ChatHistorico(computador=hostname, usuario=usuario_nome, conversa_completa=texto_completo)
        db.session.add(hist)
        ChatLog.query.filter_by(hostname=hostname).delete()
        db.session.commit()
    
    if hostname in FILA_ATENDIMENTO: FILA_ATENDIMENTO.remove(hostname)
    emit('chat_limpar', {}, to=hostname)

@socketio.on('chat_mensagem_cliente')
def handle_client_msg(data):
    hostname = data['hostname']
    join_room(hostname) # Reforço
    usuario_real = data.get('user', 'Desconhecido')
    msg = data['msg']
    
    if hostname not in FILA_ATENDIMENTO: FILA_ATENDIMENTO.append(hostname)
    
    db.session.add(ChatLog(hostname=hostname, usuario_real=usuario_real, remetente=usuario_real, mensagem=msg))
    db.session.commit()
    # Envia para os admins verem
    emit('admin_receber_chat', {'hostname': hostname, 'remetente': usuario_real, 'msg': msg}, to='admins')

@socketio.on('chat_mensagem_admin')
def handle_admin_msg(data): 
    hostname = data['hostname']
    msg = data['msg']
    
    db.session.add(ChatLog(hostname=hostname, usuario_real='Admin', remetente='Admin', mensagem=msg))
    db.session.commit()
    
    # Envia especificamente para o cliente (agora funciona por causa do join_room)
    emit('chat_receber', {'msg': msg, 'remetente': 'Admin'}, to=hostname)

@socketio.on('enviar_mensagem_geral')
def handle_msg_geral(data): emit('aviso_sistema', {'msg': data['msg']}, broadcast=True)

@socketio.on('enviar_mensagem_individual')
def handle_msg_individual(data): emit('aviso_sistema', {'msg': data['msg']}, to=data['hostname'])

@socketio.on('solicitar_acesso_remoto')
def handle_solicitar_remoto(data): emit('pedido_acesso_remoto', {}, to=data['hostname'])

@socketio.on('acesso_remoto_aceito')
def handle_aceito(data): emit('iniciar_transmissao_remota', {'hostname': data['hostname']}, to='admins')

@socketio.on('frame_tela_cliente')
def handle_frame(data): 
    # Repassa o frame APENAS para os admins (sala 'admins')
    emit('atualizar_tela_remota', data, to='admins')

@socketio.on('comando_mouse_teclado')
def handle_input(data): emit('executar_input_remoto', data, to=data['hostname'])