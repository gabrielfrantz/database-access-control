import sys
import yaml
import json
import os
import logging
from pathlib import Path

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validar_entrada():
    """Valida os argumentos de entrada."""
    if len(sys.argv) != 3:
        logger.error("Uso: python merge_permissions.py <caminho_arquivo.yml> <json_permissoes>")
        sys.exit(1)

def validar_json_permissoes(json_string):
    """Valida o JSON de permissões (formato simples ou granular)."""
    try:
        permissoes = json.loads(json_string)
        
        if not isinstance(permissoes, list):
            raise ValueError("JSON deve ser uma lista de objetos")
        
        for i, item in enumerate(permissoes):
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
                
                for j, tabela in enumerate(item["tabelas"]):
                    if not isinstance(tabela, dict):
                        raise ValueError(f"Item {i+1}, tabela {j+1}: deve ser um objeto")
                    
                    if "nome" not in tabela:
                        raise ValueError(f"Item {i+1}, tabela {j+1}: campo 'nome' é obrigatório")
                    
                    if "permissions" not in tabela:
                        raise ValueError(f"Item {i+1}, tabela {j+1}: campo 'permissions' é obrigatório")
                    
                    if not isinstance(tabela["permissions"], list):
                        raise ValueError(f"Item {i+1}, tabela {j+1}: 'permissions' deve ser uma lista")
                    
                    if not tabela["permissions"]:
                        raise ValueError(f"Item {i+1}, tabela {j+1}: pelo menos uma permissão deve ser especificada")
            else:
                # Formato simples - validar permissions
                if "permissions" not in item:
                    raise ValueError(f"Item {i+1}: campo 'permissions' é obrigatório")
                
                if not isinstance(item["permissions"], list):
                    raise ValueError(f"Item {i+1}: 'permissions' deve ser uma lista")
                
                if not item["permissions"]:
                    raise ValueError(f"Item {i+1}: pelo menos uma permissão deve ser especificada")
        
        return permissoes
        
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido: {e}")

def validar_variaveis_ambiente():
    """Valida se as variáveis de ambiente necessárias estão definidas."""
    variaveis_obrigatorias = ["INPUT_HOST", "INPUT_EMAIL", "INPUT_DATABASE", "INPUT_ENGINE", "INPUT_REGION", "INPUT_PORT"]
    
    for var in variaveis_obrigatorias:
        if not os.environ.get(var):
            raise ValueError(f"Variável de ambiente obrigatória não definida: {var}")

def criar_dados_iniciais():
    """Cria estrutura inicial de dados baseada nas variáveis de ambiente."""
    try:
        validar_variaveis_ambiente()
        
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
        logger.error(f"Erro na validação de variáveis de ambiente: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro ao criar dados iniciais: {e}")
        raise

def carregar_dados_existentes(caminho):
    """Carrega dados existentes do arquivo YAML."""
    try:
        if caminho.exists():
            logger.info(f"Carregando arquivo existente: {caminho}")
            with open(caminho, 'r', encoding='utf-8') as arquivo:
                dados = yaml.safe_load(arquivo)
                if not dados:
                    logger.warning("Arquivo YAML vazio, criando nova estrutura")
                    return criar_dados_iniciais()
                return dados
        else:
            logger.info("Arquivo não existe, criando nova estrutura")
            return criar_dados_iniciais()
            
    except yaml.YAMLError as e:
        logger.error(f"Erro ao processar YAML existente: {e}")
        raise ValueError(f"Arquivo YAML inválido: {e}")
    except Exception as e:
        logger.error(f"Erro ao carregar arquivo: {e}")
        raise

def normalizar_schema_existente(schema):
    """Normaliza schema existente para formato padrão de comparação."""
    if "tipo" in schema and schema["tipo"] == "granular":
        # Já está no formato granular
        return schema
    else:
        # Converter formato simples para granular para processamento uniforme
        return {
            "nome": schema["nome"],
            "tipo": "simples",
            "permissions": schema["permissions"]
        }

def processar_permissoes(dados, novas_permissoes, remover_modo):
    """Processa as permissões (adicionar ou remover) - suporta formato granular."""
    schemas_existentes = {}
    
    # Normalizar schemas existentes
    for schema in dados.get("schemas", []):
        nome = schema["nome"]
        schemas_existentes[nome] = normalizar_schema_existente(schema)
    
    for item in novas_permissoes:
        nome_schema = item["nome"]
        logger.info(f"Processando schema: {nome_schema}")
        
        # Verificar se é granular ou simples
        if "tipo" in item and item["tipo"] == "granular":
            # Formato granular
            if nome_schema in schemas_existentes:
                schema_existente = schemas_existentes[nome_schema]
                
                if remover_modo:
                    # Remover permissões granulares
                    if schema_existente.get("tipo") == "granular":
                        # Ambos granulares - remover tabelas específicas
                        tabelas_existentes = {t["nome"]: set(t["permissions"]) for t in schema_existente.get("tabelas", [])}
                        
                        for nova_tabela in item["tabelas"]:
                            nome_tabela = nova_tabela["nome"]
                            perms_remover = set(nova_tabela["permissions"])
                            
                            if nome_tabela in tabelas_existentes:
                                tabelas_existentes[nome_tabela] -= perms_remover
                                logger.info(f"Removidas permissões {', '.join(perms_remover)} da tabela {nome_tabela}")
                                
                                if not tabelas_existentes[nome_tabela]:
                                    del tabelas_existentes[nome_tabela]
                                    logger.info(f"Tabela {nome_tabela} removida (sem permissões)")
                        
                        if tabelas_existentes:
                            schemas_existentes[nome_schema] = {
                                "nome": nome_schema,
                                "tipo": "granular",
                                "tabelas": [
                                    {"nome": nome, "permissions": sorted(list(perms))}
                                    for nome, perms in tabelas_existentes.items()
                                ]
                            }
                        else:
                            del schemas_existentes[nome_schema]
                            logger.info(f"Schema {nome_schema} removido (sem tabelas)")
                    else:
                        # Existente simples, novo granular - não faz sentido remover
                        logger.warning(f"Tentativa de remoção granular em schema simples: {nome_schema}")
                else:
                    # Adicionar/atualizar permissões granulares
                    if schema_existente.get("tipo") == "granular":
                        # Ambos granulares - merge de tabelas
                        tabelas_existentes = {t["nome"]: set(t["permissions"]) for t in schema_existente.get("tabelas", [])}
                        
                        for nova_tabela in item["tabelas"]:
                            nome_tabela = nova_tabela["nome"]
                            novas_perms = set(nova_tabela["permissions"])
                            
                            if nome_tabela in tabelas_existentes:
                                tabelas_existentes[nome_tabela] |= novas_perms
                                logger.info(f"Adicionadas permissões {', '.join(novas_perms)} à tabela {nome_tabela}")
                            else:
                                tabelas_existentes[nome_tabela] = novas_perms
                                logger.info(f"Nova tabela adicionada: {nome_tabela}")
                        
                        schemas_existentes[nome_schema] = {
                            "nome": nome_schema,
                            "tipo": "granular",
                            "tabelas": [
                                {"nome": nome, "permissions": sorted(list(perms))}
                                for nome, perms in tabelas_existentes.items()
                            ]
                        }
                    else:
                        # Existente simples, novo granular - substituir por granular
                        schemas_existentes[nome_schema] = item
                        logger.info(f"Schema {nome_schema} convertido para granular")
            elif not remover_modo:
                # Novo schema granular
                schemas_existentes[nome_schema] = item
                logger.info(f"Novo schema granular adicionado: {nome_schema}")
        else:
            # Formato simples
            novas_perms = set(item["permissions"])
            
            if nome_schema in schemas_existentes:
                schema_existente = schemas_existentes[nome_schema]
                
                if remover_modo:
                    if schema_existente.get("tipo") == "simples":
                        # Ambos simples - remover permissões
                        perms_existentes = set(schema_existente["permissions"])
                        perms_existentes -= novas_perms
                        logger.info(f"Removidas permissões: {', '.join(novas_perms)}")
                        
                        if perms_existentes:
                            schemas_existentes[nome_schema] = {
                                "nome": nome_schema,
                                "tipo": "simples",
                                "permissions": sorted(list(perms_existentes))
                            }
                        else:
                            del schemas_existentes[nome_schema]
                            logger.info(f"Schema {nome_schema} removido (sem permissões)")
                    else:
                        # Existente granular, novo simples - não faz sentido remover
                        logger.warning(f"Tentativa de remoção simples em schema granular: {nome_schema}")
                else:
                    if schema_existente.get("tipo") == "simples":
                        # Ambos simples - merge de permissões
                        perms_existentes = set(schema_existente["permissions"])
                        perms_existentes |= novas_perms
                        schemas_existentes[nome_schema] = {
                            "nome": nome_schema,
                            "tipo": "simples",
                            "permissions": sorted(list(perms_existentes))
                        }
                        logger.info(f"Adicionadas permissões: {', '.join(novas_perms)}")
                    else:
                        # Existente granular, novo simples - manter granular
                        logger.warning(f"Mantendo formato granular para schema: {nome_schema}")
            elif not remover_modo:
                # Novo schema simples
                schemas_existentes[nome_schema] = {
                    "nome": nome_schema,
                    "tipo": "simples",
                    "permissions": sorted(list(novas_perms))
                }
                logger.info(f"Novo schema simples adicionado: {nome_schema}")
    
    # Converter de volta para formato final (remover campo "tipo" para compatibilidade)
    schemas_final = []
    for schema in schemas_existentes.values():
        if schema.get("tipo") == "granular":
            schemas_final.append({
                "nome": schema["nome"],
                "tipo": "granular",
                "tabelas": schema["tabelas"]
            })
        else:
            schemas_final.append({
                "nome": schema["nome"],
                "permissions": schema["permissions"]
            })
    
    return schemas_final

def salvar_arquivo(caminho, dados, remover_modo):
    """Salva o arquivo YAML atualizado."""
    try:
        # Atualizar flag de remoção
        if remover_modo:
            dados["remover_permissoes"] = True
        elif "remover_permissoes" in dados:
            del dados["remover_permissoes"]
        
        # Criar diretório se não existir
        caminho.parent.mkdir(parents=True, exist_ok=True)
        
        # Salvar arquivo
        with open(caminho, "w", encoding='utf-8') as arquivo:
            yaml.safe_dump(dados, arquivo, sort_keys=False, allow_unicode=True)
        
        logger.info(f"Arquivo salvo com sucesso: {caminho}")
        
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo: {e}")
        raise

def main():
    """Função principal."""
    try:
        logger.info("Iniciando merge de permissões")
        
        # Validar entrada
        validar_entrada()
        
        # Obter argumentos
        caminho = Path(sys.argv[1])
        json_permissoes = sys.argv[2]
        remover_modo = os.getenv("REMOVER_PERMISSOES", "false").lower() == "true"
        
        logger.info(f"Modo: {'Remoção' if remover_modo else 'Adição'}")
        
        # Validar e processar JSON
        novas_permissoes = validar_json_permissoes(json_permissoes)
        logger.info(f"Processando {len(novas_permissoes)} schema(s)")
        
        # Carregar dados existentes
        dados = carregar_dados_existentes(caminho)
        
        # Processar permissões
        schemas_final = processar_permissoes(dados, novas_permissoes, remover_modo)
        dados["schemas"] = schemas_final
        
        # Salvar arquivo
        salvar_arquivo(caminho, dados, remover_modo)
        
        # Relatório final
        logger.info("="*50)
        logger.info(f"MERGE CONCLUÍDO COM SUCESSO!")
        logger.info(f"Arquivo: {caminho}")
        logger.info(f"Modo: {'Remoção' if remover_modo else 'Adição'}")
        logger.info(f"Schemas finais: {len(schemas_final)}")
        for schema in schemas_final:
            if "tipo" in schema and schema["tipo"] == "granular":
                logger.info(f"  - {schema['nome']} (granular):")
                for tabela in schema["tabelas"]:
                    permissoes = ", ".join(tabela["permissions"])
                    logger.info(f"    └── {tabela['nome']}: {permissoes}")
            else:
                permissoes = ", ".join(schema["permissions"])
                logger.info(f"  - {schema['nome']}: {permissoes}")
        logger.info("="*50)
        
    except ValueError as e:
        logger.error(f"Erro de validação: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
