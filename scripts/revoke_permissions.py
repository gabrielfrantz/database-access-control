import boto3
import os
import sys
import yaml

VALID_ENGINES = ["postgres", "postgresql", "mysql"]

def validate_yaml(data):
    if 'user' not in data or 'database' not in data or 'engine' not in data or 'region' not in data:
        raise ValueError("YAML incompleto para revogação")

def generate_token(user, host, port, region):
    return boto3.client('rds', region).generate_db_auth_token(
        DBHostname=host, Port=port, DBUsername=user)

def connect_postgres(host, port, user, token, database):
    import psycopg2
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=token,
        dbname=database,
        sslmode='require')

def connect_mysql(host, port, user, token, database):
    import pymysql
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=token,
        database=database,
        ssl={"ssl": {}})

def revoke_postgres_permissions(conn, username):
    with conn.cursor() as cur:
        cur.execute(f'REASSIGN OWNED BY "{username}" TO CURRENT_USER;')
        cur.execute(f'DROP OWNED BY "{username}";')
        cur.execute(f'DROP ROLE IF EXISTS "{username}";')
    conn.commit()

def revoke_mysql_permissions(conn, username):
    with conn.cursor() as cur:
        cur.execute(f"DROP USER IF EXISTS '{username}'@'%';")
    conn.commit()

def revoke_permissions(yaml_path):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    validate_yaml(data)

    engine = data['engine'].lower()
    if engine not in VALID_ENGINES:
        raise ValueError(f"Engine não suportado: {engine}")

    user = data['user']
    host = data['host']
    dbname = data['database']
    region = data['region']
    target_user = data['user']
    port = int(data.get('port', 5432 if 'postgres' in engine else 3306))

    token = generate_token(user, host, port, region)

    if 'postgres' in engine:
        conn = connect_postgres(host, port, user, token, dbname)
        revoke_postgres_permissions(conn, target_user)
    elif 'mysql' in engine:
        conn = connect_mysql(host, port, user, token, dbname)
        revoke_mysql_permissions(conn, target_user)

    conn.close()
    print("\nPermissões revogadas com sucesso!\n")
    print(f"Usuário: {target_user}")
    print(f"Banco: {dbname}")
    print(f"Engine: {engine}")
    print(f"Região: {region}")
    print(f"Porta: {port}")

if __name__ == "__main__":
    revoke_permissions(sys.argv[1])