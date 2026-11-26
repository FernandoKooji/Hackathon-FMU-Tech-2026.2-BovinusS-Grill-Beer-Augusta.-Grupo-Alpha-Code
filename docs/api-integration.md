# Integração com a API do Smart Buffet Analytics

## Instalação local

Na raiz do repositório, use estes comandos para criar e ativar o ambiente virtual no PowerShell e instalar as dependências.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Se o PowerShell bloquear o script de ativação, use `.\.venv\Scripts\python.exe` no lugar de `python` a partir do comando de instalação.

No Linux ou macOS, ative o ambiente com `source .venv/bin/activate` antes de instalar as dependências.

A dependência `tzdata` fornece a base de fusos horários usada por `zoneinfo` em sistemas sem uma base IANA instalada, como o Windows.

Inicie o backend no mesmo terminal.

```shell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

A API local usa a URL base `http://127.0.0.1:8000`. O SQLite é inicializado na partida. O simulador pode enviar leituras assim que `GET /health` retornar `200`.

Para testar pela documentação interativa com um banco SQLite isolado, siga o [roteiro de demonstração](demo-guide.md).

## Endpoints

| Método e rota | Uso |
| --- | --- |
| `GET /` | Identificação do projeto. |
| `GET /health` | Verifica se a API está disponível. |
| `POST /leituras` | Registra uma leitura do simulador e retorna `201 Created`. |
| `GET /estado-atual` | Retorna `200 OK` com a leitura mais recente de cada balança monitorada. |
| `GET /relatorio-semanal` | Retorna `200 OK` com o relatório semanal em JSON. |
| `GET /relatorio-semanal/csv` | Retorna `200 OK` com o download do relatório semanal. |
| `GET /docs` | Documentação interativa Swagger UI. |
| `GET /redoc` | Referência ReDoc. |
| `GET /openapi.json` | Contrato OpenAPI em JSON. |

## Simulador

Envie JSON para `POST /leituras` com o cabeçalho `Content-Type: application/json`. O payload mínimo é este.

```json
{
  "balanca_id": 1,
  "prato": "Arroz",
  "peso_atual_g": 3200
}
```

Também é possível enviar os campos opcionais.

```json
{
  "balanca_id": 1,
  "prato": "Arroz",
  "peso_atual_g": 3200,
  "capacidade_max_g": 4000,
  "origem": "simulador",
  "criado_em": null
}
```

| Campo | Tipo | Regras |
| --- | --- | --- |
| `balanca_id` | Inteiro | Obrigatório, de 1 a 5. |
| `prato` | Texto | Obrigatório. O servidor remove espaços nas extremidades e rejeita texto vazio ou com caractere nulo. |
| `peso_atual_g` | Inteiro | Obrigatório, de zero até a capacidade. Unidade em gramas. |
| `capacidade_max_g` | Inteiro | Opcional, maior que zero. Padrão de 4.000 g. |
| `origem` | Texto | Opcional. Aceita `simulador`, `manual` ou `esp32`. Padrão `simulador`. |
| `criado_em` | Texto ou `null` | Opcional. Com `null` ou campo omitido, usa o horário atual do servidor. |

Para enviar uma data específica, use ISO 8601 com fuso, por exemplo `2025-01-01T09:00:00-03:00`. A API rejeita datas futuras e retorna timestamps de leitura em UTC.

Este é um exemplo de resposta `201 Created` para a primeira leitura da balança.

```json
{
  "id": 1,
  "balanca_id": 1,
  "prato": "Arroz",
  "peso_atual_g": 3200,
  "capacidade_max_g": 4000,
  "percentual": 80.0,
  "consumo_g": 0,
  "status": "OK",
  "novo_alerta": 0,
  "origem": "simulador",
  "criado_em": "2025-01-01T12:00:00Z"
}
```

`novo_alerta` é um inteiro que vale `1` para um novo evento e `0` nas demais leituras. `consumo_g` é a quantidade estimada retirada da cuba desde a leitura anterior do mesmo prato.

- `422 Unprocessable Entity` indica um payload inválido e traz a lista de erros em `detail`.
- `409 Conflict` indica uma leitura anterior à última da mesma balança e traz uma mensagem em `detail`. Timestamps iguais são aceitos e desempatados pelo ID.

### Histórico para a demonstração

1. Antes de iniciar a simulação em tempo real, escolha datas dentro do período retornado por `GET /relatorio-semanal`.
2. Envie as leituras por `POST /leituras` da mais antiga para a mais recente **em cada balança**. Defina `criado_em` explicitamente com o fuso e use apenas instantes passados. A primeira leitura de cada prato na balança é a referência de peso para as reduções seguintes.
3. Confira o histórico pelo relatório JSON ou CSV. Em seguida, inicie a simulação em tempo real com `criado_em` omitido ou `null`. Se a balança já tiver uma leitura mais recente do que o histórico a enviar, o backend retorna `409`.

## Dashboard

Consulte `GET /estado-atual` para exibir as balanças. A lista contém a leitura mais recente de cada balança com dados, em ordem crescente de `balanca_id`.

```json
{
  "balancas": [
    {
      "balanca_id": 1,
      "prato": "Arroz",
      "peso_atual_g": 3200,
      "capacidade_max_g": 4000,
      "percentual": 80.0,
      "status": "OK"
    }
  ],
  "total_monitoradas": 1,
  "total_acabando": 0
}
```

Antes da primeira leitura, a API retorna `{"balancas": [], "total_monitoradas": 0, "total_acabando": 0}`.

## Relatório semanal

`GET /relatorio-semanal` considera o dia atual e os seis dias anteriores no fuso `America/Sao_Paulo`. `periodo.inicio` e `periodo.fim` são datas locais inclusivas. A consulta inclui a meia-noite do primeiro dia e exclui a meia-noite após o último dia. Os timestamps ficam em UTC no SQLite e são convertidos para o dia local para compor `consumo_diario`.

`consumo_g` é a estimativa de quanto foi retirado da cuba. O indicador não mede vendas efetivamente registradas. Reposições contribuem com zero gramas. `total_alertas` soma os novos alertas registrados, sem repetir o evento a cada leitura consecutiva no estado `ACABANDO`. Os totais incluem todas as origens, inclusive `simulador`.

Os pratos são agrupados por nome, considerando equivalentes as diferenças de caixa e as formas Unicode equivalentes do mesmo nome. O relatório exibe a grafia da primeira leitura do grupo no período. O ranking vai do maior ao menor consumo em gramas, com desempate pelo nome normalizado. `consumo_diario` contém os sete dias em ordem cronológica, com zero nos dias sem consumo.

Exemplo do contrato JSON para um período ilustrativo.

```json
{
  "periodo": {"inicio": "2026-11-19", "fim": "2026-11-25"},
  "consumo_total_g": 8500,
  "consumo_total_kg": 8.5,
  "total_alertas": 2,
  "pratos": [
    {
      "prato": "Arroz",
      "consumo_g": 8500,
      "consumo_kg": 8.5,
      "total_alertas": 2,
      "consumo_diario": [
        {"data": "2026-11-19", "consumo_g": 0},
        {"data": "2026-11-20", "consumo_g": 0},
        {"data": "2026-11-21", "consumo_g": 0},
        {"data": "2026-11-22", "consumo_g": 0},
        {"data": "2026-11-23", "consumo_g": 0},
        {"data": "2026-11-24", "consumo_g": 3500},
        {"data": "2026-11-25", "consumo_g": 5000}
      ]
    }
  ]
}
```

Quando o período não contém leituras, a resposta mantém `periodo`, devolve os totais zerados e retorna `pratos: []`. O CSV contém apenas o cabeçalho.

Exemplo de consulta no dashboard.

```javascript
const api = 'http://127.0.0.1:8000';

async function consultarRelatorioSemanal() {
  const resposta = await fetch(`${api}/relatorio-semanal`);
  if (!resposta.ok) {
    throw new Error(`Falha ao consultar relatório (${resposta.status})`);
  }
  return resposta.json();
}
```

### Download CSV

`GET /relatorio-semanal/csv` exporta uma linha por prato na mesma ordem do JSON, usando UTF-8 com BOM, delimitador `;` e vírgula decimal com três casas em `consumo_kg`. Nomes que poderiam ser interpretados como fórmulas recebem um apóstrofo no CSV. O nome armazenado e o exibido no JSON são preservados.

```csv
periodo_inicio;periodo_fim;prato;consumo_g;consumo_kg;total_alertas
2026-11-19;2026-11-25;Arroz;8500;8,500;2
```

`Content-Disposition` indica que a resposta é um anexo e fornece o nome sugerido, por exemplo `relatorio-semanal_2026-11-19_2026-11-25.csv`. O navegador aceita download direto pelo endpoint, e o CORS expõe esse cabeçalho ao JavaScript das origens autorizadas. Para baixar com `fetch`, a função abaixo usa a constante `api` do exemplo anterior.

```javascript
async function baixarRelatorioSemanal() {
  const resposta = await fetch(`${api}/relatorio-semanal/csv`);
  if (!resposta.ok) {
    throw new Error(`Falha ao baixar relatório (${resposta.status})`);
  }

  const disposicao = resposta.headers.get('Content-Disposition') ?? '';
  const nome = /filename="([^"]+)"/.exec(disposicao)?.[1] ?? 'relatorio-semanal.csv';
  const blob = await resposta.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = nome;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
```

### Limitações do MVP

O período é fixo em sete dias de calendário e termina no dia atual de São Paulo. O relatório não oferece filtros por período, origem ou balança. Cada consulta usa os dados disponíveis naquele momento. Se o simulador registrar novas leituras entre duas requisições, a prévia em JSON e o download podem refletir instantes diferentes.

## CORS no desenvolvimento

Sirva a interface por HTTP local usando `localhost` ou `127.0.0.1` nas portas `5500`, `3000` ou `5173`. A API permite `GET`, `POST` e `OPTIONS` dessas origens, com `Content-Type` para JSON e sem credenciais. Revise a lista de origens antes de implantar em produção.
