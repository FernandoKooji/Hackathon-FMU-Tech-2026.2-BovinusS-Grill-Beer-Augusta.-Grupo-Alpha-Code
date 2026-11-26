from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.database import database
from app.main import app


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "limites.db")
    with TestClient(app) as cliente:
        yield cliente


def _registros():
    with closing(database.get_connection()) as conexao:
        return [dict(linha) for linha in conexao.execute("SELECT * FROM leituras ORDER BY id")]


@pytest.mark.parametrize("campo", ["peso_atual_g", "capacidade_max_g"])
@pytest.mark.parametrize("valor", [2**63, 10**100], ids=["primeiro_fora_do_limite", "inteiro_enorme"])
def test_rejeita_inteiro_fora_do_sqlite_sem_alterar_dados(cliente, campo, valor):
    payload = {"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 3200}
    assert cliente.post("/leituras", json=payload).status_code == 201
    registros_antes = _registros()
    estado_antes = cliente.get("/estado-atual").json()

    invalido = {**payload, "capacidade_max_g": 2**63 - 1, campo: valor}
    resposta = cliente.post("/leituras", json=invalido)

    assert resposta.status_code == 422
    assert any(
        erro["loc"] == ["body", campo] and erro["type"] == "less_than_equal"
        for erro in resposta.json()["detail"]
    )
    assert _registros() == registros_antes
    assert cliente.get("/estado-atual").json() == estado_antes

    proxima = cliente.post("/leituras", json={**payload, "peso_atual_g": 3000})
    assert proxima.status_code == 201
    assert proxima.json()["consumo_g"] == 200
    assert len(_registros()) == 2


def test_limite_sqlite_e_aceito_persistido_e_usado_no_consumo(cliente):
    limite = 2**63 - 1
    payload = {
        "balanca_id": 1,
        "prato": "Arroz",
        "peso_atual_g": limite,
        "capacidade_max_g": limite,
    }
    primeira = cliente.post("/leituras", json=payload)
    assert primeira.status_code == 201
    assert primeira.json()["percentual"] == 100.0
    assert primeira.json()["consumo_g"] == 0

    segunda = cliente.post("/leituras", json={**payload, "peso_atual_g": 0})
    assert segunda.status_code == 201
    assert segunda.json()["consumo_g"] == limite
    assert segunda.json()["novo_alerta"] == 1

    registros = _registros()
    assert len(registros) == 2
    assert registros[0]["peso_atual_g"] == limite
    assert registros[0]["capacidade_max_g"] == limite
    assert registros[1]["peso_atual_g"] == 0
    assert registros[1]["capacidade_max_g"] == limite
    assert registros[1]["consumo_g"] == limite

    estado = cliente.get("/estado-atual")
    assert estado.status_code == 200
    assert estado.json() == {
        "balancas": [
            {
                "balanca_id": 1,
                "prato": "Arroz",
                "peso_atual_g": 0,
                "capacidade_max_g": limite,
                "percentual": 0.0,
                "status": "ACABANDO",
            }
        ],
        "total_monitoradas": 1,
        "total_acabando": 1,
    }
