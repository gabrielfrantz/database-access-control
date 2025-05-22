import sys
import yaml
import json
from pathlib import Path
import os

caminho = Path(sys.argv[1])
novo_input = json.loads(sys.argv[2])
remover = os.getenv("REMOVER_PERMISSOES", "false").lower() == "true"

if caminho.exists():
    with open(caminho) as f:
        dados = yaml.safe_load(f)
else:
    dados = {
        "host": os.environ["INPUT_HOST"],
        "user": os.environ["INPUT_EMAIL"],
        "database": os.environ["INPUT_DATABASE"],
        "engine": os.environ["INPUT_ENGINE"],
        "region": os.environ["INPUT_REGION"],
        "port": int(os.environ["INPUT_PORT"]),
        "schemas": []
    }

schemas_existentes = {s['nome']: set(s['permissions']) for s in dados.get("schemas", [])}

for item in novo_input:
    nome = item["nome"]
    novas_perms = set(item["permissions"])
    if nome in schemas_existentes:
        if remover:
            schemas_existentes[nome] -= novas_perms
            if not schemas_existentes[nome]:
                del schemas_existentes[nome]  # Remove schema vazio
        else:
            schemas_existentes[nome] |= novas_perms
    elif not remover:
        schemas_existentes[nome] = novas_perms

# Atualiza dados e salva novamente
schemas_final = [
    {"nome": nome, "permissions": sorted(list(perms))}
    for nome, perms in schemas_existentes.items()
]
dados["schemas"] = schemas_final

with open(caminho, "w") as f:
    yaml.safe_dump(dados, f, sort_keys=False)

print(f"Permissões {'removidas' if remover else 'atualizadas'} com sucesso no arquivo: {caminho}")