import boto3
import yaml
import os
import sys

VALID_ENGINES = ["postgres", "postgresql", "mysql"]

VALID_PERMISSIONS_POSTGRES = [
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "TRUNCATE", "REFERENCES", "TRIGGER", "USAGE",
    "EXECUTE", "CREATE", "TEMP", "ALL PRIVILEGES"
]

VALID_PERMISSIONS_MYSQL = [
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "CREATE", "DROP", "INDEX", "ALTER",
    "REFERENCES", "EXECUTE", "USAGE", "ALL PRIVILEGES"
]

def validate_yaml(data):
    required_fields = ["host", "user", "database", "engine", "region", "schemas"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Campo obrigatório ausente: {field}")

    if not isinstance(data["user"], str):
        raise ValueError("Campo 'user' deve ser uma string")

    if not isinstance(data["database"], str):
        raise ValueError("Campo 'database' deve ser uma string")

    engine = data["engine"].lower()
    if engine not in VALID_ENGINES:
        raise ValueError(f"Engine inválido: {data['engine']}")

    valid_permissions = VALID_PERMISSIONS_POSTGRES if "postgres" in engine else VALID_PERMISSIONS_MYSQL

    if not isinstance(data["schemas"], list) or len(data["schemas"]) == 0:
        raise ValueError("Campo 'schemas' deve ser uma lista com ao menos um item")

    for schema in data["schemas"]:
        if "nome" not in schema or "permissions" not in schema:
            raise ValueError("Cada schema deve conter 'nome' e 'permissions'")
        if not isinstance(schema["permissions"], list):
            raise ValueError(f"'permissions' no schema {schema['nome']} deve ser uma lista")
        for perm in schema["permissions"]:
            if perm.upper() not in valid_permissions:
                raise ValueError(f"Permissão inválida: {perm} (schema: {schema['nome']})")

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

def apply_postgres_permissions(conn, username, schemas):
    with conn.cursor() as cur:
        cur.execute(f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{username}') THEN CREATE ROLE \"{username}\" WITH LOGIN; END IF; END $$;")
        for schema in schemas:
            for perm in schema['permissions']:
                cur.execute(
                    f'GRANT {perm.upper()} ON ALL TABLES IN SCHEMA {schema["nome"]} TO "{username}";')
        conn.commit()

def apply_mysql_permissions(conn, username, database, schemas):
    with conn.cursor() as cur:
        cur.execute(f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED VIA AWSAuthenticationPlugin AS 'RDS';")
        for schema in schemas:
            for perm in schema['permissions']:
                cur.execute(
                    f'GRANT {perm.upper()} ON `{database}`.`{schema["nome"]}` TO \'{username}\'@\'%\';')
        conn.commit()

def apply_permissions(yaml_path):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    validate_yaml(data)

    engine = data["engine"].lower()
    if engine not in ["postgres", "postgresql", "mysql"]:
        raise Exception(f"Engine não suportado: {engine}")

    user = os.environ["DB_USER"]
    password = os.environ["DB_PASS"]
    host = data["host"]
    region = data["region"]
    dbname = data["database"]
    target_user = data["user"]
    schemas = data["schemas"]

    port = int(data.get("port", 5432 if "postgres" in engine else 3306))

    if "postgres" in engine:
        conn = connect_postgres(host, port, user, token, dbname)
        apply_postgres_permissions(conn, target_user, schemas)
    elif "mysql" in engine:
        conn = connect_mysql(host, port, user, token, dbname)
        apply_mysql_permissions(conn, target_user, dbname, schemas)

    conn.close()
    print("\nPermissões aplicadas com sucesso!\n")
    print(f"Usuário: {target_user}")
    print(f"Banco: {dbname}")
    print(f"Engine: {engine}")
    print(f"Região: {region}")
    print(f"Porta: {port}")
    print("Schemas e permissões aplicadas:")

    for schema in schemas:
        perms = ", ".join([p.upper() for p in schema["permissions"]])
        print(f"  - Schema: {schema['nome']} → Permissões: {perms}")

if __name__ == "__main__":
    apply_permissions(sys.argv[1])
