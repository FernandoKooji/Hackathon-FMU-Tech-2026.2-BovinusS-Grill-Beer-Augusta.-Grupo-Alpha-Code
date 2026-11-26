import argparse
import json
import math
import random
import time
from dataclasses import dataclass
from datetime import datetime, time as hora, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from app.utils.constants import CAPACIDADE_PADRAO_G, ORIGEM_SIMULADOR, TIMEZONE_LOCAL


@dataclass
class Balanca:
    balanca_id: int
    prato: str
    capacidade_max_g: int
    peso_atual_g: float
    origem: str = ORIGEM_SIMULADOR

    # comportamento
    prob_servir: float = 0.6
    limite_reabastecer: float = 0.12

    def _ruido(self) -> float:
        return random.uniform(-3, 3)

    def tick(self) -> None:
        if self.peso_atual_g <= self.capacidade_max_g * self.limite_reabastecer:
            if random.random() < 0.35:
                self.peso_atual_g = self.capacidade_max_g * random.uniform(0.7, 1.0)
                return
        if random.random() < self.prob_servir:
            self.peso_atual_g -= random.uniform(80, 350)
        self.peso_atual_g = max(
            0.0, min(self.capacidade_max_g, self.peso_atual_g + self._ruido())
        )

    def leitura(self) -> dict:
        # O contrato da API aceita gramas inteiras e rejeita floats.
        return {
            "balanca_id": self.balanca_id,
            "prato": self.prato,
            "peso_atual_g": round(self.peso_atual_g),
            "capacidade_max_g": self.capacidade_max_g,
            "origem": self.origem,
        }


def criar_balancas() -> list[Balanca]:
    pratos = ["Arroz Branco", "Feijão", "Farofa", "Frango Grelhado", "Salada Mista"]
    return [
        Balanca(
            balanca_id=i + 1,
            prato=nome,
            capacidade_max_g=CAPACIDADE_PADRAO_G,
            peso_atual_g=CAPACIDADE_PADRAO_G * random.uniform(0.4, 1.0),
            prob_servir=random.uniform(0.3, 0.8),
        )
        for i, nome in enumerate(pratos)
    ]


def gerar_historico_semanal(agora: datetime | None = None):
    """Sete dias locais, com consumo, alerta consecutivo e reposição por dia."""
    fuso = ZoneInfo(TIMEZONE_LOCAL)
    fim = (agora or datetime.now(timezone.utc)).astimezone(fuso) - timedelta(seconds=1)
    balancas = criar_balancas()
    pesos = [4000, 2000, 900, 800, 4000]
    for indice in range(7):
        dia = fim.date() - timedelta(days=6 - indice)
        inicio = datetime.combine(dia, hora.min, tzinfo=fuso)
        limite = min(inicio + timedelta(days=1) - timedelta(seconds=1), fim)
        for passo, peso in enumerate(pesos):
            instante = inicio + (limite - inicio) * (passo / (len(pesos) - 1))
            for balanca in balancas:
                balanca.peso_atual_g = peso
                yield {
                    **balanca.leitura(),
                    "criado_em": instante.astimezone(timezone.utc).isoformat(),
                }


def enviar_leitura(cliente, leitura: dict) -> dict:
    resposta = cliente.post("/leituras", json=leitura)
    if resposta.status_code != 201:
        raise RuntimeError(
            f"Leitura rejeitada (HTTP {resposta.status_code}): {resposta.text[:500]}"
        )
    return resposta.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulador das cinco balanças do buffet.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL base da API")
    parser.add_argument("--intervalo", type=float, default=1.0, help="Segundos entre ciclos")
    parser.add_argument("--ciclos", type=int, help="Limite de ciclos; omitido = contínuo")
    parser.add_argument("--seed", type=int, help="Semente para reprodução da simulação")
    parser.add_argument("--somente-imprimir", action="store_true", help="Não envia à API")
    parser.add_argument("--historico-semanal", action="store_true", help="Envia 175 leituras dos sete dias locais; requer API sem leituras")
    args = parser.parse_args()
    if not math.isfinite(args.intervalo) or args.intervalo < 0:
        parser.error("--intervalo deve ser finito e não negativo")
    if args.ciclos is not None and args.ciclos <= 0:
        parser.error("--ciclos deve ser positivo")
    if args.seed is not None:
        random.seed(args.seed)
    try:
        with httpx.Client(base_url=args.url.rstrip("/"), timeout=10) as cliente:
            if args.historico_semanal:
                if not args.somente_imprimir:
                    estado = cliente.get("/estado-atual")
                    estado.raise_for_status()
                    if estado.json()["balancas"]:
                        raise RuntimeError("Histórico não enviado: a API já contém leituras. Use uma instância com um banco novo, sem excluir dados existentes.")
                for leitura in gerar_historico_semanal():
                    if not args.somente_imprimir:
                        enviar_leitura(cliente, leitura)
                    print(json.dumps(leitura, ensure_ascii=False))
                return 0
            balancas = criar_balancas()
            ciclo = 0
            while args.ciclos is None or ciclo < args.ciclos:
                for balanca in balancas:
                    balanca.tick()
                    leitura = balanca.leitura()
                    if not args.somente_imprimir:
                        enviar_leitura(cliente, leitura)
                    print(json.dumps(leitura, ensure_ascii=False))
                ciclo += 1
                if args.ciclos is None or ciclo < args.ciclos:
                    time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("Simulação encerrada.")
    except (httpx.HTTPError, RuntimeError) as erro:
        print(f"Falha no simulador: {erro}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
