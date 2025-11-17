# DNA Urbano 

Sistema inteligente de otimização de rotas para equipes de manutenção urbana usando algoritmo baseado em tags hierárquicas.

## Sobre o Projeto

Este sistema resolve o problema de roteamento de equipes de manutenção urbana (buracos, vazamentos, problemas elétricos, etc.) usando um algoritmo baseado em **tags hierárquicas** que permitem agrupar e priorizar problemas de forma inteligente.

## Como Funcionam as Tags

### Conceito

As tags neste sistema são **classificadores hierárquicos** que permitem organizar problemas de manutenção urbana. Diferente de algoritmos tradicionais que consideram apenas distância, nosso sistema usa tags para:

1. **Classificar problemas** por tipo, prioridade e equipe necessária
2. **Criar clusters dinâmicos** baseados em proximidade geográfica e características similares
3. **Paralelizar o processamento** resolvendo subproblemas de forma independente
4. **Priorizar atendimentos** considerando impacto social e urgência

### Hierarquia de Tags

```
PRIORIDADE (Nível 0)
├── Emergência (risco iminente)
├── Urgente (alta prioridade)
├── Alta
├── Média
└── Baixa

TIPO DE EQUIPE (Nível 1)
├── Asfalto
├── Hidráulica
├── Elétrica
├── Saneamento
└── Geral

LOCALIZAÇÃO (Nível 2)
├── Região
├── Bairro
└── Via Principal (sim/não)

IMPACTO (Nível 3)
├── Afeta Trânsito
├── Afeta Comércio
├── Próximo a Local Crítico
└── Número de Reclamações
```

## Tipos de Problemas Suportados

- `buraco_asfalto`
- `vazamento_agua`
- `vazamento_esgoto`
- `poste_sem_luz`
- `fiacao_exposta`
- `bueiro_entupido`
- `calcada_quebrada`
- `semaforo_defeito`

## Níveis de Prioridade

- **Emergência**: Risco iminente à segurança
- **Urgente**: Requer atenção em até 24h
- **Alta**: Deve ser resolvido em até 3 dias
- **Média**: Pode aguardar até 1 semana
- **Baixa**: Sem urgência imediata

## Vantagens do Algoritmo com Tags

### 1. Redução de Complexidade
- Divide o problema em subgrupos menores
- Permite processamento em paralelo de clusters independentes
- Escala de forma eficiente com o aumento de pontos

### 2. Paralelização Natural

```text
Cluster A ─┐
Cluster B ─┼─→ Processamento Paralelo ─→ Rota Otimizada
Cluster C ─┘
```

Cada cluster geográfico é resolvido de forma independente, aproveitando múltiplos cores do processador.

### 3. Priorização Inteligente
- Emergências são sempre processadas primeiro
- Considera impacto social (proximidade a escolas, hospitais, áreas comerciais)
- Agrupa problemas similares (mesma equipe, materiais necessários)

### 4. Escalabilidade
- Projetado para funcionar com diferentes volumes de pontos
- Tempo de processamento cresce de forma sublinear
- Cache de distâncias para otimizar consultas repetidas

### 5. Flexibilidade
- Fácil adicionar novos tipos de tags
- Pesos ajustáveis para diferentes cidades/regiões
- API REST para integração com sistemas existentes

## Como Funciona o Algoritmo

### Fase 1: Clustering Inteligente
```text
pontos → [Filtro por Equipe] → [DBSCAN Geográfico] → clusters
       ↓
   [Priorização] → ordenação por urgência
```

### Fase 2: Resolução de Clusters

```python
ThreadPoolExecutor: resolve cada cluster com nearest neighbor
```

### Fase 3: Conexão de Clusters

```text
clusters → [MST - Minimum Spanning Tree] → ordem de visita → [2-opt] → rota final
```

### Fase 4: Validação
- Verifica tempo máximo de trabalho
- Respeita dependências entre problemas
- Calcula estatísticas da rota

## Como Rodar com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Instalação

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/urban-dna.git
cd urban-dna
```

2. **Configure as variáveis de ambiente** (se necessário)
```bash
cp .env.example .env
```

3. **Inicie os containers**
```bash
docker-compose up -d
```

4. **Verifique se a API está rodando**
```bash
curl http://localhost:8000/docs
```

Acesse http://localhost:8000/docs para ver a documentação interativa (Swagger).

## Uso da API

### Criar um Ponto de Manutenção

```bash
curl -X POST http://localhost:8000/api/v1/points \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": -10.965490,
    "longitude": -37.057259,
    "address": "Rua Principal, 123",
    "problem_type": "buraco_asfalto",
    "priority": "emergencia",
    "team_type": "asfalto",
    "problem_size": "grande",
    "estimated_time": 45,
    "neighborhood": "Centro",
    "region": "Centro",
    "main_road": true,
    "complaints_count": 15,
    "affects_traffic": true
  }'
```

### Otimizar Rota para uma Equipe

```bash
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "team_type": "asfalto",
    "max_hours": 8,
    "max_points": 30,
    "strategy": "mixed"
  }'
```

### Listar Pontos com Filtros

```bash
curl "http://localhost:8000/api/v1/points?team_type=asfalto&priority=emergencia&limit=10"
```

## Estrutura do Projeto

```
urban-dna/
├── src/
│   ├── core/
│   │   ├── algorithms/      # Algoritmos de otimização
│   │   │   ├── optimizer.py
│   │   │   ├── prioritizer.py
│   │   │   └── distance.py
│   │   └── models/          # Modelos de dados
│   │       ├── point.py
│   │       └── tag.py
│   ├── infra/
│   │   └── db/             # Camada de banco de dados
│   │       └── database.py
│   ├── web/                # API REST
│   │   ├── routes.py
│   │   └── schemas.py
│   └── main.py
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Tecnologias Utilizadas

- **FastAPI**: Framework web moderno e rápido
- **PostgreSQL + PostGIS**: Banco de dados com extensões geoespaciais
- **asyncpg**: Driver assíncrono para PostgreSQL
- **Redis**: Cache de distâncias
- **NetworkX**: Algoritmos de grafos (MST, DFS)
- **scikit-learn**: Clustering (DBSCAN)
- **Pydantic**: Validação de dados

## Desenvolvimento

### Executar Testes
```bash
docker-compose exec urban_router_app pytest
```

### Ver Logs
```bash
docker-compose logs -f urban_router_app
```

### Reconstruir Containers
```bash
docker-compose down -v
docker-compose up --build
```
