#!/usr/bin/env python3
"""
Script de Merge de Permissões - Database Access Control
Processa e combina permissões de usuários em arquivos YAML
"""

import sys
import yaml
import json
import os
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_input_arguments():
    """Valida os argumentos de entrada do script."""
    if len(sys.argv) != 3:
        logger.error("❌ Uso: python merge_permissions.py <caminho_arquivo.yml> <json_permissoes>")
        sys.exit(1)

def validate_permissions_json(json_string):
    """Valida o JSON de permissões (formato simples ou granular)."""
    try:
        permissions_data = json.loads(json_string)
        
        if not isinstance(permissions_data, list):
            raise ValueError("JSON deve ser uma lista de objetos")
        
        for i, item in enumerate(permissions_data):
            if not isinstance(item, dict):
                raise ValueError(f"Item {i+1} deve ser um objeto")
            
            if "nome" not in item:
                raise ValueError(f"Item {i+1}: campo 'nome' é obrigatório")
            
            # Verificar se é formato granular ou simples
            if "tipo" in item and item["tipo"] == "granular":
                # Formato granular - validar tabelas
                if "tabelas" not in item:
                    raise ValueError(f"Item {i+1}: formato granular requer campo 'tabelas'")
                
                if not isinstance(item["tabelas"], list):
                    raise ValueError(f"Item {i+1}: 'tabelas' deve ser uma lista")
                
                for j, table in enumerate(item["tabelas"]):
                    if not isinstance(table, dict):
                        raise ValueError(f"Item {i+1}, tabela {j+1}: deve ser um objeto")
                    
                    if "nome" not in table:
                        raise ValueError(f"Item {i+1}, tabela {j+1}: campo 'nome' é obrigatório")
                    
                    if "permissions" not in table:
                        raise ValueError(f"Item {i+1}, tabela {j+1}: campo 'permissions' é obrigatório")
                    
                    if not isinstance(table["permissions"], list):
                        raise ValueError(f"Item {i+1}, tabela {j+1}: 'permissions' deve ser uma lista")
                    
                    if not table["permissions"]:
                        raise ValueError(f"Item {i+1}, tabela {j+1}: pelo menos uma permissão deve ser especificada")
            else:
                # Formato simples - validar permissions
                if "permissions" not in item:
                    raise ValueError(f"Item {i+1}: campo 'permissions' é obrigatório")
                
                if not isinstance(item["permissions"], list):
                    raise ValueError(f"Item {i+1}: 'permissions' deve ser uma lista")
                
                if not item["permissions"]:
                    raise ValueError(f"Item {i+1}: pelo menos uma permissão deve ser especificada")
        
        return permissions_data
        
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido: {e}")

def validate_environment_variables():
    """Valida se as variáveis de ambiente necessárias estão definidas."""
    required_variables = ["INPUT_HOST", "INPUT_EMAIL", "INPUT_DATABASE", "INPUT_ENGINE", "INPUT_REGION", "INPUT_PORT"]
    
    for var in required_variables:
        if not os.environ.get(var):
            raise ValueError(f"Variável de ambiente obrigatória não definida: {var}")

def create_initial_data():
    """Cria estrutura inicial de dados baseada nas variáveis de ambiente."""
    try:
        validate_environment_variables()
        
        return {
            "host": os.environ["INPUT_HOST"],
            "user": os.environ["INPUT_EMAIL"],
            "database": os.environ["INPUT_DATABASE"],
            "engine": os.environ["INPUT_ENGINE"],
            "region": os.environ["INPUT_REGION"],
            "port": int(os.environ["INPUT_PORT"]),
            "schemas": []
        }
    except ValueError as e:
        logger.error(f"❌ Erro na validação de variáveis de ambiente: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao criar dados iniciais: {e}")
        raise

def load_existing_data(file_path):
    """Carrega dados existentes do arquivo YAML."""
    try:
        if os.path.exists(file_path):
            logger.info(f"📂 Carregando arquivo existente: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                if not data:
                    logger.warning("⚠️ Arquivo YAML vazio, criando nova estrutura")
                    return create_initial_data()
                return data
        else:
            logger.info("🆕 Arquivo não existe, criando nova estrutura")
            return create_initial_data()
            
    except yaml.YAMLError as e:
        logger.error(f"❌ Erro ao processar YAML existente: {e}")
        raise ValueError(f"Arquivo YAML inválido: {e}")
    except Exception as e:
        logger.error(f"❌ Erro ao carregar arquivo: {e}")
        raise

def add_or_update_permissions(data, new_permissions):
    """Adiciona ou atualiza permissões nos dados existentes."""
    if "schemas" not in data:
        data["schemas"] = []
    
    existing_schemas = {schema["nome"]: schema for schema in data["schemas"]}
    
    for new_schema in new_permissions:
        schema_name = new_schema["nome"]
        
        if schema_name in existing_schemas:
            # Atualizar schema existente
            existing_schema = existing_schemas[schema_name]
            
            if "tipo" in new_schema and new_schema["tipo"] == "granular":
                # Novo schema é granular
                if "tipo" in existing_schema and existing_schema["tipo"] == "granular":
                    # Ambos granulares - merge tabelas
                    existing_tables = {t["nome"]: t for t in existing_schema.get("tabelas", [])}
                    
                    for new_table in new_schema["tabelas"]:
                        table_name = new_table["nome"]
                        if table_name in existing_tables:
                            # Merge permissões da tabela
                            existing_perms = set(existing_tables[table_name]["permissions"])
                            new_perms = set(new_table["permissions"])
                            existing_tables[table_name]["permissions"] = sorted(list(existing_perms | new_perms))
                            logger.info(f"🔄 Atualizadas permissões da tabela {table_name}")
                        else:
                            # Nova tabela
                            existing_tables[table_name] = new_table
                            logger.info(f"➕ Nova tabela adicionada: {table_name}")
                    
                    existing_schema["tabelas"] = list(existing_tables.values())
                else:
                    # Existente simples, novo granular - substituir
                    existing_schemas[schema_name] = new_schema
                    logger.info(f"🔄 Schema {schema_name} convertido para granular")
            else:
                # Novo schema é simples
                if "tipo" in existing_schema and existing_schema["tipo"] == "granular":
                    # Manter granular
                    logger.warning(f"⚠️ Mantendo formato granular para schema: {schema_name}")
                else:
                    # Ambos simples - merge permissões
                    existing_perms = set(existing_schema.get("permissions", []))
                    new_perms = set(new_schema["permissions"])
                    existing_schema["permissions"] = sorted(list(existing_perms | new_perms))
                    logger.info(f"🔄 Atualizadas permissões do schema {schema_name}")
        else:
            # Novo schema
            existing_schemas[schema_name] = new_schema
            logger.info(f"➕ Novo schema adicionado: {schema_name}")
    
    # Atualizar dados
    data["schemas"] = list(existing_schemas.values())

def remove_specific_permissions(data, permissions_to_remove):
    """Remove permissões específicas dos dados existentes."""
    if "schemas" not in data:
        return
    
    existing_schemas = {schema["nome"]: schema for schema in data["schemas"]}
    
    for schema_to_remove in permissions_to_remove:
        schema_name = schema_to_remove["nome"]
        
        if schema_name in existing_schemas:
            existing_schema = existing_schemas[schema_name]
            
            if "tipo" in schema_to_remove and schema_to_remove["tipo"] == "granular":
                # Remover permissões granulares
                if "tipo" in existing_schema and existing_schema["tipo"] == "granular":
                    existing_tables = {t["nome"]: t for t in existing_schema.get("tabelas", [])}
                    
                    for table_to_remove in schema_to_remove["tabelas"]:
                        table_name = table_to_remove["nome"]
                        if table_name in existing_tables:
                            existing_perms = set(existing_tables[table_name]["permissions"])
                            perms_to_remove = set(table_to_remove["permissions"])
                            remaining_perms = existing_perms - perms_to_remove
                            
                            if remaining_perms:
                                existing_tables[table_name]["permissions"] = sorted(list(remaining_perms))
                                logger.info(f"➖ Removidas permissões da tabela {table_name}")
                            else:
                                del existing_tables[table_name]
                                logger.info(f"🗑️ Tabela {table_name} removida (sem permissões)")
                    
                    if existing_tables:
                        existing_schema["tabelas"] = list(existing_tables.values())
                    else:
                        del existing_schemas[schema_name]
                        logger.info(f"🗑️ Schema {schema_name} removido (sem tabelas)")
            else:
                # Remover permissões simples
                if "tipo" not in existing_schema or existing_schema["tipo"] != "granular":
                    existing_perms = set(existing_schema.get("permissions", []))
                    perms_to_remove = set(schema_to_remove["permissions"])
                    remaining_perms = existing_perms - perms_to_remove
                    
                    if remaining_perms:
                        existing_schema["permissions"] = sorted(list(remaining_perms))
                        logger.info(f"➖ Removidas permissões do schema {schema_name}")
                    else:
                        del existing_schemas[schema_name]
                        logger.info(f"🗑️ Schema {schema_name} removido (sem permissões)")
    
    # Atualizar dados
    data["schemas"] = list(existing_schemas.values())

def process_permissions(data, new_permissions, remove_mode):
    """Processa as permissões (adiciona ou remove)."""
    try:
        if remove_mode:
            logger.info("🗑️ Modo: Remoção de permissões")
            remove_specific_permissions(data, new_permissions)
        else:
            logger.info("➕ Modo: Adição/atualização de permissões")
            add_or_update_permissions(data, new_permissions)
            
        logger.info(f"✅ Processamento concluído. Total de schemas: {len(data.get('schemas', []))}")
        
    except Exception as e:
        logger.error(f"❌ Erro no processamento de permissões: {e}")
        raise

def save_file(file_path, data, remove_mode):
    """Salva o arquivo YAML com criação dinâmica de diretórios."""
    try:
        # Criar diretórios dinamicamente se não existirem
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            logger.info(f"🏗️ Criando estrutura de diretórios: {directory}")
            os.makedirs(directory, exist_ok=True)
        
        # Salvar arquivo YAML
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        if remove_mode:
            logger.info(f"📝 Arquivo atualizado (remoção): {file_path}")
        else:
            logger.info(f"💾 Arquivo salvo/atualizado: {file_path}")
            
    except Exception as e:
        logger.error(f"❌ Erro ao salvar arquivo: {e}")
        raise

def main():
    """Função principal do script."""
    try:
        logger.info("🚀 Iniciando processamento de permissões...")
        
        # Validar argumentos
        validate_input_arguments()
        
        # Obter parâmetros
        file_path = sys.argv[1]
        permissions_json = sys.argv[2]
        
        logger.info(f"📁 Arquivo: {file_path}")
        logger.info(f"📊 JSON: {permissions_json}")
        
        # Validar JSON
        new_permissions = validate_permissions_json(permissions_json)
        
        # Verificar modo de remoção
        remove_mode = os.environ.get("REMOVER_PERMISSOES", "false").lower() == "true"
        
        # Carregar dados existentes ou criar novos
        data = load_existing_data(file_path)
        
        # Processar permissões
        process_permissions(data, new_permissions, remove_mode)
        
        # Salvar arquivo (com criação dinâmica de diretórios)
        save_file(file_path, data, remove_mode)
        
        logger.info("🎉 Processamento concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro no processamento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
