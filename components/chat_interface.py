#!/usr/bin/env python3
"""
Interface de Chat Integrada
Sistema completo de chat com API principal baseado no 8505-viewer
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional

def render_integrated_chat_interface(main_api_url: str = "http://localhost:8990"):
    """
    Renderiza interface de chat integrada completa
    
    Args:
        main_api_url: URL da API principal para chat
    """
    
    st.header("💬 Chat Integrado com Claude")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        render_chat_configuration(main_api_url)
    
    with col2:
        render_chat_conversation()

def render_chat_configuration(main_api_url: str):
    """Renderiza painel de configuração do chat"""
    
    st.subheader("⚙️ Configuração do Chat")
    
    # Status da conexão
    test_connection_status(main_api_url)
    
    # Configurações da sessão
    st.markdown("#### 🛠️ Configurações da Sessão")
    
    # System prompt
    system_prompt = st.text_area(
        "System Prompt:",
        value=st.session_state.get('chat_system_prompt', 
                                  "Você é um assistente especializado em Claude Code. Responda sempre em português brasileiro."),
        height=100,
        help="Instruções iniciais para o Claude"
    )
    st.session_state.chat_system_prompt = system_prompt
    
    # Ferramentas permitidas
    available_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebFetch", "TodoWrite"]
    
    selected_tools = st.multiselect(
        "Ferramentas Permitidas:",
        available_tools,
        default=st.session_state.get('chat_tools', ["Read", "Write", "Edit", "Bash"]),
        help="Ferramentas que o Claude pode usar nesta sessão"
    )
    st.session_state.chat_tools = selected_tools
    
    # Configurações avançadas
    with st.expander("⚙️ Configurações Avançadas"):
        max_turns = st.number_input("Máximo de turnos:", value=20, min_value=1, max_value=100)
        permission_mode = st.selectbox("Modo de permissão:", ["acceptEdits", "requireApproval"])
        
        st.session_state.chat_max_turns = max_turns
        st.session_state.chat_permission_mode = permission_mode
    
    # Botões de criação de sessão
    st.markdown("#### 🆕 Criar Nova Sessão")
    
    col_create1, col_create2 = st.columns(2)
    
    with col_create1:
        if st.button("🚀 Sessão Simples", use_container_width=True):
            create_simple_session(main_api_url)
    
    with col_create2:
        if st.button("⚙️ Sessão Configurada", use_container_width=True):
            create_configured_session(main_api_url)
    
    # Status da sessão ativa
    if st.session_state.get('active_chat_session'):
        st.markdown(f"""
        <div style="background: #d1ecf1; border: 1px solid #bee5eb; 
                    padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h5 style="margin: 0 0 10px 0; color: #0c5460;">🔗 Sessão Ativa</h5>
            <div><strong>ID:</strong> <code>{st.session_state.active_chat_session[:8]}...</code></div>
            <div><strong>Mensagens:</strong> {len(st.session_state.get('chat_history', []))}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botões de controle da sessão
        col_ctrl1, col_ctrl2 = st.columns(2)
        
        with col_ctrl1:
            if st.button("🧹 Limpar Contexto", use_container_width=True):
                clear_chat_context(main_api_url)
        
        with col_ctrl2:
            if st.button("🗑️ Encerrar Sessão", use_container_width=True):
                st.session_state.active_chat_session = None
                st.session_state.chat_history = []
                st.success("✅ Sessão encerrada!")
                st.rerun()

def test_connection_status(main_api_url: str):
    """Testa e exibe status da conexão"""
    
    st.markdown("#### 🌐 Status da Conexão")
    
    try:
        response = requests.get(f"{main_api_url}/health", timeout=5)
        if response.status_code == 200:
            st.success("🟢 API Principal conectada")
            st.session_state.api_connected = True
        else:
            st.error(f"🔴 API Principal: HTTP {response.status_code}")
            st.session_state.api_connected = False
    except Exception as e:
        st.error(f"🔴 API Principal offline: {str(e)}")
        st.session_state.api_connected = False
    
    # Botão de reconexão
    if not st.session_state.get('api_connected', False):
        if st.button("🔄 Tentar Reconectar", use_container_width=True):
            st.rerun()

def create_simple_session(main_api_url: str):
    """Cria sessão simples"""
    
    if not st.session_state.get('api_connected', False):
        st.warning("⚠️ API Principal não está conectada")
        return
    
    try:
        response = requests.post(f"{main_api_url}/api/new-session", timeout=10)
        if response.status_code == 200:
            result = response.json()
            st.session_state.active_chat_session = result['session_id']
            st.session_state.chat_history = []
            
            st.success(f"✅ Sessão simples criada: {result['session_id'][:8]}...")
            
            # Log da criação
            add_chat_log("info", f"Sessão simples criada: {result['session_id']}")
            st.rerun()
        else:
            st.error("❌ Erro ao criar sessão")
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")

def create_configured_session(main_api_url: str):
    """Cria sessão com configurações personalizadas"""
    
    if not st.session_state.get('api_connected', False):
        st.warning("⚠️ API Principal não está conectada")
        return
    
    try:
        config_data = {
            "system_prompt": st.session_state.get('chat_system_prompt', ''),
            "allowed_tools": st.session_state.get('chat_tools', ["Read", "Write"]),
            "max_turns": st.session_state.get('chat_max_turns', 20),
            "permission_mode": st.session_state.get('chat_permission_mode', "acceptEdits")
        }
        
        response = requests.post(f"{main_api_url}/api/session-with-config", json=config_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            st.session_state.active_chat_session = result['session_id']
            st.session_state.chat_history = []
            
            st.success(f"✅ Sessão configurada criada: {result['session_id'][:8]}...")
            
            # Log detalhado
            add_chat_log("info", f"Sessão configurada criada: {result['session_id']}", {
                "config": config_data
            })
            st.rerun()
        else:
            st.error("❌ Erro ao criar sessão configurada")
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")

def render_chat_conversation():
    """Renderiza área de conversação"""
    
    st.subheader("💭 Área de Conversa")
    
    # Container do histórico
    chat_container = st.container()
    
    # Exibir histórico
    with chat_container:
        if st.session_state.get('chat_history'):
            for i, msg in enumerate(st.session_state.chat_history):
                if msg['role'] == 'user':
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                                padding: 15px; border-radius: 12px; margin: 15px 0; text-align: right;
                                border-left: 4px solid #2196f3; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <div style="display: flex; align-items: center; justify-content: flex-end; margin-bottom: 8px;">
                            <strong style="margin-right: 8px;">👤 Você</strong>
                            <span style="font-size: 12px; color: #666;">{msg.get('timestamp', datetime.now().strftime('%H:%M'))}</span>
                        </div>
                        <div style="color: #1976d2; font-weight: 500;">
                            {msg['content']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #f1f8e9 0%, #dcedc8 100%); 
                                padding: 15px; border-radius: 12px; margin: 15px 0;
                                border-left: 4px solid #4caf50; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <strong style="margin-right: 8px;">🤖 Claude</strong>
                            <span style="font-size: 12px; color: #666;">{msg.get('timestamp', datetime.now().strftime('%H:%M'))}</span>
                        </div>
                        <div style="color: #2e7d2e; line-height: 1.6;">
                            {msg['content']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("💬 Histórico de conversa aparecerá aqui")
    
    # Interface de envio
    st.markdown("#### ✍️ Nova Mensagem")
    
    if st.session_state.get('active_chat_session'):
        # Input de mensagem
        user_input = st.text_area(
            "Sua mensagem:",
            height=100,
            placeholder="Digite sua mensagem para o Claude...",
            key="chat_input"
        )
        
        # Botões de ação
        col_send1, col_send2, col_send3 = st.columns(3)
        
        with col_send1:
            if st.button("📤 Enviar", use_container_width=True):
                if user_input.strip():
                    send_chat_message(user_input.strip(), main_api_url)
                else:
                    st.warning("⚠️ Digite uma mensagem primeiro")
        
        with col_send2:
            if st.button("💡 Exemplo", use_container_width=True):
                example_message = "Olá Claude! Você pode me explicar como funciona o sistema de resumos?"
                send_chat_message(example_message, main_api_url)
        
        with col_send3:
            if st.button("🗑️ Limpar Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.success("✅ Histórico limpo!")
                st.rerun()
    
    else:
        st.info("🔗 Crie uma sessão para começar a conversar")
        
        if st.button("🆕 Criar Sessão Rápida", use_container_width=True):
            create_simple_session(main_api_url)

def send_chat_message(message: str, main_api_url: str):
    """Envia mensagem para o chat ativo"""
    
    try:
        # Adicionar mensagem do usuário ao histórico
        st.session_state.chat_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().strftime("%H:%M")
        })
        
        # Preparar dados da requisição
        chat_data = {
            "message": message,
            "session_id": st.session_state.active_chat_session
        }
        
        # Log do envio
        add_chat_log("info", f"Enviando mensagem para sessão {st.session_state.active_chat_session[:8]}...", {
            "message_length": len(message)
        })
        
        # Fazer requisição streaming
        with st.spinner("🤖 Claude está processando..."):
            response = requests.post(
                f"{main_api_url}/api/chat", 
                json=chat_data,
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                claude_response = ""
                
                # Processar stream SSE
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                if data['type'] == 'content':
                                    claude_response += data.get('content', '')
                                elif data['type'] == 'done':
                                    break
                                elif data['type'] == 'error':
                                    st.error(f"❌ Erro do Claude: {data.get('error')}")
                                    return
                            except json.JSONDecodeError:
                                continue
                
                # Adicionar resposta do Claude ao histórico
                if claude_response.strip():
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": claude_response.strip(),
                        "timestamp": datetime.now().strftime("%H:%M")
                    })
                    
                    add_chat_log("info", "Resposta de chat processada", {
                        "session_id": st.session_state.active_chat_session,
                        "response_length": len(claude_response)
                    })
                    
                    st.rerun()
                else:
                    st.warning("⚠️ Claude retornou resposta vazia")
            else:
                st.error(f"❌ Erro HTTP {response.status_code}")
                add_chat_log("error", f"Erro HTTP {response.status_code} no chat")
    
    except Exception as e:
        st.error(f"❌ Erro no chat: {str(e)}")
        add_chat_log("error", f"Erro no chat: {str(e)}")

def clear_chat_context(main_api_url: str):
    """Limpa contexto da sessão ativa"""
    
    try:
        clear_data = {"session_id": st.session_state.active_chat_session}
        response = requests.post(f"{main_api_url}/api/clear", json=clear_data, timeout=10)
        
        if response.status_code == 200:
            st.success("✅ Contexto da sessão limpo!")
            add_chat_log("info", f"Contexto limpo para sessão {st.session_state.active_chat_session[:8]}...")
        else:
            st.error(f"❌ Erro ao limpar contexto: HTTP {response.status_code}")
    
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")
        add_chat_log("error", f"Erro ao limpar contexto: {str(e)}")

def render_chat_statistics():
    """Renderiza estatísticas do chat atual"""
    
    if not st.session_state.get('chat_history'):
        return
    
    st.markdown("#### 📊 Estatísticas da Conversa")
    
    # Contar mensagens
    user_messages = sum(1 for msg in st.session_state.chat_history if msg['role'] == 'user')
    claude_messages = sum(1 for msg in st.session_state.chat_history if msg['role'] == 'assistant')
    
    # Calcular estatísticas
    total_chars = sum(len(msg['content']) for msg in st.session_state.chat_history)
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        st.metric("Mensagens Usuário", user_messages)
    
    with col_stat2:
        st.metric("Respostas Claude", claude_messages)
    
    with col_stat3:
        st.metric("Total de Caracteres", f"{total_chars:,}")

def export_chat_history() -> str:
    """Exporta histórico de chat"""
    
    if not st.session_state.get('chat_history'):
        return ""
    
    export_data = {
        "export_timestamp": datetime.now().isoformat(),
        "session_id": st.session_state.get('active_chat_session'),
        "chat_history": st.session_state.chat_history,
        "session_config": {
            "system_prompt": st.session_state.get('chat_system_prompt'),
            "tools": st.session_state.get('chat_tools'),
            "max_turns": st.session_state.get('chat_max_turns'),
            "permission_mode": st.session_state.get('chat_permission_mode')
        }
    }
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)

def add_chat_log(level: str, message: str, details: Dict = None):
    """Adiciona log específico do chat"""
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": f"[CHAT] {message}",
        "details": details or {},
        "category": "chat"
    }
    
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    
    st.session_state.debug_logs.append(log_entry)

# Funções auxiliares para compatibilidade
def create_simple_session(main_api_url: str):
    """Wrapper para criação de sessão simples"""
    
    if not st.session_state.get('api_connected', False):
        st.warning("⚠️ Conecte-se à API principal primeiro")
        return
    
    try:
        response = requests.post(f"{main_api_url}/api/new-session", timeout=10)
        if response.status_code == 200:
            result = response.json()
            st.session_state.active_chat_session = result['session_id']
            st.session_state.chat_history = []
            st.success(f"✅ Sessão criada: {result['session_id'][:8]}...")
            add_chat_log("info", f"Nova sessão simples: {result['session_id']}")
            st.rerun()
        else:
            st.error("❌ Erro ao criar sessão")
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")

def create_configured_session(main_api_url: str):
    """Wrapper para criação de sessão configurada"""
    
    if not st.session_state.get('api_connected', False):
        st.warning("⚠️ Conecte-se à API principal primeiro")
        return
    
    try:
        config_data = {
            "system_prompt": st.session_state.get('chat_system_prompt', ''),
            "allowed_tools": st.session_state.get('chat_tools', ["Read", "Write"]),
            "max_turns": st.session_state.get('chat_max_turns', 20),
            "permission_mode": st.session_state.get('chat_permission_mode', "acceptEdits")
        }
        
        response = requests.post(f"{main_api_url}/api/session-with-config", json=config_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            st.session_state.active_chat_session = result['session_id']
            st.session_state.chat_history = []
            st.success(f"✅ Sessão configurada: {result['session_id'][:8]}...")
            add_chat_log("info", f"Nova sessão configurada: {result['session_id']}", {"config": config_data})
            st.rerun()
        else:
            st.error("❌ Erro ao criar sessão configurada")
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")