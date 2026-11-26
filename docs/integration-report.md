# Relatório da integração do MVP

## Resultado

As três fontes publicadas foram reunidas na branch `integration/mvp`, no worktree `C:\Users\junju\smart-buffet-integration`, a partir do `origin/main` atualizado. A integração inicial passou na validação HTTP e nos 128 testes automatizados, sem push ou merge na main nessa etapa. A estabilização final corrigiu a indicação de desconexão do dashboard e validou conexão, perda de comunicação e recuperação no Edge real, conforme os resultados ao final deste documento.

## Fontes e análise anterior aos merges

Remoto: `https://github.com/FernandoKooji/projeto-hakathon-FMU-2026.2-`.

| Fonte | Commit utilizado | Conteúdo |
| --- | --- | --- |
| origin/main | d6daab1 | Apresentação, problema, solução e divisão da equipe no README. |
| origin/feature/backend | ec604d7 | FastAPI, SQLite, schemas, regras, relatórios, documentação e 122 testes. |
| origin/feature/simulador-balancas | a6d7df8 | Simulação das cinco balanças; saída apenas no terminal. |
| origin/feature/integrante-3-dashboard | 09d0a25 | Dashboard HTML/CSS/JS, alertas, relatório, resumo e CSV demonstrativos. |

As quatro fontes compartilham o ancestral `d3b22de`. Nenhuma das três branches de componente continha os commits das outras. O dashboard foi localizado e confirmado no remoto. Seus arquivos foram preservados como base da integração; não houve reconstrução do trabalho do integrante 3.

Antes do fetch, `origin/main` apontava para `d3b22de`; o fetch atualizou somente essa referência para `d6daab1`. A main local permaneceu em `d3b22de`. A análise de arquivos exclusivos identificou backend em `app/`, `tests/`, `docs/` e arquivos de configuração; simulador em `simuladores/`; dashboard em `frontend/`. Somente o README teve conflito de merge, entre a documentação atualizada da main e a documentação operacional do backend. Ambas foram mantidas, corrigindo a descrição de `OK` para incluir exatamente 50%.

## Preservação do original

O repositório original estava em `feature/integrante-3-dashboard`, commit `09d0a25`, sem modificações ou arquivos não rastreados visíveis no `git status --short --untracked-files=all`. Havia arquivos ignorados, incluindo AGENTS.md, banco SQLite, caches e ambiente virtual. A orientação do AGENTS.md foi lida sem alteração; a solicitação específica autorizou os merges e ajustes dos três componentes somente no novo worktree.

O snapshot inicial em `%TEMP%\smart-buffet-original-20261126.json` registra tamanho e SHA-256 dos **3.613 arquivos** fora de `.git`, inclusive arquivos ignorados. A comparação após a implementação encontrou **zero arquivos alterados, removidos ou acrescentados** no diretório original. O banco original tem 24.576 bytes e SHA-256 `D21A2C499A5D29F251A3C5DD5ED4266ACD474FA28AB5D99B2F55459B54D279E4`.

As branches individuais e a main local mantiveram seus commits. Não foram executados switch/checkout no original, stash, reset, clean, descarte de alterações ou exclusão de banco. Somente o ambiente Python já instalado foi reutilizado para os testes, com `-B` para evitar escrita de bytecode. Merges, código e testes ocorreram no worktree separado.

## Decisões e arquivos ajustados

- `README.md`: consolidação das duas documentações, execução dos três componentes e demonstração com banco isolado sem apagar dados.
- `simuladores/simulador_balancas.py`: preservação do modelo de consumo, ruído e reposição; envio HTTP efetivo, origem válida, gramas inteiras, capacidade padrão compartilhada, execução finita e modo somente impressão. O gerador semanal estava ausente na fonte recebida e foi acrescentado com recusa de carga sobre uma API que já tenha leituras.
- `tests/test_simulador.py`: seis testes de integração para envio, limites de status, reposição, alertas, histórico de sete dias, conflito e proteção dos registros existentes.
- `frontend/dashboard.html`: layout preservado, API real por padrão, mock opcional explícito, mapeamento de `total_alertas` e `consumo_diario[].data`, download do CSV oficial e mensagem de falha no download. Cálculo de status de fallback usa o percentual antes do arredondamento. URLs temporárias de downloads são liberadas.
- `requirements.txt`: conversão de UTF-16 para UTF-8, preservando todas as versões e todos os pacotes. Nenhuma dependência foi acrescentada.
- `docs/integration-report.md`: registro das fontes, decisões, evidências e limitações.

Nenhum contrato público do backend foi alterado. Inicialização SQLite, CORS, routers e regras de negócio foram preservados. A lista de arquivos rastreados não continha bancos ou bytecode nas fontes integradas. O `.gitignore` recebido já ignora SQLite e seus arquivos auxiliares, ambientes virtuais, caches, credenciais e `.env`; não foi necessário alterá-lo.

## Contratos e validação inicial

O OpenAPI foi consultado na API em execução. Entradas: `balanca_id`, `prato`, `peso_atual_g`, `capacidade_max_g`, `origem` e `criado_em`. Peso e capacidade são inteiros estritos. A leitura retorna identificação, peso, capacidade, percentual, consumo, status, novo alerta, origem e timestamp. Estado atual retorna `balancas`, `total_monitoradas` e `total_acabando`. Relatório retorna `periodo`, totais, pratos com `total_alertas` e `consumo_diario` por `data`. Os contratos completos continuam em [api-integration.md](api-integration.md).

| Verificação | Resultado |
| --- | --- |
| Backend antes de integrar clientes | 122 testes aprovados. |
| Simulador integrado | 6 novos testes aprovados. |
| Suíte completa | 128 testes aprovados no Python 3.15.2. |
| Dependências | `python -m pip check`: nenhuma incompatibilidade instalada. |
| HTTP real | Health, OpenAPI, POST e consultas JSON/CSV validados. |
| Histórico pelo CLI contra Uvicorn | 175 leituras; 112.000 g; 35 alertas; segunda carga recusada sem alterar os totais. |
| Eventos críticos adicionais | 900 g e 800 g na balança 1: total 115.200 g e 36 alertas, sem duplicar o segundo alerta crítico. |
| Erros HTTP | Dados inválidos retornaram 422; timestamp retroativo retornou 409. |
| Simulador contínuo limitado | Um ciclo com cinco leituras enviado em HTTP real. |
| CORS | Consultas e preflight das origens localhost:5500 e 127.0.0.1:5500 aprovados; Content-Disposition exposto para o CSV. |
| Dashboard servido por HTTP | Resposta 200 na porta 5500. |
| Preservação do original | 3.613 arquivos iguais por SHA-256, nenhum arquivo novo ou ausente. |

Comando da suíte: `python -B -m pytest -q`. Os testes usam bancos temporários, nunca o banco original. A primeira execução neste worktree falhou por ausência da pasta pai de `--basetemp`; após criar a pasta, a suíte passou. O ambiente emitiu um aviso existente sobre a futura substituição de HTTPX no TestClient do Starlette; não houve atualização de dependências.

Evidências locais, ignoradas pelo Git, estão em `.pytest-tmp/http-validation/` (OpenAPI consultado, saída do histórico, banco exclusivo de validação e resultados JSON) e `.pytest-tmp/http-validation.log`. Os servidores temporários foram encerrados após os testes.

## Limitações e promoção à main

- A validação inicial no navegador ficou pendente, mas foi concluída na estabilização final: cinco cubas, alertas, reposição, sete dias, ranking, cópia, CSV e estados de conexão foram exercitados no Edge real. Outros navegadores não foram testados.
- Python 3.11 consta do contexto inicial, mas apenas Python 3.15.2 estava instalado e é a versão declarada no README recebido do backend. A execução em Python 3.11 não foi validada.
- O histórico semanal precisa ser enviado antes de leituras atuais, com banco inicialmente vazio e todos os outros escritores parados. O preflight recusa uma base já preenchida, mas não bloqueia gravações concorrentes durante os 175 POSTs independentes. Uma interrupção pode deixar carga parcial; não repita a carga cegamente. Preserve os registros aceitos e use outra instância isolada com banco novo para repetir a demonstração completa.
- A referência `origin/integration/mvp` já existia ao iniciar a estabilização. Esta etapa prevê somente commit local; não executa push ou merge na main. A promoção à main continua dependente de autorização posterior.

O anexo da integração inicial terminava em “Nome do” no início da seção 9. Aquela execução considerou as instruções disponíveis, sem presumir conteúdo ausente.

## Estabilização final — 26/11/2026

### Escopo e preservação

Estado inicial confirmado: diretório `C:\Users\junju\smart-buffet-integration`, branch `integration/mvp`, HEAD `9a57c441a4b0fd9285adf4679a6d56a3a4b055cd`, Git limpo e nenhum conflito pendente. O trabalho ficou restrito ao worktree de integração. Backend, simulador, schema SQLite, contratos públicos, dependências e testes existentes foram preservados.

### Correções realizadas

- `frontend/dashboard.html`: o indicador começa em “Conectando…” e passa a “Ao vivo” após uma consulta válida. Se `GET /estado-atual` falhar, muda para “Desconectado”, substitui o banner de abastecimento por uma mensagem de comunicação indisponível e preserva os pesos e status como últimas leituras conhecidas. As cubas e os indicadores de monitoramento ficam visualmente neutros e identificados como dados desatualizados. Sem leituras anteriores, o painel informa a ausência de dados, sem inventar valores ou ativar mock.
- O polling continua após falhas. A primeira consulta bem-sucedida restaura pesos, status, alertas, cores e indicador de conexão. O horário da última consulta bem-sucedida é preservado durante a desconexão. Uma consulta de estado ainda em andamento não é sobreposta por outro ciclo.
- A consulta do relatório mantém tratamento de erro separado: uma falha somente nele não muda a conexão das balanças. O mock continua opcional somente por `?mock=1`.
- `docs/architecture.md`: descrição, diagrama Mermaid, componentes, fluxo HTTP, comandos e URLs refletem os componentes integrados existentes. ESP32 e sensores físicos permanecem explicitamente futuros.
- `README.md`: consolidação das descrições repetidas de problema, solução e equipe, preservando as contribuições dos três integrantes. O clone aponta para `integration/mvp`; a estrutura inclui o relatório de integração e os testes do simulador. Os comandos de execução continuam correspondendo às interfaces reais.
- `README.md` e `docs/api-integration.md`: orientações explícitas sobre ordem da carga semanal, banco vazio, exclusividade de escrita, carga parcial e proibição de repetição cega após uma falha.

A ressalva da carga semanal parcial foi **aceita deliberadamente para o Hackathon**. Não foram acrescentados endpoint em lote, transação de importação, retomada, exclusão de leituras, reset do banco ou mudança de schema.

### Python e regressão

`python --version` e `py -0p` identificaram somente **Python 3.15.2**. A suíte foi executada nessa versão, reutilizando o ambiente temporário da revisão anterior, sem modificar o Python global ou o ambiente virtual original. Python 3.11 não estava disponível e **não foi validado nem instalado**. Nenhuma dependência foi atualizada para eliminar o aviso de depreciação do TestClient.

Comando executado: `python -m pytest -q`. As fixtures definem `DB_PATH` em bancos temporários antes de inicializar a API. `PYTHONDONTWRITEBYTECODE=1` evitou bytecode; `PYTEST_ADDOPTS` desativou o cache e direcionou `basetemp` e JUnit para `%TEMP%`, usando barras normais nos caminhos para evitar interpretação incorreta no Windows.

| Verificação desta estabilização | Aprovados | Reprovados | Ignorados |
| --- | ---: | ---: | ---: |
| Suíte pytest: regras, persistência e HTTP via TestClient | 128 | 0 | 0 |
| Smoke HTTP real com Uvicorn: rodada completa final | 12 | 0 | 0 |
| Navegador real Edge 158.0.4370.33: rodada completa final | 20 | 0 | 0 |

O pytest terminou com um aviso de depreciação do TestClient e nenhum erro. `python -m pip check` não encontrou incompatibilidades. `git diff --check` passou. Essas verificações estáticas e de ambiente são distintas dos testes HTTP e de navegador da tabela.

### Conexão e reconexão no navegador real

Foi reutilizado o método de automação pelo protocolo DevTools do Edge, com perfil exclusivo de teste, servidores locais e SQLite em `%TEMP%`. O servidor estático serviu `http://127.0.0.1:5500/dashboard.html`; a API de teste usou a porta 8000 e um caminho SQLite substituído em memória antes da inicialização.

1. Com a API inicialmente desligada, o dashboard mostrou “Desconectado” e ausência de leituras, mantendo os indicadores sem valores inventados e sem fallback mock.
2. Ao iniciar a API com banco vazio, o polling restaurou “Ao vivo” e informou corretamente que ainda não havia leituras.
3. O CLI enviou 175 leituras pela API real. Foram confirmados cinco pratos, sete dias, **112.000 g e 35 alertas**. Uma segunda carga foi recusada sem alterar os totais. Também foram conferidos `422`, `409`, CORS, OpenAPI, Swagger, ReDoc e CSV com BOM e totais iguais ao JSON.
4. Leituras de 900 g e 800 g na balança 1 produziram um único novo alerta; a reposição para 4.000 g teve consumo zero. O relatório atualizado pelo timer mostrou **115.200 g e 36 alertas**. Ranking, sete dias, download real do CSV e cópia do resumo foram preservados.
5. O bloqueio somente da consulta do relatório no navegador exibiu seu erro sem desconectar as balanças. A liberação dessa consulta removeu o erro isoladamente.
6. O processo Uvicorn criado para o teste foi encerrado. Após o polling, o indicador mudou para “Desconectado”, o banner verde desapareceu e os mesmos pesos e status ficaram identificados como desatualizados, em cores neutras. O horário da última atualização válida permaneceu estável durante novas falhas. As mensagens de falha do relatório e do CSV continuaram funcionando.
7. O Uvicorn foi reiniciado com o mesmo banco temporário, preservando os dados. O dashboard reconectou automaticamente, retirou os marcadores de desatualização e restaurou o banner atual. Uma nova leitura de 500 g apareceu pelo polling, com `ACABANDO` e aviso de reposição.
8. O modo `?mock=1` continuou identificado como “Simulação”; o retorno à URL padrão recuperou os dados reais. Não houve exceções JavaScript não tratadas.

A preparação teve uma tentativa sem porta DevTools e outra interrompida pela automação da cópia sem foco. Com outro perfil temporário e clique com foco real, a rodada final concluiu as 20 verificações. As contagens da tabela se referem à execução completa final, sem somar repetições das tentativas parciais; os 36 checks HTTP e 11 checks de navegador da revisão anterior não foram reutilizados como resultados desta etapa.

Os processos temporários foram encerrados ao final, sem interromper servidores externos ao teste. Nenhum banco original foi usado, e `app/database/database.db` não foi criado. Evidências locais fora do Git: `%TEMP%\smart-buffet-stabilization-fpb6wxbc\pytest-results.xml` e, na subpasta `final`, `validation-results.json`, logs, CSV baixado e as capturas `dashboard-desconectado.png` e `dashboard-reconectado.png`.

Permanecem como limites do MVP a carga semanal não atômica, a ausência de validação em Python 3.11 e outros navegadores, a operação local sem autenticação e a integração física futura com ESP32.
