#!/usr/bin/env python3
"""
Navegador de Sessões Avançado
Interface rica para visualização e gerenciamento de sessões
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

def render_advanced_session_browser(viewer_api_url: str = "http://localhost:3041"):
    """
    Renderiza navegador de sessões com interface avançada
    
    Args:
        viewer_api_url: URL da API do viewer HTTP
    """
    
    st.header("📋 Navegador de Sessões Avançado")
    
    # Carregar sessões
    sessions = get_sessions_from_api(viewer_api_url)
    
    if not sessions:
        st.error("❌ Não foi possível carregar sessões do viewer")
        return
    
    # Layout principal
    col1, col2 = st.columns([1, 2])
    
    with col1:
        render_session_list(sessions, viewer_api_url)
    
    with col2:
        render_session_details(viewer_api_url)

def render_session_list(sessions: List[Dict], viewer_api_url: str):
    """Renderiza lista de sessões com filtros e busca"""
    
    st.subheader("🔍 Lista de Sessões")
    
    # Estatísticas rápidas
    st.info(f"📊 **{len(sessions)} sessões** encontradas no sistema")
    
    # Filtros avançados
    with st.expander("🔽 Filtros Avançados", expanded=True):
        
        # Filtro por projeto/diretório
        directories = sorted(list(set(s['directory'] for s in sessions)))
        directory_options = ["🗂️ Todos os Projetos"] + [f"📁 {d}" for d in directories]
        
        selected_dir = st.selectbox("Filtrar por projeto:", directory_options)
        actual_dir = selected_dir.replace("📁 ", "") if selected_dir != "🗂️ Todos os Projetos" else None
        
        # Filtro por horário
        col_time1, col_time2 = st.columns(2)
        
        with col_time1:
            min_time = st.time_input("⏰ Após horário:", value=None, help="Mostrar apenas sessões após este horário")
        
        with col_time2:
            max_time = st.time_input("⏰ Antes horário:", value=None, help="Mostrar apenas sessões antes deste horário")
        
        # Busca por texto
        search_term = st.text_input("🔍 Buscar:", placeholder="Digite ID da sessão ou parte do nome...")
    
    # Aplicar filtros
    filtered_sessions = sessions
    
    if actual_dir:
        filtered_sessions = [s for s in filtered_sessions if s['directory'] == actual_dir]
    
    if search_term:
        search_lower = search_term.lower()
        filtered_sessions = [s for s in filtered_sessions 
                           if search_lower in s['session_id'].lower() or 
                              search_lower in s['directory'].lower()]
    
    # TODO: Implementar filtros de horário se necessário
    
    st.info(f"📋 **{len(filtered_sessions)}** sessões após filtros")
    
    # Lista de sessões
    if filtered_sessions:
        # Limitar para performance
        display_sessions = filtered_sessions[:50]  # Máximo 50 por vez
        
        session_options = []
        for session in display_sessions:
            last_time = session.get('last_interaction', 'N/A')
            directory_short = session['directory'].replace('-home-suthub--claude-', '')
            display_name = f"⏰ {last_time} | 📁 {directory_short} | 🆔 {session['session_id'][:8]}..."
            session_options.append((display_name, session))
        
        # Seletor principal
        selected_idx = st.selectbox(
            "Selecionar Sessão:",
            range(len(session_options)),
            format_func=lambda i: session_options[i][0] if session_options else "Nenhuma sessão"
        )
        
        if session_options:
            selected_session = session_options[selected_idx][1]
            st.session_state.selected_session = selected_session
            
            # Preview da sessão selecionada
            render_session_preview(selected_session)
    
    else:
        st.warning("⚠️ Nenhuma sessão corresponde aos filtros aplicados")

def render_session_preview(session: Dict):
    """Renderiza preview da sessão selecionada"""
    
    st.markdown("#### 👁️ Preview da Sessão")
    
    # Card da sessão
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                border-radius: 12px; padding: 20px; margin: 15px 0;
                border-left: 5px solid #2196f3;">
        <h5 style="margin: 0 0 15px 0; color: #1976d2;">📄 {session['session_id']}</h5>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
            <div><strong>📁 Projeto:</strong><br><code>{session['directory']}</code></div>
            <div><strong>⏰ Última Atividade:</strong><br>{session.get('last_interaction', 'N/A')}</div>
        </div>
        
        <div style="font-size: 12px; color: #666;">
            <strong>📂 Arquivo:</strong> <code>{session.get('file_path', 'N/A')}</code>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_session_details(viewer_api_url: str):
    """Renderiza detalhes e ações da sessão selecionada"""
    
    st.subheader("🎯 Detalhes & Ações")
    
    if not st.session_state.get('selected_session'):
        st.info("👈 Selecione uma sessão na lista ao lado para ver detalhes")
        return
    
    session = st.session_state.selected_session
    
    # Informações detalhadas
    st.markdown("#### 📊 Informações Completas")
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown(f"""
        **🆔 ID da Sessão:**
        ```
        {session['session_id']}
        ```
        
        **📁 Diretório:**
        ```
        {session['directory']}
        ```
        """)
    
    with col_info2:
        # Carregar estatísticas do arquivo .jsonl
        file_path = Path(session.get('file_path', ''))
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                # Contar tipos de mensagem
                user_msgs = sum(1 for line in lines if '"type":"user"' in line)
                assistant_msgs = sum(1 for line in lines if '"type":"assistant"' in line)
                
                st.markdown(f"""
                **📊 Estatísticas:**
                - 📄 Linhas no arquivo: {len(lines)}
                - 👤 Mensagens usuário: {user_msgs}  
                - 🤖 Respostas Claude: {assistant_msgs}
                - 💬 Total mensagens: {user_msgs + assistant_msgs}
                """)
                
            except Exception as e:
                st.error(f"❌ Erro ao ler arquivo: {str(e)}")
        else:
            st.warning("⚠️ Arquivo da sessão não encontrado")
    
    # Ações principais
    st.markdown("#### ⚡ Ações Disponíveis")
    
    # Grid de ações
    col_action1, col_action2, col_action3 = st.columns(3)
    
    with col_action1:
        # Link para viewer HTTP
        viewer_url = f"{viewer_api_url}/{session['directory']}/{session['session_id']}"
        st.markdown(f"""
        <a href="{viewer_url}" target="_blank" style="text-decoration: none;">
            <div style="background: linear-gradient(45deg, #28a745, #20c997); color: white; 
                        padding: 15px; border-radius: 10px; text-align: center; margin: 10px 0;
                        transition: transform 0.2s; cursor: pointer;" 
                 onmouseover="this.style.transform='scale(1.05)'" 
                 onmouseout="this.style.transform='scale(1)'">
                🌐 Abrir no Viewer
            </div>
        </a>
        """, unsafe_allow_html=True)
    
    with col_action2:
        # Central de resumos
        resumo_url = f"{viewer_url}/resumo"
        st.markdown(f"""
        <a href="{resumo_url}" target="_blank" style="text-decoration: none;">
            <div style="background: linear-gradient(45deg, #667eea, #764ba2); color: white; 
                        padding: 15px; border-radius: 10px; text-align: center; margin: 10px 0;
                        transition: transform 0.2s; cursor: pointer;" 
                 onmouseover="this.style.transform='scale(1.05)'" 
                 onmouseout="this.style.transform='scale(1)'">
                📝 Central de Resumos
            </div>
        </a>
        """, unsafe_allow_html=True)
    
    with col_action3:
        # Excluir sessão
        if st.button("🗑️ Excluir Sessão", use_container_width=True, type="secondary"):
            delete_session_with_confirmation(session, viewer_api_url)
    
    # Seção de resumos rápidos
    st.markdown("#### 🚀 Geração de Resumos")
    
    col_resume1, col_resume2, col_resume3 = st.columns(3)
    
    with col_resume1:
        if st.button("📝 Conciso (20 palavras)", use_container_width=True):
            generate_summary_for_session(session, "conciso", viewer_api_url)
    
    with col_resume2:
        if st.button("📋 Detalhado (400 palavras)", use_container_width=True):
            generate_summary_for_session(session, "detalhado", viewer_api_url)
    
    with col_resume3:
        if st.button("• Bullet Points", use_container_width=True):
            generate_summary_for_session(session, "bullet_points", viewer_api_url)

def get_sessions_from_api(viewer_api_url: str) -> List[Dict]:
    """Carrega sessões da API do viewer"""
    try:
        response = requests.get(f"{viewer_api_url}/api/sessions", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"❌ Erro ao carregar sessões: {str(e)}")
    return []

def delete_session_with_confirmation(session: Dict, viewer_api_url: str):
    """Exclui sessão com confirmação"""
    
    # Confirmação via checkbox
    confirm = st.checkbox(f"⚠️ Confirmar exclusão da sessão {session['session_id'][:8]}...")
    
    if confirm:
        try:
            delete_url = f"{viewer_api_url}/api/session/{session['directory']}/{session['session_id']}"
            response = requests.delete(delete_url, timeout=10)
            
            if response.status_code == 200:
                st.success("✅ Sessão excluída com sucesso!")
                
                # Limpar seleção
                if 'selected_session' in st.session_state:
                    del st.session_state.selected_session
                if 'last_generated_summary' in st.session_state:
                    del st.session_state.last_generated_summary
                
                # Log da exclusão
                if hasattr(st.session_state, 'debug_logs'):
                    from utils.metrics_collector import get_metrics_collector
                    collector = get_metrics_collector()
                    collector.record_session_activity(
                        session['session_id'], 
                        "session_deleted",
                        {"directory": session['directory']}
                    )
                
                st.rerun()
            else:
                st.error(f"❌ Erro ao excluir: HTTP {response.status_code}")
                
        except Exception as e:
            st.error(f"❌ Erro na exclusão: {str(e)}")

def generate_summary_for_session(session: Dict, summary_type: str, viewer_api_url: str):
    """Gera resumo para a sessão via API"""
    
    try:
        payload = {
            "directory": session['directory'],
            "session_id": session['session_id'],
            "summary_type": summary_type
        }
        
        with st.spinner(f"🤖 Gerando resumo {summary_type}..."):
            start_time = time.time()
            response = requests.post(
                f"{viewer_api_url}/api/summarize", 
                json=payload,
                timeout=60
            )
            execution_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                st.success(f"✅ Resumo {summary_type} gerado em {execution_time:.2f}s")
                
                # Salvar resultado no estado
                st.session_state.last_generated_summary = {
                    "session": session,
                    "result": result,
                    "summary_type": summary_type,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }
                
                # Registrar métricas
                from utils.metrics_collector import get_metrics_collector
                collector = get_metrics_collector()
                collector.record_summary_generation(
                    session['session_id'],
                    summary_type,
                    execution_time,
                    result.get('metrics', {}),
                    True
                )
                
                # Log de sucesso
                if hasattr(st.session_state, 'debug_logs'):
                    st.session_state.debug_logs.append({
                        "timestamp": datetime.now().isoformat(),
                        "level": "info",
                        "message": f"Resumo {summary_type} gerado para {session['session_id'][:8]}...",
                        "details": {
                            "execution_time": execution_time,
                            "summary_length": len(result.get('summary', ''))
                        }
                    })
                
                st.rerun()
            else:
                st.error(f"❌ Erro na API: {result.get('error')}")
        else:
            st.error(f"❌ HTTP {response.status_code}")
            
    except Exception as e:
        st.error(f"❌ Erro na geração: {str(e)}")

def render_session_details(viewer_api_url: str):
    """Renderiza detalhes completos da sessão selecionada"""
    
    if not st.session_state.get('selected_session'):
        st.info("👈 Selecione uma sessão para ver detalhes completos")
        return
    
    session = st.session_state.selected_session
    
    # Card principal da sessão
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 25px; border-radius: 15px; margin: 20px 0;">
        <h3 style="margin: 0 0 15px 0;">📄 {session['session_id']}</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <div><strong>📁 Projeto:</strong><br>{session['directory']}</div>
            <div><strong>⏰ Última Atividade:</strong><br>{session.get('last_interaction', 'N/A')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Abas de detalhes
    detail_tab1, detail_tab2, detail_tab3 = st.tabs([
        "📝 Resumos", 
        "📊 Estatísticas", 
        "🔗 Links & Export"
    ])
    
    with detail_tab1:
        render_summary_section(session, viewer_api_url)
    
    with detail_tab2:
        render_session_statistics(session)
    
    with detail_tab3:
        render_links_and_export(session, viewer_api_url)

def render_summary_section(session: Dict, viewer_api_url: str):
    """Seção dedicada aos resumos"""
    
    st.markdown("### 📝 Geração de Resumos")
    
    # Botões de geração em cards
    summary_types = [
        {
            "type": "conciso",
            "title": "📝 Resumo Conciso", 
            "description": "Ultra-condensado em 20 palavras",
            "color": "#28a745"
        },
        {
            "type": "detalhado", 
            "title": "📋 Resumo Detalhado",
            "description": "Análise completa até 400 palavras", 
            "color": "#2196f3"
        },
        {
            "type": "bullet_points",
            "title": "• Bullet Points",
            "description": "Lista organizada por tópicos",
            "color": "#ff9800"
        }
    ]
    
    for summary_config in summary_types:
        st.markdown(f"""
        <div style="border: 2px solid {summary_config['color']}; border-radius: 10px; 
                    padding: 15px; margin: 10px 0; cursor: pointer;
                    transition: transform 0.2s ease;">
            <h5 style="color: {summary_config['color']}; margin: 0 0 8px 0;">
                {summary_config['title']}
            </h5>
            <p style="color: #666; margin: 0; font-size: 14px;">
                {summary_config['description']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão de geração
        if st.button(f"Gerar {summary_config['title']}", 
                    key=f"gen_{summary_config['type']}", 
                    use_container_width=True):
            generate_summary_for_session(session, summary_config['type'], viewer_api_url)
    
    # Exibir último resumo gerado
    if 'last_generated_summary' in st.session_state:
        render_last_summary_result()

def render_last_summary_result():
    """Renderiza resultado do último resumo gerado"""
    
    summary_data = st.session_state.last_generated_summary
    
    if not summary_data.get('success'):
        st.error("❌ Último resumo falhou")
        return
    
    st.markdown("### ✅ Último Resumo Gerado")
    
    # Usar parser markdown avançado
    from utils.markdown_parser import get_markdown_parser
    parser = get_markdown_parser()
    
    result = summary_data['result']
    summary_html = parser.create_summary_card(result, summary_data['summary_type'])
    
    st.markdown(summary_html, unsafe_allow_html=True)
    
    # Ações no resumo
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Copiar Conteúdo"):
            st.success("✅ Use Ctrl+A e Ctrl+C na área do resumo acima")
    
    with col2:
        session = summary_data['session']
        viewer_url = f"http://localhost:3041/{session['directory']}/{session['session_id']}/resumo?tipo={summary_data['summary_type']}"
        st.markdown(f"[🌐 Ver no Viewer]({viewer_url})")
    
    with col3:
        if st.button("🗑️ Limpar Resultado"):
            del st.session_state.last_generated_summary
            st.rerun()

def render_session_statistics(session: Dict):
    """Renderiza estatísticas detalhadas da sessão"""
    
    st.markdown("### 📊 Estatísticas Detalhadas")
    
    # Placeholder para estatísticas avançadas
    st.info("📊 Estatísticas detalhadas da sessão aparecerão aqui")
    
    # Implementar análise do conteúdo do arquivo .jsonl
    # TODO: Adicionar análise de tokens, custos históricos, etc.

def render_links_and_export(session: Dict, viewer_api_url: str):
    """Seção de links úteis e exportação"""
    
    st.markdown("### 🔗 Links & Exportação")
    
    # Links úteis
    st.markdown("#### 🌐 Links Diretos")
    
    base_url = f"{viewer_api_url}/{session['directory']}/{session['session_id']}"
    
    links = [
        ("📄 Ver Sessão", base_url),
        ("📝 Resumo Conciso", f"{base_url}/resumo?tipo=conciso"),
        ("📋 Resumo Detalhado", f"{base_url}/resumo?tipo=detalhado"),
        ("• Bullet Points", f"{base_url}/resumo?tipo=bullet_points")
    ]
    
    for title, url in links:
        st.markdown(f"- [{title}]({url})")
    
    # Exportação
    st.markdown("#### 💾 Exportação")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if st.button("📄 Exportar Sessão (JSON)", use_container_width=True):
            # Implementar exportação
            st.info("💡 Funcionalidade de exportação será implementada")
    
    with col_exp2:
        if st.button("📊 Exportar Métricas", use_container_width=True):
            # Exportar métricas da sessão
            from utils.metrics_collector import get_metrics_collector
            collector = get_metrics_collector()
            export_data = collector.export_metrics("json")
            
            st.download_button(
                label="💾 Download Métricas JSON",
                data=export_data,
                file_name=f"metricas_sessao_{session['session_id'][:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )