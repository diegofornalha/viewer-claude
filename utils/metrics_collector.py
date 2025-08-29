#!/usr/bin/env python3
"""
Sistema de Coleta de Métricas para Analytics
Baseado no sistema avançado do 8505-viewer
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

class MetricsCollector:
    """Coletor de métricas para analytics do viewer"""
    
    def __init__(self):
        self.metrics_file = Path("/home/suthub/.claude/cc-sdk-chat/viewer-claude/metrics.json")
        self.session_metrics = {}
        self.performance_history = []
        
    def record_summary_generation(self, session_id: str, summary_type: str, 
                                execution_time: float, metrics: Dict, success: bool):
        """Registra métricas de geração de resumo"""
        
        metric_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "summary_type": summary_type,
            "execution_time": execution_time,
            "success": success,
            "metrics": metrics,
            "tokens_total": metrics.get('input_tokens', 0) + metrics.get('output_tokens', 0),
            "cost": metrics.get('cost', 0)
        }
        
        self.performance_history.append(metric_entry)
        
        # Manter apenas últimos 1000 registros
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
        
        # Salvar em arquivo
        self._save_metrics()
    
    def record_session_activity(self, session_id: str, activity_type: str, details: Dict = None):
        """Registra atividade em uma sessão"""
        
        if session_id not in self.session_metrics:
            self.session_metrics[session_id] = {
                "created_at": datetime.now().isoformat(),
                "activities": [],
                "total_summaries": 0,
                "total_cost": 0,
                "last_activity": None
            }
        
        activity = {
            "timestamp": datetime.now().isoformat(),
            "type": activity_type,
            "details": details or {}
        }
        
        self.session_metrics[session_id]["activities"].append(activity)
        self.session_metrics[session_id]["last_activity"] = activity["timestamp"]
        
        if activity_type == "summary_generated":
            self.session_metrics[session_id]["total_summaries"] += 1
            if details and details.get("cost"):
                self.session_metrics[session_id]["total_cost"] += details["cost"]
    
    def get_performance_stats(self, hours: int = 24) -> Dict:
        """Obtém estatísticas de performance das últimas N horas"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.performance_history 
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "total_operations": 0,
                "success_rate": 0,
                "avg_execution_time": 0,
                "total_cost": 0,
                "total_tokens": 0
            }
        
        successful = [m for m in recent_metrics if m["success"]]
        
        return {
            "total_operations": len(recent_metrics),
            "successful_operations": len(successful),
            "success_rate": len(successful) / len(recent_metrics) * 100,
            "avg_execution_time": sum(m["execution_time"] for m in recent_metrics) / len(recent_metrics),
            "total_cost": sum(m["cost"] for m in recent_metrics),
            "total_tokens": sum(m["tokens_total"] for m in recent_metrics),
            "by_type": self._group_by_type(recent_metrics),
            "hourly_breakdown": self._hourly_breakdown(recent_metrics)
        }
    
    def get_session_stats(self) -> Dict:
        """Obtém estatísticas por sessão"""
        
        total_sessions = len(self.session_metrics)
        active_sessions = sum(1 for s in self.session_metrics.values() 
                            if self._is_session_active(s))
        
        total_summaries = sum(s.get("total_summaries", 0) for s in self.session_metrics.values())
        total_cost = sum(s.get("total_cost", 0) for s in self.session_metrics.values())
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_summaries": total_summaries,
            "total_cost": total_cost,
            "avg_summaries_per_session": total_summaries / max(total_sessions, 1),
            "most_active_sessions": self._get_most_active_sessions()
        }
    
    def get_cost_analysis(self) -> Dict:
        """Análise detalhada de custos"""
        
        recent_metrics = self.performance_history[-100:]  # Últimos 100 resumos
        
        if not recent_metrics:
            return {"total_cost": 0, "breakdown": {}}
        
        cost_by_type = {}
        for metric in recent_metrics:
            summary_type = metric["summary_type"]
            cost = metric["cost"]
            
            if summary_type not in cost_by_type:
                cost_by_type[summary_type] = {"total": 0, "count": 0}
            
            cost_by_type[summary_type]["total"] += cost
            cost_by_type[summary_type]["count"] += 1
        
        # Calcular médias
        for type_data in cost_by_type.values():
            type_data["average"] = type_data["total"] / type_data["count"]
        
        total_cost = sum(m["cost"] for m in recent_metrics)
        
        return {
            "total_cost": total_cost,
            "average_cost": total_cost / len(recent_metrics),
            "breakdown_by_type": cost_by_type,
            "most_expensive": max(recent_metrics, key=lambda x: x["cost"], default={}),
            "cheapest": min(recent_metrics, key=lambda x: x["cost"], default={})
        }
    
    def _group_by_type(self, metrics: List[Dict]) -> Dict:
        """Agrupa métricas por tipo de resumo"""
        
        grouped = {}
        for metric in metrics:
            summary_type = metric["summary_type"]
            if summary_type not in grouped:
                grouped[summary_type] = {
                    "count": 0,
                    "success_count": 0,
                    "total_time": 0,
                    "total_cost": 0
                }
            
            grouped[summary_type]["count"] += 1
            if metric["success"]:
                grouped[summary_type]["success_count"] += 1
            grouped[summary_type]["total_time"] += metric["execution_time"]
            grouped[summary_type]["total_cost"] += metric["cost"]
        
        # Calcular médias
        for type_data in grouped.values():
            count = type_data["count"]
            type_data["avg_time"] = type_data["total_time"] / count
            type_data["avg_cost"] = type_data["total_cost"] / count
            type_data["success_rate"] = type_data["success_count"] / count * 100
        
        return grouped
    
    def _hourly_breakdown(self, metrics: List[Dict]) -> Dict:
        """Quebra métricas por hora"""
        
        hourly = {}
        for metric in metrics:
            hour = datetime.fromisoformat(metric["timestamp"]).strftime("%H:00")
            if hour not in hourly:
                hourly[hour] = {"count": 0, "successes": 0}
            
            hourly[hour]["count"] += 1
            if metric["success"]:
                hourly[hour]["successes"] += 1
        
        return hourly
    
    def _is_session_active(self, session: Dict) -> bool:
        """Verifica se sessão está ativa (atividade nas últimas 2 horas)"""
        
        last_activity = session.get("last_activity")
        if not last_activity:
            return False
        
        try:
            last_time = datetime.fromisoformat(last_activity)
            return datetime.now() - last_time < timedelta(hours=2)
        except:
            return False
    
    def _get_most_active_sessions(self, limit: int = 5) -> List[Dict]:
        """Obtém sessões mais ativas"""
        
        sessions_with_activity = [
            {
                "session_id": sid,
                "total_summaries": data.get("total_summaries", 0),
                "total_cost": data.get("total_cost", 0),
                "last_activity": data.get("last_activity")
            }
            for sid, data in self.session_metrics.items()
        ]
        
        # Ordenar por número de resumos
        sessions_with_activity.sort(key=lambda x: x["total_summaries"], reverse=True)
        
        return sessions_with_activity[:limit]
    
    def _save_metrics(self):
        """Salva métricas em arquivo JSON"""
        try:
            data = {
                "performance_history": self.performance_history[-500:],  # Últimos 500
                "session_metrics": self.session_metrics,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Erro ao salvar métricas: {e}")
    
    def load_metrics(self):
        """Carrega métricas salvas"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                
                self.performance_history = data.get("performance_history", [])
                self.session_metrics = data.get("session_metrics", {})
                
                print(f"✅ Métricas carregadas: {len(self.performance_history)} registros")
            else:
                print("📊 Arquivo de métricas não encontrado, iniciando novo")
                
        except Exception as e:
            print(f"❌ Erro ao carregar métricas: {e}")
    
    def export_metrics(self, format_type: str = "json") -> str:
        """Exporta métricas em formato específico"""
        
        stats = self.get_performance_stats(24)
        session_stats = self.get_session_stats()
        cost_analysis = self.get_cost_analysis()
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "performance_stats_24h": stats,
            "session_statistics": session_stats,
            "cost_analysis": cost_analysis,
            "raw_performance_data": self.performance_history[-100:]  # Últimos 100
        }
        
        if format_type == "json":
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            # Formato texto simples
            return f"""
# Relatório de Métricas - {datetime.now().strftime("%d/%m/%Y %H:%M")}

## Performance (24h)
- Total de operações: {stats['total_operations']}
- Taxa de sucesso: {stats['success_rate']:.1f}%
- Tempo médio: {stats['avg_execution_time']:.2f}s
- Custo total: ${stats['total_cost']:.6f}

## Sessões
- Total: {session_stats['total_sessions']}
- Ativas: {session_stats['active_sessions']}
- Resumos gerados: {session_stats['total_summaries']}

## Custos
- Custo total: ${cost_analysis['total_cost']:.6f}
- Custo médio por resumo: ${cost_analysis['average_cost']:.6f}
"""

# Instância global
metrics_collector = MetricsCollector()

def get_metrics_collector():
    """Retorna instância global do coletor de métricas"""
    return metrics_collector