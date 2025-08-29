#!/usr/bin/env python3
"""
Parser Markdown Avançado para Resumos
Sistema de formatação rica baseado no 8505-viewer
"""

import re
from typing import Dict, List, Optional

class AdvancedMarkdownParser:
    """Parser markdown profissional para resumos do Claude"""
    
    def __init__(self):
        self.emoji_colors = {
            "📋": "#667eea",
            "🎯": "#28a745", 
            "✅": "#20c997",
            "🔧": "#fd7e14",
            "⚙️": "#6f42c1",
            "💡": "#ffc107",
            "🔄": "#17a2b8",
            "📊": "#e83e8c",
            "💰": "#28a745"
        }
    
    def parse_summary_content(self, content: str) -> str:
        """
        Converte conteúdo markdown em HTML formatado
        
        Args:
            content: Conteúdo markdown do resumo
            
        Returns:
            HTML formatado com estilos ricos
        """
        html = content
        
        # 1. Headers principais (## título)
        html = re.sub(
            r'^## (.*?)$', 
            r'<h3 style="color: #667eea; margin: 25px 0 15px 0; font-weight: bold; font-size: 18px; border-bottom: 2px solid #f0f0f0; padding-bottom: 8px;">\1</h3>', 
            html, flags=re.MULTILINE
        )
        
        # 2. Headers secundários (### título)
        html = re.sub(
            r'^### (.*?)$',
            r'<h4 style="color: #495057; margin: 20px 0 10px 0; font-weight: 600; font-size: 16px;">\1</h4>',
            html, flags=re.MULTILINE
        )
        
        # 3. Bold com emojis estruturados (📋 **Contexto**: texto)
        html = re.sub(
            r'(📋|🎯|✅|🔧|⚙️|💡|🔄|📊|💰)\s*\*\*(.*?)\*\*:', 
            lambda m: f'<div style="margin: 15px 0;"><span style="font-size: 16px; margin-right: 10px; color: {self.emoji_colors.get(m.group(1), "#333")};">{m.group(1)}</span><strong style="color: #333; font-size: 15px;">{m.group(2)}:</strong></div>', 
            html
        )
        
        # 4. Bold simples (**texto**)
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #333; font-weight: 600;">\1</strong>', html)
        
        # 5. Itálico (*texto*)
        html = re.sub(r'\*(.*?)\*', r'<em style="color: #666; font-style: italic;">\1</em>', html)
        
        # 6. Separadores horizontais (---)
        html = re.sub(
            r'^---+$', 
            r'<hr style="border: none; border-top: 2px solid #e9ecef; margin: 25px 0;">', 
            html, flags=re.MULTILINE
        )
        
        # 7. Listas com bullet points (• item)
        html = re.sub(
            r'^• (.*?)$', 
            r'<div style="margin: 8px 0 8px 20px; color: #555;"><span style="color: #667eea; margin-right: 8px; font-weight: bold;">•</span>\1</div>', 
            html, flags=re.MULTILINE
        )
        
        # 8. Listas numeradas (1. item)
        html = re.sub(
            r'^(\d+)\. (.*?)$',
            r'<div style="margin: 8px 0 8px 20px; color: #555;"><span style="color: #28a745; margin-right: 8px; font-weight: bold;">\1.</span>\2</div>',
            html, flags=re.MULTILINE
        )
        
        # 9. Código inline (`código`)
        html = re.sub(
            r'`(.*?)`', 
            r'<code style="background: #f8f9fa; padding: 2px 6px; border-radius: 4px; font-family: \'Monaco\', \'Courier New\', monospace; color: #e83e8c; font-size: 0.9em;">\1</code>', 
            html
        )
        
        # 10. Links [texto](url)
        html = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            r'<a href="\2" style="color: #667eea; text-decoration: none; font-weight: 500;" target="_blank">\1</a>',
            html
        )
        
        # 11. Blocos de código (```código```)
        html = re.sub(
            r'```(.*?)```',
            r'<pre style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; font-family: \'Monaco\', monospace; overflow-x: auto; font-size: 0.9em; color: #333; margin: 15px 0;"><code>\1</code></pre>',
            html, flags=re.DOTALL
        )
        
        # 12. Emojis isolados com espaçamento melhorado
        for emoji in self.emoji_colors.keys():
            html = re.sub(
                f'^({emoji})([^*])',
                f'<span style="display: inline-block; margin-right: 8px; font-size: 16px;">{emoji}</span>\\2',
                html, flags=re.MULTILINE
            )
        
        # 13. Quebras de linha duplas para parágrafos
        html = re.sub(r'\n\s*\n', '</p><p style="margin: 15px 0; line-height: 1.6; color: #444;">', html)
        
        # 14. Quebras simples para <br>
        html = html.replace('\n', '<br>')
        
        # 15. Envolver em parágrafo se não começar com tag HTML
        if not html.strip().startswith('<'):
            html = f'<p style="margin: 15px 0; line-height: 1.6; color: #444;">{html}</p>'
        
        # 16. Limpeza final
        html = html.replace('<br></p><p', '</p><p')  # Remove <br> antes de parágrafos
        html = re.sub(r'<p[^>]*></p>', '', html)  # Remove parágrafos vazios
        
        return html
    
    def parse_session_metadata(self, metadata: Dict) -> str:
        """
        Formata metadados de sessão em HTML rico
        
        Args:
            metadata: Dicionário com metadados da sessão
            
        Returns:
            HTML formatado com informações da sessão
        """
        return f"""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                    padding: 20px; border-radius: 12px; margin: 15px 0;
                    border-left: 5px solid #667eea;">
            <h4 style="margin: 0 0 15px 0; color: #333;">📊 Informações da Sessão</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div><strong>💬 Total de Mensagens:</strong> {metadata.get('total_messages', 'N/A')}</div>
                <div><strong>👤 Mensagens do Usuário:</strong> {metadata.get('user_messages', 'N/A')}</div>
                <div><strong>🤖 Respostas do Claude:</strong> {metadata.get('assistant_messages', 'N/A')}</div>
                <div><strong>⏰ Duração da Conversa:</strong> {metadata.get('duration', 'N/A')}</div>
                <div><strong>🕐 Primeira Mensagem:</strong> {self._format_timestamp(metadata.get('first_message', ''))}</div>
                <div><strong>🕑 Última Mensagem:</strong> {self._format_timestamp(metadata.get('last_message', ''))}</div>
            </div>
        </div>
        """
    
    def parse_summary_metrics(self, metrics: Dict) -> str:
        """
        Formata métricas de resumo em HTML
        
        Args:
            metrics: Dicionário com métricas do resumo
            
        Returns:
            HTML formatado com métricas
        """
        input_tokens = metrics.get('input_tokens', 0)
        output_tokens = metrics.get('output_tokens', 0)
        total_tokens = input_tokens + output_tokens
        cost = metrics.get('cost', 0)
        
        return f"""
        <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                    padding: 20px; border-radius: 12px; margin: 15px 0;
                    border-left: 5px solid #ffc107;">
            <h4 style="margin: 0 0 15px 0; color: #333;">💰 Métricas de Custo & Performance</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                <div><strong>🔢 Tokens Entrada:</strong> {input_tokens:,}</div>
                <div><strong>📤 Tokens Saída:</strong> {output_tokens:,}</div>
                <div><strong>📊 Total de Tokens:</strong> {total_tokens:,}</div>
                <div><strong>💲 Custo Estimado:</strong> ${cost:.6f}</div>
                <div><strong>📝 Tamanho do Resumo:</strong> {metrics.get('summary_length', 0)} chars</div>
                <div><strong>⚡ Eficiência:</strong> {(output_tokens / max(input_tokens, 1) * 100):.1f}%</div>
            </div>
        </div>
        """
    
    def _format_timestamp(self, timestamp: str) -> str:
        """Formata timestamp para exibição amigável"""
        if not timestamp:
            return "N/A"
        
        try:
            # Tentar parsear timestamp ISO
            dt = None
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            
            return dt.strftime("%d/%m/%Y %H:%M")
        except:
            return timestamp
    
    def create_summary_card(self, summary: Dict, summary_type: str) -> str:
        """
        Cria card completo para um resumo
        
        Args:
            summary: Conteúdo do resumo
            summary_type: Tipo do resumo (conciso, detalhado, bullet_points)
            
        Returns:
            HTML do card completo
        """
        
        # Cores por tipo
        type_colors = {
            "conciso": {"bg": "#e8f5e8", "border": "#28a745", "icon": "📝"},
            "detalhado": {"bg": "#e3f2fd", "border": "#2196f3", "icon": "📋"},
            "bullet_points": {"bg": "#fff3e0", "border": "#ff9800", "icon": "•"}
        }
        
        colors = type_colors.get(summary_type, type_colors["conciso"])
        
        # Parse do conteúdo
        parsed_content = self.parse_summary_content(summary.get('summary', ''))
        
        # Parse das métricas se disponíveis
        metrics_html = ""
        if summary.get('metrics'):
            metrics_html = self.parse_summary_metrics(summary['metrics'])
        
        return f"""
        <div style="background: {colors['bg']}; border: 2px solid {colors['border']}; 
                    border-radius: 15px; padding: 25px; margin: 20px 0;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <span style="font-size: 24px; margin-right: 12px;">{colors['icon']}</span>
                <h3 style="margin: 0; color: {colors['border']};">Resumo {summary_type.title()}</h3>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 10px; 
                        border-left: 5px solid {colors['border']}; margin: 15px 0;">
                {parsed_content}
            </div>
            
            {metrics_html}
        </div>
        """

# Instância global
parser = AdvancedMarkdownParser()

def get_markdown_parser():
    """Retorna instância do parser markdown"""
    return parser