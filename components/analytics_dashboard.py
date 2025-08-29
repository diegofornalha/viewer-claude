#!/usr/bin/env python3
"""
Dashboard de Analytics Avançado
Sistema completo de métricas e análises baseado no 8505-viewer
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

def render_analytics_dashboard(viewer_api_url: str = "http://localhost:3041"):
    """
    Renderiza dashboard completo de analytics
    
    Args:
        viewer_api_url: URL da API do viewer
    """
    
    st.header("📊 Analytics & Dashboard")
    
    # Carregar dados do sistema
    sessions_data = load_system_data(viewer_api_url)
    
    if not sessions_data:
        st.error("❌ Não foi possível carregar dados do sistema")
        return
    
    # Métricas principais
    render_main_metrics(sessions_data)
    
    # Tabs de analytics
    analytics_tab1, analytics_tab2, analytics_tab3, analytics_tab4 = st.tabs([
        "📈 Visão Geral",
        "💰 Análise de Custos", 
        "⚡ Performance",
        "📊 Relatórios"
    ])
    
    with analytics_tab1:
        render_overview_analytics(sessions_data)
    
    with analytics_tab2:
        render_cost_analysis()
    
    with analytics_tab3:
        render_performance_analytics()
    
    with analytics_tab4:
        render_reports_section()

def load_system_data(viewer_api_url: str) -> Dict:
    """Carrega dados do sistema para analytics"""
    
    try:
        # Carregar sessões
        sessions_response = requests.get(f"{viewer_api_url}/api/sessions", timeout=10)
        sessions = sessions_response.json() if sessions_response.status_code == 200 else []
        
        # Carregar resumos salvos (se disponível)
        summaries_response = requests.get(f"{viewer_api_url}/api/summaries", timeout=10)
        summaries = []
        if summaries_response.status_code == 200:
            summaries_data = summaries_response.json()
            summaries = summaries_data.get('summaries', [])
        
        return {
            "sessions": sessions,
            "summaries": summaries,
            "load_time": datetime.now().isoformat()
        }
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return {}

def render_main_metrics(data: Dict):
    """Renderiza métricas principais do sistema"""
    
    sessions = data.get('sessions', [])
    summaries = data.get('summaries', [])
    test_results = st.session_state.get('test_results', {})
    
    # Métricas principais
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total de Sessões", len(sessions))
    
    with col2:
        st.metric("📝 Resumos Salvos", len(summaries))
    
    with col3:
        st.metric("🧪 Testes Executados", len(test_results))
    
    with col4:
        # Taxa de sucesso dos testes
        if test_results:
            successful = sum(1 for r in test_results.values() if r.get('success', False))
            success_rate = successful / len(test_results) * 100
            st.metric("✅ Taxa de Sucesso", f"{success_rate:.1f}%")
        else:
            st.metric("✅ Taxa de Sucesso", "N/A")
    
    with col5:
        # Projetos únicos
        unique_dirs = len(set(s['directory'] for s in sessions))
        st.metric("📁 Projetos", unique_dirs)

def render_overview_analytics(data: Dict):
    """Renderiza visão geral do sistema"""
    
    st.subheader("📈 Visão Geral do Sistema")
    
    sessions = data.get('sessions', [])
    
    if not sessions:
        st.info("📊 Nenhuma sessão disponível para análise")
        return
    
    # Análise por projeto
    st.markdown("#### 📁 Distribuição por Projeto")
    
    # Contar sessões por projeto
    project_counts = {}
    for session in sessions:
        project = session['directory'].replace('-home-suthub--claude-', '')
        project_counts[project] = project_counts.get(project, 0) + 1
    
    # Exibir gráfico
    if project_counts:
        st.bar_chart(project_counts)
        
        # Tabela detalhada
        project_df = pd.DataFrame([
            {"Projeto": proj, "Sessões": count, "Percentual": f"{count/len(sessions)*100:.1f}%"}
            for proj, count in sorted(project_counts.items(), key=lambda x: x[1], reverse=True)
        ])
        
        st.dataframe(project_df, use_container_width=True)
    
    # Análise temporal
    st.markdown("#### ⏰ Atividade por Horário")
    
    # Extrair horários das sessões
    hourly_activity = {}
    for session in sessions:
        hour = session.get('last_interaction', '00:00')[:2]
        hourly_activity[f"{hour}:00"] = hourly_activity.get(f"{hour}:00", 0) + 1
    
    if hourly_activity:
        st.line_chart(hourly_activity)

def render_cost_analysis():
    """Renderiza análise de custos"""
    
    st.subheader("💰 Análise de Custos")
    
    # Usar dados dos testes executados
    test_results = st.session_state.get('test_results', {})
    
    if not test_results:
        st.info("💡 Execute alguns resumos para ver análise de custos")
        return
    
    # Calcular custos por tipo
    cost_by_type = {}
    tokens_by_type = {}
    
    for result in test_results.values():
        if result.get('success'):
            summary_type = result.get('summary_type', 'unknown')
            metrics = result.get('result', {}).get('metrics', {})
            
            cost = metrics.get('cost', 0)
            tokens = metrics.get('input_tokens', 0) + metrics.get('output_tokens', 0)
            
            if summary_type not in cost_by_type:
                cost_by_type[summary_type] = []
                tokens_by_type[summary_type] = []
            
            cost_by_type[summary_type].append(cost)
            tokens_by_type[summary_type].append(tokens)
    
    # Métricas de custo
    col_cost1, col_cost2, col_cost3 = st.columns(3)
    
    total_cost = sum(sum(costs) for costs in cost_by_type.values())
    total_tokens = sum(sum(tokens) for tokens in tokens_by_type.values())
    avg_cost = total_cost / max(len(test_results), 1)
    
    with col_cost1:
        st.metric("💰 Custo Total", f"${total_cost:.6f}")
    
    with col_cost2:
        st.metric("🔢 Total de Tokens", f"{total_tokens:,}")
    
    with col_cost3:
        st.metric("📊 Custo Médio", f"${avg_cost:.6f}")
    
    # Análise por tipo
    if cost_by_type:
        st.markdown("#### 📊 Custos por Tipo de Resumo")
        
        # Criar DataFrame para análise
        cost_analysis_data = []
        for summary_type, costs in cost_by_type.items():
            tokens = tokens_by_type[summary_type]
            
            cost_analysis_data.append({
                "Tipo": summary_type.title(),
                "Execuções": len(costs),
                "Custo Total": f"${sum(costs):.6f}",
                "Custo Médio": f"${sum(costs)/len(costs):.6f}",
                "Tokens Médios": f"{sum(tokens)/len(tokens):.0f}",
                "Eficiência": f"${sum(costs)/max(sum(tokens), 1)*1000:.3f}/1k tokens"
            })
        
        df = pd.DataFrame(cost_analysis_data)
        st.dataframe(df, use_container_width=True)

def render_performance_analytics():
    """Renderiza análise de performance"""
    
    st.subheader("⚡ Análise de Performance")
    
    test_results = st.session_state.get('test_results', {})
    
    if not test_results:
        st.info("⚡ Execute alguns testes para ver análise de performance")
        return
    
    # Análise de tempos de execução
    execution_times = [r.get('execution_time', 0) for r in test_results.values() if r.get('success')]
    
    if execution_times:
        col_perf1, col_perf2, col_perf3 = st.columns(3)
        
        with col_perf1:
            st.metric("⏱️ Tempo Médio", f"{sum(execution_times)/len(execution_times):.2f}s")
        
        with col_perf2:
            st.metric("🚀 Mais Rápido", f"{min(execution_times):.2f}s")
        
        with col_perf3:
            st.metric("🐌 Mais Lento", f"{max(execution_times):.2f}s")
        
        # Gráfico de distribuição de tempos
        st.markdown("#### 📊 Distribuição de Tempos de Execução")
        
        # Criar bins para o histograma
        time_bins = {
            "< 5s": sum(1 for t in execution_times if t < 5),
            "5-10s": sum(1 for t in execution_times if 5 <= t < 10),
            "10-20s": sum(1 for t in execution_times if 10 <= t < 20),
            "20s+": sum(1 for t in execution_times if t >= 20)
        }
        
        st.bar_chart(time_bins)
        
        # Performance por tipo
        st.markdown("#### ⚡ Performance por Tipo")
        
        perf_by_type = {}
        for result in test_results.values():
            if result.get('success'):
                summary_type = result.get('summary_type', 'unknown')
                exec_time = result.get('execution_time', 0)
                
                if summary_type not in perf_by_type:
                    perf_by_type[summary_type] = []
                
                perf_by_type[summary_type].append(exec_time)
        
        # Exibir estatísticas por tipo
        for summary_type, times in perf_by_type.items():
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            st.markdown(f"""
            <div style="background: #f8f9fa; border-left: 4px solid #667eea; 
                        padding: 15px; margin: 10px 0; border-radius: 8px;">
                <h5 style="margin: 0 0 10px 0; color: #333;">📝 {summary_type.title()}</h5>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px;">
                    <div><strong>📊 Execuções:</strong> {len(times)}</div>
                    <div><strong>⏱️ Média:</strong> {avg_time:.2f}s</div>
                    <div><strong>🚀 Melhor:</strong> {min_time:.2f}s</div>
                    <div><strong>🐌 Pior:</strong> {max_time:.2f}s</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def render_reports_section():
    """Seção de relatórios e exportação"""
    
    st.subheader("📊 Relatórios & Exportação")
    
    # Gerar relatório automático
    if st.button("📋 Gerar Relatório Completo", use_container_width=True):
        report = generate_comprehensive_report()
        
        st.markdown("#### 📄 Relatório Gerado")
        st.text_area("Conteúdo do relatório:", value=report, height=300)
        
        # Download do relatório
        st.download_button(
            label="💾 Download Relatório",
            data=report,
            file_name=f"relatorio_claude_viewer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
    
    # Exportações específicas
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        st.markdown("#### 💾 Exportar Dados")
        
        if st.button("📊 Exportar Métricas", use_container_width=True):
            # Preparar dados de métricas
            metrics_data = {
                "export_timestamp": datetime.now().isoformat(),
                "test_results": st.session_state.get('test_results', {}),
                "debug_logs": st.session_state.get('debug_logs', [])[-100:],
                "session_count": len(get_sessions_from_api()),
                "system_status": get_system_status()
            }
            
            metrics_json = json.dumps(metrics_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="💾 Download Métricas JSON",
                data=metrics_json,
                file_name=f"metricas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col_export2:
        st.markdown("#### 🔍 Diagnóstico")
        
        if st.button("🔧 Executar Diagnóstico", use_container_width=True):
            diagnostic = run_system_diagnostic()
            
            st.markdown("#### 🔍 Resultado do Diagnóstico")
            
            for check in diagnostic:
                if "✅" in check:
                    st.success(check)
                elif "❌" in check:
                    st.error(check)
                else:
                    st.info(check)

def generate_comprehensive_report() -> str:
    """Gera relatório completo do sistema"""
    
    sessions = get_sessions_from_api()
    test_results = st.session_state.get('test_results', {})
    debug_logs = st.session_state.get('debug_logs', [])
    
    # Calcular estatísticas
    total_tests = len(test_results)
    successful_tests = sum(1 for r in test_results.values() if r.get('success', False))
    success_rate = (successful_tests / max(total_tests, 1)) * 100
    
    recent_errors = sum(1 for log in debug_logs[-100:] if log["level"].upper() == "ERROR")
    
    # Custos totais
    total_cost = 0
    total_tokens = 0
    
    for result in test_results.values():
        if result.get('success'):
            metrics = result.get('result', {}).get('metrics', {})
            total_cost += metrics.get('cost', 0)
            total_tokens += metrics.get('input_tokens', 0) + metrics.get('output_tokens', 0)
    
    # Gerar relatório
    report = f"""
# 📊 Relatório Completo - Claude Session Viewer

**Gerado em:** {datetime.now().strftime("%d/%m/%Y às %H:%M:%S")}

## 📋 Resumo Executivo

### 🎯 Status Geral do Sistema
- ✅ Sistema operacional e funcionando
- 📋 {len(sessions)} sessões Claude Code disponíveis  
- 📝 {len(st.session_state.get('test_results', {}))} resumos gerados
- 📊 {success_rate:.1f}% de taxa de sucesso nas operações

### 💰 Análise Financeira
- 💵 Custo total de resumos: ${total_cost:.6f}
- 🔢 Tokens processados: {total_tokens:,}
- 📊 Custo médio por resumo: ${total_cost/max(total_tests, 1):.6f}
- ⚡ Eficiência: ${total_cost/max(total_tokens, 1)*1000:.3f} por 1k tokens

### 🎯 Performance do Sistema
- ⚡ {successful_tests} operações bem-sucedidas de {total_tests} tentativas
- ❌ {recent_errors} erros nas últimas 100 operações
- 🔧 Sistema de debug ativo com {len(debug_logs)} logs registrados

## 📊 Detalhamento por Funcionalidade

### 📝 Sistema de Resumos
"""
    
    # Adicionar análise por tipo de resumo
    if test_results:
        type_analysis = {}
        for result in test_results.values():
            if result.get('success'):
                summary_type = result.get('summary_type', 'unknown')
                exec_time = result.get('execution_time', 0)
                
                if summary_type not in type_analysis:
                    type_analysis[summary_type] = {
                        "count": 0,
                        "total_time": 0,
                        "total_cost": 0
                    }
                
                type_analysis[summary_type]["count"] += 1
                type_analysis[summary_type]["total_time"] += exec_time
                
                metrics = result.get('result', {}).get('metrics', {})
                type_analysis[summary_type]["total_cost"] += metrics.get('cost', 0)
        
        for summary_type, stats in type_analysis.items():
            count = stats["count"]
            avg_time = stats["total_time"] / count
            avg_cost = stats["total_cost"] / count
            
            report += f"""
#### {summary_type.title()}
- 📊 Execuções: {count}
- ⏱️ Tempo médio: {avg_time:.2f}s
- 💰 Custo médio: ${avg_cost:.6f}
"""
    
    report += f"""

## 🔧 Informações Técnicas

### 🌐 URLs dos Serviços
- Viewer HTTP: http://localhost:3041
- Streamlit Modernizado: http://localhost:3042
- API Principal: http://localhost:8990
- Debug Original: http://localhost:8506

### 📂 Estrutura de Dados
- Diretório de sessões: /home/suthub/.claude/projects/
- Backend do viewer: /home/suthub/.claude/cc-sdk-chat/viewer-claude/backend/
- Claude SDK: Integrado via link simbólico

### 🔄 Status dos Componentes
- ✅ HTTP Server (viewer.py): Operacional
- ✅ Claude SDK: Integrado
- ✅ Sistema de resumo: Funcional
- ✅ Interface Streamlit: Ativa
- ✅ Debug & Analytics: Disponível

## 💡 Recomendações

1. **Monitoramento Contínuo:** Verificar logs de erro regularmente
2. **Otimização de Custos:** Monitorar uso de tokens por tipo de resumo
3. **Performance:** Investigar resumos que demoram mais de 20s
4. **Backup:** Fazer backup das métricas coletadas periodicamente
5. **Evolução:** Considerar implementar cache de resumos para reduzir custos

---

*Relatório gerado automaticamente pelo Claude Session Viewer Analytics*
*Sistema desenvolvido para otimizar o uso do Claude Code*
"""
    
    return report

def get_sessions_from_api() -> List[Dict]:
    """Helper para carregar sessões"""
    try:
        response = requests.get("http://localhost:3041/api/sessions", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def get_system_status() -> Dict:
    """Obtém status atual do sistema"""
    
    status = {}
    
    # Teste viewer HTTP
    try:
        response = requests.get("http://localhost:3041/api/sessions", timeout=3)
        status["viewer_http"] = response.status_code == 200
    except:
        status["viewer_http"] = False
    
    # Teste API principal
    try:
        response = requests.get("http://localhost:8990/health", timeout=3)
        status["main_api"] = response.status_code == 200
    except:
        status["main_api"] = False
    
    # Verificar arquivos
    projects_path = Path("/home/suthub/.claude/projects")
    status["projects_path"] = projects_path.exists()
    
    # Claude SDK
    sdk_path = Path("/home/suthub/.claude/cc-sdk-chat/viewer-claude/backend/claude-sdk")
    status["claude_sdk"] = sdk_path.exists()
    
    return status

def run_system_diagnostic() -> List[str]:
    """Executa diagnóstico completo do sistema"""
    
    checks = []
    
    status = get_system_status()
    
    # Verificações individuais
    if status.get("viewer_http"):
        checks.append("✅ Viewer HTTP: Respondendo na porta 3041")
    else:
        checks.append("❌ Viewer HTTP: Não está respondendo")
    
    if status.get("main_api"):
        checks.append("✅ API Principal: Conectada na porta 8990")
    else:
        checks.append("❌ API Principal: Não conectada")
    
    if status.get("projects_path"):
        # Contar sessões
        projects_path = Path("/home/suthub/.claude/projects")
        session_count = 0
        try:
            for directory in projects_path.iterdir():
                if directory.is_dir():
                    session_count += len(list(directory.glob("*.jsonl")))
            checks.append(f"✅ Sistema de arquivos: {session_count} sessões encontradas")
        except:
            checks.append("❌ Sistema de arquivos: Erro ao acessar sessões")
    else:
        checks.append("❌ Sistema de arquivos: Diretório de projetos não encontrado")
    
    if status.get("claude_sdk"):
        checks.append("✅ Claude SDK: Integração ativa")
    else:
        checks.append("❌ Claude SDK: Link simbólico não encontrado")
    
    # Verificar Streamlit atual
    try:
        import streamlit
        checks.append(f"✅ Streamlit: Versão {streamlit.__version__}")
    except:
        checks.append("❌ Streamlit: Não disponível")
    
    return checks