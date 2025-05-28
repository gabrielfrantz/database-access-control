import boto3
import yaml
import os
import sys
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constantes de validação
ENGINES_VALIDOS = ["postgres", "postgresql", "mysql", "aurora"]

PERMISSOES_VALIDAS_POSTGRES = [
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "TRUNCATE", "REFERENCES", "TRIGGER",
    "USAGE", "EXECUTE", "CREATE", "TEMP", "ALL PRIVILEGES"
]

PERMISSOES_VALIDAS_MYSQL = [
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "CREATE", "DROP", "INDEX", "ALTER",
    "REFERENCES", "EXECUTE", "USAGE", "ALL PRIVILEGES"
]

def validar_yaml(dados):
    """Valida a estrutura básica do arquivo YAML (formato simples ou granular)."""
    campos_obrigatorios = ["host", "user", "database", "engine", "region", "schemas"]
    
    for campo in campos_obrigatorios:
        if campo not in dados:
            raise ValueError(f"Campo obrigatório ausente: {campo}")
        if not dados[campo]:
            raise ValueError(f"Campo '{campo}' não pode estar vazio")

    engine = dados["engine"].lower()
    if engine not in ENGINES_VALIDOS:
        raise ValueError(f"Engine inválido: {dados['engine']}")

    # Validar permissões baseado no engine
    permissoes_validas = PERMISSOES_VALIDAS_POSTGRES if "postgres" in engine else PERMISSOES_VALIDAS_MYSQL

    for schema in dados.get("schemas", []):
        if "nome" not in schema:
            raise ValueError("Cada schema deve conter campo 'nome'")
        
        # Verificar se é formato granular ou simples
        if "tipo" in schema and schema["tipo"] == "granular":
            # Formato granular - validar tabelas
            if "tabelas" not in schema:
                raise ValueError(f"Schema granular '{schema['nome']}' deve conter campo 'tabelas'")
            
            for tabela in schema["tabelas"]:
                if "nome" not in tabela or "permissions" not in tabela:
                    raise ValueError(f"Cada tabela no schema '{schema['nome']}' deve conter 'nome' e 'permissions'")
                
                for permissao in tabela["permissions"]:
                    if permissao.upper() not in permissoes_validas:
                        raise ValueError(f"Permissão inválida: {permissao} (tabela: {tabela['nome']}, schema: {schema['nome']})")
        else:
            # Formato simples - validar permissions
            if "permissions" not in schema:
                raise ValueError(f"Schema simples '{schema['nome']}' deve conter campo 'permissions'")
            
            for permissao in schema["permissions"]:
                if permissao.upper() not in permissoes_validas:
                    raise ValueError(f"Permissão inválida: {permissao} (schema: {schema['nome']})")

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

def aplicar_permissoes_postgres_granular(conn, username, schema_nome, tabelas):
    """Aplica permissões PostgreSQL granulares (por tabela)."""
    with conn.cursor() as cur:
        # Aplicar USAGE no schema automaticamente para permissões granulares
        cur.execute(f'GRANT USAGE ON SCHEMA {schema_nome} TO "{username}";')
        logger.info(f"Aplicada permissão USAGE no schema {schema_nome}")
        
        for tabela in tabelas:
            nome_tabela = tabela["nome"]
            logger.info(f"Processando tabela: {schema_nome}.{nome_tabela}")
            
            for permissao in tabela["permissions"]:
                permissao_upper = permissao.upper()
                
                if permissao_upper in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]:
                    cur.execute(f'GRANT {permissao_upper} ON {schema_nome}.{nome_tabela} TO "{username}";')
                elif permissao_upper == "ALL PRIVILEGES":
                    cur.execute(f'GRANT ALL PRIVILEGES ON {schema_nome}.{nome_tabela} TO "{username}";')
                else:
                    # Para permissões que não se aplicam a tabelas específicas, aplicar no schema
                    if permissao_upper == "EXECUTE":
                        cur.execute(f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema_nome} TO "{username}";')
                    elif permissao_upper in ["USAGE", "CREATE"]:
                        cur.execute(f'GRANT {permissao_upper} ON SCHEMA {schema_nome} TO "{username}";')
                    elif permissao_upper == "TEMP":
                        cur.execute(f'GRANT TEMP ON DATABASE {conn.info.dbname} TO "{username}";')
                
                logger.info(f"Aplicada permissão {permissao_upper} na tabela {schema_nome}.{nome_tabela}")

def aplicar_permissoes_postgres_simples(conn, username, schema_nome, permissions):
    """Aplica permissões PostgreSQL simples (schema completo)."""
    with conn.cursor() as cur:
        for permissao in permissions:
            permissao_upper = permissao.upper()
            
            if permissao_upper in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]:
                cur.execute(f'GRANT {permissao_upper} ON ALL TABLES IN SCHEMA {schema_nome} TO "{username}";')
            elif permissao_upper == "EXECUTE":
                cur.execute(f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema_nome} TO "{username}";')
            elif permissao_upper in ["USAGE", "CREATE"]:
                cur.execute(f'GRANT {permissao_upper} ON SCHEMA {schema_nome} TO "{username}";')
            elif permissao_upper == "TEMP":
                cur.execute(f'GRANT TEMP ON DATABASE {conn.info.dbname} TO "{username}";')
            elif permissao_upper == "ALL PRIVILEGES":
                cur.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema_nome} TO "{username}";')
            
            logger.info(f"Aplicada permissão {permissao_upper} no schema {schema_nome}")

def aplicar_permissoes_postgres(conn, username, schemas):
    """Aplica permissões PostgreSQL (suporta formato granular e simples)."""
    try:
        with conn.cursor() as cur:
            # Criar usuário se não existir
            logger.info(f"Criando/verificando usuário: {username}")
            cur.execute(f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{username}') THEN CREATE ROLE \"{username}\" WITH LOGIN; END IF; END $$;")
            
            for schema in schemas:
                schema_nome = schema['nome']
                logger.info(f"Processando schema: {schema_nome}")
                
                # Verificar se é granular ou simples
                if "tipo" in schema and schema["tipo"] == "granular":
                    aplicar_permissoes_postgres_granular(conn, username, schema_nome, schema["tabelas"])
                else:
                    aplicar_permissoes_postgres_simples(conn, username, schema_nome, schema["permissions"])
            
            conn.commit()
            logger.info("Transação commitada com sucesso")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao aplicar permissões PostgreSQL: {e}")
        raise

def aplicar_permissoes_mysql_granular(conn, username, database, schema_nome, tabelas):
    """Aplica permissões MySQL granulares (por tabela)."""
    with conn.cursor() as cur:
        for tabela in tabelas:
            nome_tabela = tabela["nome"]
            logger.info(f"Processando tabela: {database}.{nome_tabela}")
            
            for permissao in tabela["permissions"]:
                cur.execute(f'GRANT {permissao.upper()} ON `{database}`.`{nome_tabela}` TO \'{username}\'@\'%\';')
                logger.info(f"Aplicada permissão {permissao.upper()} na tabela {database}.{nome_tabela}")

def aplicar_permissoes_mysql_simples(conn, username, database, schema_nome, permissions):
    """Aplica permissões MySQL simples (schema completo)."""
    with conn.cursor() as cur:
        for permissao in permissions:
            cur.execute(f'GRANT {permissao.upper()} ON `{database}`.`{schema_nome}` TO \'{username}\'@\'%\';')
            logger.info(f"Aplicada permissão {permissao.upper()} no schema {schema_nome}")

def aplicar_permissoes_mysql(conn, username, database, schemas):
    """Aplica permissões MySQL (suporta formato granular e simples)."""
    try:
        with conn.cursor() as cur:
            # Criar usuário se não existir
            logger.info(f"Criando/verificando usuário: {username}")
            cur.execute(f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED VIA AWSAuthenticationPlugin AS 'RDS';")
            
            for schema in schemas:
                schema_nome = schema['nome']
                logger.info(f"Processando schema: {schema_nome}")
                
                # Verificar se é granular ou simples
                if "tipo" in schema and schema["tipo"] == "granular":
                    aplicar_permissoes_mysql_granular(conn, username, database, schema_nome, schema["tabelas"])
                else:
                    aplicar_permissoes_mysql_simples(conn, username, database, schema_nome, schema["permissions"])
            
            conn.commit()
            logger.info("Transação commitada com sucesso")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao aplicar permissões MySQL: {e}")
        raise

def aplicar_permissoes(caminho_yaml):
    """Função principal para aplicar permissões."""
    try:
        logger.info(f"Iniciando aplicação de permissões: {caminho_yaml}")
        
        # Carregar e validar arquivo YAML
        with open(caminho_yaml, 'r', encoding='utf-8') as arquivo:
            dados = yaml.safe_load(arquivo)

        validar_yaml(dados)

        # Extrair informações
        engine = dados["engine"].lower()
        user = os.environ.get("DB_USER")
        password = os.environ.get("DB_PASS")
        host = dados["host"]
        dbname = dados["database"]
        target_user = dados["user"]
        schemas = dados["schemas"]
        port = int(dados.get("port", 5432 if "postgres" in engine else 3306))

        # Validar variáveis de ambiente
        if not user or not password:
            raise ValueError("Variáveis DB_USER e DB_PASS devem estar definidas")

        logger.info(f"Configuração: Engine={engine}, Host={host}, Porta={port}, Banco={dbname}")

        # Conectar e aplicar permissões
        conn = None
        try:
            if "postgres" in engine:
                conn = conectar_postgres(host, port, user, password, dbname)
                aplicar_permissoes_postgres(conn, target_user, schemas)
            elif "mysql" in engine:
                conn = conectar_mysql(host, port, user, password, dbname)
                aplicar_permissoes_mysql(conn, target_user, dbname, schemas)
            else:
                raise ValueError(f"Engine não suportado: {engine}")

        finally:
            if conn:
                conn.close()
                logger.info("Conexão fechada")

        # Relatório final
        logger.info("="*50)
        logger.info("PERMISSÕES APLICADAS COM SUCESSO!")
        logger.info(f"Usuário: {target_user}")
        logger.info(f"Banco: {dbname}")
        logger.info(f"Engine: {engine}")
        logger.info("Schemas e permissões aplicadas:")
        for schema in schemas:
            if "tipo" in schema and schema["tipo"] == "granular":
                logger.info(f"  - Schema: {schema['nome']} (granular)")
                for tabela in schema["tabelas"]:
                    permissoes = ", ".join([p.upper() for p in tabela["permissions"]])
                    logger.info(f"    └── Tabela: {tabela['nome']} → Permissões: {permissoes}")
            else:
                permissoes = ", ".join([p.upper() for p in schema["permissions"]])
                logger.info(f"  - Schema: {schema['nome']} → Permissões: {permissoes}")
        logger.info("="*50)

    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {caminho_yaml}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Erro ao processar YAML: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Erro de validação: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python apply_permissions.py <caminho_arquivo.yml>")
        sys.exit(1)
    
    aplicar_permissoes(sys.argv[1])
