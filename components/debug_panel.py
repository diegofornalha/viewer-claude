#!/usr/bin/env python3
"""
Painel de Debug Avançado
Sistema completo de debugging baseado no 8505-viewer
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Optional
import traceback

def render_advanced_debug_panel(debug_logs: List[Dict], test_results: Dict):
    """
    Renderiza painel de debug avançado
    
    Args:
        debug_logs: Lista de logs do sistema
        test_results: Resultados de testes executados
    """
    
    st.header("🔧 Debug & Monitoramento Avançado")
    
    # Estatísticas gerais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_logs = len(debug_logs)
        st.metric("Total de Logs", total_logs)
    
    with col2:
        error_count = sum(1 for log in debug_logs[-100:] if log["level"].upper() == "ERROR")
        st.metric("Erros Recentes", error_count, delta="últimas 100 operações")
    
    with col3:
        warning_count = sum(1 for log in debug_logs[-100:] if log["level"].upper() == "WARNING")
        st.metric("Avisos Recentes", warning_count)
    
    with col4:
        success_rate = 0
        if test_results:
            successful = sum(1 for r in test_results.values() if r.get('success', False))
            success_rate = successful / len(test_results) * 100
        st.metric("Taxa de Sucesso", f"{success_rate:.1f}%")
    
    # Tabs do debug
    debug_tab1, debug_tab2, debug_tab3 = st.tabs([
        "📝 Logs Estruturados", 
        "⚠️ Análise de Erros", 
        "📊 Performance"
    ])
    
    # Tab 1: Logs estruturados
    with debug_tab1:
        render_structured_logs(debug_logs)
    
    # Tab 2: Análise de erros
    with debug_tab2:
        render_error_analysis(debug_logs)
    
    # Tab 3: Performance
    with debug_tab3:
        render_performance_analysis(test_results)

def render_structured_logs(debug_logs: List[Dict]):
    """Renderiza logs de forma estruturada"""
    
    st.subheader("📝 Logs Estruturados")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_logs = st.number_input("Máximo de logs:", value=50, min_value=10, max_value=200)
    
    with col2:
        level_filter = st.selectbox("Filtrar por nível:", ["all", "error", "warning", "info"])
    
    with col3:
        search_term = st.text_input("Buscar nos logs:", placeholder="Digite termo...")
    
    # Aplicar filtros
    filtered_logs = debug_logs[-max_logs:]
    
    if level_filter != "all":
        filtered_logs = [log for log in filtered_logs if log["level"].lower() == level_filter]
    
    if search_term:
        filtered_logs = [log for log in filtered_logs 
                        if search_term.lower() in log["message"].lower()]
    
    # Exibir logs em grid
    if filtered_logs:
        # Mostrar em grid de 2 colunas
        for i in range(0, len(filtered_logs), 2):
            cols = st.columns(2)
            
            for j, col in enumerate(cols):
                if i + j < len(filtered_logs):
                    log = filtered_logs[i + j]
                    render_log_card(log, col)
    else:
        st.info("📋 Nenhum log corresponde aos filtros aplicados")

def render_log_card(log: Dict, container):
    """Renderiza card individual de log"""
    
    timestamp = log["timestamp"].split("T")[1][:8]
    level = log["level"].upper()
    message = log["message"]
    
    # Estilo baseado no nível
    level_styles = {
        "ERROR": {"color": "#fee", "border": "#dc3545", "emoji": "🔴"},
        "WARNING": {"color": "#fff8e1", "border": "#ffc107", "emoji": "🟡"},
        "INFO": {"color": "#e8f5e8", "border": "#28a745", "emoji": "🔵"}
    }
    
    style = level_styles.get(level, level_styles["INFO"])
    
    with container:
        st.markdown(f"""
        <div style="border: 2px solid {style['border']}; border-radius: 10px; 
                    padding: 15px; margin: 10px 0; background: {style['color']};
                    transition: transform 0.2s ease;">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 18px; margin-right: 10px;">{style['emoji']}</span>
                <strong style="color: #333;">[{timestamp}] {level}</strong>
            </div>
            <div style="color: #555; font-size: 14px; margin-bottom: 10px; line-height: 1.4;">
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Detalhes expandidos
        if log.get("details"):
            with st.expander(f"🔍 Detalhes ({timestamp})"):
                st.json(log["details"])
        
        # Stack trace para erros
        if level == "ERROR" and log.get("stack_trace"):
            with st.expander(f"📚 Stack Trace ({timestamp})"):
                for line in log["stack_trace"]:
                    st.code(line.strip(), language="python")

def render_error_analysis(debug_logs: List[Dict]):
    """Análise específica de erros"""
    
    st.subheader("⚠️ Análise de Erros")
    
    # Filtrar apenas erros
    error_logs = [log for log in debug_logs if log["level"].upper() == "ERROR"]
    
    if not error_logs:
        st.success("🎉 Nenhum erro registrado!")
        return
    
    # Estatísticas de erros
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total de Erros", len(error_logs))
        
        # Erros por categoria
        error_types = {}
        for log in error_logs:
            error_msg = log["message"]
            # Categorizar erros básicos
            if "connection" in error_msg.lower():
                category = "Conexão"
            elif "timeout" in error_msg.lower():
                category = "Timeout"
            elif "json" in error_msg.lower():
                category = "Parsing"
            elif "permission" in error_msg.lower():
                category = "Permissões"
            else:
                category = "Outros"
            
            error_types[category] = error_types.get(category, 0) + 1
        
        if error_types:
            st.bar_chart(error_types)
    
    with col2:
        # Erros mais recentes
        st.markdown("#### 🔴 Erros Mais Recentes")
        
        for log in error_logs[-5:]:  # Últimos 5 erros
            timestamp = log["timestamp"].split("T")[1][:8]
            st.markdown(f"""
            <div style="background: #f8d7da; border-left: 4px solid #dc3545; 
                        padding: 10px; margin: 5px 0; border-radius: 5px;">
                <strong>[{timestamp}]</strong> {log["message"][:80]}...
            </div>
            """, unsafe_allow_html=True)

def render_performance_analysis(test_results: Dict):
    """Análise de performance dos testes"""
    
    st.subheader("📊 Análise de Performance")
    
    if not test_results:
        st.info("📊 Execute alguns testes para ver análise de performance")
        return
    
    # Preparar dados
    successful_tests = [r for r in test_results.values() if r.get('success', False)]
    failed_tests = [r for r in test_results.values() if not r.get('success', False)]
    
    # Métricas gerais
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Testes Bem-sucedidos", len(successful_tests))
    
    with col2:
        st.metric("Testes Falhados", len(failed_tests))
    
    with col3:
        if test_results:
            avg_time = sum(r.get('execution_time', 0) for r in test_results.values()) / len(test_results)
            st.metric("Tempo Médio", f"{avg_time:.2f}s")
    
    # Análise por tipo de resumo
    if successful_tests:
        st.markdown("#### 📊 Performance por Tipo")
        
        type_performance = {}
        for test in successful_tests:
            summary_type = test.get('summary_type', 'unknown')
            exec_time = test.get('execution_time', 0)
            
            if summary_type not in type_performance:
                type_performance[summary_type] = {
                    "times": [],
                    "costs": [],
                    "tokens": []
                }
            
            type_performance[summary_type]["times"].append(exec_time)
            
            # Métricas se disponíveis
            metrics = test.get('result', {}).get('metrics', {})
            if metrics:
                type_performance[summary_type]["costs"].append(metrics.get('cost', 0))
                total_tokens = metrics.get('input_tokens', 0) + metrics.get('output_tokens', 0)
                type_performance[summary_type]["tokens"].append(total_tokens)
        
        # Exibir análise
        for summary_type, data in type_performance.items():
            avg_time = sum(data["times"]) / len(data["times"])
            avg_cost = sum(data["costs"]) / len(data["costs"]) if data["costs"] else 0
            avg_tokens = sum(data["tokens"]) / len(data["tokens"]) if data["tokens"] else 0
            
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; 
                        margin: 10px 0; border-left: 4px solid #667eea;">
                <h5 style="margin: 0 0 10px 0; color: #333;">📝 {summary_type.title()}</h5>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px;">
                    <div><strong>⏱️ Tempo:</strong> {avg_time:.2f}s</div>
                    <div><strong>💰 Custo:</strong> ${avg_cost:.6f}</div>
                    <div><strong>🔢 Tokens:</strong> {avg_tokens:.0f}</div>
                    <div><strong>📊 Testes:</strong> {len(data["times"])}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def create_diagnostic_report() -> str:
    """Cria relatório de diagnóstico do sistema"""
    
    report_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Verificações básicas do sistema
    checks = []
    
    # Verificar se viewer HTTP está rodando
    try:
        import requests
        response = requests.get("http://localhost:3041/api/sessions", timeout=3)
        if response.status_code == 200:
            sessions = response.json()
            checks.append(f"✅ Viewer HTTP: {len(sessions)} sessões ativas")
        else:
            checks.append(f"❌ Viewer HTTP: Status {response.status_code}")
    except:
        checks.append("❌ Viewer HTTP: Não responsivo")
    
    # Verificar API principal
    try:
        response = requests.get("http://localhost:8990/health", timeout=3)
        if response.status_code == 200:
            checks.append("✅ API Principal: Online")
        else:
            checks.append(f"❌ API Principal: Status {response.status_code}")
    except:
        checks.append("❌ API Principal: Não responsivo")
    
    # Verificar arquivos do sistema
    from pathlib import Path
    
    claude_projects = Path("/home/suthub/.claude/projects")
    if claude_projects.exists():
        session_files = sum(len(list(d.glob("*.jsonl"))) for d in claude_projects.iterdir() if d.is_dir())
        checks.append(f"✅ Sistema de arquivos: {session_files} sessões encontradas")
    else:
        checks.append("❌ Sistema de arquivos: Diretório não encontrado")
    
    # Verificar Claude SDK
    sdk_path = Path("/home/suthub/.claude/cc-sdk-chat/viewer-claude/backend/claude-sdk")
    if sdk_path.exists():
        checks.append("✅ Claude SDK: Linkado corretamente")
    else:
        checks.append("❌ Claude SDK: Link não encontrado")
    
    # Gerar relatório
    report = f"""
# 🔧 Relatório de Diagnóstico do Sistema

**Gerado em:** {report_time}

## 🌐 Status dos Serviços

{chr(10).join(checks)}

## 📊 URLs dos Serviços

- **Viewer HTTP (produção):** http://localhost:3041
- **Streamlit Modernizado:** http://localhost:3042 (nova interface)
- **API Principal:** http://localhost:8990
- **Debug Original:** http://localhost:8506

## 🎯 Funcionalidades Ativas

✅ Visualização de sessões .jsonl
✅ Sistema de resumo inteligente  
✅ Claude SDK integrado
✅ URLs diretas para sessões
✅ Interface de debug avançada
✅ Sistema de métricas

## 💡 Recomendações

- Monitorar logs de erro regularmente
- Verificar performance dos resumos
- Manter APIs principais online
- Backup das métricas coletadas

---
*Relatório gerado automaticamente pelo Claude Session Viewer*
"""
    
    return report

def export_debug_data() -> Dict:
    """Exporta dados de debug para análise"""
    
    return {
        "export_timestamp": datetime.now().isoformat(),
        "system_status": create_diagnostic_report(),
        "debug_logs": st.session_state.get("debug_logs", [])[-100:],  # Últimos 100
        "test_results": st.session_state.get("test_results", {}),
        "session_state_keys": list(st.session_state.keys()),
        "performance_summary": {
            "total_logs": len(st.session_state.get("debug_logs", [])),
            "total_tests": len(st.session_state.get("test_results", {})),
            "debug_mode_active": st.session_state.get("debug_mode", False)
        }
    }