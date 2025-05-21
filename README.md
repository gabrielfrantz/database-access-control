# 🔐 RDS Access GitOps via GitHub Actions (Atualizado)

Este repositório implementa uma solução GitOps para **criação, atualização e revogação de permissões** de acesso a bancos de dados RDS (PostgreSQL, MySQL, Aurora) na AWS utilizando GitHub Actions.

---

## ✅ Objetivo

Gerenciar acessos a bancos de dados com:
- Versionamento completo via Git
- Automação via Pull Request
- Segurança com autenticação via owner tradicional (usuário/senha do RDS)
- Integração com Parameter Store para múltiplas bases

---

## 🧱 Estrutura do Projeto

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
README.md
```

---

## 🏗️ Etapas na AWS

### 1. Criar Banco RDS

- Engine: PostgreSQL ou MySQL
- Identificador: `rds-access-control-dev`
- Porta: `5432` (PostgreSQL) ou `3306` (MySQL)
- Usuário admin: `rdsadmin` (por exemplo)
- Marcar ✅ **Enable IAM authentication** (opcional)
- VPC com acesso via NAT Gateway, Bastion ou VPN

---

### 2. Criar Parâmetros no Parameter Store

Crie parâmetros no AWS Systems Manager > Parameter Store:

| Nome do parâmetro                                 | Tipo         | Valor         |
|---------------------------------------------------|--------------|---------------|
| `/rds-access-control/appdb-postgres/user`         | SecureString | `rdsadmin`    |
| `/rds-access-control/appdb-postgres/password`     | SecureString | senha do user |

Repita isso para cada `database-engine` que quiser controlar.

---

### 3. Criar Role IAM com OIDC

#### 3.1. Adicionar provedor OIDC no IAM

- URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

#### 3.2. Criar Role: `GitHubActions_RDSAccessRole`

**Trust Policy:**
```json
{
  "Effect": "Allow",
  "Principal": {
    "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
    },
    "StringLike": {
      "token.actions.githubusercontent.com:sub": "repo:<owner>/<repo>:*"
    }
  }
}
```

**Policy anexada:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameter"],
      "Resource": "arn:aws:ssm:*:*:parameter/rds-access-control/*"
    },
    {
      "Effect": "Allow",
      "Action": ["rds-db:connect"],
      "Resource": "*"
    }
  ]
}
```

---

### 4. Configurar GitHub Secrets

| Nome                 | Valor (exemplo)                                         |
|----------------------|----------------------------------------------------------|
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::<account_id>:role/GitHubActions_RDSAccessRole` |

> Você não precisa mais de DB_ADMIN nem DB_HOST!

---

## 🚀 Como Usar

### ✅ Solicitar acesso

1. Vá no GitHub Actions > `request-access.yml`
2. Clique em "Run workflow"
3. Preencha:
   - `email`: usuário SSO (ex: `gabriel.frantz@empresa.com`)
   - `engine`: `postgres`, `mysql`
   - `database`: nome da base (ex: `appdb`)
   - `host`, `port`, `region`
   - `schemas` (exemplo):
     ```json
     [
       {"nome": "public", "permissions": ["SELECT", "INSERT"]}
     ]
     ```
4. O workflow:
   - Busca os dados do owner no Parameter Store
   - Cria YAML em `access-requests/<ambiente>/<user>-<engine>-<db>.yml`
   - Abre Pull Request

5. Após o merge:
   - `apply-access.yml` roda `apply_permissions.py`

---

### ❌ Revogar acesso

1. Execute novamente `request-access.yml`
2. Marque `revogar = true`
3. O arquivo YAML será removido
4. O PR será criado
5. Após merge, o `revoke_permissions.py` será executado

---

## 🔐 Segurança

- Zero secrets no repositório
- Autenticação via Parameter Store criptografado (SecureString)
- Controle por ambiente
- Acesso via Pull Request (auditoria completa)

---

## 📎 Exemplo de arquivo YAML gerado

```yaml
user: gabriel.frantz@empresa.com
host: db.app.rds.amazonaws.com
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

## 🧠 Benefícios

- Git como fonte de verdade
- Segurança centralizada
- Múltiplos ambientes e bancos
- Fluxo auditável e controlado
- GitHub Actions como orquestrador confiável

---

## 📌 Requisitos

- Banco RDS com IAM ou usuário owner
- Parameter Store com usuário/senha por banco/engine
- GitHub Actions habilitado no repositório
- Permissão para rodar workflows e revisar PRs

---

## 🙋‍♂️ Dúvidas?
Abra uma issue ou crie um PR com sugestões! 🚀