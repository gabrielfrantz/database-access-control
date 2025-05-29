#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para validar segurança das credenciais nos workflows
"""

import re
import sys
import os
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

def validar_mascaramento_workflows():
    """Validar se os workflows estão mascarando credenciais corretamente"""
    
    workflows_dir = Path(".github/workflows")
    problemas = []
    
    if not workflows_dir.exists():
        print(f"[WARN] Diretório {workflows_dir} não encontrado")
        return problemas
    
    for workflow_file in workflows_dir.glob("*.yml"):
        print(f"[INFO] Analisando {workflow_file.name}...")
        
        try:
            content = workflow_file.read_text(encoding='utf-8')
            
            # Verificar se há mascaramento após extração de credenciais
            if "Parameter.Value" in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    # Procurar linhas que extraem credenciais
                    if 'cut -d' in line and ('user=' in line or 'pass=' in line):
                        # Verificar se as próximas 10 linhas contêm mascaramento
                        next_lines = lines[i+1:i+11]
                        has_mask_user = any('::add-mask::$user' in next_line for next_line in next_lines)
                        has_mask_pass = any('::add-mask::$pass' in next_line for next_line in next_lines)
                        
                        # Só reportar problema se não houver mascaramento para ambos
                        if 'user=' in line and not has_mask_user:
                            problemas.append(f"{workflow_file.name}: Credencial user extraída sem mascaramento imediato na linha {i+1}")
                        if 'pass=' in line and not has_mask_pass:
                            problemas.append(f"{workflow_file.name}: Credencial pass extraída sem mascaramento imediato na linha {i+1}")
            
            # Verificar uso de export com credenciais (ignorar comentários)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                # Ignorar comentários
                if line.strip().startswith('#'):
                    continue
                if 'export DB_USER' in line or 'export DB_PASS' in line:
                    problemas.append(f"{workflow_file.name}: Uso de 'export' com credenciais na linha {i+1}")
            
            # Verificar se credenciais são passadas como argumentos (mais específico)
            if 'python' in content and ('$DB_USER' in content or '$DB_PASS' in content):
                # Verificar se é passagem via argumentos diretos
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'python' in line and ('$DB_USER' in line or '$DB_PASS' in line):
                        # Verificar se não está usando 'env' (que é seguro)
                        if 'env ' not in line and 'env:' not in line:
                            # Verificar contexto para env: em seção YAML
                            context_lines = lines[max(0, i-5):i+5]
                            context = '\n'.join(context_lines)
                            if 'env:' not in context:
                                problemas.append(f"{workflow_file.name}: Credenciais passadas como argumentos na linha {i+1}")
        
        except Exception as e:
            print(f"[ERROR] Erro ao analisar {workflow_file.name}: {e}")
    
    return problemas

def validar_scripts_python():
    """Validar se os scripts Python estão recebendo credenciais de forma segura"""
    
    scripts_dir = Path("scripts")
    problemas = []
    
    if not scripts_dir.exists():
        print(f"[WARN] Diretório {scripts_dir} não encontrado")
        return problemas
    
    target_scripts = ['apply_permissions.py', 'revoke_permissions.py', 'merge_permissions.py']
    
    for script_name in target_scripts:
        script_file = scripts_dir / script_name
        
        if not script_file.exists():
            print(f"[WARN] Script {script_name} não encontrado")
            continue
            
        print(f"[INFO] Analisando {script_name}...")
        
        try:
            content = script_file.read_text(encoding='utf-8')
            
            # Verificar se usa os.environ para credenciais
            uses_environ = False
            
            if script_name == 'merge_permissions.py':
                # Para merge_permissions, verificar INPUT_* vars
                if 'os.environ' in content and 'INPUT_' in content:
                    uses_environ = True
            else:
                # Para apply e revoke, verificar DB_USER/DB_PASS
                if 'os.environ' in content and ('DB_USER' in content or 'DB_PASS' in content):
                    uses_environ = True
            
            if not uses_environ:
                problemas.append(f"{script_name}: Não usa os.environ para credenciais")
            
            # Verificar se há logging de credenciais REAIS (mais específico)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if any(keyword in line.lower() for keyword in ['print', 'log', 'logger']):
                    # Verificar se loga variáveis que podem conter credenciais REAIS
                    dangerous_patterns = [
                        r'logger\..*\$?\{?user\}?',  # logger com variável user
                        r'logger\..*\$?\{?password\}?',  # logger com variável password
                        r'print.*\$?\{?user\}?',  # print com variável user
                        r'print.*\$?\{?password\}?',  # print com variável password
                        r'logger\..*DB_USER',  # logger com DB_USER
                        r'logger\..*DB_PASS',  # logger com DB_PASS
                    ]
                    
                    # Padrões seguros que NÃO devem ser reportados
                    safe_patterns = [
                        'target_user',  # usuário alvo (não é credencial)
                        'username',     # nome de usuário (não é credencial)
                        'Usuário:',     # log de informação
                        'User:',        # log de informação
                        'Criando/verificando usuário',  # log seguro
                        'Processando',  # logs de processamento
                        'Aplicada permissão',  # logs de resultado
                        'Schema:',      # logs de schema
                        'Engine=',      # logs de configuração
                        'Banco:',       # logs de banco
                        'Porta:',       # logs de porta
                        'Host:',        # logs de host (sem credenciais)
                    ]
                    
                    # Verificar se é um padrão perigoso
                    is_dangerous = any(re.search(pattern, line, re.IGNORECASE) for pattern in dangerous_patterns)
                    
                    # Verificar se é um padrão seguro
                    is_safe = any(safe in line for safe in safe_patterns)
                    
                    # Só reportar se for perigoso E não for seguro
                    if is_dangerous and not is_safe:
                        problemas.append(f"{script_name}: Possível logging de credenciais na linha {i+1}")
            
            # Verificar credenciais hardcoded
            hardcoded_patterns = [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'user\s*=\s*["\'][^"\']+["\']',
                r'DB_PASS\s*=\s*["\'][^"\']+["\']',
                r'DB_USER\s*=\s*["\'][^"\']+["\']'
            ]
            
            for pattern in hardcoded_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Verificar contexto - se está próximo de os.environ, é seguro
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    context = content[start:end]
                    
                    if 'os.environ' not in context:
                        problemas.append(f"{script_name}: Possível credencial hardcoded")
                        break
        
        except Exception as e:
            print(f"[ERROR] Erro ao analisar {script_name}: {e}")
    
    return problemas

def main():
    """Função principal"""
    print("Validando segurança das credenciais...")
    print("=" * 50)
    
    try:
        problemas_workflows = validar_mascaramento_workflows()
        problemas_scripts = validar_scripts_python()
        
        todos_problemas = problemas_workflows + problemas_scripts
        
        if todos_problemas:
            print("[FAIL] Problemas de segurança encontrados:")
            for problema in todos_problemas:
                print(f"  - {problema}")
            return 1
        else:
            print("[PASS] Nenhum problema de segurança encontrado!")
            return 0
    
    except Exception as e:
        print(f"[ERROR] Erro durante validação: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
