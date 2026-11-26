# Smart Buffet Analytics

## Apresentação

O Smart Buffet Analytics é um projeto do **Hackathon Tech FMU 2026.2** para o desafio **Bovinos Grill**. O backend recebe leituras de peso das cubas de um buffet, mostra a disponibilidade dos pratos e consolida o consumo estimado e os eventos de alerta em um relatório semanal.

## Problema

A equipe de um buffet precisa acompanhar quanto ainda há de cada alimento e quais cubas estão próximas de acabar. A verificação visual esporádica pode causar ruptura sem aviso e filas; a falta de histórico dificulta comparar o consumo entre pratos e dias e planejar compras e produção sem excesso de sobras.

## Solução proposta

Cada leitura associa uma balança, um prato e um peso. A API calcula a disponibilidade da cuba, sinaliza a entrada em estado crítico e armazena as leituras para consulta posterior. O relatório semanal resume o consumo por prato e por dia e pode ser baixado como CSV.

O MVP pode ser demonstrado com pesos simulados, enviados por um cliente HTTP ou pelo Swagger. Uma fonte futura com ESP32 e sensores de peso poderá enviar leituras pelo mesmo endpoint, sem alterar o painel e o relatório. O sistema é de controle interno do buffet, sem exigir balança fiscal para cobrança no caixa.

## Funcionalidades

- Registro e validação de leituras para até cinco balanças.
- Estado atual com a última leitura de cada balança monitorada e os totais de balanças monitoradas e críticas.
- Histórico de leituras no SQLite, com consumo estimado e registro de novos alertas.
- Relatório semanal em JSON com totais, consumo diário e ranking por prato.
- Exportação CSV e documentação interativa da API com Swagger e ReDoc.

## Tecnologias

| Tecnologia | Uso |
| --- | --- |
| Python e Uvicorn | Execução do backend e servidor ASGI. |
| FastAPI e Pydantic v2 | Rotas HTTP, validação, contratos e OpenAPI. |
| SQLite via `sqlite3` | Armazenamento local das leituras. |
| `zoneinfo` e `tzdata` | Conversão entre UTC e o calendário de São Paulo. |
| pytest, TestClient e HTTPX | Testes de regras, contratos e integração. |

## Arquitetura

```mermaid
flowchart LR
    Sim["Simulador ou envio manual"] -->|"POST /leituras"| API["API FastAPI"]
    IoT["Fonte IoT futura"] -.-> API
    Dash["Dashboard de monitoramento"] -->|"Consultas GET"| API
    API --> Servicos["Serviços de leituras e relatórios"]
    Servicos --> Banco[("SQLite")]
    API --> Saidas["Estado atual, relatório semanal em JSON e CSV"]
```

Veja o [documento de arquitetura](docs/architecture.md) para o modelo de dados e os fluxos de execução.

## Estrutura de pastas

```text
.
├── app/
│   ├── main.py
│   ├── database/
│   │   ├── database.py
│   │   ├── queries.py
│   │   └── schema.sql
│   ├── routers/
│   │   ├── leitura_router.py
│   │   └── relatorio_router.py
│   ├── schemas/
│   │   ├── leitura_schema.py
│   │   └── relatorio_schema.py
│   ├── services/
│   │   ├── leitura_service.py
│   │   └── relatorio_service.py
│   └── utils/
│       ├── constants.py
│       └── normalizacao.py
├── docs/
│   ├── api-integration.md
│   ├── architecture.md
│   ├── demo-guide.md
│   └── integration-report.md
├── frontend/
│   └── dashboard.html
├── simuladores/
│   └── simulador_balancas.py
├── tests/
│   ├── test_api.py
│   ├── test_integracao.py
│   ├── test_leituras.py
│   ├── test_limites_sqlite.py
│   ├── test_relatorio.py
│   ├── test_schemas.py
│   └── test_simulador.py
├── .gitignore
├── AGENTS.md
├── README.md
└── requirements.txt
```

## Pré-requisitos

- Python 3.15, validado com a versão 3.15.2, com `pip` e `venv`.
- Git para clonar o repositório.
- Dependências fixadas em [requirements.txt](requirements.txt). O SQLite é fornecido pela biblioteca padrão do Python.

## Instalação

Use o worktree da branch `integration/mvp` para executar os três componentes integrados. Para instalar em outro diretório, clone essa branch e acesse a pasta. A branch `feature/backend` contém somente o componente de backend.

```shell
git clone --branch integration/mvp https://github.com/FernandoKooji/projeto-hakathon-FMU-2026.2-
cd projeto-hakathon-FMU-2026.2-
python -m venv .venv
```

No PowerShell, ative o ambiente com este comando.

```powershell
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear o script de ativação, substitua `python` por `.\.venv\Scripts\python.exe` nos comandos de instalação, execução e testes.

No Linux ou macOS, use este comando.

```shell
source .venv/bin/activate
```

Instale as dependências no ambiente ativo.

```shell
python -m pip install -r requirements.txt
```

## Execução

Execute o Uvicorn na raiz do repositório.

```shell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

O FastAPI cria `app/database/database.db` automaticamente na primeira inicialização e reaproveita os dados nas seguintes. Para uma série de testes manuais com banco vazio, use o [roteiro de demonstração](docs/demo-guide.md).

- [URL base da API](http://127.0.0.1:8000)
- [Swagger UI](http://127.0.0.1:8000/docs)
- [ReDoc](http://127.0.0.1:8000/redoc)

## Endpoints

| Método e rota | Finalidade | Códigos HTTP |
| --- | --- | --- |
| `GET /` | Identifica o projeto. | `200` |
| `GET /health` | Verifica a disponibilidade do serviço HTTP. | `200` |
| `POST /leituras` | Valida e registra uma leitura. | `201` criada, `409` fora de ordem, `422` inválida |
| `GET /estado-atual` | Retorna a última leitura de cada balança com dados. | `200` |
| `GET /relatorio-semanal` | Retorna o resumo semanal em JSON. | `200` |
| `GET /relatorio-semanal/csv` | Baixa o resumo semanal em CSV. | `200` |
| `GET /openapi.json` | Retorna a especificação OpenAPI. | `200` |

O [guia de integração](docs/api-integration.md) detalha os payloads, as respostas, o CORS e o download via JavaScript.

## Regras de negócio

- A capacidade padrão é de **4.000 g**. O peso deve estar entre zero e a capacidade informada, que precisa ser positiva.
- O percentual é calculado com `peso_atual_g / capacidade_max_g × 100`. O status usa o valor antes do arredondamento para exibição.

| Disponibilidade | Status |
| --- | --- |
| Menor que 25% | `ACABANDO` |
| A partir de 25% e abaixo de 50% | `ATENCAO` |
| A partir de 50% | `OK` |

- O consumo estimado é a redução de peso entre leituras consecutivas da mesma balança e do mesmo prato. Peso inalterado ou aumento por reposição tem consumo zero.
- A primeira leitura e a troca de prato definem uma nova referência com consumo zero. A comparação de nomes ignora diferenças de maiúsculas, minúsculas e representações Unicode equivalentes.
- Um novo alerta é contado ao entrar em `ACABANDO`, inclusive na primeira leitura ou após trocar de prato. Leituras críticas consecutivas do mesmo prato não somam novos eventos.
- As leituras devem chegar em ordem cronológica por balança. Um instante anterior retorna `409`. Se os timestamps forem iguais, o ID resolve o empate.
- O relatório cobre o dia atual e os seis anteriores em `America/Sao_Paulo`. As leituras são armazenadas em UTC e agrupadas pelo dia local.

## Testes automatizados

```shell
python -m pytest -v
python -m pytest -q
```

Os testes que acessam o SQLite usam bancos em diretórios temporários. A validação integrada executou **128 testes com sucesso** no Python 3.15.2. Python 3.11 não estava instalado neste ambiente para verificação.

## Demonstração

1. Inicie o backend e abra o Swagger.
2. Registre uma leitura de Arroz em uma balança com capacidade de 4.000 g.
3. Envie pesos decrescentes e consulte `GET /estado-atual`.
4. Reduza o peso abaixo de 25% para observar `ACABANDO` e um novo alerta.
5. Envie uma reposição, confira a mudança de status e consulte o relatório semanal.
6. Baixe o CSV e compare o consumo e os alertas com o relatório JSON.

O [roteiro completo](docs/demo-guide.md) inclui um banco isolado, payloads copiáveis e resultados esperados.

## Limitações do MVP

- O consumo é uma estimativa de retirada da cuba. Reduções podem incluir desperdício ou retirada operacional, além do alimento servido.
- A API funciona sem autenticação. O CORS está configurado para origens locais de desenvolvimento.
- A demonstração usa dados simulados. Uma implantação com hardware físico exigirá calibração, tara e validação das medições.
- A ordem cronológica é obrigatória por balança. O relatório cobre uma janela fixa e não oferece filtros.
- O SQLite permite leituras concorrentes em modo WAL, mas serializa as escritas. Os testes exercitam a concorrência esperada no MVP.

## Evoluções futuras

- Integração física com ESP32 e sensores de peso.
- Calibração automática.
- Integração com registros de venda.
- Indicadores de desperdício.
- Previsão de demanda.
- Monitoramento de múltiplas unidades de restaurante.

## Equipe

| Integrante | Responsabilidade |
| --- | --- |
| Integrante 1 | Entrada de dados e simulador: pesos e pratos, quedas, reposição e histórico semanal. |
| Integrante 2 | Backend, banco de dados, regras de consumo e status e relatório semanal. |
| Integrante 3 | Dashboard com atualização automática, avisos de reposição, relatório, cópia do resumo e CSV. |


## Fluxo de desenvolvimento e integração

1. Padronização inicial: alinhar os campos de envio de leitura (`balanca_id`, `prato`, `peso_atual_g`, `capacidade_max_g`, `origem`) e as rotas antes de codar em paralelo.
2. Núcleo em tempo real: subir o envio de leituras, o cálculo de status e o painel exibindo as 5 posições e os avisos abaixo de 25%.
3. Ciclo de reposição e relatório: testar a subida de peso na reposição (sem contar como consumo) e validar o consolidado semanal com dados de teste.
4. Refinamento e consistência: tratar valores inválidos (como peso negativo ou acima da capacidade máxima) e conferir se o painel reflete as mudanças sem travar.

## Executar os três componentes integrados

Na raiz do worktree `smart-buffet-integration`, use um ambiente Python com as dependências de `requirements.txt`. Os comandos abaixo presumem que `python` aponta para esse ambiente. Cada servidor deve ficar em seu próprio terminal.

1. Inicie a API, preservando qualquer banco já existente:

   ```powershell
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. Para preencher os sete dias, execute **antes do simulador contínuo**:

   ```powershell
   python -m simuladores.simulador_balancas --historico-semanal
   ```

   O gerador envia 175 leituras pela API, em ordem cronológica, para cinco pratos com capacidade de 4.000 g. O resultado esperado é **112.000 g de consumo e 35 eventos de alerta**, com sete dias em São Paulo e timestamps UTC. Prepare um banco inicialmente vazio e mantenha o simulador contínuo e qualquer outro processo de escrita parados até terminar a carga. O gerador recusa o envio se a API já tiver leituras. Não remova o banco para repetir: use uma nova instância isolada, como no comando abaixo, na porta 8000 com a API anterior encerrada:

   ```powershell
   python -c "from pathlib import Path; from tempfile import mkdtemp; import uvicorn; from app.database import database; database.DB_PATH = Path(mkdtemp(prefix='smart-buffet-integrado-')) / 'demo.db'; uvicorn.run('app.main:app', host='127.0.0.1', port=8000)"
   ```

3. Sirva o dashboard em outro terminal:

   ```powershell
   python -m http.server 5500 --bind 127.0.0.1 --directory frontend
   ```

   Abra [o dashboard ao vivo](http://127.0.0.1:5500/dashboard.html). Ele consulta a API na porta 8000, atualiza as cubas a cada três segundos e o relatório a cada trinta segundos. Se o monitoramento falhar, o painel mostra “Desconectado”, identifica as últimas leituras como desatualizadas e continua tentando reconectar. Uma falha isolada no relatório não altera a conexão das balanças. O botão CSV baixa o arquivo gerado pelo backend. O [modo demonstrativo opcional](http://127.0.0.1:5500/dashboard.html?mock=1) usa dados fictícios e aparece identificado como “Simulação”.

4. Para continuar gerando leituras reais, execute em outro terminal:

   ```powershell
   python -m simuladores.simulador_balancas
   ```

   Encerre com `Ctrl+C`. Para uma execução curta, use `--ciclos 3 --intervalo 1 --seed 42`. Para imprimir sem enviar, acrescente `--somente-imprimir`. Uma API em outra porta pode ser selecionada com `--url http://127.0.0.1:8001`; ajuste também `API_URL` no dashboard caso queira consultá-la.

A API recebe pesos e capacidades em **gramas inteiras**, com origem `simulador`, `manual` ou `esp32`. O simulador usa `httpx`, já presente nas dependências, e informa falhas de conexão ou rejeição da API. Não repete automaticamente um POST que possa já ter sido gravado. A carga semanal usa POSTs independentes: se for interrompida, os registros aceitos permanecem no banco. Não repita a carga cegamente após uma falha; confira os dados e use outra instância isolada com banco novo para repetir a demonstração completa, preservando a base anterior.

Veja [o relatório da integração](docs/integration-report.md) para as revisões utilizadas, validações e pendências.
