# Roteiro de demonstração do backend

Use o Swagger para registrar pesos simulados, observar a disponibilidade e baixar o relatório semanal. O roteiro usa apenas a API.

## 1. Prepare e inicie o servidor

Instale e ative o ambiente conforme o [README](../README.md#instalação). Execute os comandos a partir da raiz do repositório.

Se o PowerShell bloquear a ativação, use `.\.venv\Scripts\python.exe` no lugar de `python` no comando abaixo.

**Para reproduzir os totais deste roteiro, comece com um banco vazio.** O comando abaixo coloca o banco em uma pasta temporária nova e usa a porta local 8001. Uma nova execução cria outro banco de demonstração. O caminho do banco aparece no terminal.

```shell
python -c "from pathlib import Path; from tempfile import mkdtemp; import uvicorn; from app.database import database; database.DB_PATH = Path(mkdtemp(prefix='smart-buffet-demo-')) / 'demo.db'; uvicorn.run('app.main:app', host='127.0.0.1', port=8001)"
```

Para consultar uma base local já existente, siga a [execução padrão](../README.md#execução) na porta 8000. Nesse caso, as leituras anteriores influenciam os totais. Se quiser reproduzir as transições de uma primeira leitura nessa base, substitua `balanca_id` em todos os blocos pelo mesmo ID de uma balança sem histórico. Mantenha o banco existente e use a opção isolada para começar do zero.

Os links abaixo apontam para a porta 8001. Se usar a execução padrão, troque a porta por 8000.

## 2. Confirme a inicialização

1. Acesse [GET /health](http://127.0.0.1:8001/health) e confira o HTTP `200`.
2. Abra o [Swagger](http://127.0.0.1:8001/docs) e localize `POST /leituras`, `GET /estado-atual`, `GET /relatorio-semanal` e `GET /relatorio-semanal/csv`.
3. Em um banco vazio, [GET /estado-atual](http://127.0.0.1:8001/estado-atual) retorna lista vazia e zero nas duas contagens.

## 3. Registre a primeira leitura e reduza o peso

No Swagger, abra `POST /leituras`, clique em **Try it out** e execute cada bloco abaixo como uma requisição separada, na ordem apresentada. O servidor usa 4.000 g de capacidade, origem `simulador` e o horário atual quando esses campos são omitidos.

**Primeira leitura — 4.000 g.**

```json
{"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 4000}
```

**Consumo gradual — 3.000 g e depois 1.500 g.**

```json
{"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 3000}
```

```json
{"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 1500}
```

**Entrada em estado crítico — 900 g.**

```json
{"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 900}
```

Consulte o [estado atual](http://127.0.0.1:8001/estado-atual). A balança deve aparecer com 22,5%, status `ACABANDO` e `total_acabando` igual a 1. A resposta do registro tem `novo_alerta` igual a 1.

**Leitura crítica consecutiva — 700 g.**

```json
{"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 700}
```

**Reposição — 4.000 g.**

```json
{"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 4000}
```

As seis requisições retornam `201`. Estes são os valores esperados no banco isolado.

| Peso | Percentual | Status | Consumo | Novo alerta |
| ---: | ---: | --- | ---: | ---: |
| 4.000 g | 100% | `OK` | 0 g | 0 |
| 3.000 g | 75% | `OK` | 1.000 g | 0 |
| 1.500 g | 37,5% | `ATENCAO` | 1.500 g | 0 |
| 900 g | 22,5% | `ACABANDO` | 600 g | 1 |
| 700 g | 17,5% | `ACABANDO` | 200 g | 0 |
| 4.000 g | 100% | `OK` | 0 g | 0 |

## 4. Confira o estado atual e o relatório

- [Estado atual](http://127.0.0.1:8001/estado-atual) mostra Arroz com 4.000 g e status `OK`. `total_monitoradas` vale 1 e `total_acabando` vale 0.
- [Relatório semanal](http://127.0.0.1:8001/relatorio-semanal) mostra 3.300 g, 3,3 kg e um alerta. Arroz é o único prato. Se a demonstração ocorrer no mesmo dia em São Paulo, todo o consumo aparece nesse dia e os seis anteriores ficam zerados.
- [Download CSV](http://127.0.0.1:8001/relatorio-semanal/csv) entrega um arquivo com o período no nome e uma linha para Arroz, com `3300` gramas, `3,300` quilogramas e `1` alerta.

Encerre o servidor da demonstração com **Ctrl+C** no terminal em que ele foi iniciado.
