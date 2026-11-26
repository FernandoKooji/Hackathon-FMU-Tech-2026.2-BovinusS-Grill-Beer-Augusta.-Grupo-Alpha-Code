from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from threading import Barrier

import pytest

from app.database import database
from app.database.queries import INSERT_LEITURA
from app.schemas.leitura_schema import LeituraRequest, LeituraResponse
from app.services import leitura_service
from app.utils.constants import (
    CAPACIDADE_PADRAO_G,
    NOVO_ALERTA,
    ORIGEM_MANUAL,
    ORIGEM_PADRAO,
    SEM_NOVO_ALERTA,
    STATUS_ACABANDO,
    STATUS_ATENCAO,
    STATUS_OK,
)


@pytest.fixture
def banco_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "leituras.db")
    database.init_db()


def _registrar(peso_atual_g: int, **dados) -> LeituraResponse:
    payload = {"balanca_id": 1, "prato": "Arroz", "peso_atual_g": peso_atual_g, **dados}
    return leitura_service.registrar_leitura(LeituraRequest.model_validate(payload))


def _registros() -> list[dict]:
    with closing(database.get_connection()) as conexao:
        return [dict(linha) for linha in conexao.execute("SELECT * FROM leituras ORDER BY id")]


@pytest.mark.parametrize(
    ("peso", "percentual_esperado", "status_esperado"),
    [
        (4000, 100.0, STATUS_OK),
        (2000, 50.0, STATUS_OK),
        (1500, 37.5, STATUS_ATENCAO),
        (1000, 25.0, STATUS_ATENCAO),
        (999, 24.975, STATUS_ACABANDO),
        (0, 0.0, STATUS_ACABANDO),
    ],
)
def test_percentual_e_status(peso, percentual_esperado, status_esperado):
    percentual = leitura_service.calcular_percentual(peso, CAPACIDADE_PADRAO_G)

    assert percentual == pytest.approx(percentual_esperado)
    assert leitura_service.determinar_status(percentual) == status_esperado


@pytest.mark.parametrize(
    ("peso", "percentual_exibido", "status_esperado"),
    [(249_999, 25.0, STATUS_ACABANDO), (499_999, 50.0, STATUS_ATENCAO)],
)
def test_arredondamento_nao_altera_status(
    banco_temporario, peso, percentual_exibido, status_esperado
):
    leitura = _registrar(peso, capacidade_max_g=1_000_000)
    estado = leitura_service.obter_estado_atual().balancas[0]

    assert leitura.percentual == estado.percentual == percentual_exibido
    assert leitura.status == estado.status == status_esperado


def test_primeira_leitura_tem_consumo_zero(banco_temporario):
    assert _registrar(1500).consumo_g == 0


@pytest.mark.parametrize(
    ("peso_atual", "consumo_esperado"),
    [
        pytest.param(1500, 500, id="reducao"),
        pytest.param(2500, 0, id="reposicao"),
        pytest.param(2000, 0, id="inalterado"),
    ],
)
def test_consumo_por_variacao_de_peso(banco_temporario, peso_atual, consumo_esperado):
    _registrar(2000)

    assert _registrar(peso_atual).consumo_g == consumo_esperado


def test_troca_de_prato_reinicia_consumo(banco_temporario):
    _registrar(3000)

    assert _registrar(1500, prato="Feijão").consumo_g == 0


def test_variacao_de_caixa_preserva_consumo_e_nome(banco_temporario):
    _registrar(3000, prato="Feijão")

    leitura = _registrar(1500, prato="FEIJÃO")

    assert leitura.consumo_g == 1500
    assert leitura.prato == "FEIJÃO"


def test_balancas_tem_consumo_e_alertas_independentes(banco_temporario):
    _registrar(3000)
    primeira_balanca_2 = _registrar(800, balanca_id=2)
    segunda_balanca_1 = _registrar(700)
    segunda_balanca_2 = _registrar(600, balanca_id=2)

    assert primeira_balanca_2.consumo_g == 0
    assert segunda_balanca_1.consumo_g == 2300
    assert segunda_balanca_2.consumo_g == 200
    assert primeira_balanca_2.novo_alerta == segunda_balanca_1.novo_alerta == NOVO_ALERTA
    assert segunda_balanca_2.novo_alerta == SEM_NOVO_ALERTA


@pytest.mark.parametrize(
    ("pesos", "alertas"),
    [
        pytest.param([1500, 900], [SEM_NOVO_ALERTA, NOVO_ALERTA], id="entrada"),
        pytest.param([900], [NOVO_ALERTA], id="primeira_leitura_critica"),
        pytest.param([900, 500, 0], [NOVO_ALERTA, SEM_NOVO_ALERTA, SEM_NOVO_ALERTA], id="consecutivas"),
        pytest.param([900, 4000, 800], [NOVO_ALERTA, SEM_NOVO_ALERTA, NOVO_ALERTA], id="apos_reposicao"),
    ],
)
def test_alertas_por_transicao_de_status(banco_temporario, pesos, alertas):
    assert [_registrar(peso).novo_alerta for peso in pesos] == alertas


def test_troca_de_prato_critico_gera_novo_alerta(banco_temporario):
    _registrar(900)

    leitura = _registrar(800, prato="Feijão")

    assert leitura.consumo_g == 0
    assert leitura.novo_alerta == NOVO_ALERTA


def test_persiste_campos_id_e_historico(banco_temporario):
    anterior = _registrar(3000, balanca_id=3, criado_em="2025-01-01T11:00:00Z")
    leitura = _registrar(
        800,
        balanca_id=3,
        capacidade_max_g=3500,
        origem=ORIGEM_MANUAL,
        criado_em="2025-01-01T09:00:00.123456-03:00",
    )

    primeira, segunda = _registros()
    assert primeira["id"] == anterior.id
    assert primeira["peso_atual_g"] == 3000
    assert segunda == {
        "id": leitura.id,
        "balanca_id": 3,
        "prato": "Arroz",
        "peso_atual_g": 800,
        "capacidade_max_g": 3500,
        "consumo_g": 2200,
        "status": STATUS_ACABANDO,
        "novo_alerta": NOVO_ALERTA,
        "origem": ORIGEM_MANUAL,
        "criado_em": "2025-01-01T12:00:00.123456+00:00",
    }
    assert leitura.id > anterior.id
    assert leitura.criado_em == datetime(2025, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
    assert leitura.percentual == 22.857


def test_data_omitida_usa_horario_atual_em_utc(banco_temporario):
    inicio = datetime.now(timezone.utc)
    leitura = _registrar(1000)
    fim = datetime.now(timezone.utc)

    assert inicio <= leitura.criado_em <= fim
    assert _registros()[0]["criado_em"] == leitura.criado_em.isoformat(timespec="microseconds")
    assert _registros()[0]["criado_em"].endswith("+00:00")


def test_rejeita_leitura_anterior_sem_persistir(banco_temporario):
    ultima = _registrar(1500, criado_em="2025-01-01T12:00:00Z")

    with pytest.raises(leitura_service.LeituraForaDeOrdemError):
        _registrar(1000, criado_em="2025-01-01T13:59:59+02:00")

    outra_balanca = _registrar(800, balanca_id=2, criado_em="2025-01-01T11:00:00Z")
    assert [registro["id"] for registro in _registros()] == [ultima.id, outra_balanca.id]


def test_timestamps_iguais_sao_desempatados_pelo_id(banco_temporario):
    primeira = _registrar(3000, criado_em="2025-01-01T12:00:00Z")
    segunda = _registrar(2000, criado_em="2025-01-01T09:00:00-03:00")

    assert primeira.criado_em == segunda.criado_em
    assert segunda.id > primeira.id
    assert _registros()[1]["criado_em"] == "2025-01-01T12:00:00.000000+00:00"
    assert leitura_service.obter_estado_atual().balancas[0].peso_atual_g == 2000

    terceira = _registrar(1500, criado_em="2025-01-01T12:00:00Z")
    assert terceira.consumo_g == 500


def test_rollback_quando_validacao_da_resposta_falha(banco_temporario, monkeypatch):
    primeira = _registrar(3000)

    def falhar_validacao(registro):
        assert registro["id"] > primeira.id
        assert registro["peso_atual_g"] == 1000
        raise RuntimeError("Falha ao construir resposta")

    monkeypatch.setattr(LeituraResponse, "model_validate", staticmethod(falhar_validacao))

    with pytest.raises(RuntimeError, match="Falha ao construir resposta"):
        _registrar(1000)

    assert [registro["id"] for registro in _registros()] == [primeira.id]


def test_gravacoes_simultaneas_geram_um_unico_alerta(banco_temporario):
    barreira = Barrier(2, timeout=5)

    def gravar():
        barreira.wait()
        return _registrar(800, criado_em="2025-01-01T12:00:00Z")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(gravar) for _ in range(2)]
        leituras = sorted((futuro.result() for futuro in futuros), key=lambda leitura: leitura.id)

    assert [leitura.novo_alerta for leitura in leituras] == [NOVO_ALERTA, SEM_NOVO_ALERTA]
    assert len(_registros()) == 2


def test_estado_atual_do_banco_vazio(banco_temporario):
    assert leitura_service.obter_estado_atual().model_dump() == {
        "balancas": [],
        "total_monitoradas": 0,
        "total_acabando": 0,
    }


def test_estado_atual_retorna_so_a_ultima_leitura_da_balanca(banco_temporario):
    _registrar(500)
    ultima = _registrar(2500, prato="Feijão")

    estado = leitura_service.obter_estado_atual()

    assert estado.total_monitoradas == 1
    assert estado.total_acabando == 0
    assert len(estado.balancas) == 1
    assert estado.balancas[0].model_dump() == {
        "balanca_id": 1,
        "prato": "Feijão",
        "peso_atual_g": 2500,
        "capacidade_max_g": CAPACIDADE_PADRAO_G,
        "percentual": ultima.percentual,
        "status": ultima.status,
    }


def test_estado_atual_ordena_balancas_e_conta_status_recentes(banco_temporario):
    _registrar(800, balanca_id=3)
    _registrar(3000)
    _registrar(2000, balanca_id=2)
    _registrar(1500)
    _registrar(0, balanca_id=2)

    estado = leitura_service.obter_estado_atual()

    assert [balanca.balanca_id for balanca in estado.balancas] == [1, 2, 3]
    assert [balanca.percentual for balanca in estado.balancas] == [37.5, 0.0, 20.0]
    assert [balanca.status for balanca in estado.balancas] == [
        STATUS_ATENCAO,
        STATUS_ACABANDO,
        STATUS_ACABANDO,
    ]
    assert estado.total_monitoradas == 3
    assert estado.total_acabando == 2


def test_consultas_priorizam_timestamp_antes_do_id(banco_temporario):
    mais_recente = _registrar(3000, criado_em="2025-01-01T12:00:00Z")
    with closing(database.get_connection()) as conexao, conexao:
        id_anterior = conexao.execute(
            INSERT_LEITURA,
            (1, "Arroz", 800, CAPACIDADE_PADRAO_G, 0, STATUS_ACABANDO, NOVO_ALERTA,
             ORIGEM_PADRAO, "2025-01-01T10:00:00.000000+00:00"),
        ).lastrowid

    assert id_anterior > mais_recente.id
    assert leitura_service.obter_estado_atual().balancas[0].peso_atual_g == 3000
    with pytest.raises(leitura_service.LeituraForaDeOrdemError):
        _registrar(1500, criado_em="2025-01-01T11:00:00Z")


def test_sequencia_integrada_de_consumo_e_alertas(banco_temporario):
    pesos = [4000, 3000, 1500, 900, 400, 0, 4000, 800]
    for peso in pesos:
        _registrar(peso)

    registros = _registros()
    assert len(registros) == 8
    assert sum(registro["consumo_g"] for registro in registros) == 7200
    assert sum(registro["novo_alerta"] for registro in registros) == 2

    atual = leitura_service.obter_estado_atual().balancas[0]
    assert atual.peso_atual_g == 800
    assert atual.percentual == 20.0
    assert atual.status == STATUS_ACABANDO
