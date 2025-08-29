#!/usr/bin/env python3
"""
Session Summarizer for Claude Viewer
Processamento de sessões .jsonl para geração de resumos inteligentes
"""

import json
import asyncio
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from claude_integration import get_claude_viewer

logger = logging.getLogger(__name__)

CLAUDE_PROJECTS_PATH = Path("/home/suthub/.claude/projects")

class SessionSummarizer:
    """Gerenciador de resumos de sessões Claude"""
    
    def __init__(self):
        self.claude_viewer = get_claude_viewer()
        self.cache = {}  # Cache simples em memória
    
    def _get_cache_key(self, directory: str, session_id: str, summary_type: str) -> str:
        """Gera chave única para cache de resumo"""
        content = f"{directory}:{session_id}:{summary_type}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_session_file(self, directory: str, session_id: str) -> Optional[Dict]:
        """Carrega arquivo .jsonl da sessão"""
        try:
            file_path = CLAUDE_PROJECTS_PATH / directory / f"{session_id}.jsonl"
            
            if not file_path.exists():
                logger.error(f"Arquivo de sessão não encontrado: {file_path}")
                return None
            
            messages = []
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            messages.append(data)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Erro linha {line_num} em {file_path}: {e}")
                            continue
            
            logger.info(f"Sessão carregada: {len(messages)} mensagens de {file_path}")
            return {
                "session_id": session_id,
                "directory": directory,
                "messages": messages,
                "file_path": str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Erro ao carregar sessão {directory}/{session_id}: {e}")
            return None
    
    def _extract_conversation(self, messages: List[Dict]) -> str:
        """Extrai texto limpo da conversa para resumo"""
        conversation_parts = []
        
        for msg in messages:
            try:
                msg_type = msg.get("type", "")
                timestamp = msg.get("timestamp", "")
                
                if msg_type == "user":
                    # Mensagem do usuário
                    message_data = msg.get("message", {})
                    content = message_data.get("content", "")
                    
                    if content:
                        conversation_parts.append(f"👤 Usuário: {content}")
                
                elif msg_type == "assistant":
                    # Resposta do Claude
                    message_data = msg.get("message", {})
                    content = message_data.get("content", [])
                    
                    text_parts = []
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                    elif isinstance(content, str):
                        text_parts.append(content)
                    
                    full_text = "\n".join(text_parts)
                    if full_text.strip():
                        conversation_parts.append(f"🤖 Claude: {full_text}")
                
            except Exception as e:
                logger.warning(f"Erro ao processar mensagem: {e}")
                continue
        
        conversation_text = "\n\n".join(conversation_parts)
        logger.info(f"Conversa extraída: {len(conversation_text)} caracteres")
        return conversation_text
    
    def _get_session_metadata(self, session_data: Dict) -> Dict:
        """Extrai metadados da sessão para incluir no resumo"""
        messages = session_data.get("messages", [])
        
        # Contadores
        user_messages = sum(1 for msg in messages if msg.get("type") == "user")
        assistant_messages = sum(1 for msg in messages if msg.get("type") == "assistant")
        
        # Timestamps
        first_msg = messages[0] if messages else {}
        last_msg = messages[-1] if messages else {}
        
        first_time = first_msg.get("timestamp", "")
        last_time = last_msg.get("timestamp", "")
        
        # Duração estimada
        duration = "N/A"
        if first_time and last_time:
            try:
                first_dt = datetime.fromisoformat(first_time.replace('Z', '+00:00'))
                last_dt = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                duration_delta = last_dt - first_dt
                duration = str(duration_delta).split('.')[0]  # Remove microseconds
            except:
                pass
        
        return {
            "total_messages": len(messages),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "first_message": first_time,
            "last_message": last_time,
            "duration": duration,
            "directory": session_data.get("directory"),
            "session_id": session_data.get("session_id")
        }
    
    async def generate_summary(self, directory: str, session_id: str, 
                             summary_type: str = "conciso") -> Dict[str, Any]:
        """
        Gera resumo completo de uma sessão
        
        Args:
            directory: Nome do diretório da sessão
            session_id: ID único da sessão
            summary_type: Tipo de resumo ("conciso", "detalhado", "bullet_points")
            
        Returns:
            Dict com resumo completo e metadados
        """
        
        logger.info(f"Iniciando resumo: {directory}/{session_id} tipo: {summary_type}")
        
        try:
            # Verifica cache primeiro
            cache_key = self._get_cache_key(directory, session_id, summary_type)
            if cache_key in self.cache:
                logger.info(f"Resumo encontrado em cache: {cache_key}")
                return self.cache[cache_key]
            
            # Carrega dados da sessão
            session_data = self._load_session_file(directory, session_id)
            if not session_data:
                return {
                    "success": False,
                    "error": f"Não foi possível carregar sessão {directory}/{session_id}",
                    "summary": ""
                }
            
            # Extrai conversa para resumo
            conversation_text = self._extract_conversation(session_data["messages"])
            if not conversation_text.strip():
                return {
                    "success": False,
                    "error": "Conversa vazia ou não processável",
                    "summary": ""
                }
            
            # Gera resumo usando Claude
            summary_result = await self.claude_viewer.generate_summary(
                conversation_text, 
                summary_type
            )
            
            if not summary_result.get("success"):
                return summary_result
            
            # Adiciona metadados da sessão
            metadata = self._get_session_metadata(session_data)
            
            # Monta resultado completo
            final_result = {
                "success": True,
                "summary": summary_result["summary"],
                "type": summary_type,
                "session_metadata": metadata,
                "metrics": summary_result.get("metrics", {}),
                "generated_at": datetime.now().isoformat(),
                "conversation_length": len(conversation_text)
            }
            
            # Salva no cache
            self.cache[cache_key] = final_result
            
            logger.info(f"Resumo gerado com sucesso para {directory}/{session_id}")
            return final_result
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}",
                "summary": ""
            }
    
    def clear_cache(self):
        """Limpa cache de resumos"""
        self.cache = {}
        logger.info("Cache de resumos limpo")
    
    def get_cache_stats(self) -> Dict:
        """Retorna estatísticas do cache"""
        return {
            "cached_summaries": len(self.cache),
            "cache_keys": list(self.cache.keys())
        }

    def test_summarizer(self) -> Dict[str, Any]:
        """Testa funcionalidade do summarizer"""
        try:
            # Testa conexão Claude
            claude_test = self.claude_viewer.test_connection()
            
            # Testa acesso aos arquivos .jsonl
            projects_accessible = CLAUDE_PROJECTS_PATH.exists()
            
            # Lista sessões disponíveis para teste
            available_sessions = 0
            if projects_accessible:
                for directory in CLAUDE_PROJECTS_PATH.iterdir():
                    if directory.is_dir():
                        jsonl_files = list(directory.glob("*.jsonl"))
                        available_sessions += len(jsonl_files)
            
            return {
                "success": True,
                "claude_sdk_status": claude_test,
                "projects_path_accessible": projects_accessible,
                "available_sessions": available_sessions,
                "projects_path": str(CLAUDE_PROJECTS_PATH),
                "cache_stats": self.get_cache_stats()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro no teste: {str(e)}"
            }

    async def generate_summary_from_content(self, custom_content: str, 
                                           summary_type: str = "conciso") -> Dict[str, Any]:
        """
        Gera resumo a partir de conteúdo customizado fornecido pelo usuário
        
        Args:
            custom_content: Conteúdo da conversa fornecido diretamente
            summary_type: Tipo de resumo ("conciso", "detalhado", "bullet_points")
            
        Returns:
            Dict com resumo e metadados
        """
        
        logger.info(f"Iniciando resumo customizado: tipo {summary_type}, {len(custom_content)} chars")
        
        try:
            if not custom_content.strip():
                return {
                    "success": False,
                    "error": "Conteúdo customizado vazio",
                    "summary": ""
                }
            
            # Gera resumo usando Claude diretamente com o conteúdo customizado
            summary_result = await self.claude_viewer.generate_summary(
                custom_content, 
                summary_type
            )
            
            if not summary_result.get("success"):
                return summary_result
            
            # Metadados básicos para conteúdo customizado
            custom_metadata = {
                "content_source": "user_edited",
                "content_length": len(custom_content),
                "custom_edit": True,
                "estimated_messages": custom_content.count("👤 Usuário:") + custom_content.count("🤖 Claude:")
            }
            
            # Resultado completo
            complete_result = {
                "success": True,
                "summary": summary_result["summary"],
                "type": summary_type,
                "session_metadata": custom_metadata,
                "metrics": summary_result.get("metrics", {}),
                "generated_at": datetime.now().isoformat(),
                "conversation_length": len(custom_content)
            }
            
            logger.info(f"Resumo customizado concluído: {len(complete_result['summary'])} chars")
            return complete_result
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo customizado: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao processar conteúdo customizado: {str(e)}",
                "summary": ""
            }

# Instância global
session_summarizer = SessionSummarizer()

def get_session_summarizer() -> SessionSummarizer:
    """Retorna instância global do summarizer"""
    return session_summarizer