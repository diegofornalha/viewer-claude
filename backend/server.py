"""
Servidor dedicado Claude Session Viewer
Servidor FastAPI independente para visualização de sessões do Claude Code
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime
import asyncio

# Configuração da aplicação
app = FastAPI(
    title="Claude Session Viewer API",
    description="""
    ## API dedicada para visualização de sessões do Claude Code
    
    Esta API fornece funcionalidades para:
    
    * **Listar Sessões** - Descobrir todas as sessões disponíveis
    * **Visualizar Conteúdo** - Ver mensagens e histórico completo
    * **Exportar Dados** - Download em JSON ou Markdown
    * **Estatísticas** - Análise de uso e métricas
    
    ### Endpoints principais:
    
    * `GET /api/claude-sessions/` - Lista todas as sessões
    * `GET /api/claude-sessions/{directory}/{session_id}` - Dados da sessão
    * `GET /api/claude-sessions/{directory}/{session_id}/export` - Exportar sessão
    * `GET /api/claude-sessions/stats` - Estatísticas gerais
    """,
    version="1.0.0",
    contact={
        "name": "Claude Session Viewer",
        "email": "viewer@suthub.com"
    }
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3042",  # Frontend do viewer
        "http://localhost:3040",  # Chat principal 
        "http://localhost:3039",
        "http://127.0.0.1:3042",
        "http://127.0.0.1:3040",
        "https://suthub.agentesintegrados.com",
        "http://suthub.agentesintegrados.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Path para sessões do Claude Code
CLAUDE_PROJECTS_PATH = Path("/home/.claude/projects")

# Models Pydantic
class SessionInfo(BaseModel):
    """Informações básicas de uma sessão."""
    session_id: str
    directory: str
    full_path: str
    file_path: str


class SessionData(BaseModel):
    """Dados completos de uma sessão específica."""
    session_id: str
    directory: str
    message_count: int
    messages: List[Dict[str, Any]]
    first_message: Optional[str] = None
    last_message: Optional[str] = None


class SessionsList(BaseModel):
    """Lista de todas as sessões disponíveis."""
    sessions: List[SessionInfo]


# Funções auxiliares
def convert_path_to_directory_name(dir_path: str) -> str:
    """Converte caminho em nome de diretório."""
    return dir_path.replace("/", "-")


async def parse_jsonl_file(file_path: Path) -> List[Dict[str, Any]]:
    """Parse assíncrono de arquivo JSONL."""
    messages = []
    
    try:
        # Leitura assíncrona seria ideal, mas por simplicidade vamos usar síncrona
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        messages.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Erro linha {line_num} em {file_path}: {e}")
                        continue
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session file not found: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file {file_path}: {str(e)}")
    
    return messages


def clean_directory_name(dir_name: str) -> str:
    """Limpa nome do diretório para exibição."""
    # Remove prefixos padrão
    clean = dir_name.replace("-home-suthub--claude-", "").replace("-home-suthub--claude", "root")
    return clean if clean else "root"


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "claude-session-viewer",
        "version": "1.0.0",
        "claude_projects_path": str(CLAUDE_PROJECTS_PATH),
        "path_exists": CLAUDE_PROJECTS_PATH.exists()
    }


# Endpoints do Session Viewer
@app.get("/sessions")
async def list_all_sessions():
    """Lista todas as sessões disponíveis do Claude Code."""
    try:
        if not CLAUDE_PROJECTS_PATH.exists():
            return SessionsList(sessions=[])
        
        sessions = []
        
        # Percorrer todos os diretórios de projetos
        for directory in CLAUDE_PROJECTS_PATH.iterdir():
            if directory.is_dir():
                # Buscar arquivos .jsonl (sessões)
                jsonl_files = list(directory.glob("*.jsonl"))
                
                for file_path in jsonl_files:
                    session_id = file_path.stem
                    clean_dir = clean_directory_name(directory.name)
                    
                    sessions.append(SessionInfo(
                        session_id=session_id,
                        directory=clean_dir,
                        full_path=directory.name,
                        file_path=str(file_path)
                    ))
        
        # Ordenar por diretório e depois por session_id
        sessions.sort(key=lambda x: (x.directory, x.session_id))
        
        return SessionsList(sessions=sessions)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@app.get(
    "/api/claude-sessions/{directory}/{session_id}",
    response_model=SessionData,
    summary="Obter dados de uma sessão",
    description="Retorna todos os dados e mensagens de uma sessão específica."
)
async def get_session_data(directory: str, session_id: str):
    """Retorna dados completos de uma sessão específica."""
    try:
        # Construir caminho completo do diretório
        if directory == "root":
            full_dir_name = "-home-suthub--claude"
        else:
            full_dir_name = f"-home-suthub--claude-{directory.replace('/', '-')}"
        
        file_path = CLAUDE_PROJECTS_PATH / full_dir_name / f"{session_id}.jsonl"
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Session not found: {directory}/{session_id}"
            )
        
        # Fazer parse das mensagens
        messages = await parse_jsonl_file(file_path)
        
        # Processar mensagens para formato padronizado
        processed_messages = []
        for msg in messages:
            # Extrair dados padronizados
            message_data = msg.get("message", {})
            content = message_data.get("content", msg.get("message", ""))
            
            processed_msg = {
                "uuid": msg.get("uuid", ""),
                "timestamp": msg.get("timestamp", ""),
                "type": msg.get("type", ""),
                "role": message_data.get("role", msg.get("type", "")),
                "content": content,
                "cwd": msg.get("cwd", ""),
                "git_branch": msg.get("gitBranch", ""),
                "parent_uuid": msg.get("parentUuid")
            }
            processed_messages.append(processed_msg)
        
        # Timestamps da primeira e última mensagem
        first_message = messages[0].get("timestamp") if messages else None
        last_message = messages[-1].get("timestamp") if messages else None
        
        return SessionData(
            session_id=session_id,
            directory=directory,
            message_count=len(messages),
            messages=processed_messages,
            first_message=first_message,
            last_message=last_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read session: {str(e)}")


@app.get(
    "/api/claude-sessions/{directory}/{session_id}/export",
    summary="Exportar sessão",
    description="Exporta uma sessão em formato JSON ou Markdown para download."
)
async def export_session(directory: str, session_id: str, format: str = "json"):
    """Exporta uma sessão em formato JSON ou Markdown."""
    try:
        # Obter dados da sessão
        session_data = await get_session_data(directory, session_id)
        
        if format.lower() == "markdown":
            # Gerar conteúdo Markdown
            content = f"# Claude Session: {session_id}\n\n"
            content += f"**Directory:** {directory}\n"
            content += f"**Messages:** {session_data.message_count}\n"
            
            if session_data.first_message:
                try:
                    dt = datetime.fromisoformat(session_data.first_message.replace('Z', '+00:00'))
                    content += f"**Date:** {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                except:
                    content += f"**Date:** {session_data.first_message}\n"
            
            content += "\n---\n\n"
            
            # Processar mensagens
            for msg in session_data.messages:
                role = msg.get("role", "").title()
                msg_content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                
                if role and msg_content:
                    content += f"## {role}\n"
                    
                    # Tratar conteúdo complexo (arrays de objetos)
                    if isinstance(msg_content, list):
                        text_parts = []
                        for item in msg_content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                        msg_content = "\n".join(text_parts)
                    
                    content += f"{msg_content}\n\n"
                    
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            content += f"*{dt.strftime('%H:%M:%S')}*\n\n"
                        except:
                            content += f"*{timestamp}*\n\n"
                    
                    content += "---\n\n"
            
            # Retornar como download
            return StreamingResponse(
                iter([content.encode('utf-8')]),
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename=session-{session_id}.md"}
            )
        
        else:  # JSON format
            # Retornar dados JSON
            json_content = json.dumps(session_data.dict(), indent=2, ensure_ascii=False)
            return StreamingResponse(
                iter([json_content.encode('utf-8')]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=session-{session_id}.json"}
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export session: {str(e)}")


@app.get(
    "/api/claude-sessions/stats",
    summary="Estatísticas gerais",
    description="Retorna estatísticas gerais sobre as sessões disponíveis."
)
async def get_sessions_stats():
    """Retorna estatísticas gerais das sessões."""
    try:
        sessions_list = await list_all_sessions()
        sessions = sessions_list.sessions
        
        # Agrupar por diretório
        by_directory = {}
        total_sessions = len(sessions)
        
        for session in sessions:
            dir_name = session.directory
            if dir_name not in by_directory:
                by_directory[dir_name] = 0
            by_directory[dir_name] += 1
        
        return {
            "total_sessions": total_sessions,
            "directories": len(by_directory),
            "sessions_by_directory": by_directory,
            "claude_projects_path": str(CLAUDE_PROJECTS_PATH)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3041, reload=False)