from fastapi import APIRouter, HTTPException, status

from app.schemas.leitura_schema import EstadoAtualResponse, LeituraRequest, LeituraResponse
from app.services.leitura_service import (
    LeituraForaDeOrdemError,
    obter_estado_atual,
    registrar_leitura,
)


router = APIRouter(tags=["Leituras"])


@router.post(
    "/leituras",
    response_model=LeituraResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"description": "Leitura fora de ordem"}},
)
def criar_leitura(dados: LeituraRequest) -> LeituraResponse:
    try:
        return registrar_leitura(dados)
    except LeituraForaDeOrdemError as erro:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(erro)) from erro


@router.get("/estado-atual", response_model=EstadoAtualResponse, status_code=status.HTTP_200_OK)
def consultar_estado_atual() -> EstadoAtualResponse:
    return obter_estado_atual()
