#!/usr/bin/env python3
"""
Script de Revogação Total de Permissões - Database Access Control
Revoga todas as permissões de um usuário quando um arquivo YAML é deletado
"""

import os
import sys
import yaml
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ENGINES_VALIDOS = ["postgres", "postgresql", "mysql", "aurora"]

PERMISSOES_VALIDAS_POSTGRES = [
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "TRUNCATE", "REFERENCES", "TRIGGER",
    "USAGE", "EXECUTE", "CREATE", "TEMP", "CONNECT", "ALL PRIVILEGES"
]

PERMISSOES_VALIDAS_MYSQL = [
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "CREATE", "DROP", "INDEX", "ALTER",
    "REFERENCES", "EXECUTE", "USAGE", "ALL PRIVILEGES"
]

def validar_yaml(dados):
    """Valida a estrutura básica do arquivo YAML."""
    if not dados:
        raise ValueError("Arquivo YAML vazio ou inválido")
        
    campos_obrigatorios = ["host", "user", "database", "engine", "region", "schemas"]
    
    for campo in campos_obrigatorios:
        if campo not in dados:
            raise ValueError(f"Campo obrigatório ausente: {campo}")
        if not dados[campo]:
            raise ValueError(f"Campo '{campo}' não pode estar vazio")

    engine = dados["engine"].lower()
    if engine not in ENGINES_VALIDOS:
        raise ValueError(f"Engine inválido: {dados['engine']}")

def conectar_postgres(host, port, user, password, database):
    """Conecta ao PostgreSQL com tratamento de erro."""
    try:
        import psycopg2
        return psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database,
            sslmode='require',
            connect_timeout=30
        )
    except Exception as e:
        logger.error(f"Erro ao conectar PostgreSQL: {e}")
        raise

def conectar_mysql(host, port, user, password, database):
    """Conecta ao MySQL com tratamento de erro."""
    try:
        import pymysql
        return pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl={"ssl": {}},
            connect_timeout=30
        )
    except Exception as e:
        logger.error(f"Erro ao conectar MySQL: {e}")
        raise

def revogar_todas_permissoes_postgres(conn, username, schemas):
    """Revoga todas as permissões PostgreSQL de um usuário."""
    try:
        with conn.cursor() as cur:
            logger.info(f"Iniciando revogação total para usuário PostgreSQL: {username}")
            
            for schema in schemas:
                schema_nome = schema['nome']
                logger.info(f"Revogando permissões do schema: {schema_nome}")
                
                if "tipo" in schema and schema["tipo"] == "granular":
                    for tabela in schema["tabelas"]:
                        nome_tabela = tabela["nome"]
                        logger.info(f"Revogando permissões da tabela: {schema_nome}.{nome_tabela}")
                        
                        for permissao in tabela["permissions"]:
                            permissao_upper = permissao.upper()
                            try:
                                if permissao_upper in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]:
                                    cur.execute(f'REVOKE {permissao_upper} ON {schema_nome}.{nome_tabela} FROM "{username}";')
                                elif permissao_upper == "ALL PRIVILEGES":
                                    cur.execute(f'REVOKE ALL PRIVILEGES ON {schema_nome}.{nome_tabela} FROM "{username}";')
                                elif permissao_upper == "EXECUTE":
                                    cur.execute(f'REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema_nome} FROM "{username}";')
                                elif permissao_upper in ["USAGE", "CREATE"]:
                                    cur.execute(f'REVOKE {permissao_upper} ON SCHEMA {schema_nome} FROM "{username}";')
                                elif permissao_upper == "TEMP":
                                    cur.execute(f'REVOKE TEMP ON DATABASE {conn.info.dbname} FROM "{username}";')
                                elif permissao_upper == "CONNECT":
                                    cur.execute(f'REVOKE CONNECT ON DATABASE {conn.info.dbname} FROM "{username}";')
                                
                                logger.info(f"Revogada permissão {permissao_upper} da tabela {schema_nome}.{nome_tabela}")
                            except Exception as e:
                                logger.warning(f"Erro ao revogar {permissao_upper} da tabela {schema_nome}.{nome_tabela}: {e}")
                else:
                    for permissao in schema["permissions"]:
                        permissao_upper = permissao.upper()
                        try:
                            if permissao_upper in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]:
                                cur.execute(f'REVOKE {permissao_upper} ON ALL TABLES IN SCHEMA {schema_nome} FROM "{username}";')
                            elif permissao_upper == "EXECUTE":
                                cur.execute(f'REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema_nome} FROM "{username}";')
                            elif permissao_upper in ["USAGE", "CREATE"]:
                                cur.execute(f'REVOKE {permissao_upper} ON SCHEMA {schema_nome} FROM "{username}";')
                            elif permissao_upper == "TEMP":
                                cur.execute(f'REVOKE TEMP ON DATABASE {conn.info.dbname} FROM "{username}";')
                            elif permissao_upper == "ALL PRIVILEGES":
                                cur.execute(f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema_nome} FROM "{username}";')
                                cur.execute(f'REVOKE ALL PRIVILEGES ON SCHEMA {schema_nome} FROM "{username}";')
                            elif permissao_upper == "CONNECT":
                                cur.execute(f'REVOKE CONNECT ON DATABASE {conn.info.dbname} FROM "{username}";')
                            
                            logger.info(f"Revogada permissão {permissao_upper} do schema {schema_nome}")
                        except Exception as e:
                            logger.warning(f"Erro ao revogar {permissao_upper} do schema {schema_nome}: {e}")
            
            try:
                logger.info(f"Removendo usuário: {username}")
                cur.execute(f'DROP ROLE IF EXISTS "{username}";')
                logger.info(f"Usuário {username} removido com sucesso")
            except Exception as e:
                logger.warning(f"Erro ao remover usuário {username}: {e}")
            
            conn.commit()
            logger.info("Revogação total PostgreSQL concluída com sucesso")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro durante revogação PostgreSQL: {e}")
        raise

def revogar_todas_permissoes_mysql(conn, username, database, schemas):
    """Revoga todas as permissões MySQL de um usuário."""
    try:
        with conn.cursor() as cur:
            logger.info(f"Iniciando revogação total para usuário MySQL: {username}")
            
            for schema in schemas:
                schema_nome = schema['nome']
                logger.info(f"Revogando permissões do schema: {schema_nome}")
                
                if "tipo" in schema and schema["tipo"] == "granular":
                    for tabela in schema["tabelas"]:
                        nome_tabela = tabela["nome"]
                        logger.info(f"Revogando permissões da tabela: {database}.{nome_tabela}")
                        
                        for permissao in tabela["permissions"]:
                            try:
                                cur.execute(f'REVOKE {permissao.upper()} ON `{database}`.`{nome_tabela}` FROM \'{username}\'@\'%\';')
                                logger.info(f"Revogada permissão {permissao.upper()} da tabela {database}.{nome_tabela}")
                            except Exception as e:
                                logger.warning(f"Erro ao revogar {permissao.upper()} da tabela {database}.{nome_tabela}: {e}")
                else:
                    for permissao in schema["permissions"]:
                        try:
                            if permissao.upper() == "ALL PRIVILEGES":
                                cur.execute(f'REVOKE ALL PRIVILEGES ON `{database}`.* FROM \'{username}\'@\'%\';')
                            else:
                                cur.execute(f'REVOKE {permissao.upper()} ON `{database}`.`{schema_nome}` FROM \'{username}\'@\'%\';')
                            logger.info(f"Revogada permissão {permissao.upper()} do schema {schema_nome}")
                        except Exception as e:
                            logger.warning(f"Erro ao revogar {permissao.upper()} do schema {schema_nome}: {e}")
            
            try:
                logger.info(f"Removendo usuário: {username}")
                cur.execute(f'DROP USER IF EXISTS \'{username}\'@\'%\';')
                logger.info(f"Usuário {username} removido com sucesso")
            except Exception as e:
                logger.warning(f"Erro ao remover usuário {username}: {e}")
            
            conn.commit()
            logger.info("Revogação total MySQL concluída com sucesso")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro durante revogação MySQL: {e}")
        raise

def revogar_todas_permissoes(caminho_yaml):
    """Revoga todas as permissões de um usuário baseado no arquivo YAML."""
    try:
        logger.info(f"Iniciando revogação total baseada em: {caminho_yaml}")
        
        with open(caminho_yaml, 'r', encoding='utf-8') as arquivo:
            dados = yaml.safe_load(arquivo)
        
        validar_yaml(dados)
        
        host = dados['host']
        port = dados.get('port', 3306 if dados['engine'].lower() == 'mysql' else 5432)
        database = dados['database']
        engine = dados['engine'].lower()
        username = dados['user']
        schemas = dados['schemas']
        
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASS')
        db_host = os.environ.get('DB_HOST', host)
        
        if not db_user or not db_pass:
            raise ValueError("Credenciais de banco não fornecidas via variáveis de ambiente")
        
        logger.info(f"Conectando ao {engine} em {db_host}:{port}")
        logger.info(f"Revogando permissões do usuário: {username}")
        
        if engine in ['postgres', 'postgresql', 'aurora']:
            conn = conectar_postgres(db_host, port, db_user, db_pass, database)
            revogar_todas_permissoes_postgres(conn, username, schemas)
        elif engine == 'mysql':
            conn = conectar_mysql(db_host, port, db_user, db_pass, database)
            revogar_todas_permissoes_mysql(conn, username, database, schemas)
        else:
            raise ValueError(f"Engine não suportado: {engine}")
        
        conn.close()
        logger.info(f"Revogação total concluída com sucesso para usuário: {username}")
        
    except Exception as e:
        logger.error(f"Erro durante revogação total: {e}")
        sys.exit(1)

def main():
    """Função principal"""
    if len(sys.argv) != 2:
        logger.error("Uso: python revoke_all_permissions.py <caminho_arquivo.yml>")
        sys.exit(1)
    
    caminho_yaml = sys.argv[1]
    
    if not os.path.exists(caminho_yaml):
        logger.error(f"Arquivo não encontrado: {caminho_yaml}")
        sys.exit(1)
    
    try:
        revogar_todas_permissoes(caminho_yaml)
        logger.info("Script executado com sucesso!")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 