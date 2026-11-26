import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.database import database
from app.main import app
from app.routers import leitura_router


@pytest.fixture
def caminho_banco(tmp_path, monkeypatch) -> Path:
    caminho = tmp_path / "api.db"
    monkeypatch.setattr(database, "DB_PATH", caminho)
    return caminho


@pytest.fixture
def cliente(caminho_banco) -> Iterator[TestClient]:
    with TestClient(app) as cliente:
        yield cliente


def _post_leitura(cliente: TestClient, peso: int, **dados) -> httpx.Response:
    return cliente.post(
        "/leituras", json={"balanca_id": 1, "prato": "Arroz", "peso_atual_g": peso, **dados}
    )


def _registros(caminho_banco: Path) -> list[dict]:
    with closing(sqlite3.connect(f"{caminho_banco.as_uri()}?mode=ro", uri=True)) as conexao:
        conexao.row_factory = sqlite3.Row
        return [dict(linha) for linha in conexao.execute("SELECT * FROM leituras ORDER BY id")]


def test_lifespan_cria_banco_e_preserva_rotas_basicas(caminho_banco):
    assert not caminho_banco.exists()

    with TestClient(app) as cliente:
        assert caminho_banco.is_file()
        assert _registros(caminho_banco) == []

        raiz = cliente.get("/")
        assert raiz.status_code == 200
        assert raiz.json() == {"projeto": "Smart Buffet Analytics", "status": "online"}

        health = cliente.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        assert cliente.get("/docs").status_code == 200
        assert cliente.get("/redoc").status_code == 200


def test_openapi_documenta_rotas_de_leituras(cliente):
    resposta = cliente.get("/openapi.json")

    assert resposta.status_code == 200
    documento = resposta.json()
    assert documento["info"]["title"] == "Smart Buffet Analytics"
    assert documento["info"]["version"] == "1.0.0"
    post = documento["paths"]["/leituras"]["post"]
    estado = documento["paths"]["/estado-atual"]["get"]
    assert post["tags"] == estado["tags"] == ["Leituras"]
    assert {"201", "409", "422"} <= post["responses"].keys()
    assert "200" in estado["responses"]


@pytest.mark.parametrize(
    "dados",
    [
        pytest.param({}, id="payload_simplificado"),
        pytest.param(
            {"capacidade_max_g": 4000, "origem": "simulador", "criado_em": None},
            id="payload_completo",
        ),
    ],
)
def test_post_retorna_contrato_completo_e_persiste(cliente, caminho_banco, dados):
    resposta = _post_leitura(cliente, 3200, **dados)

    assert resposta.status_code == 201
    leitura = resposta.json()
    criado_em = datetime.fromisoformat(leitura["criado_em"])
    assert criado_em.utcoffset() == timedelta(0)
    assert type(leitura["id"]) is int and leitura["id"] > 0
    assert leitura == {
        "id": leitura["id"],
        "balanca_id": 1,
        "prato": "Arroz",
        "peso_atual_g": 3200,
        "capacidade_max_g": 4000,
        "percentual": 80.0,
        "consumo_g": 0,
        "status": "OK",
        "novo_alerta": 0,
        "origem": "simulador",
        "criado_em": leitura["criado_em"],
    }
    persistido = {chave: valor for chave, valor in leitura.items() if chave != "percentual"}
    persistido["criado_em"] = criado_em.isoformat(timespec="microseconds")
    assert _registros(caminho_banco) == [persistido]


def test_troca_de_prato_reinicia_consumo(cliente):
    primeira = _post_leitura(cliente, 900)
    troca = _post_leitura(cliente, 800, prato="Feijão")

    assert primeira.status_code == troca.status_code == 201
    assert troca.json()["prato"] == "Feijão"
    assert troca.json()["consumo_g"] == 0
    assert troca.json()["novo_alerta"] == 1


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        pytest.param("balanca_id", 0, id="balanca_abaixo_do_minimo"),
        pytest.param("balanca_id", 6, id="balanca_acima_do_maximo"),
        pytest.param("peso_atual_g", -1, id="peso_negativo"),
        pytest.param("peso_atual_g", 4001, id="peso_acima_da_capacidade"),
        pytest.param("capacidade_max_g", 0, id="capacidade_zero"),
        pytest.param("peso_atual_g", 1.5, id="peso_fracionario"),
        pytest.param("prato", "", id="prato_vazio"),
        pytest.param("prato", "   ", id="prato_apenas_espacos"),
        pytest.param("origem", "desconhecida", id="origem_invalida"),
        pytest.param("criado_em", "9999-01-01T00:00:00Z", id="timestamp_futuro"),
        pytest.param("criado_em", "2025-01-01T12:00:00", id="timestamp_sem_fuso"),
    ],
)
def test_rejeita_payload_invalido_sem_gravar(cliente, caminho_banco, campo, valor):
    payload = {"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 3200}
    payload[campo] = valor

    resposta = cliente.post("/leituras", json=payload)

    assert resposta.status_code == 422
    assert resposta.json()["detail"]
    assert _registros(caminho_banco) == []


def test_rejeita_campo_obrigatorio_ausente_sem_gravar(cliente, caminho_banco):
    resposta = cliente.post("/leituras", json={"balanca_id": 1, "prato": "Arroz"})

    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["loc"] == ["body", "peso_atual_g"]
    assert _registros(caminho_banco) == []


def test_rejeita_leitura_fora_de_ordem_sem_gravar(cliente, caminho_banco):
    recente = _post_leitura(cliente, 3200, criado_em="2025-01-01T12:00:00Z")
    anterior = _post_leitura(cliente, 3000, criado_em="2025-01-01T08:00:00-03:00")

    assert recente.status_code == 201
    assert anterior.status_code == 409
    assert "anterior à última leitura da balança 1" in anterior.json()["detail"]
    assert [registro["id"] for registro in _registros(caminho_banco)] == [recente.json()["id"]]


def test_erro_inesperado_retorna_500_sem_detalhes(caminho_banco, monkeypatch):
    def falhar(_dados):
        raise RuntimeError("detalhe interno simulado")

    monkeypatch.setattr(leitura_router, "registrar_leitura", falhar)
    with TestClient(app, raise_server_exceptions=False) as cliente:
        resposta = _post_leitura(cliente, 3200)

    assert resposta.status_code == 500
    assert resposta.text == "Internal Server Error"
    assert _registros(caminho_banco) == []


def test_estado_atual_vazio(cliente):
    resposta = cliente.get("/estado-atual")

    assert resposta.status_code == 200
    assert resposta.json() == {"balancas": [], "total_monitoradas": 0, "total_acabando": 0}


def test_estado_atual_mostra_ultima_leitura_apos_reposicao(cliente):
    critica = _post_leitura(cliente, 800)
    reposicao = _post_leitura(cliente, 3200)

    assert critica.status_code == reposicao.status_code == 201
    assert critica.json()["status"] == "ACABANDO"
    resposta = cliente.get("/estado-atual")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "balancas": [
            {
                "balanca_id": 1,
                "prato": "Arroz",
                "peso_atual_g": 3200,
                "capacidade_max_g": 4000,
                "percentual": 80.0,
                "status": "OK",
            }
        ],
        "total_monitoradas": 1,
        "total_acabando": 0,
    }


def test_estado_atual_ordena_cinco_balancas_e_conta_status(cliente):
    pesos = {5: 800, 3: 4000, 1: 3200, 4: 0, 2: 1600}
    for balanca_id, peso in pesos.items():
        assert _post_leitura(cliente, peso, balanca_id=balanca_id).status_code == 201

    resposta = cliente.get("/estado-atual")

    assert resposta.status_code == 200
    estado = resposta.json()
    assert [balanca["balanca_id"] for balanca in estado["balancas"]] == [1, 2, 3, 4, 5]
    assert [balanca["percentual"] for balanca in estado["balancas"]] == [80, 40, 100, 0, 20]
    assert [balanca["status"] for balanca in estado["balancas"]] == [
        "OK", "ATENCAO", "OK", "ACABANDO", "ACABANDO"
    ]
    assert estado["total_monitoradas"] == 5
    assert estado["total_acabando"] == 2


def _preflight(cliente: TestClient, origem: str) -> httpx.Response:
    return cliente.options(
        "/leituras",
        headers={
            "Origin": origem,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
@pytest.mark.parametrize("porta", [5500, 3000, 5173])
def test_cors_permite_preflight_de_desenvolvimento(cliente, host, porta):
    origem = f"http://{host}:{porta}"

    resposta = _preflight(cliente, origem)

    assert resposta.status_code == 200
    assert resposta.headers["Access-Control-Allow-Origin"] == origem
    metodos = resposta.headers["Access-Control-Allow-Methods"].replace(" ", "").split(",")
    cabecalhos = resposta.headers["Access-Control-Allow-Headers"].lower().replace(" ", "").split(",")
    assert set(metodos) == {"GET", "POST", "OPTIONS"}
    assert "content-type" in cabecalhos
    assert "Access-Control-Allow-Credentials" not in resposta.headers


def test_cors_nao_autoriza_outras_origens(cliente):
    resposta = _preflight(cliente, "http://localhost:5501")

    assert resposta.status_code == 400
    assert "Access-Control-Allow-Origin" not in resposta.headers


def test_simulador_e_dashboard_de_ponta_a_ponta(cliente, caminho_banco):
    pesos = [4000, 3000, 1500, 900, 400, 0, 4000, 800]
    respostas = [_post_leitura(cliente, peso, capacidade_max_g=4000) for peso in pesos]

    assert [resposta.status_code for resposta in respostas] == [201] * 8
    leituras = [resposta.json() for resposta in respostas]
    assert [leitura["peso_atual_g"] for leitura in leituras] == pesos
    assert [leitura["consumo_g"] for leitura in leituras] == [0, 1000, 1500, 600, 500, 400, 0, 3200]
    assert [leitura["novo_alerta"] for leitura in leituras] == [0, 0, 0, 1, 0, 0, 0, 1]
    registros = _registros(caminho_banco)
    assert len(registros) == 8
    assert sum(registro["consumo_g"] for registro in registros) == 7200
    assert sum(registro["novo_alerta"] for registro in registros) == 2

    resposta = cliente.get("/estado-atual")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "balancas": [
            {
                "balanca_id": 1,
                "prato": "Arroz",
                "peso_atual_g": 800,
                "capacidade_max_g": 4000,
                "percentual": 20.0,
                "status": "ACABANDO",
            }
        ],
        "total_monitoradas": 1,
        "total_acabando": 1,
    }
