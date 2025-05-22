import os
import sys
import yaml

VALID_ENGINES = ["postgres", "postgresql", "mysql"]

PG_TABLE_PERMS = {"SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"}
PG_FUNCTION_PERMS = {"EXECUTE"}
PG_SCHEMA_PERMS = {"USAGE", "CREATE"}
PG_DB_PERMS = {"TEMP"}

MYSQL_ALL_PERMS = {
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "CREATE", "DROP", "INDEX", "ALTER",
    "REFERENCES", "EXECUTE", "USAGE", "ALL PRIVILEGES"
}

def validate_yaml(data):
    required_fields = ["user", "database", "engine", "region", "host", "schemas"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Campo obrigatório ausente: {field}")

def connect_postgres(host, port, user, password, database):
    import psycopg2
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=database,
        sslmode='require'
    )

def connect_mysql(host, port, user, password, database):
    import pymysql
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        ssl={"ssl": {}}
    )

def calcular_permissoes_revogadas(antes, depois):
    antes_map = {s["nome"]: set(s["permissions"]) for s in antes}
    depois_map = {s["nome"]: set(s["permissions"]) for s in depois}

    revogadas = []
    for schema, perms_antes in antes_map.items():
        perms_depois = depois_map.get(schema, set())
        diferenca = perms_antes - perms_depois
        if diferenca:
            revogadas.append({
                "nome": schema,
                "permissions": sorted(list(diferenca))
            })
    return revogadas

def revoke_postgres_permissions(conn, username, schemas):
    with conn.cursor() as cur:
        for schema in schemas:
            for perm in schema["permissions"]:
                p = perm.upper()
                if p in PG_TABLE_PERMS or p == "ALL PRIVILEGES":
                    cur.execute(f'REVOKE {p} ON ALL TABLES IN SCHEMA {schema["nome"]} FROM "{username}";')
                elif p in PG_FUNCTION_PERMS:
                    cur.execute(f'REVOKE {p} ON ALL FUNCTIONS IN SCHEMA {schema["nome"]} FROM "{username}";')
                elif p in PG_SCHEMA_PERMS:
                    cur.execute(f'REVOKE {p} ON SCHEMA {schema["nome"]} FROM "{username}";')
                elif p in PG_DB_PERMS:
                    cur.execute(f'REVOKE {p} ON DATABASE {conn.get_dsn_parameters()["dbname"]} FROM "{username}";')
    conn.commit()

def revoke_mysql_permissions(conn, username, database, schemas):
    with conn.cursor() as cur:
        for schema in schemas:
            for perm in schema["permissions"]:
                cur.execute(
                    f'REVOKE {perm.upper()} ON `{database}`.`{schema["nome"]}` FROM \'{username}\'@\'%\';'
                )
    conn.commit()

def revoke_permissions(old_yaml_path, new_yaml_path):
    with open(old_yaml_path, 'r') as f:
        dados_antes = yaml.safe_load(f)

    with open(new_yaml_path, 'r') as f:
        dados_depois = yaml.safe_load(f) or {}

    validate_yaml(dados_antes)

    # Se dados_depois não tem schemas, assume que todas as permissões devem ser revogadas
    revogar_schemas = dados_antes["schemas"] if "schemas" not in dados_depois else calcular_permissoes_revogadas(dados_antes["schemas"], dados_depois.get("schemas", []))

    validate_yaml(dados_antes)
    validate_yaml(dados_depois)

    engine = dados_antes["engine"].lower()
    if engine not in VALID_ENGINES:
        raise ValueError(f"Engine não suportado: {engine}")

    host = dados_antes["host"]
    dbname = dados_antes["database"]
    region = dados_antes["region"]
    target_user = dados_antes["user"]
    port = int(dados_antes.get("port", 5432 if "postgres" in engine else 3306))

    user = os.environ["DB_USER"]
    password = os.environ["DB_PASS"]

    revogar_schemas = calcular_permissoes_revogadas(dados_antes["schemas"], dados_depois["schemas"])
    if not revogar_schemas:
        print("Nenhuma permissão a ser revogada.")
        return

    if "postgres" in engine:
        conn = connect_postgres(host, port, user, password, dbname)
        revoke_postgres_permissions(conn, target_user, revogar_schemas)
    elif "mysql" in engine:
        conn = connect_mysql(host, port, user, password, dbname)
        revoke_mysql_permissions(conn, target_user, dbname, revogar_schemas)

    conn.close()

    print("\nPermissões revogadas com sucesso!\n")
    print(f"Usuário: {target_user}")
    print(f"Banco: {dbname}")
    print(f"Engine: {engine}")
    print(f"Região: {region}")
    print(f"Porta: {port}")
    print("Permissões revogadas:")
    for schema in revogar_schemas:
        print(f"  - Schema: {schema['nome']} → {', '.join(schema['permissions'])}")

if __name__ == "__main__":
    revoke_permissions(sys.argv[1], sys.argv[2])
