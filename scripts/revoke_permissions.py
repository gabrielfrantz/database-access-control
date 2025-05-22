import os
import sys
import yaml

VALID_ENGINES = ["postgres", "postgresql", "mysql"]

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

def revoke_postgres_permissions(conn, username, schemas):
    with conn.cursor() as cur:
        for schema in schemas:
            for perm in schema["permissions"]:
                cur.execute(
                    f'REVOKE {perm.upper()} ON ALL TABLES IN SCHEMA {schema["nome"]} FROM "{username}";'
                )
    conn.commit()

def revoke_mysql_permissions(conn, username, database, schemas):
    with conn.cursor() as cur:
        for schema in schemas:
            for perm in schema["permissions"]:
                cur.execute(
                    f'REVOKE {perm.upper()} ON `{database}`.`{schema["nome"]}` FROM \'{username}\'@\'%\';'
                )
    conn.commit()

def revoke_permissions(yaml_path):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    validate_yaml(data)

    engine = data["engine"].lower()
    if engine not in VALID_ENGINES:
        raise ValueError(f"Engine não suportado: {engine}")

    host = data["host"]
    dbname = data["database"]
    region = data["region"]
    target_user = data["user"]
    port = int(data.get("port", 5432 if "postgres" in engine else 3306))
    schemas = data["schemas"]

    user = os.environ["DB_USER"]
    password = os.environ["DB_PASS"]

    if "postgres" in engine:
        conn = connect_postgres(host, port, user, password, dbname)
        revoke_postgres_permissions(conn, target_user, schemas)
    elif "mysql" in engine:
        conn = connect_mysql(host, port, user, password, dbname)
        revoke_mysql_permissions(conn, target_user, dbname, schemas)

    conn.close()
    print("\nPermissões revogadas com sucesso!\n")
    print(f"Usuário: {target_user}")
    print(f"Banco: {dbname}")
    print(f"Engine: {engine}")
    print(f"Região: {region}")
    print(f"Porta: {port}")
    print("Permissões revogadas:")
    for schema in schemas:
        print(f"  - Schema: {schema['nome']} → {', '.join(schema['permissions'])}")

if __name__ == "__main__":
    revoke_permissions(sys.argv[1])
    