# Relatório da integração do MVP

## Resultado

As três fontes publicadas foram reunidas na branch local `integration/mvp`, no worktree `C:\Users\junju\smart-buffet-integration`, a partir do `origin/main` atualizado. Nenhum push ou merge na main foi executado. A validação HTTP e os 128 testes automatizados passaram. A validação visual e de execução do JavaScript no navegador permanece pendente.

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

## Contratos e validação

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

## Pendências para promoção à main

- Conferir visualmente no navegador: cinco cubas, alertas ao reduzir peso abaixo de 25%, sete colunas de dias, ranking, cópia do resumo, download e mensagens quando a API estiver indisponível. A tentativa automatizada com Edge sem interface retornou sem DOM ou logs úteis; portanto renderização, execução JavaScript e interações não estão comprovadas pelos testes desta execução.
- Python 3.11 consta do contexto inicial, mas apenas Python 3.15.2 estava instalado e é a versão declarada no README recebido do backend. A execução em Python 3.11 não foi validada.
- O histórico semanal precisa ser enviado antes de leituras atuais. O preflight impede a carga em uma base já preenchida, mas não bloqueia gravações de outros clientes durante a carga; mantenha o simulador contínuo parado nessa etapa. Não há transação única entre os 175 POSTs.
- Publicação da branch e integração futura na main ficam para uma ação posterior autorizada. Apenas commits de merge foram autorizados para esta entrega local.

O anexo recebido termina em “Nome do” no início da seção 9. A execução considerou integralmente as instruções disponíveis, sem presumir conteúdo ausente.
