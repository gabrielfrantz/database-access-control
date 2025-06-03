#!/usr/bin/env python3
"""
Script de Geração de Relatório Geral - Database Access Control
Gera relatório HTML geral de todos os usuários e permissões
"""

import os
import sys
import yaml
import json
import argparse
from datetime import datetime
from collections import defaultdict
import glob

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

class GeneralReportGenerator:
    def __init__(self, base_path="users-access-requests"):
        self.base_path = base_path
        self.environments = ["development", "staging", "production"]
        
    def load_all_permissions(self):
        """Carrega todas as permissões de todos os usuários em todos os ambientes."""
        all_data = {}
        
        for environment in self.environments:
            env_path = os.path.join(self.base_path, environment)
            if not os.path.exists(env_path):
                continue
                
            env_data = {}
            
            try:
                engine_dirs = [d for d in os.listdir(env_path) 
                             if os.path.isdir(os.path.join(env_path, d)) and d != "audit"]
            except OSError:
                continue
                
            for engine in engine_dirs:
                engine_path = os.path.join(env_path, engine)
                
                try:
                    database_dirs = [d for d in os.listdir(engine_path) 
                                   if os.path.isdir(os.path.join(engine_path, d))]
                except OSError:
                    continue
                    
                for database in database_dirs:
                    db_path = os.path.join(engine_path, database)
                    
                    try:
                        user_files = glob.glob(os.path.join(db_path, "*.yml"))
                    except OSError:
                        continue
                        
                    for user_file in user_files:
                        try:
                            with open(user_file, 'r', encoding='utf-8') as f:
                                user_data = yaml.safe_load(f)
                                
                            user_email = user_data.get('usuario', {}).get('email')
                            if not user_email:
                                user_email = os.path.basename(user_file).replace('.yml', '')
                            
                            db_key = f"{engine}-{database}"
                            
                            if user_email not in env_data:
                                env_data[user_email] = {}
                                
                            env_data[user_email][db_key] = {
                                'engine': engine,
                                'database': database,
                                'user_info': user_data.get('usuario', {}),
                                'database_info': user_data.get('database', {}),
                                'schemas': user_data.get('schemas', []),
                                'solicitacao': user_data.get('solicitacao', {}),
                                'file_path': user_file
                            }
                            
                        except Exception as e:
                            print(f"❌ Erro ao processar {user_file}: {e}")
            
            if env_data:
                all_data[environment] = env_data
                
        return all_data

    def generate_general_html_report(self, output_file="relatorio-geral.html"):
        """Gera relatório HTML geral."""
        all_data = self.load_all_permissions()
        
        stats = self._calculate_stats(all_data)
        
        html_content = self._generate_html_template(all_data, stats)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return output_file, os.path.getsize(output_file)
    
    def _calculate_stats(self, data):
        """Calcula estatísticas gerais."""
        stats = {
            'total_users': set(),
            'total_databases': set(),
            'total_environments': len(data),
            'engines': set(),
            'permissions_by_env': {},
            'users_by_dept': defaultdict(int),
            'databases_by_engine': defaultdict(int)
        }
        
        for env, env_data in data.items():
            stats['permissions_by_env'][env] = len(env_data)
            
            for user, databases in env_data.items():
                stats['total_users'].add(user)
                
                for db_key, db_info in databases.items():
                    stats['total_databases'].add(db_key)
                    stats['engines'].add(db_info['engine'])
                    stats['databases_by_engine'][db_info['engine']] += 1
                    
                    dept = db_info.get('user_info', {}).get('departamento', 'Não informado')
                    stats['users_by_dept'][dept] += 1
        
        stats['total_users'] = len(stats['total_users'])
        stats['total_databases'] = len(stats['total_databases'])
        stats['engines'] = list(stats['engines'])
        
        return stats
    
    def _generate_html_template(self, data, stats):
        """Gera template HTML completo com o mesmo layout do generate_audit_reports.py."""
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Geral de Permissões - Database Access Control</title>
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
        
        .environment-header.development {{
            background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
        }}
        
        .environment-header.staging {{
            background: linear-gradient(135deg, #6f42c1 0%, #e83e8c 100%);
        }}
        
        .environment-header.production {{
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
        
        .user-section {{
            margin: 30px 0;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .user-header {{
            background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
            color: white;
            padding: 20px 30px;
            font-size: 1.2em;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗂️ Relatório Geral de Permissões</h1>
            <div class="subtitle">Database Access Control System</div>
            <div class="meta">
                <strong>Gerado em:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}<br>
                <strong>Tipo:</strong> Relatório Consolidado de Todos os Usuários
            </div>
        </div>
        
        <div class="content">
            <div class="user-info">
                <h2>📊 Resumo Executivo</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="number">{stats['total_users']}</div>
                        <div class="label">Usuários</div>
                    </div>
                    <div class="stat-card">
                        <div class="number">{stats['total_databases']}</div>
                        <div class="label">Bancos de Dados</div>
                    </div>
                    <div class="stat-card">
                        <div class="number">{stats['total_environments']}</div>
                        <div class="label">Ambientes</div>
                    </div>
                    <div class="stat-card">
                        <div class="number">{len(stats['engines'])}</div>
                        <div class="label">Engines</div>
                    </div>
                </div>
                {self._generate_engines_info(stats)}
            </div>
            
            {self._generate_environments_content(data)}
        </div>
        
        <div class="footer">
            <p><strong>Database Access Control System</strong></p>
            <p>Relatório gerado automaticamente • Confidencial</p>
        </div>
    </div>
</body>
</html>"""
        
        return html_template

    def _generate_engines_info(self, stats):
        """Gera informações sobre os engines utilizados."""
        if stats.get('engines'):
            engines_list = ', '.join(stats['engines'])
            return f'<p><strong>Engines utilizados:</strong> {engines_list}</p>'
        return ""

    def _generate_environments_content(self, data):
        """Gera conteúdo das seções por ambiente usando layout de tabela."""
        content = ""
        
        if not data:
            return """
            <div class="no-data">
                <h3>📭 Nenhuma permissão encontrada</h3>
                <p>Não foram encontradas configurações de permissões no sistema.</p>
            </div>
            """
        
        for env_name, env_data in data.items():
            if env_data:
                content += f"""
                <div class="environment-section">
                    <div class="environment-header {env_name}">
                        🌍 Ambiente: {env_name.upper()}
                        <span style="margin-left: auto; font-size: 0.9em;">
                            {len(env_data)} usuário(s)
                        </span>
                    </div>
                    {self._generate_users_table_content(env_data)}
                </div>
                """
        
        return content
    
    def _generate_users_table_content(self, users_data):
        """Gera conteúdo em formato de tabela para usuários."""
        content = """
        <table class="database-table">
            <thead>
                <tr>
                    <th>Usuário</th>
                    <th>Engine</th>
                    <th>Banco de Dados</th>
                    <th>Host</th>
                    <th>Schemas e Permissões</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for user_email, databases in users_data.items():
            user_info = next(iter(databases.values())).get('user_info', {})
            user_name = user_info.get('nome', user_email.split('@')[0].title())
            user_dept = user_info.get('departamento', 'N/A')
            
            for db_key, db_info in databases.items():
                engine = db_info['engine']
                database = db_info['database']
                host = db_info.get('database_info', {}).get('host', 'N/A') if isinstance(db_info.get('database_info'), dict) else 'N/A'
                schemas = db_info.get('schemas', [])
                
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
                        <strong>👤 {user_name}</strong><br>
                        <small style="color: #6c757d;">{user_email}</small><br>
                        <small style="color: #6c757d;">Dept: {user_dept}</small>
                    </td>
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
        """
        
        return content

def main():
    parser = argparse.ArgumentParser(description='Gerador de Relatório Geral')
    parser.add_argument('--output', default='relatorio-geral.html', 
                       help='Arquivo de saída HTML')
    
    args = parser.parse_args()
    
    generator = GeneralReportGenerator()
    
    print("🔍 Gerando relatório geral de todos os usuários...")
    
    output_file, file_size = generator.generate_general_html_report(args.output)
    
    print(f"✅ Relatório HTML geral salvo em: {output_file}")
    print(f"📁 Tamanho do arquivo: {file_size:,} bytes")

if __name__ == "__main__":
    main() 