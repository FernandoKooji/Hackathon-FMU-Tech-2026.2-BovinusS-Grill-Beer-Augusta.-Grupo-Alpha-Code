from contextlib import nullcontext
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import database
from app.main import app
from app.schemas.leitura_schema import LeituraRequest
from app.services import relatorio_service
from simuladores import simulador_balancas as simulador


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "simulador.db")
    with TestClient(app) as cliente:
        yield cliente


def test_simulador_envia_gramas_inteiras_para_as_cinco_balancas(cliente):
    for balanca in simulador.criar_balancas():
        for peso, status, consumo in [(4000, "OK", 0), (2000, "OK", 2000), (1000, "ATENCAO", 1000), (999, "ACABANDO", 1), (800, "ACABANDO", 199), (4000, "OK", 0)]:
            balanca.peso_atual_g = peso + 0.1
            leitura = balanca.leitura()
            LeituraRequest.model_validate(leitura)
            resposta = simulador.enviar_leitura(cliente, leitura)
            assert (resposta["status"], resposta["consumo_g"]) == (status, consumo)
    estado = cliente.get("/estado-atual").json()
    assert estado["total_monitoradas"] == 5
    assert estado["total_acabando"] == 0
    assert cliente.get("/relatorio-semanal").json()["total_alertas"] == 5


def test_historico_semanal_completo_via_api(cliente, monkeypatch):
    class RelogioFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            instante = datetime(2025, 1, 3, 20, tzinfo=timezone.utc)
            return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)

    monkeypatch.setattr(relatorio_service, "datetime", RelogioFixo)
    leituras = list(simulador.gerar_historico_semanal(RelogioFixo.now(timezone.utc)))
    assert len(leituras) == 175
    instantes = [datetime.fromisoformat(l["criado_em"]) for l in leituras]
    assert instantes == sorted(instantes)
    respostas = [simulador.enviar_leitura(cliente, leitura) for leitura in leituras]
    assert all(r["criado_em"].endswith("Z") for r in respostas)
    relatorio = cliente.get("/relatorio-semanal").json()
    assert relatorio["periodo"] == {"inicio": "2024-12-28", "fim": "2025-01-03"}
    assert relatorio["consumo_total_g"] == 112000
    assert relatorio["total_alertas"] == 35
    for prato in relatorio["pratos"]:
        assert len(prato["consumo_diario"]) == 7
        assert [d["consumo_g"] for d in prato["consumo_diario"]] == [3200] * 7
    assert cliente.get("/estado-atual").json()["total_monitoradas"] == 5
    assert cliente.get("/relatorio-semanal/csv").content.startswith(b"\xef\xbb\xbf")


def test_simulador_reporta_conflito_sem_reenviar(cliente):
    leitura = simulador.criar_balancas()[0].leitura()
    simulador.enviar_leitura(cliente, leitura)
    with pytest.raises(RuntimeError, match="409"):
        simulador.enviar_leitura(cliente, {**leitura, "criado_em": "2024-01-01T00:00:00Z"})


def test_cli_historico_preserva_banco_existente(cliente, monkeypatch):
    simulador.enviar_leitura(cliente, simulador.criar_balancas()[0].leitura())
    antes = cliente.get("/estado-atual").json()
    monkeypatch.setattr(simulador.httpx, "Client", lambda **kwargs: nullcontext(cliente))
    monkeypatch.setattr("sys.argv", ["simulador", "--historico-semanal"])
    assert simulador.main() == 1
    assert cliente.get("/estado-atual").json() == antes


def test_cli_envia_ciclo_finito(cliente, monkeypatch):
    monkeypatch.setattr(simulador.httpx, "Client", lambda **kwargs: nullcontext(cliente))
    monkeypatch.setattr("sys.argv", ["simulador", "--ciclos", "1", "--intervalo", "0"])
    assert simulador.main() == 0
    assert cliente.get("/estado-atual").json()["total_monitoradas"] == 5


def test_historico_inclui_dia_atual_exatamente_na_meia_noite():
    from zoneinfo import ZoneInfo

    agora = datetime(2025, 1, 4, 3, tzinfo=timezone.utc)
    leituras = list(simulador.gerar_historico_semanal(agora))
    instantes = [datetime.fromisoformat(l["criado_em"]) for l in leituras]
    dias = {instante.astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat() for instante in instantes}
    assert len(dias) == 7
    assert min(dias) == "2024-12-29"
    assert max(dias) == "2025-01-04"
    assert max(instantes) <= agora
