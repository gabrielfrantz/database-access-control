import os
import sys
import yaml
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constantes de validação
ENGINES_VALIDOS = ["postgres", "postgresql", "mysql", "aurora"]

# Permissões categorizadas para PostgreSQL
PG_TABLE_PERMS = {"SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"}
PG_FUNCTION_PERMS = {"EXECUTE"}
PG_SCHEMA_PERMS = {"USAGE", "CREATE"}
PG_DB_PERMS = {"TEMP"}

# Permissões MySQL
MYSQL_ALL_PERMS = {
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "CREATE", "DROP", "INDEX", "ALTER",
    "REFERENCES", "EXECUTE", "USAGE", "ALL PRIVILEGES"
}

def validar_yaml(dados):
    """Valida a estrutura básica do arquivo YAML (formato simples ou granular)."""
    if not dados:
        return  # Arquivo vazio é válido para revogação total
        
    campos_obrigatorios = ["user", "database", "engine", "region", "host", "schemas"]
    for campo in campos_obrigatorios:
        if campo not in dados:
            raise ValueError(f"Campo obrigatório ausente: {campo}")
        if not dados[campo]:
            raise ValueError(f"Campo '{campo}' não pode estar vazio")

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

def normalizar_schema_para_comparacao(schema):
    """Normaliza schema para comparação (converte granular para estrutura uniforme)."""
    if "tipo" in schema and schema["tipo"] == "granular":
        # Granular - criar mapa de tabela -> permissões
        tabelas_map = {}
        for tabela in schema.get("tabelas", []):
            tabelas_map[tabela["nome"]] = set(tabela["permissions"])
        return {
            "nome": schema["nome"],
            "tipo": "granular",
            "tabelas": tabelas_map
        }
    else:
        # Simples - manter como está
        return {
            "nome": schema["nome"],
            "tipo": "simples",
            "permissions": set(schema["permissions"])
        }

def calcular_permissoes_revogadas(antes, depois):
    """Calcula quais permissões devem ser revogadas (suporta formato granular)."""
    # Normalizar schemas para comparação
    antes_map = {}
    for schema in antes:
        nome = schema["nome"]
        antes_map[nome] = normalizar_schema_para_comparacao(schema)
    
    depois_map = {}
    for schema in depois:
        nome = schema["nome"]
        depois_map[nome] = normalizar_schema_para_comparacao(schema)

    revogadas = []
    
    for schema_nome, schema_antes in antes_map.items():
        schema_depois = depois_map.get(schema_nome)
        
        if not schema_depois:
            # Schema foi completamente removido - revogar tudo
            if schema_antes["tipo"] == "granular":
                tabelas_revogadas = []
                for tabela_nome, perms in schema_antes["tabelas"].items():
                    tabelas_revogadas.append({
                        "nome": tabela_nome,
                        "permissions": sorted(list(perms))
                    })
                revogadas.append({
                    "nome": schema_nome,
                    "tipo": "granular",
                    "tabelas": tabelas_revogadas
                })
            else:
                revogadas.append({
                    "nome": schema_nome,
                    "permissions": sorted(list(schema_antes["permissions"]))
                })
        else:
            # Schema ainda existe - calcular diferenças
            if schema_antes["tipo"] == "granular" and schema_depois["tipo"] == "granular":
                # Ambos granulares - comparar tabela por tabela
                tabelas_revogadas = []
                
                for tabela_nome, perms_antes in schema_antes["tabelas"].items():
                    perms_depois = schema_depois["tabelas"].get(tabela_nome, set())
                    diferenca = perms_antes - perms_depois
                    
                    if diferenca:
                        tabelas_revogadas.append({
                            "nome": tabela_nome,
                            "permissions": sorted(list(diferenca))
                        })
                
                if tabelas_revogadas:
                    revogadas.append({
                        "nome": schema_nome,
                        "tipo": "granular",
                        "tabelas": tabelas_revogadas
                    })
                    
            elif schema_antes["tipo"] == "simples" and schema_depois["tipo"] == "simples":
                # Ambos simples - comparar permissões
                diferenca = schema_antes["permissions"] - schema_depois["permissions"]
                if diferenca:
                    revogadas.append({
                        "nome": schema_nome,
                        "permissions": sorted(list(diferenca))
                    })
            else:
                # Tipos diferentes - revogar tudo do anterior (conversão de formato)
                logger.warning(f"Conversão de formato detectada para schema {schema_nome} - revogando permissões anteriores")
                if schema_antes["tipo"] == "granular":
                    tabelas_revogadas = []
                    for tabela_nome, perms in schema_antes["tabelas"].items():
                        tabelas_revogadas.append({
                            "nome": tabela_nome,
                            "permissions": sorted(list(perms))
                        })
                    revogadas.append({
                        "nome": schema_nome,
                        "tipo": "granular",
                        "tabelas": tabelas_revogadas
                    })
                else:
                    revogadas.append({
                        "nome": schema_nome,
                        "permissions": sorted(list(schema_antes["permissions"]))
                    })
    
    return revogadas

def revogar_permissoes_postgres_granular(conn, username, schema_nome, tabelas):
    """Revoga permissões PostgreSQL granulares (por tabela)."""
    with conn.cursor() as cur:
        for tabela in tabelas:
            nome_tabela = tabela["nome"]
            logger.info(f"Revogando permissões da tabela: {schema_nome}.{nome_tabela}")
            
            for permissao in tabela["permissions"]:
                permissao_upper = permissao.upper()
                
                if permissao_upper in PG_TABLE_PERMS or permissao_upper == "ALL PRIVILEGES":
                    cur.execute(f'REVOKE {permissao_upper} ON {schema_nome}.{nome_tabela} FROM "{username}";')
                else:
                    # Para permissões que não se aplicam a tabelas específicas, revogar do schema
                    if permissao_upper in PG_FUNCTION_PERMS:
                        cur.execute(f'REVOKE {permissao_upper} ON ALL FUNCTIONS IN SCHEMA {schema_nome} FROM "{username}";')
                    elif permissao_upper in PG_SCHEMA_PERMS:
                        cur.execute(f'REVOKE {permissao_upper} ON SCHEMA {schema_nome} FROM "{username}";')
                    elif permissao_upper in PG_DB_PERMS:
                        cur.execute(f'REVOKE {permissao_upper} ON DATABASE {conn.get_dsn_parameters()["dbname"]} FROM "{username}";')
                
                logger.info(f"Revogada permissão {permissao_upper} da tabela {schema_nome}.{nome_tabela}")

def revogar_permissoes_postgres_simples(conn, username, schema_nome, permissions):
    """Revoga permissões PostgreSQL simples (schema completo)."""
    with conn.cursor() as cur:
        for permissao in permissions:
            permissao_upper = permissao.upper()
            
            if permissao_upper in PG_TABLE_PERMS or permissao_upper == "ALL PRIVILEGES":
                cur.execute(f'REVOKE {permissao_upper} ON ALL TABLES IN SCHEMA {schema_nome} FROM "{username}";')
            elif permissao_upper in PG_FUNCTION_PERMS:
                cur.execute(f'REVOKE {permissao_upper} ON ALL FUNCTIONS IN SCHEMA {schema_nome} FROM "{username}";')
            elif permissao_upper in PG_SCHEMA_PERMS:
                cur.execute(f'REVOKE {permissao_upper} ON SCHEMA {schema_nome} FROM "{username}";')
            elif permissao_upper in PG_DB_PERMS:
                cur.execute(f'REVOKE {permissao_upper} ON DATABASE {conn.get_dsn_parameters()["dbname"]} FROM "{username}";')
            
            logger.info(f"Revogada permissão {permissao_upper} do schema {schema_nome}")

def revogar_permissoes_postgres(conn, username, schemas):
    """Revoga permissões PostgreSQL (suporta formato granular e simples)."""
    try:
        with conn.cursor() as cur:
            for schema in schemas:
                schema_nome = schema["nome"]
                logger.info(f"Revogando permissões do schema: {schema_nome}")
                
                # Verificar se é granular ou simples
                if "tipo" in schema and schema["tipo"] == "granular":
                    revogar_permissoes_postgres_granular(conn, username, schema_nome, schema["tabelas"])
                else:
                    revogar_permissoes_postgres_simples(conn, username, schema_nome, schema["permissions"])
            
            conn.commit()
            logger.info("Transação de revogação commitada com sucesso")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao revogar permissões PostgreSQL: {e}")
        raise

def revogar_permissoes_mysql_granular(conn, username, database, schema_nome, tabelas):
    """Revoga permissões MySQL granulares (por tabela)."""
    with conn.cursor() as cur:
        for tabela in tabelas:
            nome_tabela = tabela["nome"]
            logger.info(f"Revogando permissões da tabela: {database}.{nome_tabela}")
            
            for permissao in tabela["permissions"]:
                cur.execute(f'REVOKE {permissao.upper()} ON `{database}`.`{nome_tabela}` FROM \'{username}\'@\'%\';')
                logger.info(f"Revogada permissão {permissao.upper()} da tabela {database}.{nome_tabela}")

def revogar_permissoes_mysql_simples(conn, username, database, schema_nome, permissions):
    """Revoga permissões MySQL simples (schema completo)."""
    with conn.cursor() as cur:
        for permissao in permissions:
            cur.execute(f'REVOKE {permissao.upper()} ON `{database}`.`{schema_nome}` FROM \'{username}\'@\'%\';')
            logger.info(f"Revogada permissão {permissao.upper()} do schema {schema_nome}")

def revogar_permissoes_mysql(conn, username, database, schemas):
    """Revoga permissões MySQL (suporta formato granular e simples)."""
    try:
        with conn.cursor() as cur:
            for schema in schemas:
                schema_nome = schema["nome"]
                logger.info(f"Revogando permissões do schema: {schema_nome}")
                
                # Verificar se é granular ou simples
                if "tipo" in schema and schema["tipo"] == "granular":
                    revogar_permissoes_mysql_granular(conn, username, database, schema_nome, schema["tabelas"])
                else:
                    revogar_permissoes_mysql_simples(conn, username, database, schema_nome, schema["permissions"])
            
            conn.commit()
            logger.info("Transação de revogação commitada com sucesso")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao revogar permissões MySQL: {e}")
        raise

def revogar_permissoes(caminho_yaml_antes, caminho_yaml_depois):
    """Função principal para revogar permissões."""
    try:
        logger.info(f"Iniciando revogação de permissões: {caminho_yaml_antes} -> {caminho_yaml_depois}")
        
        # Carregar arquivo anterior
        with open(caminho_yaml_antes, 'r', encoding='utf-8') as arquivo:
            dados_antes = yaml.safe_load(arquivo)

        # Carregar arquivo atual (pode estar vazio para revogação total)
        with open(caminho_yaml_depois, 'r', encoding='utf-8') as arquivo:
            dados_depois = yaml.safe_load(arquivo) or {}

        # Validar dados
        validar_yaml(dados_antes)
        if "schemas" in dados_depois:
            validar_yaml(dados_depois)

        # Extrair informações do arquivo anterior
        engine = dados_antes["engine"].lower()
        if engine not in ENGINES_VALIDOS:
            raise ValueError(f"Engine não suportado: {engine}")

        host = dados_antes["host"]
        dbname = dados_antes["database"]
        region = dados_antes["region"]
        target_user = dados_antes["user"]
        port = int(dados_antes.get("port", 5432 if "postgres" in engine else 3306))
        
        # Obter credenciais das variáveis de ambiente
        user = os.environ.get("DB_USER")
        password = os.environ.get("DB_PASS")
        
        if not user or not password:
            raise ValueError("Variáveis DB_USER e DB_PASS devem estar definidas")

        # Calcular permissões a serem revogadas
        if "schemas" not in dados_depois:
            # Revogação total
            revogar_schemas = dados_antes["schemas"]
            logger.info("Revogação total - removendo todas as permissões")
        else:
            # Revogação parcial
            revogar_schemas = calcular_permissoes_revogadas(dados_antes["schemas"], dados_depois["schemas"])
            logger.info("Revogação parcial - removendo permissões específicas")

        if not revogar_schemas:
            logger.info("Nenhuma permissão a ser revogada.")
            return

        logger.info(f"Configuração: Engine={engine}, Host={host}, Porta={port}, Banco={dbname}")

        # Conectar e revogar permissões
        conn = None
        try:
            if "postgres" in engine:
                conn = conectar_postgres(host, port, user, password, dbname)
                revogar_permissoes_postgres(conn, target_user, revogar_schemas)
            elif "mysql" in engine:
                conn = conectar_mysql(host, port, user, password, dbname)
                revogar_permissoes_mysql(conn, target_user, dbname, revogar_schemas)
            else:
                raise ValueError(f"Engine não suportado: {engine}")

        finally:
            if conn:
                conn.close()
                logger.info("Conexão fechada")

        # Relatório final
        logger.info("="*50)
        logger.info("PERMISSÕES REVOGADAS COM SUCESSO!")
        logger.info(f"Usuário: {target_user}")
        logger.info(f"Banco: {dbname}")
        logger.info(f"Engine: {engine}")
        logger.info("Schemas e permissões revogadas:")
        for schema in revogar_schemas:
            if "tipo" in schema and schema["tipo"] == "granular":
                logger.info(f"  - Schema: {schema['nome']} (granular)")
                for tabela in schema["tabelas"]:
                    permissoes = ", ".join([p.upper() for p in tabela["permissions"]])
                    logger.info(f"    └── Tabela: {tabela['nome']} → Permissões: {permissoes}")
            else:
                permissoes = ", ".join([p.upper() for p in schema["permissions"]])
                logger.info(f"  - Schema: {schema['nome']} → Permissões: {permissoes}")
        logger.info("="*50)

    except FileNotFoundError as e:
        logger.error(f"Arquivo não encontrado: {e}")
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
    if len(sys.argv) != 3:
        print("Uso: python revoke_permissions.py <caminho_yaml_antes> <caminho_yaml_depois>")
        sys.exit(1)
    
    revogar_permissoes(sys.argv[1], sys.argv[2])