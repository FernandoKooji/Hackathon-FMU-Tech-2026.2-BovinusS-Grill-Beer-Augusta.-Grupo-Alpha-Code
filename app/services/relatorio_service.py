import csv
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from io import StringIO
from zoneinfo import ZoneInfo

from app.database.database import get_connection
from app.database.queries import GET_LEITURAS_PERIODO
from app.schemas.relatorio_schema import (
    ConsumoDiario,
    PeriodoRelatorio,
    PratoRelatorio,
    RelatorioSemanalResponse,
)
from app.utils.constants import GRAMAS_POR_KG, PERIODO_RELATORIO_DIAS, TIMEZONE_LOCAL
from app.utils.normalizacao import chave_prato


@dataclass
class _ConsumoPorPrato:
    nome: str
    consumo_diario: Counter[date] = field(default_factory=Counter)
    total_alertas: int = 0


def _inicio_do_dia_em_utc(dia: date, fuso_local: ZoneInfo) -> str:
    inicio_local = datetime.combine(dia, time.min, tzinfo=fuso_local)
    return inicio_local.astimezone(timezone.utc).isoformat(timespec="microseconds")


def obter_relatorio_semanal(data_referencia: date | None = None) -> RelatorioSemanalResponse:
    fuso_local = ZoneInfo(TIMEZONE_LOCAL)
    fim = data_referencia or datetime.now(fuso_local).date()
    inicio = fim - timedelta(days=PERIODO_RELATORIO_DIAS - 1)
    limites_utc = (
        _inicio_do_dia_em_utc(inicio, fuso_local),
        _inicio_do_dia_em_utc(fim + timedelta(days=1), fuso_local),
    )

    acumulados: dict[str, _ConsumoPorPrato] = {}
    conexao = get_connection()
    try:
        for leitura in conexao.execute(GET_LEITURAS_PERIODO, limites_utc):
            nome = leitura["prato"]
            chave = chave_prato(nome)
            if chave not in acumulados:
                acumulados[chave] = _ConsumoPorPrato(nome)
            prato = acumulados[chave]
            dia = datetime.fromisoformat(leitura["criado_em"]).astimezone(fuso_local).date()
            # O total em gramas pode ultrapassar o limite inteiro do SQLite.
            prato.consumo_diario[dia] += leitura["consumo_g"] * leitura["quantidade"]
            prato.total_alertas += leitura["total_alertas"]
    finally:
        conexao.close()

    dias = [inicio + timedelta(days=indice) for indice in range(PERIODO_RELATORIO_DIAS)]
    pratos = []
    for prato in acumulados.values():
        gramas = sum(prato.consumo_diario.values())
        pratos.append(
            PratoRelatorio(
                prato=prato.nome,
                consumo_g=gramas,
                consumo_kg=gramas / GRAMAS_POR_KG,
                total_alertas=prato.total_alertas,
                consumo_diario=[
                    ConsumoDiario(data=dia, consumo_g=prato.consumo_diario[dia]) for dia in dias
                ],
            )
        )
    pratos.sort(key=lambda prato: (-prato.consumo_g, chave_prato(prato.prato)))

    consumo_total_g = sum(prato.consumo_g for prato in pratos)
    return RelatorioSemanalResponse(
        periodo=PeriodoRelatorio(inicio=inicio, fim=fim),
        consumo_total_g=consumo_total_g,
        consumo_total_kg=consumo_total_g / GRAMAS_POR_KG,
        total_alertas=sum(prato.total_alertas for prato in pratos),
        pratos=pratos,
    )


def _proteger_texto_csv(valor: str) -> str:
    for caractere in valor:
        if caractere in "=+-@＝＋－＠" or unicodedata.category(caractere) in {"Cc", "Cf"}:
            return "'" + valor
        if not caractere.isspace():
            break
    return valor


def gerar_relatorio_csv(relatorio: RelatorioSemanalResponse) -> str:
    with StringIO(newline="") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(
            ("periodo_inicio", "periodo_fim", "prato", "consumo_g", "consumo_kg", "total_alertas")
        )
        for prato in relatorio.pratos:
            escritor.writerow(
                (
                    relatorio.periodo.inicio.isoformat(),
                    relatorio.periodo.fim.isoformat(),
                    _proteger_texto_csv(prato.prato),
                    prato.consumo_g,
                    f"{prato.consumo_kg:.3f}".replace(".", ","),
                    prato.total_alertas,
                )
            )
        return arquivo.getvalue()
