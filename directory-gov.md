# ADR: Integração entre GitHub e SharePoint para Mapeamento e Gestão de Diretórios

## Status

Aceito

## Contexto

Durante a evolução de iniciativas de modernização, identificamos a necessidade de manter um inventário claro e atualizado das pastas existentes em um repositório GitHub, e cruzar essas informações com uma lista de controle mantida no SharePoint (por meio de uma planilha ou lista exportada em CSV).

Essa lista de controle inclui informações como plano de ação (modernizar, remover, reter) para cada diretório, sendo essencial para guiar decisões técnicas e operacionais.

## Decisão

Optamos por:

- Utilizar a **GitHub GraphQL API v4** para listar dinamicamente os diretórios de um caminho específico em um repositório.
- Representar a estrutura do SharePoint como um **CSV** (exportado manualmente ou via integração), contendo o nome das pastas e o plano de ação.
- Realizar uma **comparação bidirecional (full outer join)** entre os diretórios do GitHub e os registrados no SharePoint, categorizando os seguintes casos:
  - Pastas presentes em **ambas** as fontes (base para execução).
  - Pastas **apenas no SharePoint** (pode indicar algo obsoleto).
  - Pastas **apenas no GitHub** (podem não ter plano de ação definido ainda).

## Motivação

- A estrutura de pastas representa componentes e domínios do código, sendo essencial para análises de impacto.
- O SharePoint é uma fonte de verdade para o planejamento e governança, enquanto o GitHub reflete a realidade atual do repositório.
- A comparação automatizada evita erros manuais e facilita a governança contínua.

## Implementação

### 1. **Cliente GitHub GraphQL em Python**

```python
# github_tree.py

import requests
from typing import List

class GitHubAPIError(Exception):
    pass

class GitHubClient:
    def __init__(self, token: str, api_url: str = "https://api.github.com/graphql"):
        self.token = token
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def list_directories(
        self, owner: str, repo: str, branch: str, path: str
    ) -> List[str]:
        query = \"\"\"
        query($owner: String!, $name: String!, $expression: String!) {
          repository(owner: $owner, name: $name) {
            object(expression: $expression) {
              ... on Tree {
                entries {
                  name
                  type
                }
              }
            }
          }
        }
        \"\"\"
        variables = {
            "owner": owner,
            "name": repo,
            "expression": f"{branch}:{path}"
        }

        resp = requests.post(
            self.api_url,
            json={"query": query, "variables": variables},
            headers=self.headers,
            timeout=10
        )

        if resp.status_code != 200:
            raise GitHubAPIError(f"Status HTTP {resp.status_code}: {resp.text}")

        data = resp.json().get("data", {})
        tree = data.get("repository", {}).get("object")
        if tree is None or "entries" not in tree:
            raise GitHubAPIError("Diretório não encontrado ou inválido.")

        return [
            entry["name"]
            for entry in tree["entries"]
            if entry.get("type") == "tree"
        ]

```

### 2. Comparação CSV vs GitHub

```python
# folder_comparator.py

import pandas as pd
from typing import Tuple

def compare_folders(
    csv_path: str,
    github_folders: list[str]
) -> pd.DataFrame:
    sp_df = pd.read_csv(csv_path)
    gh_df = pd.DataFrame({'name': github_folders})

    comparison_df = sp_df.merge(
        gh_df,
        on='name',
        how='outer',
        indicator=True
    )
    return comparison_df


def summary_sets(comparison_df: pd.DataFrame) -> Tuple[set[str], set[str], set[str]]:
    both = set(comparison_df.loc[comparison_df['_merge'] == 'both', 'name'])
    only_left = set(comparison_df.loc[comparison_df['_merge'] == 'left_only', 'name'])
    only_right = set(comparison_df.loc[comparison_df['_merge'] == 'right_only', 'name'])
    return both, only_left, only_right

```

### 3. Exemplo de Uso

```python
from github_tree import GitHubClient
from folder_comparator import compare_folders, summary_sets

client = GitHubClient(token="SEU_TOKEN")
github_dirs = client.list_directories(
    owner="octocat",
    repo="Hello-World",
    branch="main",
    path="src"
)

comparison_df = compare_folders("sharepoint_folders.csv", github_dirs)
print(comparison_df)

both, only_sp, only_gh = summary_sets(comparison_df)
print("Em ambas:", both)
print("Só no SharePoint:", only_sp)
print("Só no GitHub:", only_gh)
```

## Consequências

### Benefícios
	•	Automatização da análise de cobertura e divergência entre planejamento (SharePoint) e execução (GitHub).
	•	Base para ações como: criar plano para novas pastas, encerrar plano de itens obsoletos, etc.
	•	Código reutilizável e modular.

### Riscos ou Limitações
	•	Requer exportação manual (ou integração) do SharePoint para CSV.
	•	Dependência de token GitHub com escopo correto.

## Próximos Passos
	•	Automatizar leitura do SharePoint via API ou PowerAutomate.
	•	Criar alertas em pipeline para detectar novas pastas não planejadas.
	•	Versionar os planos de ação no próprio repositório como YAML/CSV (governança de engenharia).

## Decisores
	•	Arquitetura & Engenharia de Dados
	•	Times de Modernização

## Data

2025-04-22