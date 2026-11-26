CREATE TABLE IF NOT EXISTS leituras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

            balanca_id INTEGER NOT NULL
        CHECK (balanca_id BETWEEN 1 AND 5),

    prato TEXT NOT NULL
        CHECK (length(trim(prato)) > 0),

    peso_atual_g INTEGER NOT NULL
        CHECK (peso_atual_g >= 0),

    capacidade_max_g INTEGER NOT NULL DEFAULT 4000
        CHECK (capacidade_max_g > 0),

    consumo_g INTEGER NOT NULL DEFAULT 0
        CHECK (consumo_g >= 0),

    status TEXT NOT NULL
        CHECK (status IN ('OK', 'ATENCAO', 'ACABANDO')),

    novo_alerta INTEGER NOT NULL DEFAULT 0
        CHECK (novo_alerta IN (0, 1)),

    origem TEXT NOT NULL DEFAULT 'simulador'
        CHECK (origem IN ('simulador', 'manual', 'esp32')),

    criado_em TEXT NOT NULL,

    CHECK (peso_atual_g <= capacidade_max_g)
);


CREATE INDEX IF NOT EXISTS idx_leituras_balanca
ON leituras (balanca_id, criado_em DESC, id DESC);


CREATE INDEX IF NOT EXISTS idx_leituras_data
ON leituras (criado_em);


CREATE INDEX IF NOT EXISTS idx_leituras_prato
ON leituras (prato, criado_em);