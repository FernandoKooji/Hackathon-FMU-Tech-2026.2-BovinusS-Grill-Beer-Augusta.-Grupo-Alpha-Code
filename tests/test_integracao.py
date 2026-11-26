import csv
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from threading import Barrier, Event

import pytest
from fastapi.testclient import TestClient

from app.database import database
from app.main import app
from app.schemas.leitura_schema import LeituraResponse
from app.services import leitura_service, relatorio_service


INICIO = datetime(2024, 12, 28, 15, tzinfo=timezone.utc)


@pytest.fixture
def caminho_banco(tmp_path, monkeypatch):
    class RelogioFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            instante = datetime(2025, 1, 4, 1, tzinfo=timezone.utc)
            return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)

    caminho = tmp_path / "integracao.db"
    monkeypatch.setattr(database, "DB_PATH", caminho)
    monkeypatch.setattr(relatorio_service, "datetime", RelogioFixo)
    return caminho


@pytest.fixture
def cliente(caminho_banco):
    with TestClient(app) as cliente:
        yield cliente


def _post(cliente, balanca_id, prato, peso, instante=INICIO):
    return cliente.post(
        "/leituras",
        json={
            "balanca_id": balanca_id,
            "prato": prato,
            "peso_atual_g": peso,
            "criado_em": instante.isoformat(),
        },
    )


def _registros(caminho_banco):
    uri = f"{caminho_banco.as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conexao:
        conexao.row_factory = sqlite3.Row
        assert conexao.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return [dict(linha) for linha in conexao.execute("SELECT * FROM leituras ORDER BY id")]


def test_sete_dias_com_cinco_balancas(cliente, caminho_banco):
    historico = [
        ("Arroz", [4000, 3100, 1600, 900, 0, 4000, 800]),
        ("Feijão", [4000, 2700, 1200, 2000, 950, 950, 1800]),
        ("Carne", [4000, 2000, 900, 800, 1800, 700, 0]),
        ("Massas", [4000, 2500, 700, 4000, 3000, 2100, 2100]),
        ("Legumes", [4000, 3200, 2600, 800, 900, 4000, 3500]),
    ]
    leituras = []
    for dia in range(7):
        instante = INICIO + timedelta(days=dia)
        for balanca_id, (prato, pesos) in enumerate(historico, start=1):
            if balanca_id == 5 and dia >= 4:
                prato = "Massas"
            resposta = _post(cliente, balanca_id, prato, pesos[dia], instante)
            assert resposta.status_code == 201, resposta.text
            leituras.append(resposta.json())

    invalida = _post(cliente, 1, "Arroz", 4001, INICIO + timedelta(days=6, minutes=1))
    fora_de_ordem = _post(cliente, 1, "Arroz", 3000, INICIO + timedelta(minutes=1))
    assert invalida.status_code == 422
    assert invalida.json()["detail"]
    assert fora_de_ordem.status_code == 409
    assert "anterior à última leitura da balança 1" in fora_de_ordem.json()["detail"]

    registros = _registros(caminho_banco)
    assert len(registros) == 35
    assert [r["id"] for r in registros] == [l["id"] for l in leituras]
    assert len({(r["balanca_id"], r["criado_em"]) for r in registros}) == 35
    assert all(r["consumo_g"] >= 0 for r in registros)

    estado = cliente.get("/estado-atual")
    semanal = cliente.get("/relatorio-semanal")
    download = cliente.get("/relatorio-semanal/csv")
    assert estado.status_code == semanal.status_code == download.status_code == 200
    atual = estado.json()
    assert atual["total_monitoradas"] == 5
    assert atual["total_acabando"] == 2
    assert [
        (b["balanca_id"], b["prato"], b["peso_atual_g"], b["percentual"], b["status"])
        for b in atual["balancas"]
    ] == [
        (1, "Arroz", 800, 20.0, "ACABANDO"),
        (2, "Feijão", 1800, 45.0, "ATENCAO"),
        (3, "Carne", 0, 0.0, "ACABANDO"),
        (4, "Massas", 2100, 52.5, "OK"),
        (5, "Massas", 3500, 87.5, "OK"),
    ]

    relatorio = semanal.json()
    assert relatorio["periodo"] == {"inicio": "2024-12-28", "fim": "2025-01-03"}
    assert relatorio["consumo_total_g"] == sum(r["consumo_g"] for r in registros) == 24950
    assert relatorio["consumo_total_kg"] == 24.95
    assert relatorio["total_alertas"] == sum(r["novo_alerta"] for r in registros) == 8
    esperado = [
        ("Arroz", 7200, 2, [0, 900, 1500, 700, 900, 0, 3200]),
        ("Massas", 5700, 2, [0, 1500, 1800, 0, 1000, 900, 500]),
        ("Carne", 5000, 2, [0, 2000, 1100, 100, 0, 1100, 700]),
        ("Feijão", 3850, 1, [0, 1300, 1500, 0, 1050, 0, 0]),
        ("Legumes", 3200, 1, [0, 800, 600, 1800, 0, 0, 0]),
    ]
    linhas_csv = csv.DictReader(StringIO(download.content.decode("utf-8-sig")), delimiter=";")
    datas = [(INICIO.date() + timedelta(days=dia)).isoformat() for dia in range(7)]
    for prato, linha, (nome, gramas, alertas, diario) in zip(
        relatorio["pratos"], linhas_csv, esperado, strict=True
    ):
        assert (prato["prato"], prato["consumo_g"], prato["total_alertas"]) == (
            nome, gramas, alertas
        )
        assert prato["consumo_diario"] == [
            {"data": data, "consumo_g": consumo}
            for data, consumo in zip(datas, diario, strict=True)
        ]
        assert linha["periodo_inicio"] == datas[0]
        assert linha["periodo_fim"] == datas[-1]
        assert (linha["prato"], int(linha["consumo_g"]), int(linha["total_alertas"])) == (
            nome, gramas, alertas
        )
        assert Decimal(linha["consumo_kg"].replace(",", ".")) == Decimal(str(prato["consumo_kg"]))


def test_consulta_durante_escritas_concorrentes(cliente, caminho_banco, monkeypatch):
    assert _post(cliente, 1, "Arroz", 4000).status_code == 201
    assert _post(cliente, 2, "Feijão", 3000).status_code == 201
    antes = cliente.get("/estado-atual").json()
    validar = LeituraResponse.model_validate
    conectar = leitura_service.get_connection
    escrita_aberta = Event()
    liberar_commit = Event()
    largada = Barrier(4, timeout=5)
    rastros = []

    def abrir_conexao():
        conexao = conectar()
        instrucoes = []
        rastros.append(instrucoes)
        conexao.set_trace_callback(instrucoes.append)
        return conexao

    def validar_apos_insercao(registro):
        resposta = validar(registro)
        if not escrita_aberta.is_set():
            escrita_aberta.set()
            assert liberar_commit.wait(5), "A leitura concorrente não terminou"
        return resposta

    monkeypatch.setattr(leitura_service, "get_connection", abrir_conexao)
    monkeypatch.setattr(LeituraResponse, "model_validate", staticmethod(validar_apos_insercao))

    def gravar(balanca_id, prato, peso):
        largada.wait()
        return _post(cliente, balanca_id, prato, peso, INICIO + timedelta(days=1))

    tarefas = [(1, "Arroz", 800), (2, "Feijão", 600)] * 2
    with ThreadPoolExecutor(max_workers=4) as executor:
        futuros = [executor.submit(gravar, *tarefa) for tarefa in tarefas]
        try:
            assert escrita_aberta.wait(5), "Nenhuma transação chegou à inserção"
            durante = cliente.get("/estado-atual")
            assert durante.status_code == 200
            assert durante.json() == antes
        finally:
            liberar_commit.set()
        respostas = [futuro.result(timeout=10) for futuro in futuros]

    assert [resposta.status_code for resposta in respostas] == [201] * 4
    aceitos = {resposta.json()["id"] for resposta in respostas}
    registros = _registros(caminho_banco)
    assert len(aceitos) == 4 and len(registros) == 6
    assert {r["id"] for r in registros[2:]} == aceitos
    for balanca_id, consumos in [(1, [3200, 0]), (2, [2400, 0])]:
        gravadas = [r for r in registros[2:] if r["balanca_id"] == balanca_id]
        assert [r["consumo_g"] for r in gravadas] == consumos
        assert [r["novo_alerta"] for r in gravadas] == [1, 0]
    gravacoes = [instrucoes for instrucoes in rastros if "BEGIN IMMEDIATE" in instrucoes]
    assert len(gravacoes) == 4
    for instrucoes in gravacoes:
        assert instrucoes[0] == "BEGIN IMMEDIATE"
        assert instrucoes[1].lstrip().startswith("SELECT")
        assert instrucoes[-1] == "COMMIT"
    assert cliente.get("/estado-atual").json()["total_acabando"] == 2


def test_timestamps_concorrentes_respeitam_a_ordem(cliente, caminho_banco):
    inicial = _post(cliente, 1, "Arroz", 4000)
    assert inicial.status_code == 201
    largada = Barrier(2, timeout=5)

    def gravar(peso, dia):
        largada.wait()
        return _post(cliente, 1, "Arroz", peso, INICIO + timedelta(days=dia))

    with ThreadPoolExecutor(max_workers=2) as executor:
        anterior = executor.submit(gravar, 2000, 1)
        posterior = executor.submit(gravar, 800, 2)
        anterior, posterior = anterior.result(timeout=10), posterior.result(timeout=10)

    assert posterior.status_code == 201
    aceitos = [inicial.json()["id"], posterior.json()["id"]]
    if anterior.status_code == 201:
        aceitos.append(anterior.json()["id"])
    else:
        assert anterior.status_code == 409
        assert "anterior" in anterior.json()["detail"]

    registros = _registros(caminho_banco)
    assert [r["id"] for r in registros] == sorted(aceitos)
    instantes = [datetime.fromisoformat(r["criado_em"]) for r in registros]
    assert instantes == sorted(set(instantes))
    assert sum(r["consumo_g"] for r in registros) == 3200
    assert sum(r["novo_alerta"] for r in registros) == 1
    assert registros[-1]["peso_atual_g"] == 800


def test_rollback_apos_insercao_permite_tentar_novamente(caminho_banco, monkeypatch):
    with TestClient(app, raise_server_exceptions=False) as cliente:
        assert _post(cliente, 1, "Arroz", 4000).status_code == 201
        antes = _registros(caminho_banco)
        instante = INICIO + timedelta(days=1)

        def falhar(_registro):
            raise RuntimeError("Falha simulada antes do commit")

        with monkeypatch.context() as substituicoes:
            substituicoes.setattr(LeituraResponse, "model_validate", staticmethod(falhar))
            falha = _post(cliente, 1, "Arroz", 800, instante)

        assert falha.status_code == 500
        assert falha.text == "Internal Server Error"
        assert _registros(caminho_banco) == antes
        repeticao = _post(cliente, 1, "Arroz", 800, instante)
        assert repeticao.status_code == 201
        assert repeticao.json()["consumo_g"] == 3200
        assert repeticao.json()["novo_alerta"] == 1
        assert len(_registros(caminho_banco)) == 2


def test_persistencia_apos_reiniciar_aplicacao(caminho_banco):
    rotas = ("/estado-atual", "/relatorio-semanal", "/relatorio-semanal/csv")
    with TestClient(app) as cliente:
        assert _post(cliente, 1, "Arroz", 4000).status_code == 201
        assert _post(cliente, 1, "Arroz", 700, INICIO + timedelta(days=1)).status_code == 201
        antes = [cliente.get(rota) for rota in rotas]
        assert [resposta.status_code for resposta in antes] == [200] * 3
        assert antes[0].json()["balancas"][0]["peso_atual_g"] == 700
        assert antes[1].json()["consumo_total_g"] == 3300
        linhas_antes = _registros(caminho_banco)

    with TestClient(app) as cliente:
        depois = [cliente.get(rota) for rota in rotas]
        assert [resposta.status_code for resposta in depois] == [200] * 3
        assert [resposta.content for resposta in depois] == [resposta.content for resposta in antes]
        assert _registros(caminho_banco) == linhas_antes


@pytest.mark.parametrize("prato", ["\x00Arroz", "Arroz\x00"], ids=["nul_inicial", "nul_final"])
def test_rejeita_caractere_nulo_no_prato(cliente, caminho_banco, prato):
    resposta = _post(cliente, 1, prato, 3200)

    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["loc"] == ["body", "prato"]
    assert _registros(caminho_banco) == []


def test_fecha_conexao_se_configuracao_sqlite_falhar(caminho_banco, monkeypatch):
    class ConexaoComFalha(sqlite3.Connection):
        def execute(self, *_args, **_kwargs):
            raise sqlite3.OperationalError("Falha simulada na configuração")

    conexao = sqlite3.connect(caminho_banco, factory=ConexaoComFalha)
    with closing(conexao):
        monkeypatch.setattr(database.sqlite3, "connect", lambda *_args, **_kwargs: conexao)
        with pytest.raises(sqlite3.OperationalError, match="Falha simulada"):
            database.get_connection()
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            conexao.cursor()
