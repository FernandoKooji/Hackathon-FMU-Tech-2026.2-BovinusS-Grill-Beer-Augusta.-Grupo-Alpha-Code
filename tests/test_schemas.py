from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.leitura_schema import LeituraRequest


@pytest.fixture
def payload() -> dict:
    return {"balanca_id": 1, "prato": "Arroz", "peso_atual_g": 1500}


def test_payload_valido(payload):
    payload.update(capacidade_max_g=3000, origem="manual")

    leitura = LeituraRequest.model_validate(payload)

    assert leitura.model_dump(exclude_unset=True) == payload


def test_capacidade_padrao(payload):
    assert LeituraRequest.model_validate(payload).capacidade_max_g == 4000


def test_origem_padrao(payload):
    assert LeituraRequest.model_validate(payload).origem == "simulador"


@pytest.mark.parametrize("peso", [0, 3000], ids=["peso_zero", "peso_igual_capacidade"])
def test_peso_valido(payload, peso):
    payload.update(peso_atual_g=peso, capacidade_max_g=3000)

    assert LeituraRequest.model_validate(payload).peso_atual_g == peso


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        pytest.param("peso_atual_g", -1, id="peso_negativo"),
        pytest.param("capacidade_max_g", 0, id="capacidade_zero"),
        pytest.param("balanca_id", 0, id="balanca_id_zero"),
        pytest.param("balanca_id", 6, id="balanca_id_seis"),
        pytest.param("prato", "", id="prato_vazio"),
        pytest.param("prato", "   ", id="prato_apenas_espacos"),
        pytest.param("origem", "desconhecida", id="origem_desconhecida"),
        pytest.param("peso_atual_g", 1500.5, id="peso_fracionario"),
        pytest.param("capacidade_max_g", 3000.5, id="capacidade_fracionaria"),
        pytest.param("balanca_id", 1.5, id="balanca_id_fracionario"),
    ],
)
def test_campo_invalido(payload, campo, valor):
    payload[campo] = valor

    with pytest.raises(ValidationError) as erro:
        LeituraRequest.model_validate(payload)

    assert erro.value.errors()[0]["loc"] == (campo,)


def test_peso_acima_da_capacidade(payload):
    payload.update(peso_atual_g=3001, capacidade_max_g=3000)

    with pytest.raises(ValidationError, match="peso_atual_g não pode ultrapassar"):
        LeituraRequest.model_validate(payload)


def test_remove_espacos_do_prato(payload):
    payload["prato"] = "  Arroz integral  "

    assert LeituraRequest.model_validate(payload).prato == "Arroz integral"


def test_data_futura_invalida(payload):
    payload["criado_em"] = datetime.now(timezone.utc) + timedelta(days=1)

    with pytest.raises(ValidationError, match="criado_em não pode estar no futuro"):
        LeituraRequest.model_validate(payload)


def test_data_com_fuso_convertida_para_utc(payload):
    payload["criado_em"] = "2025-01-01T12:30:00-03:00"

    criado_em = LeituraRequest.model_validate(payload).criado_em

    assert criado_em == datetime(2025, 1, 1, 15, 30, tzinfo=timezone.utc)
    assert criado_em.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    "criado_em",
    ["2025-01-01T12:30:00", 1735734600],
    ids=["data_sem_fuso", "timestamp_sem_fuso_explicito"],
)
def test_data_sem_fuso_invalida(payload, criado_em):
    payload["criado_em"] = criado_em

    with pytest.raises(ValidationError, match="com fuso horário"):
        LeituraRequest.model_validate(payload)


def test_data_omitida_valida(payload):
    assert LeituraRequest.model_validate(payload).criado_em is None
