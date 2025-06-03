#!/usr/bin/env python3
import sys
import yaml
import json
from pathlib import Path

def read_wizard_temp_file(session_id):
    temp_file = Path(f"wizard-temp/{session_id}.yml")
    
    if not temp_file.exists():
        print(f"❌ Arquivo temporário não encontrado: {temp_file}")
        sys.exit(1)
    
    try:
        with open(temp_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'dados_basicos' not in data:
            print(f"❌ Estrutura inválida no arquivo temporário")
            sys.exit(1)
        
        dados = data['dados_basicos']
        
        # Validar campos obrigatórios
        required_fields = ['ambiente', 'email', 'host', 'database', 'region', 'port', 'engine']
        for field in required_fields:
            if field not in dados or not dados[field]:
                print(f"❌ Campo obrigatório ausente: {field}")
                sys.exit(1)
        
        # Retornar dados como JSON environment variables
        print(f"AMBIENTE={dados['ambiente']}")
        print(f"EMAIL={dados['email']}")
        print(f"HOST={dados['host']}")
        print(f"DATABASE={dados['database']}")
        print(f"REGION={dados['region']}")
        print(f"PORT={dados['port']}")
        print(f"ENGINE={dados['engine']}")
        
        if 'timestamp' in dados:
            print(f"TIMESTAMP={dados['timestamp']}")
        
        return dados
        
    except yaml.YAMLError as e:
        print(f"❌ Erro ao ler arquivo YAML: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("❌ Uso: python3 read_wizard_temp.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    
    # Validar formato do session_id
    if not session_id.startswith(('mysql-wizard-', 'postgres-wizard-')):
        print("❌ Session ID deve começar com 'mysql-wizard-' ou 'postgres-wizard-'")
        sys.exit(1)
    
    read_wizard_temp_file(session_id)

if __name__ == "__main__":
    main() 