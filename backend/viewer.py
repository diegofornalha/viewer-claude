#!/usr/bin/env python3
"""
Viewer simples para sessões do Claude Code
Servidor HTTP básico para visualizar arquivos .jsonl
"""

import json
import os
import asyncio
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import webbrowser
import time

# Imports para funcionalidade de resumo
from session_summarizer import get_session_summarizer
from summary_storage import get_summary_storage

CLAUDE_PROJECTS_PATH = Path("/home/suthub/.claude/projects")

class ViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/":
            self.serve_index()
        elif path == "/api/sessions":
            self.serve_sessions_list()
        elif path == "/api/summaries":
            self.handle_list_summaries_request()
        elif path.startswith("/api/summaries/"):
            self.handle_summary_detail_request(path)
        elif path.startswith("/api/session/"):
            self.serve_session_detail(path)
        elif path == "/favicon.ico":
            self.send_error(404)
        else:
            # Verificar se é uma URL de sessão: /{directory}/{session_id}[/resumo]
            path_parts = path.strip('/').split('/')
            if len(path_parts) == 2:
                # URL da sessão específica - servir página principal
                self.serve_index()
            elif len(path_parts) == 3 and path_parts[2] == "resumo":
                # URL de resumo: /{directory}/{session_id}/resumo
                self.serve_index()
            else:
                self.send_error(404)
    
    def do_DELETE(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith("/api/session/"):
            self.delete_session(path)
        else:
            self.send_error(404)
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/api/summarize":
            self.handle_summarize_request()
        elif path == "/api/summarize-custom":
            self.handle_summarize_custom_request()
        elif path == "/api/summaries":
            self.handle_list_summaries_request()
        elif path.startswith("/api/summaries/"):
            self.handle_summary_detail_request(path)
        else:
            self.send_error(404)
    
    def serve_index(self):
        """Serve a página HTML principal"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Claude Session Viewer</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        
        /* Grid layout para sessões */
        .sessions-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); 
            gap: 20px; 
            margin: 20px 0; 
        }
        
        .session { 
            background: white;
            border: 1px solid #ddd; 
            padding: 20px; 
            border-radius: 10px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            min-height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .session:hover { 
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }
        
        .session-id { 
            font-weight: bold; 
            color: #333; 
            font-size: 0.9em;
            margin-bottom: 8px;
            word-break: break-all;
        }
        
        .session-path { 
            color: #666; 
            font-size: 0.8em; 
            margin-bottom: 15px;
            background: #f8f9fa;
            padding: 5px 8px;
            border-radius: 4px;
            word-break: break-all;
        }
        
        .session-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
        }
        
        .last-interaction {
            color: #888;
            font-size: 0.8em;
            font-weight: 500;
        }
        
        .view-btn { 
            background: #007cba; 
            color: white; 
            border: none; 
            padding: 8px 14px; 
            border-radius: 6px; 
            cursor: pointer; 
            font-weight: 500;
            font-size: 0.9em;
            transition: background 0.2s ease;
            margin-right: 8px;
        }
        
        .view-btn:hover { background: #005a87; }
        
        .delete-btn {
            background: #dc3545;
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: background 0.2s ease;
        }
        
        .delete-btn:hover { background: #c82333; }
        
        .session-buttons {
            display: flex;
            align-items: center;
        }
        
        .message { border-left: 3px solid #007cba; padding: 10px; margin: 10px 0; 
                  background: #f8f9fa; }
        .message-role { font-weight: bold; color: #007cba; }
        .message-time { color: #666; font-size: 0.8em; }
        .back-btn { background: #6c757d; color: white; border: none; padding: 8px 16px; 
                   border-radius: 3px; cursor: pointer; margin: 10px 0; }
        
        .summarize-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            margin: 15px 0;
            font-size: 0.95em;
            transition: background 0.2s ease;
        }
        
        .summarize-btn:hover { background: #218838; }
        #loading { text-align: center; padding: 20px; }
        
        h1 { 
            color: #333; 
            text-align: center; 
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <h1>Claude Session Viewer</h1>
    <div id="loading">Carregando sessões...</div>
    <div id="content"></div>
    
    <script>
        async function loadSessions() {
            try {
                const response = await fetch('/api/sessions');
                const sessions = await response.json();
                
                const content = document.getElementById('content');
                const loading = document.getElementById('loading');
                
                if (sessions.length === 0) {
                    content.innerHTML = '<p>Nenhuma sessão encontrada.</p>';
                } else {
                    content.innerHTML = `
                        <div class="sessions-grid">
                            ${sessions.map(session => `
                                <div class="session">
                                    <div>
                                        <div class="session-id">${session.session_id}</div>
                                        <div class="session-path">${session.directory}</div>
                                    </div>
                                    <div class="session-footer">
                                        <div class="last-interaction">${session.last_interaction}</div>
                                        <div class="session-buttons">
                                            <button class="view-btn" onclick="viewSession('${session.directory}', '${session.session_id}')">
                                                Ver Sessão
                                            </button>
                                            <button class="delete-btn" onclick="deleteSession('${session.directory}', '${session.session_id}')" title="Excluir sessão">
                                                Excluir
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
                
                loading.style.display = 'none';
            } catch (error) {
                document.getElementById('loading').innerHTML = 'Erro ao carregar sessões: ' + error.message;
            }
        }
        
        async function viewSession(directory, sessionId) {
            const content = document.getElementById('content');
            content.innerHTML = '<div id="loading">Carregando mensagens...</div>';
            
            // Atualizar URL se não estivermos já na URL correta
            const expectedPath = `/${directory}/${sessionId}`;
            if (window.location.pathname !== expectedPath) {
                history.pushState(null, '', expectedPath);
            }
            
            try {
                const response = await fetch(`/api/session/${directory}/${sessionId}`);
                const sessionData = await response.json();
                
                let html = `
                    <button class="back-btn" onclick="goHome()">← Voltar</button>
                    <h2>Sessão: ${sessionData.session_id}</h2>
                    <p><strong>Diretório:</strong> ${sessionData.directory}</p>
                    <p><strong>Total de mensagens:</strong> ${sessionData.message_count}</p>
                    <div style="display: flex; gap: 10px; margin: 15px 0;">
                        <button class="summarize-btn" onclick="goToResumoPage('${directory}', '${sessionId}')">
                            Resumir Conteúdo
                        </button>
                        <button class="delete-btn" onclick="deleteSessionFromDetail('${directory}', '${sessionId}')">
                            Excluir
                        </button>
                    </div>
                    <hr>
                `;
                
                // Reverter ordem das mensagens para mostrar mais recentes primeiro
                sessionData.messages.slice().reverse().forEach(msg => {
                    html += `
                        <div class="message">
                            <div class="message-role">${msg.role || msg.type}</div>
                            <div class="message-time">${msg.timestamp}</div>
                            <div>${typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)}</div>
                        </div>
                    `;
                });
                
                content.innerHTML = html;
            } catch (error) {
                content.innerHTML = `
                    <button class="back-btn" onclick="goHome()">← Voltar</button>
                    <p style="color: red;">Erro ao carregar sessão: ${error.message}</p>
                `;
            }
        }
        
        function goHome() {
            history.pushState(null, '', '/');
            loadSessions();
        }
        
        function goToResumoPage(directory, sessionId) {
            const resumoUrl = `/${directory}/${sessionId}/resumo`;
            history.pushState(null, '', resumoUrl);
            showResumoPage(directory, sessionId);
        }
        
        async function showResumoPage(directory, sessionId) {
            const content = document.getElementById('content');
            
            // Interface da página de resumo com opções
            content.innerHTML = `
                <button class="back-btn" onclick="viewSession('${directory}', '${sessionId}')">← Voltar à Sessão</button>
                
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px;">
                    <h2>🎯 Central de Resumos</h2>
                    <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px;">
                        <div><strong>📋 Sessão:</strong> ${sessionId.substring(0, 8)}...</div>
                        <div><strong>📁 Projeto:</strong> ${directory}</div>
                        <div><strong>🔗 URL:</strong> /${directory}/${sessionId}/resumo</div>
                    </div>
                </div>
                
                <div style="background: white; border: 1px solid #ddd; border-radius: 12px; padding: 30px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <h3 style="margin-top: 0; color: #333;">📝 Escolha o Tipo de Resumo</h3>
                    <p style="color: #666; margin-bottom: 25px;">Selecione o formato que melhor atende sua necessidade:</p>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
                        
                        <div style="border: 2px solid #28a745; border-radius: 10px; padding: 20px; cursor: pointer; transition: transform 0.2s;" onclick="generateResumoType('${directory}', '${sessionId}', 'conciso')">
                            <h4 style="color: #28a745; margin-top: 0;">📝 Resumo Conciso</h4>
                            <p style="color: #666; margin: 10px 0;">Resumo estruturado e direto ao ponto (máx. 200 palavras)</p>
                            <ul style="color: #888; font-size: 0.9em;">
                                <li>📋 Contexto e objetivo</li>
                                <li>✅ Principais resultados</li>
                                <li>🔧 Tecnologias utilizadas</li>
                            </ul>
                            <button style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 6px; width: 100%; font-weight: 500;">
                                Gerar Resumo Conciso
                            </button>
                        </div>
                        
                        <div style="border: 2px solid #007cba; border-radius: 10px; padding: 20px; cursor: pointer; transition: transform 0.2s;" onclick="generateResumoType('${directory}', '${sessionId}', 'detalhado')">
                            <h4 style="color: #007cba; margin-top: 0;">📋 Resumo Detalhado</h4>
                            <p style="color: #666; margin: 10px 0;">Análise completa e aprofundada (máx. 400 palavras)</p>
                            <ul style="color: #888; font-size: 0.9em;">
                                <li>📋 Contexto completo</li>
                                <li>⚙️ Detalhes técnicos</li>
                                <li>💡 Insights e decisões</li>
                                <li>🔄 Próximos passos</li>
                            </ul>
                            <button style="background: #007cba; color: white; border: none; padding: 10px 20px; border-radius: 6px; width: 100%; font-weight: 500;">
                                Gerar Resumo Detalhado
                            </button>
                        </div>
                        
                        <div style="border: 2px solid #fd7e14; border-radius: 10px; padding: 20px; cursor: pointer; transition: transform 0.2s;" onclick="generateResumoType('${directory}', '${sessionId}', 'bullet_points')">
                            <h4 style="color: #fd7e14; margin-top: 0;">• Lista de Pontos</h4>
                            <p style="color: #666; margin: 10px 0;">Organização em bullet points estruturados</p>
                            <ul style="color: #888; font-size: 0.9em;">
                                <li>📋 Contexto em pontos</li>
                                <li>🎯 Objetivos listados</li>
                                <li>✅ Implementações organizadas</li>
                                <li>🔧 Stack tecnológico</li>
                            </ul>
                            <button style="background: #fd7e14; color: white; border: none; padding: 10px 20px; border-radius: 6px; width: 100%; font-weight: 500;">
                                Gerar Lista de Pontos
                            </button>
                        </div>
                        
                    </div>
                    
                    <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid #eee;">
                        <h4 style="color: #333;">🔗 URLs Diretas</h4>
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 0.9em; color: #495057;">
                            <div>📝 Conciso: <code>/${directory}/${sessionId}/resumo?tipo=conciso</code></div>
                            <div>📋 Detalhado: <code>/${directory}/${sessionId}/resumo?tipo=detalhado</code></div>
                            <div>• Pontos: <code>/${directory}/${sessionId}/resumo?tipo=bullet_points</code></div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        async function generateResumoType(directory, sessionId, type) {
            // Atualizar URL com tipo específico
            history.pushState(null, '', `/${directory}/${sessionId}/resumo?tipo=${type}`);
            
            // Reutiliza a função já implementada
            await generateSummaryByType(directory, sessionId, type);
        }
        
        async function summarizeContent(directory, sessionId) {
            const content = document.getElementById('content');
            const originalContent = content.innerHTML;
            
            // Mostra loading
            content.innerHTML = `
                <button class="back-btn" onclick="goHome()">← Voltar</button>
                <h2>🤖 Gerando Resumo...</h2>
                <p>Processando conversa com Claude SDK...</p>
                <div style="text-align: center; padding: 20px;">
                    <div style="border: 4px solid #f3f3f3; border-radius: 50%; border-top: 4px solid #007cba; width: 40px; height: 40px; animation: spin 2s linear infinite; margin: 0 auto;"></div>
                </div>
                <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            `;
            
            try {
                console.log('🎯 Iniciando resumo:', directory, sessionId);
                
                const response = await fetch('/api/summarize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        directory: directory,
                        session_id: sessionId,
                        summary_type: 'conciso'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Exibe resumo com sucesso
                    const metadata = result.session_metadata || {};
                    const metrics = result.metrics || {};
                    
                    content.innerHTML = `
                        <button class="back-btn" onclick="goHome()">← Voltar</button>
                        
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                            <h2>🎯 Resumo da Sessão</h2>
                            <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px;">
                                <div><strong>📋 Sessão:</strong> ${sessionId.substring(0, 8)}...</div>
                                <div><strong>📁 Projeto:</strong> ${directory}</div>
                                <div><strong>💬 Mensagens:</strong> ${metadata.total_messages || 'N/A'}</div>
                                <div><strong>⏱️ Duração:</strong> ${metadata.duration || 'N/A'}</div>
                            </div>
                        </div>
                        
                        <div style="background: white; border: 1px solid #ddd; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                            <h3 style="color: #333; margin-top: 0;">📝 Resumo Inteligente</h3>
                            <div style="line-height: 1.6; color: #444; white-space: pre-wrap;">${result.summary}</div>
                        </div>
                        
                        <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                            <h4 style="margin-top: 0; color: #495057;">📊 Métricas do Resumo</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                                <div><strong>Tokens Entrada:</strong> ${metrics.input_tokens || 0}</div>
                                <div><strong>Tokens Saída:</strong> ${metrics.output_tokens || 0}</div>
                                <div><strong>Custo:</strong> $${(metrics.cost || 0).toFixed(6)}</div>
                                <div><strong>Gerado em:</strong> ${new Date().toLocaleTimeString()}</div>
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <button class="view-btn" onclick="viewSession('${directory}', '${sessionId}')">
                                📄 Ver Conversa Original
                            </button>
                            <button class="view-btn" onclick="generateDetailedSummary('${directory}', '${sessionId}')">
                                📋 Resumo Detalhado
                            </button>
                            <button class="view-btn" onclick="generateBulletSummary('${directory}', '${sessionId}')">
                                • Lista de Pontos
                            </button>
                            <button class="delete-btn" onclick="deleteFromResumo('${directory}', '${sessionId}')">🗑️ Excluir Sessão</button>
                        </div>
                    `;
                    
                    console.log('✅ Resumo exibido com sucesso');
                    
                } else {
                    // Exibe erro
                    content.innerHTML = `
                        <button class="back-btn" onclick="goHome()">← Voltar</button>
                        <div style="background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 15px; border-radius: 8px; margin: 20px 0;">
                            <h3>❌ Erro ao Gerar Resumo</h3>
                            <p><strong>Detalhes:</strong> ${result.error || 'Erro desconhecido'}</p>
                            <button class="view-btn" onclick="viewSession('${directory}', '${sessionId}')">
                                Ver Sessão Original
                            </button>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('❌ Erro na requisição de resumo:', error);
                content.innerHTML = `
                    <button class="back-btn" onclick="goHome()">← Voltar</button>
                    <div style="background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h3>❌ Erro de Conexão</h3>
                        <p>Não foi possível conectar com o serviço de resumo.</p>
                        <p><strong>Erro:</strong> ${error.message}</p>
                        <button class="view-btn" onclick="viewSession('${directory}', '${sessionId}')">
                            Ver Sessão Original
                        </button>
                    </div>
                `;
            }
        }
        
        // Funções auxiliares para diferentes tipos de resumo
        async function generateDetailedSummary(directory, sessionId) {
            await generateSummaryByType(directory, sessionId, 'detalhado');
        }
        
        async function generateBulletSummary(directory, sessionId) {
            await generateSummaryByType(directory, sessionId, 'bullet_points');
        }
        
        async function generateSummaryByType(directory, sessionId, type) {
            const content = document.getElementById('content');
            
            // Loading específico para tipo
            const typeNames = {
                'detalhado': 'Detalhado',
                'bullet_points': 'Lista de Pontos',
                'conciso': 'Conciso'
            };
            
            content.innerHTML = `
                <button class="back-btn" onclick="goHome()">← Voltar</button>
                <h2>🤖 Gerando Resumo ${typeNames[type]}...</h2>
                <div style="text-align: center; padding: 20px;">
                    <div style="border: 4px solid #f3f3f3; border-radius: 50%; border-top: 4px solid #007cba; width: 40px; height: 40px; animation: spin 2s linear infinite; margin: 0 auto;"></div>
                </div>
            `;
            
            try {
                const response = await fetch('/api/summarize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        directory: directory,
                        session_id: sessionId,
                        summary_type: type
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const metadata = result.session_metadata || {};
                    const metrics = result.metrics || {};
                    
                    content.innerHTML = `
                        <button class="back-btn" onclick="goHome()">← Voltar</button>
                        
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                            <h2>🎯 Resumo ${typeNames[type]}</h2>
                            <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px;">
                                <div><strong>📋 Sessão:</strong> ${sessionId.substring(0, 8)}...</div>
                                <div><strong>📁 Projeto:</strong> ${directory}</div>
                                <div><strong>💬 Mensagens:</strong> ${metadata.total_messages || 'N/A'}</div>
                            </div>
                        </div>
                        
                        <div style="background: white; border: 1px solid #ddd; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                            <div style="line-height: 1.6; color: #444; white-space: pre-wrap;">${result.summary}</div>
                        </div>
                        
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <button class="view-btn" onclick="viewSession('${directory}', '${sessionId}')">📄 Ver Conversa</button>
                            <button class="view-btn" onclick="summarizeContent('${directory}', '${sessionId}')">📝 Resumo Conciso</button>
                            ${type !== 'detalhado' ? `<button class="view-btn" onclick="generateDetailedSummary('${directory}', '${sessionId}')">📋 Detalhado</button>` : ''}
                            ${type !== 'bullet_points' ? `<button class="view-btn" onclick="generateBulletSummary('${directory}', '${sessionId}')">• Pontos</button>` : ''}
                            <button class="delete-btn" onclick="deleteFromResumo('${directory}', '${sessionId}')">🗑️ Excluir Sessão</button>
                        </div>
                    `;
                } else {
                    content.innerHTML = `
                        <button class="back-btn" onclick="goHome()">← Voltar</button>
                        <div style="background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 15px; border-radius: 8px; margin: 20px 0;">
                            <h3>❌ Erro ao Gerar Resumo</h3>
                            <p>${result.error || 'Erro desconhecido'}</p>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Erro:', error);
                content.innerHTML = `
                    <button class="back-btn" onclick="goHome()">← Voltar</button>
                    <div style="background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h3>❌ Erro de Conexão</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }
        
        async function deleteSession(directory, sessionId) {
            try {
                const response = await fetch(`/api/session/${directory}/${sessionId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    loadSessions(); // Recarregar lista
                }
            } catch (error) {
                console.error('Erro ao excluir sessão:', error);
            }
        }
        
        async function deleteSessionFromDetail(directory, sessionId) {
            try {
                const response = await fetch(`/api/session/${directory}/${sessionId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    // Redireciona para home após exclusão
                    history.pushState(null, '', '/');
                    loadSessions();
                }
            } catch (error) {
                console.error('Erro ao excluir sessão:', error);
            }
        }
        
        async function deleteFromResumo(directory, sessionId) {
            try {
                const response = await fetch(`/api/session/${directory}/${sessionId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    // Redireciona para a página da sessão que depois vai para home
                    history.pushState(null, '', `/${directory}/${sessionId}`);
                    viewSession(directory, sessionId);
                }
            } catch (error) {
                console.error('Erro ao excluir sessão:', error);
            }
        }
        
        // Função para carregar página inicial
        function loadPage() {
            const path = window.location.pathname;
            const pathParts = path.split('/').filter(p => p);
            
            if (pathParts.length === 2) {
                // URL específica da sessão: /{directory}/{session_id}
                const [directory, sessionId] = pathParts;
                viewSession(directory, sessionId);
            } else if (pathParts.length === 3 && pathParts[2] === 'resumo') {
                // URL de resumo: /{directory}/{session_id}/resumo
                const [directory, sessionId] = pathParts;
                showResumoPage(directory, sessionId);
            } else {
                // Página inicial - carregar lista de sessões
                loadSessions();
            }
        }
        
        // Carregar página ao iniciar
        loadPage();
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_sessions_list(self):
        """Lista todas as sessões disponíveis"""
        try:
            sessions = []
            
            if CLAUDE_PROJECTS_PATH.exists():
                for directory in CLAUDE_PROJECTS_PATH.iterdir():
                    if directory.is_dir():
                        for jsonl_file in directory.glob("*.jsonl"):
                            sessions.append({
                                "session_id": jsonl_file.stem,
                                "directory": directory.name,
                                "file_path": str(jsonl_file),
                                "modified_time": jsonl_file.stat().st_mtime
                            })
            
            # Ordenar do mais novo para o mais antigo (mais recentes primeiro, antigas por último)
            sessions.sort(key=lambda x: x["modified_time"], reverse=True)
            
            # Converter modified_time para horário formatado
            import datetime
            for session in sessions:
                dt = datetime.datetime.fromtimestamp(session["modified_time"])
                session["last_interaction"] = dt.strftime("%H:%M")
                del session["modified_time"]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(sessions, ensure_ascii=False).encode('utf-8'))
        
        except Exception as e:
            self.send_error(500, f"Erro ao listar sessões: {str(e)}")
    
    def serve_session_detail(self, path):
        """Serve detalhes de uma sessão específica"""
        try:
            # Extrair directory e session_id da URL
            parts = path.strip('/').split('/')
            if len(parts) < 4:  # api/session/directory/session_id
                self.send_error(400, "URL inválida")
                return
            
            directory = parts[2]
            session_id = parts[3]
            
            file_path = CLAUDE_PROJECTS_PATH / directory / f"{session_id}.jsonl"
            
            if not file_path.exists():
                self.send_error(404, f"Sessão não encontrada: {directory}/{session_id}")
                return
            
            messages = []
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            
                            # Processar mensagem
                            message_data = data.get("message", {})
                            content = message_data.get("content", data.get("message", ""))
                            
                            processed_msg = {
                                "uuid": data.get("uuid", ""),
                                "timestamp": data.get("timestamp", ""),
                                "type": data.get("type", ""),
                                "role": message_data.get("role", data.get("type", "")),
                                "content": content
                            }
                            messages.append(processed_msg)
                        except json.JSONDecodeError as e:
                            print(f"Erro linha {line_num} em {file_path}: {e}")
                            continue
            
            session_data = {
                "session_id": session_id,
                "directory": directory,
                "message_count": len(messages),
                "messages": messages[:50]  # Limitar a 50 mensagens para performance
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(session_data, ensure_ascii=False).encode('utf-8'))
        
        except Exception as e:
            self.send_error(500, f"Erro ao carregar sessão: {str(e)}")
    
    def delete_session(self, path):
        """Exclui uma sessão específica"""
        try:
            # Extrair directory e session_id da URL
            parts = path.strip('/').split('/')
            if len(parts) < 4:  # api/session/directory/session_id
                self.send_error(400, "URL inválida")
                return
            
            directory = parts[2]
            session_id = parts[3]
            
            file_path = CLAUDE_PROJECTS_PATH / directory / f"{session_id}.jsonl"
            
            if not file_path.exists():
                self.send_error(404, f"Sessão não encontrada: {directory}/{session_id}")
                return
            
            # Apagar o arquivo físico
            file_path.unlink()
            
            # Resposta de sucesso
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"success": True, "message": f"Sessão {session_id} excluída com sucesso"}
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        
        except Exception as e:
            self.send_error(500, f"Erro ao excluir sessão: {str(e)}")
    
    def handle_summarize_request(self):
        """Processa requisições de resumo de sessão"""
        try:
            # Lê dados do corpo da requisição POST
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Requisição vazia")
                return
            
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Extrai parâmetros
            directory = request_data.get('directory', '').strip()
            session_id = request_data.get('session_id', '').strip()
            summary_type = request_data.get('summary_type', 'conciso').strip()
            
            if not directory or not session_id:
                self.send_error(400, "Parâmetros directory e session_id são obrigatórios")
                return
            
            # Validações
            valid_types = ['conciso', 'detalhado', 'bullet_points']
            if summary_type not in valid_types:
                summary_type = 'conciso'
            
            print(f"🎯 Resumo solicitado: {directory}/{session_id} (tipo: {summary_type})")
            
            # Executa resumo de forma síncrona (adaptado para HTTP server simples)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                summarizer = get_session_summarizer()
                result = loop.run_until_complete(
                    summarizer.generate_summary(directory, session_id, summary_type)
                )
                
                # Salvar resumo automaticamente se foi bem-sucedido
                if result.get("success"):
                    storage = get_summary_storage()
                    summary_id = storage.save_summary(directory, session_id, result)
                    result["summary_id"] = summary_id
                    print(f"📝 Resumo salvo com ID: {summary_id}")
                
            finally:
                loop.close()
            
            # Resposta
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response_json = json.dumps(result, ensure_ascii=False)
            self.wfile.write(response_json.encode('utf-8'))
            
            print(f"✅ Resumo concluído para {directory}/{session_id}")
            
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
        except Exception as e:
            print(f"❌ Erro ao processar resumo: {e}")
            self.send_error(500, f"Erro ao processar resumo: {str(e)}")
    
    def handle_summarize_custom_request(self):
        """Processa requisições de resumo com conteúdo customizado"""
        try:
            # Lê dados do corpo da requisição POST
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Requisição vazia")
                return
            
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Extrai parâmetros
            custom_content = request_data.get('custom_content', '').strip()
            summary_type = request_data.get('summary_type', 'conciso').strip()
            
            if not custom_content:
                self.send_error(400, "Parâmetro custom_content é obrigatório")
                return
            
            # Validações
            valid_types = ['conciso', 'detalhado', 'bullet_points']
            if summary_type not in valid_types:
                summary_type = 'conciso'
            
            print(f"🎯 Resumo customizado solicitado (tipo: {summary_type}, {len(custom_content)} chars)")
            
            # Executa resumo usando conteúdo customizado
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                summarizer = get_session_summarizer()
                result = loop.run_until_complete(
                    summarizer.generate_summary_from_content(custom_content, summary_type)
                )
            finally:
                loop.close()
            
            # Resposta
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response_json = json.dumps(result, ensure_ascii=False)
            self.wfile.write(response_json.encode('utf-8'))
            
            print(f"✅ Resumo customizado concluído ({len(result.get('summary', ''))} chars)")
            
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
        except Exception as e:
            print(f"❌ Erro ao processar resumo customizado: {e}")
            self.send_error(500, f"Erro ao processar resumo customizado: {str(e)}")
    
    def handle_list_summaries_request(self):
        """Lista resumos com filtros opcionais"""
        try:
            # Parse query parameters
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            
            # Parâmetros opcionais
            directory = query_params.get('directory', [None])[0]
            session_id = query_params.get('session_id', [None])[0] 
            limit = int(query_params.get('limit', [50])[0])
            
            storage = get_summary_storage()
            
            if directory and session_id:
                # Resumos específicos de uma sessão
                summaries = storage.get_summaries_for_session(directory, session_id)
                print(f"📋 Listando {len(summaries)} resumos para {directory}/{session_id}")
            else:
                # Todos os resumos do sistema
                summaries = storage.get_all_summaries(limit)
                print(f"📋 Listando {len(summaries)} resumos totais")
            
            # Adicionar estatísticas
            stats = storage.get_storage_stats()
            
            response_data = {
                "success": True,
                "summaries": summaries,
                "total_found": len(summaries),
                "storage_stats": stats,
                "filters_applied": {
                    "directory": directory,
                    "session_id": session_id,
                    "limit": limit
                }
            }
            
            # Resposta
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_json = json.dumps(response_data, ensure_ascii=False)
            self.wfile.write(response_json.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ Erro ao listar resumos: {e}")
            self.send_error(500, f"Erro ao listar resumos: {str(e)}")
    
    def handle_summary_detail_request(self, path):
        """Retorna detalhes de um resumo específico ou deleta"""
        try:
            # Extract summary ID from path: /api/summaries/{summary_id}
            summary_id = path.split('/')[-1]
            
            if not summary_id:
                self.send_error(400, "ID do resumo é obrigatório")
                return
            
            storage = get_summary_storage()
            
            if self.command == 'GET':
                # Buscar resumo por ID
                summary = storage.get_summary_by_id(summary_id)
                
                if summary:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    response_json = json.dumps(summary, ensure_ascii=False)
                    self.wfile.write(response_json.encode('utf-8'))
                    print(f"📄 Resumo {summary_id} retornado")
                else:
                    self.send_error(404, f"Resumo {summary_id} não encontrado")
            
            elif self.command == 'DELETE':
                # Extrair directory e session_id dos query params para delete
                parsed_path = urlparse(self.path)
                query_params = parse_qs(parsed_path.query)
                directory = query_params.get('directory', [None])[0]
                session_id = query_params.get('session_id', [None])[0]
                
                if not directory or not session_id:
                    self.send_error(400, "Parâmetros directory e session_id são obrigatórios para delete")
                    return
                
                success = storage.delete_summary(directory, session_id, summary_id)
                
                if success:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    response = {"success": True, "message": f"Resumo {summary_id} removido"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    print(f"🗑️ Resumo {summary_id} removido")
                else:
                    self.send_error(404, f"Resumo {summary_id} não encontrado ou erro na remoção")
            
        except Exception as e:
            print(f"❌ Erro no handle de resumo específico: {e}")
            self.send_error(500, str(e))
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server(port=3041):
    """Inicia o servidor"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ViewerHandler)
    
    print(f"🚀 Claude Session Viewer iniciado em http://localhost:{port}")
    print(f"📁 Buscando sessões em: {CLAUDE_PROJECTS_PATH}")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor parado")
        httpd.shutdown()

if __name__ == "__main__":
    run_server(3044)