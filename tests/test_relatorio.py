import codecs
import csv
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from app.database import database
from app.database.queries import INSERT_LEITURA
from app.main import app
from app.schemas.relatorio_schema import RelatorioSemanalResponse
from app.services import relatorio_service
from app.services.relatorio_service import gerar_relatorio_csv, obter_relatorio_semanal


DATA_REFERENCIA = date(2025, 1, 3)
COLUNAS_CSV = ["periodo_inicio", "periodo_fim", "prato", "consumo_g", "consumo_kg", "total_alertas"]


@pytest.fixture
def banco_temporario(tmp_path, monkeypatch):
    caminho = tmp_path / "relatorio.db"
    monkeypatch.setattr(database, "DB_PATH", caminho)
    return caminho


@pytest.fixture
def banco_inicializado(banco_temporario):
    database.init_db()
    return banco_temporario


@pytest.fixture
def cliente(banco_temporario, monkeypatch):
    class RelogioFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 1, 4, 1, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(relatorio_service, "datetime", RelogioFixo)
    with TestClient(app) as cliente:
        yield cliente


def _leitura(
    criado_em: str,
    consumo_g: int,
    *,
    prato: str = "Arroz",
    balanca_id: int = 1,
    novo_alerta: int = 0,
    origem: str = "simulador",
) -> tuple:
    timestamp = datetime.fromisoformat(criado_em).isoformat(timespec="microseconds")
    return (balanca_id, prato, 0, 4000, consumo_g, "ACABANDO", novo_alerta, origem, timestamp)


def _inserir(*leituras: tuple) -> None:
    with closing(database.get_connection()) as conexao, conexao:
        conexao.executemany(INSERT_LEITURA, leituras)


def _linhas_csv(conteudo: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(conteudo), delimiter=";"))


@pytest.mark.parametrize(
    ("data_referencia", "inicio"),
    [
        pytest.param(date(2025, 3, 3), date(2025, 2, 25), id="mudanca_de_mes"),
        pytest.param(DATA_REFERENCIA, date(2024, 12, 28), id="mudanca_de_ano"),
    ],
)
def test_periodo_calendario_quando_banco_vazio(banco_inicializado, data_referencia, inicio):
    relatorio = obter_relatorio_semanal(data_referencia)

    assert relatorio.model_dump() == {
        "periodo": {"inicio": inicio, "fim": data_referencia},
        "consumo_total_g": 0,
        "consumo_total_kg": 0.0,
        "total_alertas": 0,
        "pratos": [],
    }
    assert len(gerar_relatorio_csv(relatorio).splitlines()) == 1


def test_limites_em_utc_e_atribuicao_ao_dia_local(banco_inicializado):
    _inserir(
        _leitura("2024-12-28T02:59:59.999999Z", 4000, prato="Fora", novo_alerta=1),
        _leitura("2024-12-28T03:00:00Z", 100),
        _leitura("2024-12-29T00:00:00Z", 10),
        _leitura("2024-12-29T02:59:59.999999Z", 1),
        _leitura("2024-12-29T03:00:00Z", 200),
        _leitura("2025-01-04T02:59:59.999999Z", 300, novo_alerta=1),
        _leitura("2025-01-04T03:00:00Z", 4000, prato="Fora", novo_alerta=1),
    )

    relatorio = obter_relatorio_semanal(DATA_REFERENCIA)

    assert relatorio.consumo_total_g == 611
    assert relatorio.total_alertas == 1
    assert [prato.prato for prato in relatorio.pratos] == ["Arroz"]
    diario = relatorio.pratos[0].consumo_diario
    assert [item.data.isoformat() for item in diario] == [
        "2024-12-28", "2024-12-29", "2024-12-30", "2024-12-31",
        "2025-01-01", "2025-01-02", "2025-01-03",
    ]
    assert [item.consumo_g for item in diario] == [111, 200, 0, 0, 0, 0, 300]


def test_limites_seguem_mudanca_historica_de_fuso(banco_inicializado):
    _inserir(
        _leitura("2018-11-02T02:59:59.999999Z", 900),
        _leitura("2018-11-02T03:00:00Z", 100),
        _leitura("2018-11-09T01:59:59.999999Z", 200),
        _leitura("2018-11-09T02:00:00Z", 900),
    )

    relatorio = obter_relatorio_semanal(date(2018, 11, 8))

    assert relatorio.periodo.inicio == date(2018, 11, 2)
    assert relatorio.consumo_total_g == 300
    assert [item.consumo_g for item in relatorio.pratos[0].consumo_diario] == [100, 0, 0, 0, 0, 0, 200]


def test_registros_apenas_fora_do_periodo(banco_inicializado):
    _inserir(_leitura("2024-12-20T12:00:00Z", 4000, novo_alerta=1))

    relatorio = obter_relatorio_semanal(DATA_REFERENCIA)

    assert relatorio.consumo_total_g == relatorio.total_alertas == 0
    assert relatorio.pratos == []


def test_agrega_caso_unicode_origens_e_balancas_com_ranking(banco_inicializado):
    _inserir(
        _leitura("2025-01-03T12:00:00Z", 200, prato="FEIJÃO", balanca_id=2),
        _leitura("2025-01-02T12:00:00Z", 500, prato="feijão", balanca_id=3, origem="esp32", novo_alerta=1),
        _leitura("2024-12-28T12:00:00Z", 900, prato="Feijão", origem="manual", novo_alerta=1),
        _leitura("2024-12-29T12:00:00Z", 700, prato="Carne"),
        _leitura("2024-12-29T12:00:00Z", 350, novo_alerta=1),
        _leitura("2024-12-29T12:00:00Z", 350, balanca_id=2),
        _leitura("2025-01-01T12:00:00Z", 10, prato="Soße"),
        _leitura("2025-01-01T12:00:00Z", 90, prato="SOSSE"),
        _leitura("2025-01-01T12:00:00Z", 0, prato="Sopa"),
    )

    relatorio = obter_relatorio_semanal(DATA_REFERENCIA)

    assert relatorio.consumo_total_g == 3100
    assert relatorio.consumo_total_kg == 3.1
    assert relatorio.total_alertas == 3
    assert [(p.prato, p.consumo_g, p.consumo_kg, p.total_alertas) for p in relatorio.pratos] == [
        ("Feijão", 1600, 1.6, 2), ("Arroz", 700, 0.7, 1), ("Carne", 700, 0.7, 0),
        ("Soße", 100, 0.1, 0), ("Sopa", 0, 0.0, 0),
    ]
    assert [dia.consumo_g for dia in relatorio.pratos[0].consumo_diario] == [900, 0, 0, 0, 0, 500, 200]
    assert all(len(prato.consumo_diario) == 7 for prato in relatorio.pratos)


def test_soma_inteira_pode_superar_limite_de_uma_leitura(banco_inicializado):
    limite = 2**63 - 1
    _inserir(
        _leitura("2024-12-29T12:00:00Z", limite, novo_alerta=1),
        _leitura("2024-12-29T12:00:00Z", limite, balanca_id=2, novo_alerta=1),
    )

    relatorio = obter_relatorio_semanal(DATA_REFERENCIA)

    assert relatorio.consumo_total_g == relatorio.pratos[0].consumo_diario[1].consumo_g == 2 * limite
    assert relatorio.total_alertas == 2


def test_unicode_no_historico_preserva_nome_e_ranking(banco_inicializado):
    nome_original = "A\u0301gua"
    _inserir(
        _leitura("2025-01-03T12:00:00Z", 100, prato="ÁGUA", balanca_id=2, novo_alerta=1),
        _leitura("2024-12-28T12:00:00Z", 200, prato=nome_original, novo_alerta=1),
        _leitura("2024-12-29T12:00:00Z", 300),
        _leitura("2025-01-01T12:00:00Z", 25, prato="Agua"),
    )

    relatorio = obter_relatorio_semanal(DATA_REFERENCIA)

    assert [(p.prato, p.consumo_g, p.consumo_kg, p.total_alertas) for p in relatorio.pratos] == [
        ("Arroz", 300, 0.3, 0), (nome_original, 300, 0.3, 2), ("Agua", 25, 0.025, 0),
    ]
    assert relatorio.consumo_total_g == sum(p.consumo_g for p in relatorio.pratos) == 625
    assert relatorio.consumo_total_kg == 0.625
    assert relatorio.total_alertas == sum(p.total_alertas for p in relatorio.pratos) == 2
    assert [dia.consumo_g for dia in relatorio.pratos[1].consumo_diario] == [200, 0, 0, 0, 0, 0, 100]
    for prato in relatorio.pratos:
        assert len(prato.consumo_diario) == 7
        assert sum(dia.consumo_g for dia in prato.consumo_diario) == prato.consumo_g


@pytest.mark.parametrize(
    ("nome_inicial", "nome_variante"),
    [("Feijão", "FEIJA\u0303O"), ("Feija\u0303o", "FEIJÃO")],
    ids=["composto_para_decomposto", "decomposto_para_composto"],
)
def test_unicode_de_ponta_a_ponta_com_json_csv_e_dias_locais(
    cliente, nome_inicial, nome_variante
):
    nomes = [nome_inicial, nome_inicial.upper(), nome_variante]
    instantes = [
        "2024-12-29T02:59:59.999999Z",
        "2024-12-29T03:00:00Z",
        "2025-01-04T02:59:59.999999Z",
    ]
    for peso, nome, instante in zip([3000, 900, 800], nomes, instantes, strict=True):
        resposta = cliente.post(
            "/leituras",
            json={"balanca_id": 1, "prato": nome, "peso_atual_g": peso, "criado_em": instante},
        )
        assert resposta.status_code == 201
        assert resposta.json()["prato"] == nome

    resposta = cliente.get("/relatorio-semanal")
    download = cliente.get("/relatorio-semanal/csv")
    estado = cliente.get("/estado-atual")

    assert resposta.status_code == download.status_code == estado.status_code == 200
    relatorio = resposta.json()
    assert relatorio["periodo"] == {"inicio": "2024-12-28", "fim": "2025-01-03"}
    assert relatorio["consumo_total_g"] == 2200
    assert relatorio["consumo_total_kg"] == 2.2
    assert relatorio["total_alertas"] == 1
    assert len(relatorio["pratos"]) == 1
    prato = relatorio["pratos"][0]
    assert (prato["prato"], prato["consumo_g"], prato["consumo_kg"], prato["total_alertas"]) == (
        nome_inicial, 2200, 2.2, 1,
    )
    assert [dia["data"] for dia in prato["consumo_diario"]] == [
        "2024-12-28", "2024-12-29", "2024-12-30", "2024-12-31",
        "2025-01-01", "2025-01-02", "2025-01-03",
    ]
    assert [dia["consumo_g"] for dia in prato["consumo_diario"]] == [0, 2100, 0, 0, 0, 0, 100]
    assert sum(dia["consumo_g"] for dia in prato["consumo_diario"]) == prato["consumo_g"]
    assert _linhas_csv(download.content.decode("utf-8-sig")) == [{
        "periodo_inicio": "2024-12-28", "periodo_fim": "2025-01-03", "prato": nome_inicial,
        "consumo_g": "2200", "consumo_kg": "2,200", "total_alertas": "1",
    }]
    assert estado.json()["balancas"][0] == {
        "balanca_id": 1, "prato": nome_variante, "peso_atual_g": 800,
        "capacidade_max_g": 4000, "percentual": 20.0, "status": "ACABANDO",
    }
    with closing(database.get_connection()) as conexao:
        registros = list(conexao.execute("SELECT prato, consumo_g, novo_alerta FROM leituras ORDER BY id"))
    assert [registro["prato"] for registro in registros] == nomes
    assert [registro["consumo_g"] for registro in registros] == [0, 2100, 100]
    assert [registro["novo_alerta"] for registro in registros] == [0, 1, 0]


def test_csv_escapa_texto_preserva_ordenacao_e_nao_cria_arquivo(banco_inicializado, monkeypatch):
    _inserir(
        _leitura("2025-01-02T12:00:00Z", 1251, prato='Feijão; "Tropeiro"', novo_alerta=1),
        _leitura("2025-01-03T12:00:00Z", 10),
    )
    relatorio = obter_relatorio_semanal(DATA_REFERENCIA)
    pasta = banco_inicializado.parent
    monkeypatch.chdir(pasta)
    arquivos_antes = set(pasta.iterdir())

    conteudo = gerar_relatorio_csv(relatorio)

    assert conteudo.splitlines()[0].split(";") == COLUNAS_CSV
    assert '"Feijão; ""Tropeiro"""' in conteudo
    assert list(csv.reader(StringIO(conteudo), delimiter=";"))[1:] == [
        ["2024-12-28", "2025-01-03", 'Feijão; "Tropeiro"', "1251", "1,251", "1"],
        ["2024-12-28", "2025-01-03", "Arroz", "10", "0,010", "0"],
    ]
    assert set(pasta.iterdir()) == arquivos_antes


@pytest.mark.parametrize("prefixo", ["=", "+", "-", "@", "\t", "\r", "\n", "  =", "\u200b", "＝"])
def test_exportacao_protege_formula_sem_alterar_json_ou_banco(cliente, prefixo):
    nome = prefixo + "Feijão"
    _inserir(_leitura("2025-01-02T12:00:00Z", 10, prato=nome))

    exportacao = cliente.get("/relatorio-semanal/csv")
    json_relatorio = cliente.get("/relatorio-semanal")

    assert exportacao.status_code == json_relatorio.status_code == 200
    assert _linhas_csv(exportacao.content.decode("utf-8-sig"))[0]["prato"] == "'" + nome
    assert json_relatorio.json()["pratos"][0]["prato"] == nome
    with closing(database.get_connection()) as conexao:
        assert conexao.execute("SELECT prato FROM leituras").fetchone()["prato"] == nome


def test_endpoints_vazios_com_bom_e_cors(cliente):
    resposta = cliente.get("/relatorio-semanal")
    origem = "http://localhost:5500"
    download = cliente.get("/relatorio-semanal/csv", headers={"Origin": origem})

    assert resposta.status_code == download.status_code == 200
    assert RelatorioSemanalResponse.model_validate_json(resposta.content).model_dump(mode="json") == {
        "periodo": {"inicio": "2024-12-28", "fim": "2025-01-03"},
        "consumo_total_g": 0,
        "consumo_total_kg": 0.0,
        "total_alertas": 0,
        "pratos": [],
    }
    assert download.headers["content-type"] == "text/csv; charset=utf-8"
    assert download.headers["content-disposition"] == (
        'attachment; filename="relatorio-semanal_2024-12-28_2025-01-03.csv"'
    )
    assert download.headers["access-control-allow-origin"] == origem
    assert "Content-Disposition" in download.headers["access-control-expose-headers"].split(", ")
    assert download.content.startswith(codecs.BOM_UTF8)
    assert download.content.decode("utf-8-sig").splitlines() == [";".join(COLUNAS_CSV)]


def test_openapi_documenta_json_e_csv(cliente):
    resposta = cliente.get("/openapi.json")

    assert resposta.status_code == 200
    rotas = resposta.json()["paths"]
    relatorio = rotas["/relatorio-semanal"]["get"]
    download = rotas["/relatorio-semanal/csv"]["get"]
    assert relatorio["tags"] == download["tags"] == ["Relatórios"]
    assert relatorio["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RelatorioSemanalResponse"
    }
    assert "text/csv" in download["responses"]["200"]["content"]


def test_relatorio_de_ponta_a_ponta(cliente):
    sequencias = [
        ("Arroz", [4000, 3000, 1500, 900, 400, 0, 4000, 800], [0, 0, 0, 1, 0, 0, 0, 1]),
        ("Feijão", [4000, 2500, 1000, 500, 4000], [0, 0, 0, 1, 0]),
        ("Carne", [4000, 2000, 900], [0, 0, 1]),
    ]
    inicio = datetime(2024, 12, 28, 15, tzinfo=timezone.utc)
    for balanca_id, (prato, pesos, alertas) in enumerate(sequencias, start=1):
        for indice, (peso, alerta) in enumerate(zip(pesos, alertas, strict=True)):
            instante = inicio + timedelta(days=indice // 2, hours=indice % 2)
            resposta = cliente.post(
                "/leituras",
                json={
                    "balanca_id": balanca_id,
                    "prato": prato,
                    "peso_atual_g": peso,
                    "capacidade_max_g": 4000,
                    "criado_em": instante.isoformat(),
                },
            )
            assert resposta.status_code == 201
            assert resposta.json()["novo_alerta"] == alerta
            if peso == 4000:
                assert resposta.json()["consumo_g"] == 0

    estado = cliente.get("/estado-atual")
    relatorio = cliente.get("/relatorio-semanal")
    download = cliente.get("/relatorio-semanal/csv")

    assert estado.status_code == relatorio.status_code == download.status_code == 200
    with closing(database.get_connection()) as conexao:
        assert conexao.execute("SELECT COUNT(*) FROM leituras").fetchone()[0] == 16
    atual = estado.json()
    assert atual["total_monitoradas"] == 3
    assert atual["total_acabando"] == 2
    assert [(b["peso_atual_g"], b["status"]) for b in atual["balancas"]] == [
        (800, "ACABANDO"), (4000, "OK"), (900, "ACABANDO"),
    ]
    semanal = RelatorioSemanalResponse.model_validate_json(relatorio.content)
    assert semanal.consumo_total_g == 13800
    assert semanal.consumo_total_kg == 13.8
    assert semanal.total_alertas == 4
    assert [(p.prato, p.consumo_g, p.total_alertas) for p in semanal.pratos] == [
        ("Arroz", 7200, 2), ("Feijão", 3500, 1), ("Carne", 3100, 1),
    ]
    linhas_csv = _linhas_csv(download.content.decode("utf-8-sig"))
    for linha, prato in zip(linhas_csv, semanal.pratos, strict=True):
        assert linha["periodo_inicio"] == semanal.periodo.inicio.isoformat()
        assert linha["periodo_fim"] == semanal.periodo.fim.isoformat()
        assert linha["prato"] == prato.prato
        assert int(linha["consumo_g"]) == prato.consumo_g
        assert Decimal(linha["consumo_kg"].replace(",", ".")) == Decimal(str(prato.consumo_kg))
        assert int(linha["total_alertas"]) == prato.total_alertas
