# 🔐 Sistema de Controle de Acesso a Bancos de Dados via GitHub Actions

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Enabled-blue?logo=github-actions)](https://github.com/features/actions)
[![AWS RDS](https://img.shields.io/badge/AWS-RDS-orange?logo=amazon-aws)](https://aws.amazon.com/rds/)
[![SSO](https://img.shields.io/badge/Auth-SSO%20Token-green?logo=aws)](https://aws.amazon.com/iam/)
[![Security](https://img.shields.io/badge/Security-Validated-green?logo=shield)](https://github.com)

Sistema GitOps para gerenciamento automatizado de permissões de acesso a bancos de dados RDS na AWS via **GitHub Actions**, com autenticação **SSO** e tokens temporários.

## 📋 Índice

- [🎯 Visão Geral](#-visão-geral)
- [✨ Funcionalidades](#-funcionalidades)
- [🏗️ Arquitetura](#️-arquitetura)
- [📋 Pré-requisitos](#-pré-requisitos)
- [⚙️ Configuração AWS](#️-configuração-aws)
- [🔐 Configuração GitHub](#-configuração-github)
- [🚀 Como Usar](#-como-usar)
- [📊 Relatórios de Auditoria](#-relatórios-de-auditoria)
- [🔒 Hierarquia de Permissões](#-hierarquia-de-permissões)
- [🧪 Testes e Validação](#-testes-e-validação)
- [📁 Estrutura do Projeto](#-estrutura-do-projeto)
- [📖 Exemplos de Uso](#-exemplos-de-uso)

## 🎯 Visão Geral

Este sistema implementa um **controle de acesso GitOps** para bancos de dados RDS via **GitHub Actions**, com:

- 🔐 **Autenticação SSO** com tokens temporários
- 🔄 **Automação completa** via workflows GitHub Actions
- 🛡️ **Validação de segurança** obrigatória
- 📊 **Relatórios de auditoria** automáticos
- 🎯 **Permissões granulares** por schema e tabela
- 🌍 **Separação por ambientes** (dev/stg/prod)
- ✅ **Aprovação via Pull Request** obrigatória

## ✨ Funcionalidades

### 🔐 Controle de Acesso
- ✅ **MySQL**, **PostgreSQL** e **Aurora** via SSO
- ✅ Permissões granulares por **schema** e **tabela**
- ✅ **Tokens temporários** gerados automaticamente
- ✅ **Aprovação obrigatória** via Pull Request
- ✅ **Aplicação automática** após merge

### 📊 Relatórios e Auditoria
- ✅ Relatórios **HTML** e **JSON** automáticos
- ✅ **Download via GitHub Actions** artifacts
- ✅ **Estatísticas detalhadas** de permissões

### 🛡️ Segurança
- ✅ **Autenticação SSO** obrigatória
- ✅ **Tokens temporários** (15 minutos)
- ✅ **Validação de segurança** em todas as operações
- ✅ **Aprovação manual** para produção
- ✅ **Auditoria completa** via Git

### 🔄 Fluxo de Trabalho

1. **Criação**: Desenvolvedor solicita criação de usuário no banco de dados com determinadas permissões
2. **Pull Request**: Submete PR para revisão
3. **Validação**: GitHub Actions executa validação automática
4. **Aguardar aprovação** (manual para todos os ambientes: dev/stg/prod)
5. **Merge**: Aprovação e merge do PR
6. **Execução**: Workflow específico do engine é executado
7. **OIDC**: Token OIDC é gerado pelo GitHub Actions
8. **Assume Role**: Role IAM é assumida via OIDC
9. **Parameter Store**: Credenciais do owner são recuperadas
10. **Aplicação**: Permissões são aplicadas no RDS
11. **Relatório**: Relatório de auditoria é gerado automaticamente

## 📋 Pré-requisitos

### 🔧 Tecnologias
- **GitHub Actions** habilitado no repositório
- **AWS Account** com RDS configurado
- **RDS** com "Password and IAM database authentication" habilitado
- **AWS SSO** configurado para usuários

### 🔑 Permissões AWS
- **RDS**: Acesso via SSO com tokens temporários
- **Parameter Store**: Leitura de credenciais do owner
- **IAM**: Geração de tokens de autenticação
- **OIDC**: Provedor configurado para GitHub Actions

### ⚠️ Importante
- ❌ **NÃO há execução local** - apenas via GitHub Actions
- ✅ **Apenas usuários SSO** podem receber permissões
- ✅ **Aprovação obrigatória** via Pull Request
- ✅ **Autenticação via OIDC** - sem credenciais estáticas

## ⚙️ Configuração AWS

### 1. 🔐 Configurar Provedor OIDC

Adicione o provedor OIDC no IAM:

```bash
# Via AWS CLI
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. 🛡️ Criar Role IAM para GitHub Actions

Crie uma role IAM: `GitHubActions_RDSAccessRole`

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
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
  ]
}
```

**Permissions Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/database-access-control/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds-db:connect"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetUser",
        "iam:ListUsers"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. 📋 Parameter Store

Crie parâmetros no AWS Systems Manager > Parameter Store > rds-access-control:

```bash
# Para MySQL
database_dev-mysql-user=user
database_dev-mysql-password=password

# Para PostgreSQL
database_prod-postgres-user=user
database_prod-postgres-password=password

# Para Aurora
database_stg-aurora-user=user
database_stg-aurora-password=password
```

## 🔐 Configuração GitHub

### 1. 🔑 GitHub Secrets

Configure os seguintes secrets no repositório (adicione dentro de algum Environment):

```bash
# Role IAM para autenticação via OIDC
AWS_ROLE_TO_ASSUME=arn:aws:iam::<account_id>:role/GitHubActions_RDSAccessRole

# Região AWS (opcional - pode ser configurada no Parameter Store)
AWS_REGION=us-east-1
```

> **⚠️ Importante**: Não são necessárias credenciais estáticas (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`). A autenticação é feita via **OIDC** com a role IAM.

### 2. 🌍 GitHub Environments

Crie os seguintes environments com proteção:

#### Environment: `dev`
- ✅ **Aprovação**: Manual
- ✅ **Revisores**: 1 pessoa obrigatória
- ✅ **Timeout**: 15 minutos

#### Environment: `stg`
- ✅ **Aprovação**: Manual
- ✅ **Revisores**: 1 pessoa obrigatória
- ✅ **Timeout**: 30 minutos

#### Environment: `prod`
- ✅ **Aprovação**: Manual
- ✅ **Revisores**: 2 pessoas obrigatórias
- ✅ **Timeout**: 60 minutos
- ✅ **Branches**: Apenas `main`

## 🚀 Como Usar

### 1. 📝 Criar Solicitação de Acesso

Crie um arquivo YAML na estrutura hierárquica através do workflow desejado:

```yaml
# users-access-requests/dev/mysql/database_dev/usuario@empresa.com.yml
host: dev-mysql.rds.amazonaws.com
user: usuario@empresa.com
database: database_dev
engine: mysql
region: us-east-1
port: 3306
schemas:
- nome: produtos
  permissions:
    - SELECT
    - INSERT
    - UPDATE
  tables:
  - nome: produtos_precos
    permissions:
      - SELECT  # Apenas leitura para dados sensíveis
- nome: usuarios
  permissions:
    - SELECT
```

### 2. 🔄 Submeter Pull Request

1. **Commit** o arquivo YAML
2. **Push** para uma branch
3. **Criar Pull Request** para `main`
4. **Aguardar aprovação** (manual para todos os ambientes: dev/stg/prod)

### 3. ⚙️ Executar Workflow após Merge

Após o merge do PR, execute o workflow específico:

#### MySQL Access
```bash
# GitHub Actions > MySQL Access Control
# Inputs:
# - Environment: dev/stg/prod
# - User Email: usuario@empresa.com
```

#### PostgreSQL/Aurora Access
```bash
# GitHub Actions > PostgreSQL Aurora Access Control
# Inputs:
# - Environment: dev/stg/prod
# - User Email: usuario@empresa.com
```

### 4. 📊 Gerar Relatórios

```bash
# GitHub Actions > Generate Audit Reports
# Inputs:
# - User Email: usuario@empresa.com
# - Format: html/json
```

## 📊 Relatórios de Auditoria

### 🎨 Formatos Disponíveis

#### 📄 HTML (Recomendado)
- Interface moderna e responsiva
- Cards estatísticos por ambiente
- Badges coloridos por engine
- Download automático via GitHub Actions

#### 📋 JSON (Automação)
- Estrutura hierárquica completa
- Ideal para integração com ferramentas
- Dados estruturados para análise

### 📈 Como Gerar

1. **Acesse**: GitHub Actions > "Generate Audit Reports"
2. **Configure**:
   - User Email: `usuario@empresa.com`
   - Format: `html` ou `json`
3. **Execute**: Run workflow
4. **Download**: Artifacts gerados automaticamente

### 📋 Tipos de Relatórios

- **👤 Usuário**: Todas as permissões de um usuário específico
- **🗄️ Banco**: Todos os usuários com acesso a um banco

## 🔒 Hierarquia de Permissões

### 🎯 Regra Fundamental
```
Permissões Específicas > Permissões Gerais
Tabela > Schema > Database
```

### 📋 Exemplo Prático

```yaml
schemas:
- nome: financeiro
  permissions: [SELECT, INSERT, UPDATE, DELETE]  # Schema permite tudo
  tables:
  - nome: salarios
    permissions: [SELECT]  # Tabela permite apenas leitura
```

**Resultado**: Usuário **NÃO pode** alterar dados da tabela `salarios`, mesmo tendo permissão no schema.

### 🛡️ Princípio de Segurança

- ✅ **Menor Privilégio**: Sempre aplicar a permissão mais restritiva
- ✅ **Granularidade**: Controle fino por tabela
- ✅ **Herança**: Tabelas herdam permissões do schema quando não especificado
- ✅ **Precedência**: Permissões de tabela sempre prevalecem

## 🧪 Testes e Validação

### 🔍 Validação Automática

Todos os workflows executam validação obrigatória:

```bash
# Executado automaticamente em todos os workflows
python scripts/security_validator.py
```

**Verificações realizadas:**
- ✅ **Credenciais**: Nenhuma credencial exposta nos arquivos
- ✅ **Permissões**: Princípio do menor privilégio aplicado
- ✅ **Estrutura**: Arquivos YAML válidos
- ✅ **Ambientes**: Separação adequada entre ambientes

### 🧪 Como Testar

#### 1. Teste de Validação
```bash
# GitHub Actions > Reusable Security Check
# Executa automaticamente em todos os workflows
```

#### 2. Teste de Conexão
```bash
# GitHub Actions > MySQL/PostgreSQL Access
# Modo: dry-run (apenas testa conexão)
```

#### 3. Teste de Relatórios
```bash
# GitHub Actions > Generate Audit Reports
# Gera relatório de teste para validar funcionamento
```

### ✅ Critérios de Aprovação

Para que um workflow seja executado com sucesso:

1. **✅ Validação de Segurança**: Deve passar sem erros
2. **✅ Aprovação Manual**: Para ambientes stg/prod
3. **✅ OIDC Authentication**: Deve assumir role com sucesso
4. **✅ Conexão RDS**: Deve conectar com sucesso
5. **✅ Aplicação**: Permissões devem ser aplicadas corretamente

## 📁 Estrutura do Projeto

```
database-access-control/
├── 📄 README.md                        # Documentação completa
├── 📄 requirements.txt                 # Dependências Python
├── 📄 .gitignore                       # Arquivos ignorados
├── 📁 .github/workflows/               # GitHub Actions
│   ├── 🔄 mysql_access.yml            # Workflow MySQL
│   ├── 🔄 postgresql_aurora_access.yml # Workflow PostgreSQL/Aurora
│   ├── 🔄 apply_access.yml            # Aplicação geral
│   ├── 🔄 generate-audit-reports.yml  # Geração de relatórios
│   └── 🔄 reusable-security-check.yml # Validação de segurança
├── 📁 scripts/                        # Scripts Python
│   ├── 🐍 apply_permissions.py        # Aplicar permissões
│   ├── 🐍 revoke_permissions.py       # Revogar permissões
│   ├── 🐍 merge_permissions.py        # Merge de permissões
│   ├── 🐍 generate_audit_reports.py   # Gerar relatórios
│   └── 🐍 security_validator.py       # Validação de segurança
└── 📁 users-access-requests/          # Solicitações de acesso
    ├── 📁 dev/                        # Ambiente desenvolvimento
    ├── 📁 stg/                        # Ambiente staging
    └── 📁 prod/                       # Ambiente produção
```

### 📂 Estrutura Hierárquica

```
users-access-requests/
└── {environment}/          # dev, stg, prod
    └── {engine}/           # mysql, postgres, aurora
        └── {database}/     # nome_do_banco
            └── {user}.yml  # usuario@empresa.com.yml
```

### 🔄 Fluxo Completo

1. **Criar arquivo YAML** com permissões necessárias via workflow
2. **Commit e push** para branch feature
3. **Criar Pull Request** para main
4. **Aguardar aprovação** (manual para todos os ambientes: dev/stg/prod)
5. **Merge** após aprovação
6. **Executar workflow** específico do engine via GitHub Actions
7. **OIDC authentication** e assume role automático
8. **Aguardar aplicação** das permissões
9. **Download do relatório** via artifacts
10. **Validar acesso** no banco de dados

---

## 🔐 Segurança e Compliance

### 🛡️ Controles Implementados

- ✅ **Autenticação OIDC** sem credenciais estáticas
- ✅ **Autenticação SSO** obrigatória
- ✅ **Tokens temporários** (15 minutos)
- ✅ **Aprovação manual** para produção
- ✅ **Validação automática** de segurança
- ✅ **Auditoria completa** via Git
- ✅ **Princípio do menor privilégio**
- ✅ **Separação de ambientes**

### 📋 Compliance

Este sistema atende aos requisitos de:
- **SOX** - Controles de acesso e auditoria
- **GDPR** - Proteção de dados pessoais
- **ISO 27001** - Gestão de segurança da informação
- **PCI DSS** - Proteção de dados de cartão

---

**🔐 Sistema desenvolvido seguindo as melhores práticas de DevSecOps e GitOps**
