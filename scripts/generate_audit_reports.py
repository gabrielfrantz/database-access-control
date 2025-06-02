#!/usr/bin/env python3
"""
Script de Geração de Relatórios - Database Access Control
Gera relatórios HTML e JSON detalhados de permissões por usuário
"""

import os
import sys
import yaml
import json
import argparse
from datetime import datetime
from collections import defaultdict
import glob

# Configurar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

class AuditReportGenerator:
    def __init__(self, base_path="users-access-requests"):
        self.base_path = base_path
        self.environments = ["development", "staging", "production"]
        
    def load_user_permissions(self, environment):
        """Carrega todas as permissões de usuários de um ambiente."""
        permissions_data = defaultdict(lambda: defaultdict(dict))
        
        env_path = os.path.join(self.base_path, environment)
        if not os.path.exists(env_path):
            print(f"⚠️ Ambiente {environment} não encontrado em {env_path}")
            return permissions_data
            
        # Percorrer engines (mysql, postgres, aurora) - apenas se existirem
        try:
            engine_dirs = [d for d in os.listdir(env_path) if os.path.isdir(os.path.join(env_path, d)) and d != "audit"]
        except OSError:
            print(f"⚠️ Erro ao acessar diretório {env_path}")
            return permissions_data
            
        if not engine_dirs:
            print(f"ℹ️ Nenhum engine encontrado em {environment} (estrutura ainda não criada)")
            return permissions_data
            
        for engine in engine_dirs:
            engine_path = os.path.join(env_path, engine)
            
            # Percorrer bancos dentro de cada engine - apenas se existirem
            try:
                database_dirs = [d for d in os.listdir(engine_path) if os.path.isdir(os.path.join(engine_path, d))]
            except OSError:
                print(f"⚠️ Erro ao acessar diretório {engine_path}")
                continue
                
            if not database_dirs:
                print(f"ℹ️ Nenhum banco encontrado em {engine} (estrutura ainda não criada)")
                continue
                
            for database in database_dirs:
                db_path = os.path.join(engine_path, database)
                
                # Percorrer arquivos de usuários (formato: usuario@email.com.yml)
                try:
                    user_files = glob.glob(os.path.join(db_path, "*.yml"))
                except OSError:
                    print(f"⚠️ Erro ao acessar diretório {db_path}")
                    continue
                    
                if not user_files:
                    print(f"ℹ️ Nenhum usuário encontrado em {engine}/{database}")
                    continue
                    
                for user_file in user_files:
                    try:
                        with open(user_file, 'r', encoding='utf-8') as f:
                            user_data = yaml.safe_load(f)
                            
                        # Extrair email do usuário do arquivo ou nome do arquivo
                        user_email = user_data.get('user')
                        if not user_email:
                            # Fallback: extrair do nome do arquivo
                            user_email = os.path.basename(user_file).replace('.yml', '')
                        
                        # Chave única para identificar banco: engine-database
                        db_key = f"{engine}-{database}"
                        
                        permissions_data[user_email][db_key] = {
                            'engine': engine,
                            'database': database,
                            'host': user_data.get('host', ''),
                            'port': user_data.get('port', ''),
                            'region': user_data.get('region', ''),
                            'schemas': user_data.get('schemas', []),
                            'metadata': user_data.get('metadata', {}),
                            'file_path': user_file,
                            'environment': environment
                        }
                        
                    except Exception as e:
                        print(f"❌ Erro ao processar {user_file}: {e}")
                        
        return permissions_data

    def generate_user_all_permissions_report(self, user_email, output_format='html'):
        """Gera relatório completo de um usuário em todos os bancos."""
        user_report = {
            'user': user_email,
            'generated_at': datetime.now().isoformat(),
            'report_type': 'all_permissions',
            'environments': {}
        }
        
        total_databases = 0
        total_schemas = 0
        total_tables = 0
        engines_used = set()
        
        for env in self.environments:
            permissions_data = self.load_user_permissions(env)
            user_permissions = permissions_data.get(user_email, {})
            
            if user_permissions:
                user_report['environments'][env] = {
                    'total_databases': len(user_permissions),
                    'databases': user_permissions
                }
                
                total_databases += len(user_permissions)
                for db_data in user_permissions.values():
                    engines_used.add(db_data['engine'])
                    schemas = db_data.get('schemas', [])
                    total_schemas += len(schemas)
                    
                    # Contar tabelas
                    for schema in schemas:
                        tabelas = schema.get('tabelas', [])
                        total_tables += len(tabelas)
        
        user_report['summary'] = {
            'total_databases': total_databases,
            'total_schemas': total_schemas,
            'total_tables': total_tables,
            'total_environments': len([env for env in user_report['environments'].values() if env['total_databases'] > 0]),
            'engines_used': sorted(list(engines_used))
        }
        
        if output_format == 'json':
            return self._generate_json_report(user_report)
        else:
            return self._generate_html_report(user_report)

    def generate_user_database_permissions_report(self, user_email, database_name, output_format='html'):
        """Gera relatório de um usuário em um banco específico."""
        user_report = {
            'user': user_email,
            'database_filter': database_name,
            'generated_at': datetime.now().isoformat(),
            'report_type': 'specific_database',
            'environments': {}
        }
        
        total_matches = 0
        
        for env in self.environments:
            permissions_data = self.load_user_permissions(env)
            user_permissions = permissions_data.get(user_email, {})
            
            # Filtrar por banco específico
            filtered_permissions = {}
            for db_key, db_data in user_permissions.items():
                if database_name.lower() in db_data['database'].lower():
                    filtered_permissions[db_key] = db_data
                    total_matches += 1
            
            if filtered_permissions:
                user_report['environments'][env] = {
                    'total_databases': len(filtered_permissions),
                    'databases': filtered_permissions
                }
        
        user_report['summary'] = {
            'total_matches': total_matches,
            'database_searched': database_name
        }
        
        if output_format == 'json':
            return self._generate_json_report(user_report)
        else:
            return self._generate_html_report(user_report)

    def _generate_json_report(self, data):
        """Gera relatório em formato JSON."""
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _generate_html_report(self, data):
        """Gera relatório em formato HTML melhorado."""
        html_template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Auditoria - {user}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 15px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{ 
            background: linear-gradient(135deg, #007acc 0%, #0056b3 100%);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="50" cy="50" r="1" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
        }}
        
        .header h1 {{ 
            font-size: 2.8em; 
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }}
        
        .header .subtitle {{ 
            font-size: 1.2em; 
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }}
        
        .header .meta {{
            margin-top: 20px;
            font-size: 0.95em;
            opacity: 0.8;
            position: relative;
            z-index: 1;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .user-info {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            border-left: 5px solid #007acc;
        }}
        
        .user-info h2 {{
            color: #007acc;
            font-size: 1.8em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #007acc 0%, #0056b3 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 8px 16px rgba(0,122,204,0.3);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .environment-section {{
            margin: 40px 0;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .environment-header {{
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 20px 30px;
            font-size: 1.4em;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .environment-header.dev {{
            background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
        }}
        
        .environment-header.stg {{
            background: linear-gradient(135deg, #6f42c1 0%, #e83e8c 100%);
        }}
        
        .environment-header.prod {{
            background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
        }}
        
        .database-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .database-table th {{
            background: #f8f9fa;
            color: #495057;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
        }}
        
        .database-table td {{
            padding: 15px;
            border-bottom: 1px solid #dee2e6;
            vertical-align: top;
        }}
        
        .database-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .engine-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
            color: white;
        }}
        
        .engine-mysql {{
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
        }}
        
        .engine-postgres {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
        }}
        
        .engine-aurora {{
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        }}
        
        .permission-list {{
            margin: 10px 0;
        }}
        
        .schema-item {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            border-left: 4px solid #007acc;
        }}
        
        .schema-name {{
            font-weight: bold;
            color: #007acc;
            margin-bottom: 8px;
        }}
        
        .permission-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.75em;
            margin: 2px 4px 2px 0;
            font-weight: 500;
        }}
        
        .no-data {{
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
            font-style: italic;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }}
        
        .alert {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            color: #856404;
        }}
        
        .alert.info {{
            background: #d1ecf1;
            border-color: #bee5eb;
            color: #0c5460;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Relatório de Auditoria</h1>
            <div class="subtitle">Sistema de Controle de Acesso a Bancos de Dados</div>
            <div class="meta">
                <strong>Gerado em:</strong> {generated_at}<br>
                <strong>Tipo:</strong> {report_type_label}
            </div>
        </div>
        
        <div class="content">
            {content}
        </div>
        
        <div class="footer">
            <p><strong>Database Access Control System</strong></p>
            <p>Relatório gerado automaticamente • Confidencial</p>
        </div>
    </div>
</body>
</html>"""
        
        content = self._generate_html_content(data)
        report_type_label = "Todas as Permissões" if data.get('report_type') == 'all_permissions' else f"Banco Específico: {data.get('database_filter', 'N/A')}"
        
        return html_template.format(
            user=data.get('user', 'N/A'),
            generated_at=datetime.fromisoformat(data.get('generated_at')).strftime('%d/%m/%Y às %H:%M:%S'),
            report_type_label=report_type_label,
            content=content
        )

    def _generate_html_content(self, data):
        """Gera o conteúdo HTML específico para relatórios de usuário."""
        user_email = data.get('user', 'N/A')
        environments = data.get('environments', {})
        summary = data.get('summary', {})
        report_type = data.get('report_type', 'all_permissions')
        
        content = f"""
        <div class="user-info">
            <h2>👤 {user_email}</h2>
        """
        
        if report_type == 'all_permissions':
            content += f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{summary.get('total_databases', 0)}</div>
                    <div class="label">Bancos de Dados</div>
                </div>
                <div class="stat-card">
                    <div class="number">{summary.get('total_schemas', 0)}</div>
                    <div class="label">Schemas</div>
                </div>
                <div class="stat-card">
                    <div class="number">{summary.get('total_tables', 0)}</div>
                    <div class="label">Tabelas</div>
                </div>
                <div class="stat-card">
                    <div class="number">{summary.get('total_environments', 0)}</div>
                    <div class="label">Ambientes</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(summary.get('engines_used', []))}</div>
                    <div class="label">Engines</div>
                </div>
            </div>
            """
            
            if summary.get('engines_used'):
                engines_list = ', '.join(summary['engines_used'])
                content += f'<p><strong>Engines utilizados:</strong> {engines_list}</p>'
        else:
            database_searched = data.get('database_filter', 'N/A')
            total_matches = summary.get('total_matches', 0)
            content += f"""
            <div class="alert info">
                <strong>Filtro aplicado:</strong> Banco de dados "{database_searched}"<br>
                <strong>Resultados encontrados:</strong> {total_matches} banco(s)
            </div>
            """
        
        content += "</div>"
        
        # Gerar seções por ambiente
        if not environments:
            content += """
            <div class="no-data">
                <h3>📭 Nenhuma permissão encontrada</h3>
                <p>Este usuário não possui permissões configuradas ou o filtro não retornou resultados.</p>
            </div>
            """
        else:
            for env_name, env_data in environments.items():
                if env_data.get('total_databases', 0) > 0:
                    content += f"""
                    <div class="environment-section">
                        <div class="environment-header {env_name}">
                            🌍 Ambiente: {env_name.upper()}
                            <span style="margin-left: auto; font-size: 0.9em;">
                                {env_data.get('total_databases', 0)} banco(s)
                            </span>
                        </div>
                        <table class="database-table">
                            <thead>
                                <tr>
                                    <th>Engine</th>
                                    <th>Banco de Dados</th>
                                    <th>Host</th>
                                    <th>Schemas e Permissões</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                    
                    for db_key, db_data in env_data.get('databases', {}).items():
                        engine = db_data.get('engine', 'N/A')
                        database = db_data.get('database', 'N/A')
                        host = db_data.get('host', 'N/A')
                        schemas = db_data.get('schemas', [])
                        
                        schemas_html = ""
                        if schemas:
                            for schema in schemas:
                                schema_name = schema.get('nome', 'N/A')
                                permissions = schema.get('permissions', [])
                                tabelas = schema.get('tabelas', [])
                                
                                permissions_badges = ''.join([
                                    f'<span class="permission-badge">{perm}</span>' 
                                    for perm in permissions
                                ])
                                
                                # Processar tabelas se existirem (granular)
                                tables_html = ""
                                if tabelas:
                                    tables_html = "<div style='margin-top: 10px; padding-left: 15px;'>"
                                    for tabela in tabelas:
                                        table_name = tabela.get('nome', 'N/A')
                                        table_permissions = tabela.get('permissions', [])
                                        
                                        table_permissions_badges = ''.join([
                                            f'<span class="permission-badge" style="background: linear-gradient(135deg, #6f42c1 0%, #e83e8c 100%); font-size: 0.7em;">{perm}</span>' 
                                            for perm in table_permissions
                                        ])
                                        
                                        tables_html += f"""
                                        <div style="margin: 5px 0; padding: 8px; background: #f1f3f4; border-radius: 6px; border-left: 3px solid #6f42c1;">
                                            <div style="font-weight: 600; color: #6f42c1; font-size: 0.85em;">🗂️ {table_name}</div>
                                            <div style="margin-top: 4px;">{table_permissions_badges}</div>
                                        </div>
                                        """
                                    tables_html += "</div>"
                                
                                schemas_html += f"""
                                <div class="schema-item">
                                    <div class="schema-name">📊 {schema_name}</div>
                                    <div>{permissions_badges}</div>
                                    {tables_html}
                                </div>
                                """
                        else:
                            schemas_html = '<div class="schema-item">Nenhum schema configurado</div>'
                        
                        content += f"""
                                <tr>
                                    <td>
                                        <span class="engine-badge engine-{engine}">{engine}</span>
                                    </td>
                                    <td><strong>{database}</strong></td>
                                    <td>{host}</td>
                                    <td>
                                        <div class="permission-list">
                                            {schemas_html}
                                        </div>
                                    </td>
                                </tr>
                        """
                    
                    content += """
                            </tbody>
                        </table>
                    </div>
                    """
        
        return content

def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(description="Gerador de Relatórios de Auditoria")
    parser.add_argument("--user", required=True, help="Email do usuário")
    parser.add_argument("--database", help="Nome do banco específico (opcional)")
    parser.add_argument("--output", help="Arquivo de saída (opcional)")
    parser.add_argument("--format", choices=['html', 'json'], default='html', help="Formato de saída (html ou json)")
    
    args = parser.parse_args()
    
    generator = AuditReportGenerator()
    
    try:
        # Determinar tipo de relatório (apenas imprimir se não for JSON para stdout)
        if args.database:
            if args.format != 'json' or args.output:
                print(f"🔍 Gerando relatório específico para usuário {args.user} no banco {args.database}")
            report = generator.generate_user_database_permissions_report(args.user, args.database, args.format)
        else:
            if args.format != 'json' or args.output:
                print(f"🔍 Gerando relatório completo para usuário {args.user}")
            report = generator.generate_user_all_permissions_report(args.user, args.format)
        
        # Salvar ou imprimir relatório
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"✅ Relatório {args.format.upper()} salvo em: {args.output}")
        else:
            print(report)
            
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()