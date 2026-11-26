from fastapi import APIRouter, Response, status

from app.schemas.relatorio_schema import RelatorioSemanalResponse
from app.services.relatorio_service import gerar_relatorio_csv, obter_relatorio_semanal


router = APIRouter(tags=["Relatórios"])


@router.get(
    "/relatorio-semanal",
    response_model=RelatorioSemanalResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_relatorio_semanal() -> RelatorioSemanalResponse:
    return obter_relatorio_semanal()


@router.get(
    "/relatorio-semanal/csv",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Download do relatório semanal em CSV",
            "content": {"text/csv": {"schema": {"type": "string"}}},
        }
    },
)
def baixar_relatorio_semanal_csv() -> Response:
    relatorio = obter_relatorio_semanal()
    inicio, fim = relatorio.periodo.inicio, relatorio.periodo.fim
    nome = f"relatorio-semanal_{inicio.isoformat()}_{fim.isoformat()}.csv"
    return Response(
        content=gerar_relatorio_csv(relatorio).encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
