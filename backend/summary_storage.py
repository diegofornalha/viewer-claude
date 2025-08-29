#!/usr/bin/env python3
"""
Sistema de Armazenamento de Resumos
Gerencia CRUD de resumos gerados por sessão
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Path para armazenar resumos
SUMMARIES_PATH = Path("/home/suthub/.claude/summaries")

class SummaryStorage:
    """Gerenciador de armazenamento de resumos"""
    
    def __init__(self):
        # Garantir que diretório existe
        SUMMARIES_PATH.mkdir(parents=True, exist_ok=True)
        
    def _get_session_summary_path(self, directory: str, session_id: str) -> Path:
        """Gera path para arquivos de resumo de uma sessão específica"""
        return SUMMARIES_PATH / directory / f"{session_id}_summaries.json"
    
    def _generate_summary_id(self, session_id: str, summary_type: str, timestamp: str, custom_prompt: str = "") -> str:
        """Gera ID único para um resumo"""
        content = f"{session_id}:{summary_type}:{timestamp}:{custom_prompt}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def save_summary(self, directory: str, session_id: str, summary_data: Dict[str, Any]) -> str:
        """
        Salva um resumo gerado
        
        Returns:
            ID único do resumo salvo
        """
        try:
            # Path do arquivo de resumos da sessão
            summary_file = self._get_session_summary_path(directory, session_id)
            summary_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Carregar resumos existentes
            existing_summaries = []
            if summary_file.exists():
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        existing_summaries = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_summaries = []
            
            # Criar registro do novo resumo
            timestamp = datetime.now().isoformat()
            summary_id = self._generate_summary_id(
                session_id, 
                summary_data.get('type', 'conciso'), 
                timestamp,
                summary_data.get('custom_prompt', '')
            )
            
            new_summary = {
                "id": summary_id,
                "session_id": session_id,
                "directory": directory,
                "timestamp": timestamp,
                "summary_type": summary_data.get('type', 'conciso'),
                "summary_content": summary_data.get('summary', ''),
                "custom_prompt": summary_data.get('custom_prompt', ''),
                "metrics": summary_data.get('metrics', {}),
                "session_metadata": summary_data.get('session_metadata', {}),
                "conversation_length": summary_data.get('conversation_length', 0),
                "generated_at": summary_data.get('generated_at', timestamp)
            }
            
            # Adicionar à lista
            existing_summaries.append(new_summary)
            
            # Manter apenas os últimos 20 resumos por sessão
            existing_summaries = existing_summaries[-20:]
            
            # Salvar arquivo
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(existing_summaries, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Resumo salvo: {summary_id} para {directory}/{session_id}")
            return summary_id
            
        except Exception as e:
            logger.error(f"Erro ao salvar resumo: {str(e)}")
            raise
    
    def get_summaries_for_session(self, directory: str, session_id: str) -> List[Dict[str, Any]]:
        """Retorna todos os resumos de uma sessão específica"""
        try:
            summary_file = self._get_session_summary_path(directory, session_id)
            
            if not summary_file.exists():
                return []
            
            with open(summary_file, 'r', encoding='utf-8') as f:
                summaries = json.load(f)
            
            # Ordenar por timestamp (mais recente primeiro)
            summaries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Erro ao carregar resumos para {directory}/{session_id}: {str(e)}")
            return []
    
    def get_summary_by_id(self, summary_id: str) -> Optional[Dict[str, Any]]:
        """Retorna um resumo específico pelo ID"""
        try:
            # Buscar em todos os arquivos (pode ser otimizado com índice)
            for summary_file in SUMMARIES_PATH.rglob("*_summaries.json"):
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summaries = json.load(f)
                    
                    for summary in summaries:
                        if summary.get('id') == summary_id:
                            return summary
                            
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo {summary_id}: {str(e)}")
            return None
    
    def delete_summary(self, directory: str, session_id: str, summary_id: str) -> bool:
        """Remove um resumo específico"""
        try:
            summary_file = self._get_session_summary_path(directory, session_id)
            
            if not summary_file.exists():
                return False
            
            with open(summary_file, 'r', encoding='utf-8') as f:
                summaries = json.load(f)
            
            # Filtrar resumo a ser removido
            updated_summaries = [s for s in summaries if s.get('id') != summary_id]
            
            if len(updated_summaries) == len(summaries):
                return False  # ID não encontrado
            
            # Salvar arquivo atualizado
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(updated_summaries, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Resumo {summary_id} removido de {directory}/{session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar resumo {summary_id}: {str(e)}")
            return False
    
    def get_all_summaries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna todos os resumos do sistema ordenados por timestamp"""
        try:
            all_summaries = []
            
            # Buscar em todos os arquivos
            for summary_file in SUMMARIES_PATH.rglob("*_summaries.json"):
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summaries = json.load(f)
                        all_summaries.extend(summaries)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
            
            # Ordenar por timestamp (mais recente primeiro)
            all_summaries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return all_summaries[:limit]
            
        except Exception as e:
            logger.error(f"Erro ao carregar todos os resumos: {str(e)}")
            return []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do armazenamento"""
        try:
            total_summaries = 0
            total_sessions = 0
            
            for summary_file in SUMMARIES_PATH.rglob("*_summaries.json"):
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summaries = json.load(f)
                        total_summaries += len(summaries)
                        total_sessions += 1
                except:
                    continue
            
            return {
                "total_summaries": total_summaries,
                "total_sessions": total_sessions,
                "storage_path": str(SUMMARIES_PATH)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {"error": str(e)}

# Instância global
summary_storage = SummaryStorage()

def get_summary_storage() -> SummaryStorage:
    """Retorna instância global do storage"""
    return summary_storage