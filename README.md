[README (1).md](https://github.com/user-attachments/files/35448804/README.1.md)
# Smart Buffet Analytics

**Hackathon Tech FMU 2026.2 | Desafio Bovinu'S Grill & Beer – Augusta**

## Apresentação

LINK PARA APRESENTAÇÃO E VIDEO: https://drive.google.com/drive/folders/1L3QHWD2KckxwZmeTsMsRW8bxtgIpdblD?usp=sharing

O Smart Buffet Analytics é um MVP de monitoramento de disponibilidade e consumo estimado de alimentos em buffets. A proposta é apoiar a reposição preventiva, reduzir interrupções no atendimento e oferecer dados para o planejamento da produção.

## Descrição do problema

No self-service de uma churrascaria como o **Bovinos Grill**, o controle dos acompanhamentos nas cubas costuma ser feito no olho ou por inspeção visual esporádica. Esse modelo gera dois problemas diretos na operação:

- **Ruptura sem aviso e filas:** quando um prato acaba de repente e a cozinha só percebe depois que a cuba esvazia, o fluxo de atendimento trava e o cliente espera mais do que o necessário.
- **Desperdício e falta de previsibilidade:** sem histórico confiável de saída por prato, a equipe tende a produzir em excesso por precaução — gerando sobras no fim do turno — ou a planejar compras e preparos semanais sem dados objetivos.

## Solução proposta

A solução é um sistema de telemetria operacional e relatório semanal para as cinco posições do buffet, desenvolvido para funcionar com dados simulados ou inseridos manualmente e permitir uma futura integração com balanças e módulos ESP32.

- **Leitura contínua por posição:** registra o peso atual, permite alterar o prato do dia e classifica sua disponibilidade em `OK`, `ATENCAO` ou `ACABANDO`.
- **Aviso de reposição na cozinha:** quando o nível cai abaixo de 25%, o painel destaca o prato em estado crítico para orientar a reposição antes que acabe.
- **Relatório semanal consolidado:** estima o consumo pela redução de peso entre leituras e apresenta os totais dos últimos sete dias, o consumo diário, o ranking por prato e os eventos de alerta, com exportação em CSV.
- **Compatibilidade com hardware futuro:** as leituras passam pelo endpoint `POST /leituras`, permitindo integrar sensores de peso futuramente sem alterar o contrato da API. O objetivo é o controle operacional interno, não a cobrança no caixa.

<!-- IMAGEM 1: Capture o dashboard com as cinco posições preenchidas e os indicadores de disponibilidade visíveis.
Salve em docs/images/dashboard-geral.png e remova os delimitadores deste comentário para exibir a imagem.
![Dashboard geral do buffet](docs/images/dashboard-geral.png)
-->

## Arquitetura

Veja o [documento de arquitetura](docs/architecture.md) para o modelo de dados e os fluxos de execução.

## Tecnologias

| Tecnologia | Uso |
| --- | --- |
| Python e Uvicorn | Execução do backend e servidor ASGI. |
| FastAPI e Pydantic v2 | Rotas HTTP, validação, contratos e OpenAPI. |
| SQLite via `sqlite3` | Armazenamento local das leituras. |
| `zoneinfo` e `tzdata` | Conversão entre UTC e o calendário de São Paulo. |
| pytest, TestClient e HTTPX | Testes de regras, contratos e integração. |

## Detalhamento e desenvolvimento do projeto

### Fluxo de desenvolvimento e integração

1. Padronização inicial: alinhar os campos de envio de leitura (`balanca_id`, `prato`, `peso_atual_g`, `capacidade_max_g`, `origem`) e as rotas antes de codar em paralelo.
2. Núcleo em tempo real: integrar o envio de leituras, o cálculo de status e o painel exibindo as 5 posições e os avisos abaixo de 25%.
3. Ciclo de reposição e relatório: testar a subida de peso na reposição (sem contar como consumo) e validar o consolidado semanal com dados de teste.
4. Refinamento e consistência: tratar valores inválidos (como peso negativo ou acima da capacidade máxima) e conferir se o painel reflete as mudanças sem travar.

## Pré-requisitos

- Python 3.15 (versão indicada no README do backend), com `pip` e `venv`.
- Git para clonar o repositório.
- Dependências fixadas em [requirements.txt](requirements.txt). O SQLite é fornecido pela biblioteca padrão do Python.

## Instalação

Clone o repositório e acesse a pasta. Utilize a branch integrada do projeto (em vez da branch individual de backend).

```shell
git clone https://github.com/FernandoKooji/projeto-hakathon-FMU-2026.2-
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

### Simulador de balanças

Mantenha o backend em execução. Abra outro terminal na raiz do repositório e ative o ambiente virtual conforme as instruções de instalação.

```shell
python simuladores/simulador_balancas.py
```

O simulador gera leituras para as cinco posições do buffet. Para consultar os argumentos disponíveis, execute:

```shell
python simuladores/simulador_balancas.py --help
```

Para interromper o simulador, pressione `Ctrl+C`.

### Dashboard

Em um terceiro terminal, na raiz do repositório e com o ambiente virtual ativo, execute:

```shell
python -m http.server 5500 --directory frontend
```

Abra o [dashboard](http://127.0.0.1:5500/dashboard.html) no navegador. Mantenha os três processos em execução durante a demonstração.

## Demonstração do MVP

1. Inicie o backend, o simulador e o dashboard. Alternativamente, envie leituras pelo Swagger.
2. Registre pratos nas posições monitoradas e simule a redução gradual de peso.

<!-- IMAGEM 2: Capture a interface do simulador em funcionamento, com as posições e os controles de peso.
Salve em docs/images/simulador.png e remova os delimitadores deste comentário para exibir a imagem.
![Simulador de balanças](docs/images/simulador.png)
-->
<img width="1147" height="465" alt="image" src="https://github.com/user-attachments/assets/29208527-ad62-49f6-94a8-892130777c6e" />



3. Reduza o peso de uma cuba abaixo de 25% e observe o alerta no dashboard.

<!-- IMAGEM 3: Capture o painel destacando pelo menos uma cuba em ACABANDO.
Salve em docs/images/alerta-reposicao.png e remova os delimitadores deste comentário para exibir a imagem.
![Alerta de reposição](docs/images/alerta-reposicao.png)
-->
<img width="1150" height="345" alt="image" src="https://github.com/user-attachments/assets/e764027d-6b30-4eb1-95cf-3054c528e874" />


4. Simule a reposição e verifique a recuperação do status, sem contabilizar o aumento como consumo.
5. Consulte o relatório semanal, confira os totais e exporte o CSV.

<!-- IMAGEM 4: Capture a tela do relatório semanal com ranking, consumo e alertas, conforme disponíveis.
Salve em docs/images/relatorio-semanal.png e remova os delimitadores deste comentário para exibir a imagem.
![Relatório semanal](docs/images/relatorio-semanal.png)
-->
<img width="1165" height="713" alt="image" src="https://github.com/user-attachments/assets/68e4a6dc-c546-499f-b167-f7e419c06ade" />
<img width="788" height="390" alt="image" src="https://github.com/user-attachments/assets/4246a02f-f000-4e6c-b08b-8546eeef3fb6" />



6. Utilize o Swagger para demonstrar os endpoints e conferir os dados retornados.

<!-- IMAGEM 5: Capture o Swagger com os endpoints ou uma resposta bem-sucedida de GET /estado-atual.
Salve em docs/images/swagger.png e remova os delimitadores deste comentário para exibir a imagem.
![Documentação interativa da API](docs/images/swagger.png)
-->
<img width="874" height="526" alt="image" src="https://github.com/user-attachments/assets/f100434f-bcd6-474b-859d-dfc570cb3ee2" />


O [roteiro completo](docs/demo-guide.md) contém payloads e resultados esperados para testes do backend.

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

## Endpoints da API

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

## Estrutura do backend

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
│   └── demo-guide.md
├── tests/
│   ├── test_api.py
│   ├── test_integracao.py
│   ├── test_leituras.py
│   ├── test_limites_sqlite.py
│   ├── test_relatorio.py
│   └── test_schemas.py
├── .gitignore
├── README.md
└── requirements.txt
```

A estrutura acima descreve o backend documentado no README1; não representa necessariamente toda a árvore da versão integrada.

## Testes automatizados

```shell
python -m pytest -v
python -m pytest -q
```

Os testes que acessam o SQLite usam bancos em diretórios temporários. O README do backend registra 122 testes bem-sucedidos na Etapa 14; esse resultado não equivale a uma nova execução de testes da versão integrada.

## Limitações do MVP

- O consumo é uma estimativa de retirada da cuba. Reduções podem incluir desperdício ou retirada operacional, além do alimento servido.
- A API funciona sem autenticação. O CORS está configurado para origens locais de desenvolvimento.
- A demonstração usa dados simulados. Uma implantação com hardware físico exigirá calibração, tara e validação das medições.
- A ordem cronológica é obrigatória por balança. O relatório cobre uma janela fixa e não oferece filtros.
- O SQLite permite leituras concorrentes em modo WAL, mas serializa as escritas. Os testes exercitam a concorrência esperada no MVP.
- O sistema não mede diretamente o tempo de fila, as vendas ou o desperdício; monitora a disponibilidade e a retirada estimada de alimentos.

## Evoluções futuras

- Integração física com ESP32 e sensores de peso.
- Calibração automática.
- Integração com registros de venda.
- Indicadores de desperdício.
- Previsão de demanda.
- Monitoramento de múltiplas unidades de restaurante.

## Equipe AlphaCode

### Vitória Peixoto

Desenvolvimento do simulador de balanças, geração de leituras, simulação de consumo e reposição e integração dos componentes do projeto.

### Fernando Shimomura

Desenvolvimento da API com FastAPI, persistência no SQLite, regras de negócio, cálculo de consumo e relatórios semanais.

### Victor Ferreira

Desenvolvimento do dashboard, integração do frontend com a API, monitoramento da disponibilidade, alertas de reposição e visualização dos relatórios.
