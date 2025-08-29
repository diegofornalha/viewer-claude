import os
import json
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Claude Session Viewer API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Path para sessões
CLAUDE_PROJECTS_PATH = Path("/home/.claude/projects")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "claude-session-viewer",
        "version": "1.0.0",
        "claude_projects_path": str(CLAUDE_PROJECTS_PATH),
        "path_exists": CLAUDE_PROJECTS_PATH.exists()
    }

@app.get("/sessions")
async def sessions():
    """Lista todas as sessões."""
    try:
        if not CLAUDE_PROJECTS_PATH.exists():
            return {"sessions": []}
        
        sessions = []
        
        for directory in CLAUDE_PROJECTS_PATH.iterdir():
            if directory.is_dir():
                jsonl_files = list(directory.glob("*.jsonl"))
                
                for file_path in jsonl_files:
                    session_id = file_path.stem
                    
                    sessions.append({
                        "session_id": session_id,
                        "directory": directory.name,
                        "file_path": str(file_path)
                    })
        
        return {"sessions": sessions}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/claude-sessions")
async def api_sessions():
    """Compatibilidade com frontend."""
    return await sessions()

@app.get("/api/claude-sessions/stats")
async def stats():
    """Estatísticas básicas."""
    session_data = await sessions()
    return {
        "total_sessions": len(session_data["sessions"]),
        "directories": len(set(s["directory"] for s in session_data["sessions"]))
    }

@app.get("/api/claude-sessions/{directory}/{session_id}")
async def get_session_data(directory: str, session_id: str):
    """Retorna dados completos de uma sessão específica."""
    try:
        file_path = CLAUDE_PROJECTS_PATH / directory / f"{session_id}.jsonl"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Session not found: {directory}/{session_id}")
        
        messages = []
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        messages.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Erro linha {line_num}: {e}")
                        continue
        
        processed_messages = []
        for msg in messages:
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
        
        return {
            "session_id": session_id,
            "directory": directory,
            "message_count": len(messages),
            "messages": processed_messages,
            "first_message": messages[0].get("timestamp") if messages else None,
            "last_message": messages[-1].get("timestamp") if messages else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read session: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3041)