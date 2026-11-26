from datetime import datetime, timezone

from app.database.database import get_connection
from app.database.queries import (
    GET_ESTADO_ATUAL,
    GET_LEITURA_BY_ID,
    GET_ULTIMA_LEITURA,
    INSERT_LEITURA,
)
from app.schemas.leitura_schema import (
    EstadoAtualResponse,
    EstadoBalancaResponse,
    LeituraRequest,
    LeituraResponse,
)
from app.utils.constants import (
    LIMITE_ACABANDO,
    LIMITE_ATENCAO,
    NOVO_ALERTA,
    SEM_NOVO_ALERTA,
    STATUS_ACABANDO,
    STATUS_ATENCAO,
    STATUS_OK,
)
from app.utils.normalizacao import chave_prato


class LeituraForaDeOrdemError(ValueError):
    """Indica uma leitura anterior à última leitura da mesma balança."""


def calcular_percentual(peso_atual_g: int, capacidade_max_g: int) -> float:
    return peso_atual_g / capacidade_max_g * 100


def determinar_status(percentual: float) -> str:
    if percentual < LIMITE_ACABANDO:
        return STATUS_ACABANDO
    if percentual < LIMITE_ATENCAO:
        return STATUS_ATENCAO
    return STATUS_OK


def calcular_consumo(peso_anterior_g: int | None, peso_atual_g: int) -> int:
    if peso_anterior_g is None:
        return 0
    return max(0, peso_anterior_g - peso_atual_g)


def detectar_novo_alerta(status_anterior: str | None, status_atual: str) -> int:
    if status_atual == STATUS_ACABANDO and status_anterior != STATUS_ACABANDO:
        return NOVO_ALERTA
    return SEM_NOVO_ALERTA


def registrar_leitura(dados: LeituraRequest) -> LeituraResponse:
    conexao = get_connection()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        criado_em = dados.criado_em or datetime.now(timezone.utc)
        criado_em = criado_em.astimezone(timezone.utc)

        ultima = conexao.execute(GET_ULTIMA_LEITURA, (dados.balanca_id,)).fetchone()
        peso_anterior_g = None
        status_anterior = None
        if ultima is not None:
            if criado_em < datetime.fromisoformat(ultima["criado_em"]):
                raise LeituraForaDeOrdemError(
                    f"A leitura é anterior à última leitura da balança {dados.balanca_id}."
                )
            if chave_prato(dados.prato) == chave_prato(ultima["prato"]):
                peso_anterior_g = ultima["peso_atual_g"]
                status_anterior = ultima["status"]

        consumo_g = calcular_consumo(peso_anterior_g, dados.peso_atual_g)
        percentual = calcular_percentual(dados.peso_atual_g, dados.capacidade_max_g)
        status = determinar_status(percentual)
        novo_alerta = detectar_novo_alerta(status_anterior, status)

        cursor = conexao.execute(
            INSERT_LEITURA,
            (
                dados.balanca_id,
                dados.prato,
                dados.peso_atual_g,
                dados.capacidade_max_g,
                consumo_g,
                status,
                novo_alerta,
                dados.origem,
                criado_em.isoformat(timespec="microseconds"),
            ),
        )
        registro = conexao.execute(GET_LEITURA_BY_ID, (cursor.lastrowid,)).fetchone()
        resposta = LeituraResponse.model_validate(
            {**dict(registro), "percentual": round(percentual, 3)}
        )
        conexao.commit()
        return resposta
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def obter_estado_atual() -> EstadoAtualResponse:
    conexao = get_connection()
    try:
        balancas = []
        for registro in conexao.execute(GET_ESTADO_ATUAL):
            percentual = calcular_percentual(
                registro["peso_atual_g"], registro["capacidade_max_g"]
            )
            balancas.append(
                EstadoBalancaResponse.model_validate(
                    {**dict(registro), "percentual": round(percentual, 3)}
                )
            )

        return EstadoAtualResponse(
            balancas=balancas,
            total_monitoradas=len(balancas),
            total_acabando=sum(balanca.status == STATUS_ACABANDO for balanca in balancas),
        )
    finally:
        conexao.close()
