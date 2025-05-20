# 🔐 RDS Access GitOps via GitHub Actions

Este repositório implementa uma solução GitOps para **criação, atualização e revogação de permissões** de acesso a bancos de dados RDS (PostgreSQL, MySQL, Aurora) na AWS utilizando GitHub Actions.

---

## ✅ Objetivo

Gerenciar acessos a bancos de dados com:
- Versionamento completo via Git
- Automação via Pull Request
- Segurança com autenticação IAM
- Separação por ambiente (`dev`, `stg`, `prod`)

---

## 🧱 Estrutura

```
.github/
  workflows/
    request-access.yml     # Entrada manual via formulário + PR automático
    apply-access.yml       # Aplica/revoga permissões ao merge

scripts/
  apply_permissions.py     # Aplica permissões a partir de YAML
  revoke_permissions.py    # Revoga permissões ao remover YAML

access-requests/
  dev/
  stg/
  prod/

requirements.txt
```

---

## 🚀 Etapas de Configuração

### 1. Criar banco no Amazon RDS

- Engine: PostgreSQL, MySQL ou Aurora
- Habilite **IAM authentication**
- Configure a VPC para acesso externo (via NAT, VPN, ou bastion)
- Exemplo: `rds-access-control-test`

---

### 2. Criar Role IAM com OIDC para GitHub

1. IAM > Identity providers > Add provider:
   - URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`

2. Criar role com permissões:
```json
{
  "Effect": "Allow",
  "Action": [
    "rds:GenerateDBAuthToken",
    "rds-db:connect"
  ],
  "Resource": "*"
}
```

3. Bloco de confiança:
```json
{
  "Effect": "Allow",
  "Principal": {
    "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringLike": {
      "token.actions.githubusercontent.com:sub": "repo:<owner>/<repo>:*"
    },
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
    }
  }
}
```

---

### 3. Dependências Python

Arquivo `requirements.txt`:
```txt
boto3
PyYAML
psycopg2-binary
pymysql
```

---

## 🛠️ Como Usar

### 📝 Solicitar acesso (criação/atualização)

1. Vá em **GitHub Actions > request-access**
2. Clique em "Run workflow"
3. Preencha os campos:
   - `email`: IAM user (ex: `gabriel.frantz@empresa.com`)
   - `engine`: `postgres`, `mysql`, `aurora`
   - `ambiente`: `dev`, `stg`, `prod`
   - `database`, `region`, `port`, `host`
   - `schemas`: JSON com permissões (ex: `[{"nome":"public","permissions":["SELECT"]}]`)
4. O workflow:
   - Gera um arquivo em `access-requests/<ambiente>/<user>-<engine>-<database>.yml`
   - Cria uma branch e um Pull Request

### ✅ Aplicar permissões

- Após **merge do PR**, o workflow `apply-access.yml` será executado:
  - Aplica permissões com `apply_permissions.py`
  - Revoga permissões com `revoke_permissions.py` (se o arquivo for removido)

### ❌ Revogar permissões

- Rode `request-access.yml` novamente com `revogar = true`
- O arquivo YAML será deletado + novo PR criado
- Após merge, o acesso será revogado automaticamente

---

## 📦 Arquivos YAML de exemplo

```yaml
user: gabriel.frantz@empresa.com
host: db.example.rds.amazonaws.com
database: appdb
engine: postgres
region: us-east-1
port: 5432
schemas:
  - nome: public
    permissions:
      - SELECT
      - INSERT
```

---

## 🔐 Segurança

- IAM Roles com OIDC (sem chave secreta)
- Autenticação via token temporário (`generate_db_auth_token`)
- Nenhum secret armazenado no repositório
- Todo acesso passa por PR + revisão

---

## 🧠 Benefícios

- Git como fonte de verdade dos acessos
- Histórico de mudanças completo
- Automação de provisionamento e revogação
- Suporte multi-engine: PostgreSQL, MySQL, Aurora

---

## 📎 Requisitos mínimos

- GitHub Actions habilitado
- Banco RDS com IAM authentication ativado
- Permissões IAM corretas
- Acesso de rede da action ao RDS (via NAT/VPN)

---

## 🙋‍♂️ Dúvidas?

Abra uma Issue ou PR com sugestões e melhorias 🚀