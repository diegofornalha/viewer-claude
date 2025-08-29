#!/usr/bin/env python3
"""
Viewer simples para sessões do Claude Code
Servidor HTTP básico para visualizar arquivos .jsonl
"""

import json
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import webbrowser
import time

CLAUDE_PROJECTS_PATH = Path("/home/suthub/.claude/projects")

class ViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/":
            self.serve_index()
        elif path == "/api/sessions":
            self.serve_sessions_list()
        elif path.startswith("/api/session/"):
            self.serve_session_detail(path)
        elif path == "/favicon.ico":
            self.send_error(404)
        else:
            # Verificar se é uma URL de sessão: /{directory}/{session_id}
            path_parts = path.strip('/').split('/')
            if len(path_parts) == 2:
                # URL da sessão específica - servir página principal
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
                    <button class="summarize-btn" onclick="summarizeContent('${directory}', '${sessionId}')">
                        Resumir Conteúdo
                    </button>
                    <hr>
                `;
                
                sessionData.messages.forEach(msg => {
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
        
        function summarizeContent(directory, sessionId) {
            // Placeholder - será implementado posteriormente
            console.log('Resumir conteúdo clicado:', directory, sessionId);
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
        
        // Função para carregar página inicial
        function loadPage() {
            const path = window.location.pathname;
            const pathParts = path.split('/').filter(p => p);
            
            if (pathParts.length === 2) {
                // URL específica da sessão: /{directory}/{session_id}
                const [directory, sessionId] = pathParts;
                viewSession(directory, sessionId);
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
            
            # Ordenar do mais antigo para o mais novo
            sessions.sort(key=lambda x: x["modified_time"])
            
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
    run_server()