GET_ULTIMA_LEITURA = """
SELECT *
FROM leituras
WHERE balanca_id = ?
ORDER BY criado_em DESC, id DESC
LIMIT 1
"""


INSERT_LEITURA = """
INSERT INTO leituras (
    balanca_id,
    prato,
    peso_atual_g,
    capacidade_max_g,
    consumo_g,
    status,
    novo_alerta,
    origem,
    criado_em
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


GET_LEITURA_BY_ID = """
SELECT *
FROM leituras
WHERE id = ?
"""


GET_ESTADO_ATUAL = """
WITH leituras_ordenadas AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY balanca_id
        ORDER BY criado_em DESC, id DESC
    ) AS posicao
    FROM leituras
)
SELECT id, balanca_id, prato, peso_atual_g, capacidade_max_g,
       consumo_g, status, novo_alerta, origem, criado_em
FROM leituras_ordenadas
WHERE posicao = 1
ORDER BY balanca_id ASC
"""
