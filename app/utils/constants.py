# ========================================
# CONFIGURACOES DAS BALANCAS
# ========================================

BALANCA_ID_MIN = 1
BALANCA_ID_MAX = 5

CAPACIDADE_PADRAO_G = 4000

PESO_MINIMO_G = 0

# Limite de armazenamento de um INTEGER assinado de 64 bits no SQLite.
SQLITE_INTEGER_MAX = 2**63 - 1


# ========================================
# STATUS DAS CUBAS
# ========================================

STATUS_OK = "OK"
STATUS_ATENCAO = "ATENCAO"
STATUS_ACABANDO = "ACABANDO"

STATUS_VALIDOS = (
    STATUS_OK,
    STATUS_ATENCAO,
    STATUS_ACABANDO
)


# ========================================
# LIMITES DE DISPONIBILIDADE
# ========================================

LIMITE_ACABANDO = 25.0
LIMITE_ATENCAO = 50.0


# ========================================
# ORIGEM DAS LEITURAS
# ========================================

ORIGEM_SIMULADOR = "simulador"
ORIGEM_MANUAL = "manual"
ORIGEM_ESP32 = "esp32"

ORIGENS_VALIDAS = (
    ORIGEM_SIMULADOR,
    ORIGEM_MANUAL,
    ORIGEM_ESP32
)

ORIGEM_PADRAO = ORIGEM_SIMULADOR


# ========================================
# EVENTOS DE ALERTA
# ========================================

SEM_NOVO_ALERTA = 0
NOVO_ALERTA = 1


# ========================================
# RELATORIOS
# ========================================

PERIODO_RELATORIO_DIAS = 7

GRAMAS_POR_KG = 1000

TIMEZONE_LOCAL = "America/Sao_Paulo"
