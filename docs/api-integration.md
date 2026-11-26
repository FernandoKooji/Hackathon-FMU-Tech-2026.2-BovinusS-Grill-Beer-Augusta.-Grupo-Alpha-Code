# Integração com a API do Smart Buffet Analytics

## Instalação local

Na raiz do repositório, use estes comandos para criar e ativar o ambiente virtual no PowerShell e instalar as dependências.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

No Linux ou macOS, ative o ambiente com `source .venv/bin/activate` antes de instalar as dependências.

Inicie o backend no mesmo terminal.

```shell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

A API local usa a URL base `http://127.0.0.1:8000`. O SQLite é inicializado na partida. O simulador pode enviar leituras assim que `GET /health` retornar `200`.

## Endpoints

| Método e rota | Uso |
| --- | --- |
| `GET /` | Identificação do projeto. |
| `GET /health` | Verifica se a API está disponível. |
| `POST /leituras` | Registra uma leitura do simulador e retorna `201 Created`. |
| `GET /estado-atual` | Retorna `200 OK` com a leitura mais recente de cada balança monitorada. |
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

O peso e a capacidade são números inteiros em gramas. A capacidade padrão é `4000` e a origem padrão é `simulador`. As demais origens aceitas são `manual` e `esp32`. Com `criado_em` omitido ou `null`, o servidor usa o horário atual em UTC. Para enviar uma data específica, use ISO 8601 com fuso, por exemplo `2025-01-01T09:00:00-03:00`.

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

`422 Unprocessable Entity` indica um payload inválido e traz os erros em `detail`. `409 Conflict` indica que a data é anterior à última leitura da mesma balança e traz uma mensagem em `detail`.

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

## CORS no desenvolvimento

Sirva a interface por HTTP local usando `localhost` ou `127.0.0.1` nas portas `5500`, `3000` ou `5173`. A API permite `GET`, `POST` e `OPTIONS` dessas origens, com `Content-Type` para JSON e sem credenciais. Revise a lista de origens antes de implantar em produção.
