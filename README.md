# projeto-hakathon-FMU-2026.2-
  Descrição do Problema

No self-service de uma churrascaria como o -Bovinos Grill-, o controle dos acompanhamentos nas cubas costuma ser feito no olho ou por inspeção visual esporádica. Esse modelo gera dois problemas diretos na operação:

  1° Ruptura sem aviso e filas:   quando um prato acaba de repente e a cozinha só percebe depois que a cuba esvazia, o fluxo de atendimento trava e o cliente espera mais do que o necessário.

  2° Desperdício e falta de previsibilidade:   sem histórico confiável de saída por prato, a equipe tende a produzir em excesso por Initial commitprecaução — gerando sobras no fim do turno — ou a planejar compras e preparos semanais no achismo.

---

   Solução Proposta

A solução é um sistema de   telemetria operacional e relatório semanal   para as posições do buffet, desenhado para funcionar hoje com dados inseridos/simulados manualmente e escalar depois para balanças ou módulos com ESP32:
  Leitura contínua por posição cada posição registra o peso atual do prato, permite alterar o nome do prato do dia e classifica o nível em `OK` (acima de 50%), `ATENCAO` (entre 25% e 50%) ou `ACABANDO` (abaixo de 25%).
  Aviso de reposição na cozinha: quando o nível cai abaixo de 25%, o painel destaca o prato em estado crítico para orientar a reposição antes que acabe.
  Relatório semanal consolidado: as quedas de peso entre leituras são contabilizadas como consumo, gerando um resumo dos últimos 7 dias com o total consumido por prato e quantas vezes cada item entrou em `ACABANDO`.
  Compatibilidade com hardware futuro: todas as leituras passam pela mesma entrada (`POST /leituras`), permitindo plugar uma balança ou ESP32 no futuro sem alterar o painel ou o relatório, e sem exigir balança fiscal (por se tratar de controle interno, não de cobrança no caixa).

---

  Detalhamento e Desenvolvimento do Projeto

  1. Divisão do Trabalho Entre os 3 Integrantes

  Integrante 1 : cria a ferramenta para inserir pesos das posições , trocar o nome do prato, simular quedas até abaixo de 25%, simular reposição e gerar leituras de teste para o relatório semanal.
  Integrante 2 : implementa o recebimento das leituras, o cálculo de status e consumo, a persistência no banco e os dados do estado atual e do relatório dos últimos 7 dias.
  Integrante 3 : monta o painel com atualização automática, o destaque visual de pratos em `ACABANDO` e a visão do relatório semanal com opção de copiar ou baixar o resumo.

   2. Fluxo de Desenvolvimento e Integração

1.   Padronização inicial:** alinhar os campos de envio de leitura (`balanca_id`, `prato`, `peso_atual_g`, `capacidade_max_g`, `origem`) e as rotas antes de codar em paralelo.

2.   Núcleo em tempo real:** subir o envio de leituras, o cálculo de status e o painel exibindo as 5 posições e os avisos abaixo de 25%.

3. Ciclo de reposição e relatório:** testar a subida de peso na reposição (sem contar como consumo) e validar o consolidado semanal com dados de teste.

4. Refinamento e consistência:** tratar valores inválidos (como peso negativo ou acima da capacidade máxima) e conferir se o painel reflete as mudanças sem travar.
