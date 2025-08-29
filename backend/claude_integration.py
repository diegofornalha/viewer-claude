#!/usr/bin/env python3
"""
Claude SDK Integration for Session Viewer
Módulo de integração com Claude Code SDK para funcionalidade de resumo
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Adiciona o Claude SDK ao path
current_dir = Path(__file__).parent
# Buscar o SDK na estrutura correta da API
sdk_path = current_dir.parent.parent / "api" / "claude-code-sdk-python" / "src"
if sdk_path.exists():
    sys.path.insert(0, str(sdk_path))
    print(f"✅ Claude SDK encontrado em: {sdk_path}")
else:
    print(f"⚠️  Claude SDK não encontrado em: {sdk_path}")
    # Tentar path alternativo
    alt_sdk_path = Path("/home/suthub/.claude/cc-sdk-chat/api/claude-code-sdk-python/src")
    if alt_sdk_path.exists():
        sys.path.insert(0, str(alt_sdk_path))
        print(f"✅ Claude SDK encontrado em path alternativo: {alt_sdk_path}")
    else:
        print(f"❌ Claude SDK não encontrado em nenhum path conhecido")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeViewer:
    """Cliente Claude integrado para o Session Viewer"""
    
    def __init__(self):
        self.client = None
        self._initialized = False
    
    def _initialize_sdk(self):
        """Inicializa o Claude SDK se ainda não foi inicializado"""
        if self._initialized:
            return True
            
        try:
            # Importar usando subprocess para evitar problemas de path
            import subprocess
            import sys
            
            # Path para o wrapper CLI do Claude
            claude_cli_path = "/home/suthub/.claude/cc-sdk-chat/api/claude-code-sdk-python/wrappers_cli/claude"
            
            # Testar se o CLI funciona
            result = subprocess.run([claude_cli_path, "--help"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self._claude_cli_path = claude_cli_path
                logger.info("Claude CLI inicializado com sucesso")
            else:
                raise Exception(f"Claude CLI retornou código {result.returncode}: {result.stderr}")
            
            # Método alternativo - executar Python diretamente no módulo SDK
            sdk_module_path = "/home/suthub/.claude/cc-sdk-chat/api/claude-code-sdk-python"
            self._sdk_module_path = sdk_module_path
            
            self._initialized = True
            logger.info("Claude SDK inicializado com sucesso")
            return True
            
        except ImportError as e:
            logger.error(f"Erro ao importar Claude SDK: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado na inicialização: {e}")
            return False
    
    async def generate_summary(self, conversation_text: str, summary_type: str = "conciso") -> Dict[str, Any]:
        """
        Gera resumo de uma conversa usando Claude SDK
        
        Args:
            conversation_text: Texto da conversa completa
            summary_type: Tipo de resumo ("conciso", "detalhado", "bullet_points")
            
        Returns:
            Dict com resumo e métricas
        """
        if not self._initialize_sdk():
            return {
                "success": False,
                "error": "Claude SDK não pôde ser inicializado",
                "summary": ""
            }
        
        try:
            # Cria prompt baseado no tipo de resumo
            prompt = self._create_summary_prompt(conversation_text, summary_type)
            
            logger.info(f"Gerando resumo tipo: {summary_type}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Executa query usando subprocess para evitar problemas de imports
            import subprocess
            import tempfile
            import json
            
            # Executar Claude SDK via subprocess passando prompt diretamente
            cmd = ["python3", "-m", "src", prompt]
            
            # Executar no diretório do SDK
            result = subprocess.run(
                cmd,
                cwd=self._sdk_module_path,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, 'PYTHONPATH': self._sdk_module_path}
            )
            
            if result.returncode == 0:
                raw_output = result.stdout.strip()
                
                # Extrair apenas a resposta do Claude, removendo header e metadata
                lines = raw_output.split('\n')
                
                # Encontrar onde começa a resposta real do Claude
                claude_response_start = -1
                for i, line in enumerate(lines):
                    if "📝 Claude:" in line and i > 0:
                        claude_response_start = i + 1
                        break
                
                if claude_response_start > 0:
                    # Pegar tudo após "📝 Claude:" até antes das métricas
                    response_lines = []
                    for i in range(claude_response_start, len(lines)):
                        line = lines[i]
                        # Parar quando encontrar métricas
                        if line.startswith("📊 Tokens:") or line.startswith("💰 Custo:"):
                            break
                        response_lines.append(line)
                    
                    summary_content = '\n'.join(response_lines).strip()
                    
                    # Se não conseguiu extrair resposta limpa, usar fallback
                    if not summary_content or len(summary_content) < 50:
                        # Buscar por padrões alternativos
                        for line in lines:
                            if "**Contexto**:" in line:
                                # Encontrou início do resumo estruturado
                                idx = lines.index(line)
                                summary_lines = lines[idx:]
                                # Parar nas métricas
                                clean_lines = []
                                for sline in summary_lines:
                                    if sline.startswith("📊 Tokens:") or sline.startswith("💰 Custo:"):
                                        break
                                    clean_lines.append(sline)
                                summary_content = '\n'.join(clean_lines).strip()
                                break
                else:
                    # Fallback: usar output completo se não conseguir extrair
                    summary_content = raw_output
                
                # Métricas básicas (estimativas melhoradas)
                input_tokens = len(prompt) // 4  # Estimativa: ~4 chars por token
                output_tokens = len(summary_content) // 4
                cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)  # Estimativa Claude
                
                logger.info(f"Resumo extraído: {len(summary_content)} chars (de {len(raw_output)} total)")
            else:
                raise Exception(f"Claude SDK erro (código {result.returncode}): {result.stderr}")
            
            logger.info(f"Resumo gerado com sucesso - {len(summary_content)} chars")
            
            return {
                "success": True,
                "summary": summary_content.strip(),
                "type": summary_type,
                "metrics": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": cost,
                    "summary_length": len(summary_content)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "summary": ""
            }
    
    def _create_summary_prompt(self, conversation_text: str, summary_type: str) -> str:
        """Cria prompt otimizado baseado no tipo de resumo"""
        
        base_instruction = """Analise esta conversa do Claude Code e crie um resumo estruturado em português brasileiro."""
        
        if summary_type == "conciso":
            format_instruction = """
Formato CONCISO (máximo 20 palavras apenas):
📋 **Contexto**: [tipo de projeto/problema]
🎯 **Objetivo**: [o que foi solicitado]
✅ **Resultado**: [o que foi implementado/resolvido]
🔧 **Tecnologias**: [principais ferramentas]

Resumo ultra-conciso em 20 palavras:"""
            
        elif summary_type == "detalhado":
            format_instruction = """
Formato DETALHADO (máximo 400 palavras):
📋 **Contexto Completo**: [situação e background do projeto]
🎯 **Objetivos**: [todos os goals e requisitos discutidos]
⚙️ **Implementação**: [detalhes técnicos, arquitetura, decisões]
✅ **Resultados**: [tudo que foi entregue e funcionalidades]
🔧 **Tecnologias**: [stack completo utilizado]
💡 **Insights**: [aprendizados e decisões importantes]
🔄 **Próximos Passos**: [se mencionados na conversa]

Resumo detalhado:"""
            
        elif summary_type == "bullet_points":
            format_instruction = """
Formato BULLET POINTS:
📋 **Contexto**:
   • [ponto 1]
   • [ponto 2]

🎯 **Objetivos**:
   • [objetivo 1]
   • [objetivo 2]

✅ **Implementações**:
   • [implementação 1]
   • [implementação 2]

🔧 **Tecnologias**:
   • [tech 1]
   • [tech 2]

Lista estruturada:"""
        
        else:
            # Default para conciso
            format_instruction = """
Formato (máximo 200 palavras):
📋 **Contexto**: [projeto/problema]
🎯 **Objetivo**: [solicitação]
✅ **Resultado**: [implementação]

Resumo:"""
        
        # Limita o tamanho da conversa para evitar tokens excessivos
        max_conv_length = 8000  # ~8k chars para deixar espaço para o prompt
        if len(conversation_text) > max_conv_length:
            conversation_text = conversation_text[-max_conv_length:]
            conversation_text = "[...conversa truncada para mostrar as partes mais recentes...]\n" + conversation_text
        
        prompt = f"""{base_instruction}

{format_instruction}

Conversa para análise:
{conversation_text}
"""
        
        return prompt
    
    def test_connection(self) -> Dict[str, Any]:
        """Testa a conexão com Claude SDK"""
        try:
            if not self._initialize_sdk():
                return {
                    "success": False,
                    "error": "Falha na inicialização do SDK"
                }
            
            # Teste simples de funcionalidade
            return {
                "success": True,
                "message": "Claude SDK conectado e funcional",
                "sdk_available": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro no teste: {str(e)}",
                "sdk_available": False
            }

# Instância global do cliente
claude_viewer = ClaudeViewer()

def get_claude_viewer() -> ClaudeViewer:
    """Retorna instância global do cliente Claude"""
    return claude_viewer