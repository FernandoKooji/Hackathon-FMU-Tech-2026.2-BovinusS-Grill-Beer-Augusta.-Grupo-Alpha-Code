# Arquitetura do sistema integrado

O Smart Buffet Analytics integra o simulador Python, o backend FastAPI, o banco SQLite e o dashboard HTML/CSS/JavaScript. O simulador envia leituras reais por HTTP; o backend calcula disponibilidade, consumo e alertas e armazena o histórico. O dashboard consulta o estado atual e o relatório semanal e baixa o CSV produzido pela API. O Swagger também permite enviar leituras manualmente. A integração física com ESP32 e sensores permanece futura.

## Componentes

```mermaid
flowchart LR
    Sim["Simulador Python existente"] -->|"POST /leituras via HTTPX"| API["Backend FastAPI existente"]
    Swagger["Swagger: envio manual"] -->|"POST /leituras"| API
    IoT["ESP32 e sensores: integração física futura"] -.->|"POST /leituras previsto"| API
    Painel["Dashboard HTML/CSS/JS existente"] -->|"GET estado atual, relatório e CSV"| API
    API <--> Schemas["Schemas Pydantic"]
    API --> Leituras["Serviço de leituras"]
    API --> Relatorio["Serviço de relatórios"]
    Leituras --> SQL["Conexões e queries SQLite"]
    Relatorio --> SQL
    SQL --> Dados[("SQLite existente: tabela leituras")]
    Relatorio --> CSV["CSV em memória"]
    CSV --> API
```

| Componente | Responsabilidade |
| --- | --- |
| `simuladores/simulador_balancas.py` | Simula cinco balanças, consumo e reposição; envia leituras à API e gera histórico de sete dias. |
| `frontend/dashboard.html` | Exibe pesos, status, alertas e relatório; consulta a API real por padrão e oferece download do CSV. |
| `app/main.py` | Configura CORS, registra os routers e inicializa o banco no ciclo de vida da API. |
| `app/routers/` | Expõe os endpoints síncronos, encaminha chamadas aos serviços e define as respostas HTTP. |
| `app/schemas/` | Valida as leituras recebidas e define os contratos de saída. |
| `app/services/` | Calcula disponibilidade, consumo, alertas e agregações do relatório. |
| `app/database/` | Inicializa o SQLite, abre conexões e mantém o SQL parametrizado. |
| `app/utils/` | Define constantes e uma chave de comparação de nomes usando NFC e `casefold()`. |
| `tests/` | Verifica contratos, regras, API, persistência, concorrência, relatórios e simulador com bancos temporários. |
| `docs/` | Mantém os contratos de integração, o roteiro de demonstração e os resultados da integração. |

## Execução e comunicação entre componentes

Na raiz do projeto, com as dependências instaladas, execute cada servidor em seu próprio terminal:

```shell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```shell
python -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

A API fica em `http://127.0.0.1:8000`, com Swagger em `/docs` e ReDoc em `/redoc`. O dashboard fica em `http://127.0.0.1:5500/dashboard.html`; seu `API_URL` aponta para a porta 8000. O servidor estático entrega a interface e o navegador consulta diretamente o backend, com CORS autorizado para essa origem.

Para a demonstração semanal, use primeiro `python -m simuladores.simulador_balancas --historico-semanal` em uma instância com banco vazio. Mantenha os demais escritores parados até concluir a carga. Depois, inicie `python -m simuladores.simulador_balancas` para gerar leituras em tempo real. O [README](../README.md#executar-os-três-componentes-integrados) contém instalação, opções do simulador e comando para uma instância com banco temporário, preservando os dados existentes.

O navegador consulta `GET /estado-atual` a cada três segundos e `GET /relatorio-semanal` a cada trinta segundos. O botão CSV busca `GET /relatorio-semanal/csv`. Se o monitoramento falhar, o indicador muda para “Desconectado”, as últimas leituras ficam identificadas como desatualizadas e o banner deixa de afirmar que o abastecimento é atual. A próxima consulta bem-sucedida restaura o estado normal. Falhas do relatório são apresentadas separadamente. O modo mock exige `?mock=1` e não é ativado como fallback de falhas.

## Registro de uma leitura

1. `POST /leituras` valida balança, prato, peso, capacidade, origem e timestamp. Dados inválidos retornam `422`.
2. O serviço abre uma conexão e inicia `BEGIN IMMEDIATE` antes de consultar a última leitura da balança, ordenada por `criado_em DESC, id DESC`.
3. O serviço rejeita um timestamp anterior ao último da balança. O router traduz o conflito para `409`. Timestamps iguais são aceitos.
4. O serviço usa a última leitura da balança como referência quando o prato continua o mesmo. Calcula o consumo, determina o status pelo percentual e identifica um novo evento de alerta. A primeira leitura e a troca de prato reiniciam a referência de consumo e alerta.
5. A nova leitura é inserida e recuperada pelo ID. O serviço valida a resposta antes de confirmar a transação. Em caso de erro, executa rollback. A conexão é fechada ao concluir a operação.

A transação engloba a leitura anterior e a nova inserção. Isso permite que escritas concorrentes na mesma balança usem como referência a última leitura confirmada.

## Consulta do estado atual

`GET /estado-atual` usa `ROW_NUMBER()` para selecionar a última leitura de cada balança. O serviço recalcula o percentual a partir dos pesos, mantém o status persistido e retorna as balanças por ID crescente. `total_monitoradas` conta as balanças com leituras e `total_acabando` conta as que estão no estado `ACABANDO`. O banco vazio retorna lista vazia e totais zero.

## Geração do relatório semanal

1. O serviço calcula sete dias de calendário em `America/Sao_Paulo`. Converte para UTC a meia-noite do primeiro dia e a meia-noite após o último dia.
2. O SQLite recupera as linhas no intervalo `[início, fim)`. A query agrupa registros com o mesmo nome, timestamp e consumo e soma os eventos de alerta de cada grupo.
3. O serviço converte cada timestamp para a data local e acumula gramas por prato e dia. Usa a grafia da primeira leitura do grupo no período para exibição e preenche os dias sem consumo com zero.
4. O resultado é ordenado por consumo decrescente, com desempate pelo nome normalizado. A API oferece o mesmo cálculo em JSON e CSV. Cada chamada consulta o banco no momento em que é feita.

A exportação gera o CSV em memória, com UTF-8 com BOM, delimitador ponto e vírgula, vírgula decimal e proteção de células de texto que poderiam ser interpretadas como fórmulas.

## Armazenamento SQLite

O lifespan lê `schema.sql` e cria a tabela e os índices quando necessário. O caminho padrão é `app/database/database.db`. O arquivo local fica fora do Git. O banco opera em modo WAL, com uma conexão por operação e espera de até dez segundos por bloqueios. As escritas são serializadas pelo SQLite.

### Tabela leituras

| Coluna | Tipo | Significado |
| --- | --- | --- |
| `id` | INTEGER | Chave primária autoincrementada, usada para desempatar timestamps iguais. |
| `balanca_id` | INTEGER | Identificador da balança, de 1 a 5. |
| `prato` | TEXT | Nome do prato usado na apresentação. |
| `peso_atual_g` | INTEGER | Peso de zero até a capacidade configurada. |
| `capacidade_max_g` | INTEGER | Capacidade positiva, com padrão de 4.000 g. |
| `consumo_g` | INTEGER | Consumo estimado da leitura, com padrão zero. |
| `status` | TEXT | `OK`, `ATENCAO` ou `ACABANDO`. |
| `novo_alerta` | INTEGER | Evento de alerta, representado por `0` ou `1`. |
| `origem` | TEXT | `simulador`, `manual` ou `esp32`, com padrão `simulador`. |
| `criado_em` | TEXT | Instante em ISO 8601, com microssegundos e offset UTC. |

Há índices por balança, data e prato. O serviço calcula o percentual a partir de peso e capacidade e o inclui nas respostas de leitura e estado atual.

### Timestamps

Timestamps recebidos devem informar fuso e ser no máximo o instante atual. Quando omitidos ou enviados como `null`, recebem o horário UTC do servidor após o início da transação. A gravação usa ISO 8601 com seis casas decimais e offset `+00:00`, permitindo ordenar e filtrar o texto no SQLite. O relatório converte para o calendário de São Paulo na consulta. O pacote `tzdata` fornece a base de fusos em ambientes como Windows.

## Testes

O pytest cobre schemas, regras de negócio, endpoints, CORS, relatório e CSV. O TestClient executa o lifespan com um caminho SQLite temporário definido antes do startup. Os testes de integração usam datas fixas e conferem escrita concorrente, rollback, reinicialização e a correspondência entre JSON e CSV.

## Decisões e limites do MVP

- A rota de ingestão atende diferentes origens pelo mesmo contrato. A origem `esp32` é um valor aceito para uma futura fonte física.
- O consumo é calculado no registro da leitura e usado nas agregações semanais. Ele estima retirada de alimento da cuba e pode incluir desperdício ou retirada operacional.
- O backend é local, sem autenticação, e o CORS permite origens de desenvolvimento específicas.
- O SQLite atende à carga de demonstração. Escritas concorrentes disputam o mesmo banco e operações que excedam a espera por bloqueio podem falhar.
- O relatório tem período fixo e cada consulta lê o histórico disponível naquele momento. O CSV contém o resumo por prato.
- A carga semanal do simulador usa POSTs independentes e pode ficar parcial em caso de interrupção. Essa limitação é aceita para o Hackathon: não repita a carga cegamente e use outra instância com banco novo para uma nova demonstração completa, sem apagar a base anterior.
