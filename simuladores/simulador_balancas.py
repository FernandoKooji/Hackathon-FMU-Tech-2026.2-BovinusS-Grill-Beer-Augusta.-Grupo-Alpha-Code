import json
import random
import time
from dataclasses import dataclass


@dataclass
class Balanca:
    balanca_id: int
    prato: str
    capacidade_max_g: float
    peso_atual_g: float
    origem: str = "simulador_manual"

    # comportamento
    prob_servir: float = 0.6      # chance de alguém se servir a cada tick
    limite_reabastecer: float = 0.12  # abaixo de 12% da capacidade, chama reposição

    def _ruido(self) -> float:
        # pequena oscilação de leitura, como uma balança real
        return random.uniform(-3, 3)

    def tick(self) -> None:
        # reabastecimento: cuba quase vazia -> enche entre 70% e 100%
        if self.peso_atual_g <= self.capacidade_max_g * self.limite_reabastecer:
            if random.random() < 0.35:  # demora um pouco para repor
                self.peso_atual_g = self.capacidade_max_g * random.uniform(0.7, 1.0)
                return

        # alguém se serve
        if random.random() < self.prob_servir:
            porcao = random.uniform(80, 350)
            self.peso_atual_g -= porcao

        # mantém dentro de 0 e capacidade, com ruído de leitura
        self.peso_atual_g = max(0.0, min(self.capacidade_max_g, self.peso_atual_g + self._ruido()))

    def leitura(self) -> dict:
        return {
            "balanca_id": self.balanca_id,
            "prato": self.prato,
            "peso_atual_g": round(self.peso_atual_g, 1),
            "capacidade_max_g": self.capacidade_max_g,
            "origem": self.origem,
        }


def criar_balancas() -> list[Balanca]:
    pratos = [
        ("Arroz Branco", 15000),
        ("Feijão", 12000),
        ("Farofa", 4000),
        ("Frango Grelhado", 8000),
        ("Salada Mista", 6000),
    ]
    return [
        Balanca(
            balanca_id=i + 1,
            prato=nome,
            capacidade_max_g=cap,
            peso_atual_g=cap * random.uniform(0.4, 1.0),  # começa em níveis variados
            prob_servir=random.uniform(0.3, 0.8),         # pratos mais ou menos populares
        )
        for i, (nome, cap) in enumerate(pratos)
    ]


def main(intervalo_s: float = 1.0) -> None:
    balancas = criar_balancas()
    try:
        while True:
            for b in balancas:
                b.tick()
                payload = json.dumps(b.leitura(), ensure_ascii=False)
                print(payload)
                # aqui você pode enviar: requests.post(URL, json=b.leitura())
                # ou publicar em MQTT/Kafka/etc.
            print("-" * 40)
            time.sleep(intervalo_s)
    except KeyboardInterrupt:
        print("Simulação encerrada.")


if __name__ == "__main__":
    main()