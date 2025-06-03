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
- [⚙️ Workflows Disponíveis](#️-workflows-disponíveis)
- [🔄 Detecção Automática de Ambiente](#-detecção-automática-de-ambiente)
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
- 🌍 **Separação por ambientes** (development/staging/production)
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

## 🏗️ Arquitetura

```mermaid
graph TB
    A[Desenvolvedor] --> B[Criar YAML]
    B --> C[Pull Request]
    C --> D[GitHub Actions]
    D --> E[Validação Segurança]
    E --> F{Aprovação?}
    F -->|Sim| G[Merge PR]
    F -->|Não| H[Rejeitar]
    G --> I[Workflow Engine]
    I --> J[OIDC Token]
    J --> K[Assume Role IAM]
    K --> L[Parameter Store]
    L --> M[Token SSO]
    M --> N[RDS Connection]
    N --> O[Aplicar Permissões]
    O --> P[Gerar Relatórios]
    P --> Q[GitHub Artifacts]
```

### 🔄 Fluxo de Trabalho

1. **Criação**: Desenvolvedor solicita criação de usuário no banco de dados com determinadas permissões
2. **Pull Request**: Submete PR para revisão
3. **Validação**: GitHub Actions executa validação automática
4. **Aguardar aprovação** (manual para todos os ambientes: development/staging/production)
5. **Merge**: Aprovação e merge do PR
6. **Aplicação Automática**: `apply_access.yml` executa automaticamente após merge
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
          "token.actions.githubusercontent.com:sub": "repo:<owner>/<repo>:<environment>:*"
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
# Padrão: {database}-{engine}-{tipo}
# Para MySQL
ecommerce-mysql-user=admin_user
ecommerce-mysql-password=secure_password

# Para PostgreSQL
analytics-postgres-user=pg_admin
analytics-postgres-password=pg_secure

# Para Aurora
financial-aurora-user=aurora_admin
financial-aurora-password=aurora_secure
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

#### Environment: `development`
- ✅ **Aprovação**: Manual
- ✅ **Revisores**: 1 pessoa obrigatória
- ✅ **Timeout**: 15 minutos

#### Environment: `staging`
- ✅ **Aprovação**: Manual
- ✅ **Revisores**: 1 pessoa obrigatória
- ✅ **Timeout**: 30 minutos

#### Environment: `production`
- ✅ **Aprovação**: Manual
- ✅ **Revisores**: 2 pessoas obrigatórias
- ✅ **Timeout**: 60 minutos
- ✅ **Branches**: Apenas `main`

## 🚀 Como Usar

### 🧙‍♂️ Método Principal: Wizards Interativos (Recomendado)

O sistema oferece **wizards interativos** em 2 passos para criar solicitações de acesso de forma guiada e intuitiva:

#### 🐬 MySQL Wizard (2 Passos) - **MÉTODO RECOMENDADO**
**🎯 Processo Simplificado e Guiado**

**Passo 1 - Configuração Básica**:
   - **Acesse**: GitHub Actions > "MySQL - Wizard Passo 1: Configuração Básica"
   - **Configure**: ambiente, email, host, database, região, porta
   - **Execute**: Run workflow
   - **Resultado**: Session ID gerado para o próximo passo

**Passo 2 - Seleção de Permissões**:
   - **Acesse**: GitHub Actions > "MySQL - Wizard Passo 2: Seleção de Permissões"
   - **Configure**: Session ID, schema, tabelas (opcional), permissões
   - **Permissões DML**: SELECT, INSERT, UPDATE, DELETE
   - **Permissões DDL**: CREATE, DROP, ALTER, INDEX
   - **⚠️ Importante**: Se nenhuma permissão for marcada, o sistema aplicará **ALL PRIVILEGES** automaticamente
   - **Execute**: Run workflow
   - **Resultado**: Pull Request criado automaticamente

#### 🐘 PostgreSQL/Aurora Wizard (2 Passos) - **MÉTODO RECOMENDADO**
**🎯 Processo Simplificado e Guiado**

**Passo 1 - Configuração Básica**:
   - **Acesse**: GitHub Actions > "PostgreSQL/Aurora - Wizard Passo 1: Configuração Básica"
   - **Configure**: ambiente, email, host, database, região, porta, engine_type (postgres/aurora)
   - **Execute**: Run workflow
   - **Resultado**: Session ID gerado para o próximo passo

**Passo 2 - Seleção de Permissões**:
   - **Acesse**: GitHub Actions > "PostgreSQL/Aurora - Wizard Passo 2: Seleção de Permissões"
   - **Configure**: Session ID, schema, tabelas (opcional), permissões
   - **Permissões DML**: SELECT, INSERT, UPDATE, DELETE
   - **Permissões Específicas**: CREATE, TRIGGER, EXECUTE, CONNECT
   - **⚠️ Importante**: Se nenhuma permissão for marcada, o sistema aplicará **ALL PRIVILEGES** automaticamente
   - **Execute**: Run workflow
   - **Resultado**: Pull Request criado automaticamente

### 🔑 Vantagens dos Wizards
- **🎯 Interface Simplificada**: Processo guiado em etapas
- **🛡️ Validação Robusta**: Validação automática de Session IDs e entrada
- **🧹 Gestão de Estado**: Arquivos temporários gerenciados automaticamente
- **⚡ ALL PRIVILEGES**: Aplica automaticamente quando nenhuma permissão específica é selecionada
- **🔄 Flexibilidade**: Suporte a permissões por schema ou tabelas específicas
- **📝 Auditoria**: Logs detalhados de cada etapa do processo
- **🛡️ Segurança**: Validação de segurança obrigatória em ambos os passos

---

### 📋 Métodos Alternativos (Para Casos Especiais)

<details>
<summary>🔧 Workflows Diretos (Para usuários avançados)</summary>

#### 🐬 MySQL Access Control (Direto)
⚠️ **NOTA**: Use apenas se precisar de controle avançado ou automação. **Para uso normal, prefira o MySQL Wizard**.

1. **Acesse**: GitHub Actions > "MySQL Access Control"
2. **Configure**:
   - **Ambiente**: development/staging/production
   - **Email**: usuario@empresa.com
   - **Database**: nome_do_banco
   - **Host**: host.rds.amazonaws.com
   - **Schema**: nome_do_schema
   - **Permissões**: JSON completo (copie de examples-permissions/)
3. **Execute**: Run workflow
4. **Resultado**: Pull Request criado automaticamente

#### 🐘 PostgreSQL/Aurora Access Control (Direto)
⚠️ **NOTA**: Use apenas se precisar de controle avançado ou automação. **Para uso normal, prefira o PostgreSQL/Aurora Wizard**.

1. **Acesse**: GitHub Actions > "PostgreSQL Aurora Access Control"  
2. **Configure**:
   - **Ambiente**: development/staging/production
   - **Engine**: postgres ou aurora
   - **Email**: usuario@empresa.com
   - **Database**: nome_do_banco
   - **Host**: host.rds.amazonaws.com
   - **Schema**: nome_do_schema
   - **Permissões**: JSON completo (copie de examples-permissions/)
3. **Execute**: Run workflow
4. **Resultado**: Pull Request criado automaticamente

</details>

### 🔄 Processo Completo de Aprovação e Aplicação

#### 1. 🔄 Aprovação e Merge

1. **Revisar**: Pull Request criado automaticamente pelo wizard
2. **Validar**: Arquivo YAML gerado com permissões corretas
3. **Aprovar**: Reviewer aprova o PR
4. **Merge**: Fazer merge para branch `main`

#### 2. 🤖 Aplicação Automática

1. **Detecção**: `apply_access.yml` detecta ambiente automaticamente pelo path
2. **Validação**: Executa validação de segurança obrigatória  
3. **Aprovação**: Aguarda aprovação manual do environment detectado
4. **Aplicação**: Aplica permissões no banco de dados correto
5. **Logs**: Gera logs detalhados da operação no GitHub Actions

#### 3. 📝 Gerar Relatórios (Opcional)

- **📝 Finalidade**: Gerar relatórios de auditoria e relatórios gerais
- **🔧 Uso**: Workflow manual via GitHub Actions
- **📋 Inputs**:
  - **Tipo de relatório**:
    - `usuario-especifico`: Relatório de um usuário específico
    - `todos-usuarios`: Relatório geral de todos os usuários
  - `user_email`: Email do usuário (obrigatório apenas para relatório específico)
  - `database_name`: Nome do banco específico (opcional para relatório específico)
  - `output_format`: html ou json (JSON não suportado para relatório geral)
- **📤 Output**: Relatórios disponíveis nos artifacts do workflow
- **🎯 Scripts utilizados**:
  - **Específico**: `generate_audit_reports.py` 
  - **Geral**: `generate_general_report.py`

#### 📋 Tipos de Relatórios

##### 👤 Relatório Específico (Usuario-Específico)
- **Escopo**: Todas as permissões de um usuário específico
- **Scripts**: `generate_audit_reports.py`
- **Casos de uso**:
  - **Usuário + Todos os bancos**: Relatório completo do usuário
  - **Usuário + Banco específico**: Relatório filtrado por banco
- **Formato**: HTML ou JSON

##### 👥 Relatório Geral (Todos-Usuários)
- **Escopo**: Visão consolidada de todos os usuários do sistema
- **Scripts**: `generate_general_report.py`
- **Casos de uso**:
  - **Auditoria geral**: Visão executiva de todas as permissões
  - **Compliance**: Relatório para auditorias regulares
  - **Administração**: Gestão centralizada de acessos
- **Formato**: HTML (JSON não suportado para relatório geral)

## 🔄 Detecção Automática de Ambiente

### 🎯 Workflow `apply_access.yml`

O sistema possui um **workflow principal** (`apply_access.yml`) que é executado **automaticamente** após o merge de qualquer Pull Request que modifique arquivos na pasta `users-access-requests/`.

### 🔍 Como Funciona a Detecção

1. **Trigger Automático**: O workflow é disparado automaticamente quando:
   - Há push para a branch `main`
   - Arquivos modificados estão no path `users-access-requests/**.yml`

2. **Extração do Ambiente**: O job `extract-environment` analisa o caminho dos arquivos modificados:
   ```bash
   # Exemplo de detecção:
   users-access-requests/development/mysql/ecommerce/user.yml → development
   users-access-requests/staging/postgres/analytics/user.yml → staging  
   users-access-requests/production/aurora/financial/user.yml → production
   ```

3. **Regex de Detecção**: Utiliza o padrão `users-access-requests/([^/]+)/` para extrair o ambiente
   - **Sucesso**: Usa o ambiente detectado
   - **Fallback**: Se não conseguir detectar, usa `development` como padrão

4. **Aplicação Dinâmica**: O ambiente detectado é passado automaticamente para o job `apply-access`:
   ```yaml
   environment: ${{ needs.extract-environment.outputs.ambiente }}
   ```

### ✅ Vantagens da Detecção Automática

- **🔄 Zero Configuração**: Não precisa especificar ambiente manualmente
- **🎯 Precisão**: Detecta automaticamente baseado no path do arquivo
- **🛡️ Segurança**: Cada ambiente tem suas próprias aprovações e proteções
- **📊 Auditoria**: Todas as operações ficam registradas no GitHub Actions

### 🔧 Fluxo Completo Automatizado

1. **Desenvolvedor**: Cria arquivo YAML no path correto
2. **Pull Request**: Submete para revisão
3. **Aprovação**: Reviewer aprova o PR
4. **Merge**: PR é mergeado na branch `main`
5. **Detecção**: `apply_access.yml` detecta ambiente automaticamente
6. **Validação**: Executa validação de segurança obrigatória
7. **Aprovação**: Aguarda aprovação manual do environment detectado
8. **Aplicação**: Aplica permissões no ambiente correto
9. **Relatório**: Gera logs detalhados da operação

> **💡 Dica**: Não é mais necessário executar workflows específicos por engine. O `apply_access.yml` gerencia tudo automaticamente!

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

1. **Acesse**: GitHub Actions > "Gerar relatórios"
2. **Configure**:
   - **Tipo de relatório**:
     - `usuario-especifico`: Relatório de um usuário específico
     - `todos-usuarios`: Relatório geral de todos os usuários
   - **User Email**: `usuario@empresa.com` (obrigatório apenas para relatório específico)
   - **Database Name**: Nome do banco específico (opcional)
   - **Format**: `html` ou `json`
3. **Execute**: Run workflow
4. **Download**: Artifacts gerados automaticamente

### 📋 Tipos de Relatórios

#### 👤 Relatório Específico (Usuario-Específico)
- **Escopo**: Todas as permissões de um usuário específico
- **Scripts**: `generate_audit_reports.py`
- **Casos de uso**:
  - **Usuário + Todos os bancos**: Relatório completo do usuário
  - **Usuário + Banco específico**: Relatório filtrado por banco
- **Formato**: HTML ou JSON

#### 👥 Relatório Geral (Todos-Usuários)
- **Escopo**: Visão consolidada de todos os usuários do sistema
- **Scripts**: `generate_general_report.py`
- **Casos de uso**:
  - **Auditoria geral**: Visão executiva de todas as permissões
  - **Compliance**: Relatório para auditorias regulares
  - **Administração**: Gestão centralizada de acessos
- **Formato**: HTML (JSON não suportado para relatório geral)

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
# GitHub Actions > Gerar relatórios
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
│   ├── 🔄 mysql_wizard_step1.yml      # MySQL Wizard - Configuração Básica
│   ├── 🔄 mysql_wizard_step2.yml      # MySQL Wizard - Seleção de Permissões
│   ├── 🔄 postgresql_aurora_access.yml # Workflow PostgreSQL/Aurora
│   ├── 🔄 postgres_wizard_step1.yml   # PostgreSQL/Aurora Wizard - Configuração Básica
│   ├── 🔄 postgres_wizard_step2.yml   # PostgreSQL/Aurora Wizard - Seleção de Permissões
│   ├── 🔄 apply_access.yml            # Aplicação geral
│   ├── 🔄 generate-audit-reports.yml  # Geração de relatórios
│   └── 🔄 reusable-security-check.yml # Validação de segurança
├── 📁 scripts/                        # Scripts Python
│   ├── 🐍 apply_permissions.py        # Aplicar permissões
│   ├── 🐍 revoke_permissions.py       # Revogar permissões
│   ├── 🐍 merge_permissions.py        # Merge de permissões
│   ├── 🐍 generate_audit_reports.py   # Gerar relatórios específicos
│   ├── 🐍 generate_general_report.py  # Gerar relatório geral
│   ├── 🐍 read_wizard_temp.py         # Leitura de arquivos temporários de wizard
│   └── 🐍 security_validator.py       # Validação de segurança
└── 📁 users-access-requests/          # Solicitações de acesso
    ├── 📁 development/                # Ambiente desenvolvimento
    ├── 📁 staging/                    # Ambiente staging
    └── 📁 production/                 # Ambiente produção
```

### 📂 Estrutura Hierárquica

```
users-access-requests/
└── {environment}/          # development, staging, production
    └── {engine}/           # mysql, postgres, aurora
        └── {database}/     # nome_do_banco
            └── {user}.yml  # usuario@empresa.com.yml
```

### 📄 Exemplo de Arquivo YAML

```yaml
# users-access-requests/development/mysql/ecommerce/usuario@empresa.com.yml
host: ecommerce-dev.rds.amazonaws.com
user: usuario@empresa.com
database: ecommerce
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

> **💡 Nota**: Este arquivo é **gerado automaticamente** pelos workflows de criação. Não é necessário criar manualmente.

### 🔄 Fluxo Completo

1. **Executar wizard** de criação (MySQL/PostgreSQL) via GitHub Actions
   - **Passo 1**: Configuração básica (ambiente, host, database, etc.)
   - **Passo 2**: Seleção de permissões (schema, tabelas, permissões específicas)
2. **Pull Request** criado automaticamente com arquivo YAML
3. **Aguardar aprovação** (manual para todos os ambientes: development/staging/production)
4. **Merge** após aprovação
5. **Aplicação automática** via `apply_access.yml` (detecta ambiente pelo path)
6. **OIDC authentication** e assume role automático
7. **Aguardar aplicação** das permissões no banco
8. **Download do relatório** via artifacts (opcional)
9. **Validar acesso** no banco de dados

### 💡 Exemplo Prático do Novo Fluxo

```
📋 CENÁRIO: Dar acesso SELECT e INSERT para usuario@empresa.com no banco "ecommerce"

🧙‍♂️ PASSO 1: MySQL Wizard - Configuração Básica
├── 🌍 Ambiente: development
├── 👤 Email: usuario@empresa.com
├── 🔌 Host: ecommerce-dev.rds.amazonaws.com
├── 🗄️ Database: ecommerce
├── 🌐 Região: us-east-1
└── 📁 Output: Session ID "mysql-wizard-1734567890-12345"

🧙‍♂️ PASSO 2: MySQL Wizard - Seleção de Permissões
├── 🔑 Session ID: mysql-wizard-1734567890-12345
├── 📂 Schema: produtos
├── ☑️ SELECT: Marcado
├── ☑️ INSERT: Marcado
├── ☐ UPDATE: Desmarcado
└── 📤 Output: Pull Request criado

🔄 FLUXO AUTOMÁTICO:
├── 👀 Revisar PR → ✅ Aprovar → 🔀 Merge
├── 🤖 apply_access.yml detecta "development" automaticamente
├── 🛡️ Validação de segurança obrigatória
├── ⏳ Aguarda aprovação manual do environment "development"
├── 🔐 Conecta via OIDC no banco MySQL
└── ✅ Aplica permissões: SELECT, INSERT no schema "produtos"

✅ RESULTADO: usuario@empresa.com pode consultar e inserir dados na tabela produtos
```

---

**🔐 Sistema desenvolvido seguindo as melhores práticas de DevSecOps e GitOps**

## ⚙️ Workflows Disponíveis

### 🧙‍♂️ Wizards Interativos (RECOMENDADO)

#### 🐬 MySQL Wizard (2 Passos)
- **📝 Finalidade**: Processo interativo de criação de permissões MySQL em 2 etapas
- **🔧 Uso**: Workflow manual via GitHub Actions
- **🛡️ Segurança**: Validação de segurança obrigatória em ambos os passos

##### 🔧 Passo 1 - Configuração Básica
- **Workflow**: `MySQL - Wizard Passo 1: Configuração Básica`
- **📋 Inputs**: ambiente, email, host, database, região, porta
- **📤 Output**: Session ID para usar no Passo 2
- **📁 Arquivo Temporário**: `wizard-temp/mysql-wizard-{timestamp}-{runid}.yml`

##### 🎯 Passo 2 - Seleção de Permissões
- **Workflow**: `MySQL - Wizard Passo 2: Seleção de Permissões`
- **📋 Inputs**:
  - `session_id`: Session ID gerado no Passo 1
  - `schema_name`: Nome do schema/database
  - `tables_list`: Lista de tabelas específicas (opcional)
  - **Permissões DML**: SELECT, INSERT, UPDATE, DELETE
  - **Permissões DDL**: CREATE, DROP, ALTER, INDEX
- **⚠️ ALL PRIVILEGES**: Se nenhuma permissão for marcada, aplica automaticamente ALL PRIVILEGES
- **📤 Output**: Pull Request com arquivo final gerado
- **🧹 Limpeza**: Remove arquivo temporário automaticamente

#### 🐘 PostgreSQL/Aurora Wizard (2 Passos)
- **📝 Finalidade**: Processo interativo de criação de permissões PostgreSQL/Aurora em 2 etapas
- **🔧 Uso**: Workflow manual via GitHub Actions
- **🛡️ Segurança**: Validação de segurança obrigatória em ambos os passos

##### 🔧 Passo 1 - Configuração Básica
- **Workflow**: `PostgreSQL/Aurora - Wizard Passo 1: Configuração Básica`
- **📋 Inputs**: ambiente, email, host, database, região, porta, engine_type (postgres/aurora)
- **📤 Output**: Session ID para usar no Passo 2
- **📁 Arquivo Temporário**: `wizard-temp/postgres-wizard-{timestamp}-{runid}.yml`

##### 🎯 Passo 2 - Seleção de Permissões
- **Workflow**: `PostgreSQL/Aurora - Wizard Passo 2: Seleção de Permissões`
- **📋 Inputs**:
  - `session_id`: Session ID gerado no Passo 1
  - `schema_name`: Nome do schema
  - `tables_list`: Lista de tabelas específicas (opcional)
  - **Permissões DML**: SELECT, INSERT, UPDATE, DELETE
  - **Permissões Específicas**: CREATE, TRIGGER, EXECUTE, CONNECT
- **⚠️ ALL PRIVILEGES**: Se nenhuma permissão for marcada, aplica automaticamente ALL PRIVILEGES
- **📤 Output**: Pull Request com arquivo final gerado
- **🧹 Limpeza**: Remove arquivo temporário automaticamente

---

### 🤖 Workflows de Sistema (Automáticos)

#### 🤖 Apply DB Access (Automático)
- **📝 Finalidade**: Aplicar permissões automaticamente após merge
- **🔧 Uso**: Executado automaticamente pelo GitHub Actions
- **🎯 Trigger**: Push para branch `main` com arquivos `users-access-requests/**.yml`
- **🔍 Detecção**: Ambiente extraído automaticamente do path do arquivo
- **🛡️ Validação**: Validação de segurança obrigatória antes da aplicação
- **⚙️ Processo**: Conecta no RDS via OIDC e aplica permissões

#### 🛡️ Reusable Security Check
- **📝 Finalidade**: Validação de segurança reutilizável
- **🔧 Uso**: Chamado automaticamente por outros workflows
- **🔍 Validações**: 
  - Credenciais não expostas
  - Arquivos YAML válidos
  - Princípio do menor privilégio
  - Estrutura de diretórios correta
- **✅ Resultado**: Aprovação/bloqueio para prosseguir com operações

---

### 📊 Workflows de Relatórios

#### 📊 Gerar Relatórios
- **📝 Finalidade**: Gerar relatórios de auditoria e relatórios gerais
- **🔧 Uso**: Workflow manual via GitHub Actions
- **📋 Inputs**:
  - **Tipo de relatório**:
    - `usuario-especifico`: Relatório de um usuário específico
    - `todos-usuarios`: Relatório geral de todos os usuários
  - `user_email`: Email do usuário (obrigatório apenas para relatório específico)
  - `database_name`: Nome do banco específico (opcional para relatório específico)
  - `output_format`: html ou json (JSON não suportado para relatório geral)
- **📤 Output**: Relatórios disponíveis nos artifacts do workflow
- **🎯 Scripts utilizados**:
  - **Específico**: `generate_audit_reports.py` 
  - **Geral**: `generate_general_report.py`

---

### 🔧 Workflows Diretos (Para Casos Especiais)

⚠️ **IMPORTANTE**: Os workflows abaixo são para **usuários avançados** ou **casos especiais**. Para uso normal, **prefira sempre os Wizards** acima.

#### 🐬 MySQL Access Control (Direto)
- **📝 Finalidade**: Criar/alterar permissões de acesso MySQL diretamente
- **🔧 Uso**: Workflow interativo via GitHub Actions
- **⚠️ Complexidade**: Requer conhecimento de JSON e estruturas de permissões
- **📋 Inputs Principais**:
  - `ambiente`: development, staging, production
  - `email`: Email do usuário (formato: user@empresa.com)
  - `database`: Nome do banco de dados
  - `host`: Endpoint do RDS MySQL
  - `schema`: Nome do schema
  - `permissões`: JSON completo (copie de examples-permissions/)
- **📤 Output**: Pull Request com arquivo YAML gerado automaticamente
- **📁 Estrutura**: `users-access-requests/{ambiente}/mysql/{database}/{email}.yml`

#### 🐘 PostgreSQL Aurora Access Control (Direto)
- **📝 Finalidade**: Criar/alterar permissões PostgreSQL/Aurora diretamente
- **🔧 Uso**: Workflow interativo via GitHub Actions
- **⚠️ Complexidade**: Requer conhecimento de JSON e estruturas de permissões
- **📋 Inputs Principais**:
  - `ambiente`: development, staging, production
  - `engine_type`: postgres ou aurora
  - `email`: Email do usuário (formato: user@empresa.com)
  - `database`: Nome do banco de dados
  - `host`: Endpoint do RDS PostgreSQL/Aurora
  - `schema`: Nome do schema
  - `permissões`: JSON completo (copie de examples-permissions/)
- **📤 Output**: Pull Request com arquivo YAML gerado automaticamente
- **📁 Estrutura**: `users-access-requests/{ambiente}/{engine}/{database}/{email}.yml`

---

> **🎯 Fluxo Recomendado**: Use os **Wizards** (MySQL/PostgreSQL) → Approve PR → Automático (Apply DB Access) → Opcional (Gerar Relatórios)