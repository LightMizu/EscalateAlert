import asyncio
from dataclasses import dataclass

from alertescalation import config
from alertescalation.benchmark_data import (
    calm_messages,
    one_sided_continuation_messages,
    strong_swings_messages,
    swing_starts_messages,
)
from alertescalation.monitor import BehaviorMonitor


@dataclass
class TestResult:
    scenario: str
    model: str

    hostility: float
    impulsivity: float
    repetition: float
    mutual_escalation: float
    escalation: float

    total: float

    @property
    def alert(self):
        return self.escalation >= 0.70


# Сумма весов = 1.0
# Основной акцент на взаимном усилении конфликта.
WEIGHTS = {
    "hostility": 0.15,
    "impulsivity": 0.10,
    "repetition": 0.25,
    "mutual_escalation": 0.50,
}


def calculate_score(analysis):
    return sum(getattr(analysis, key) * weight for key, weight in WEIGHTS.items())


async def run_test(monitor, scenario, messages, model):
    # Каждый сценарий полностью изолирован.
    monitor.history.clear()
    config.MODEL = model

    for role, content in messages:
        monitor.add_message(role, content)

    analysis = await monitor.analyze()

    if analysis is None:
        raise RuntimeError(f"Not enough context: {scenario} ({model})")

    result = TestResult(
        scenario=scenario,
        model=model,
        hostility=analysis.hostility,
        impulsivity=analysis.impulsivity,
        repetition=analysis.repetition,
        mutual_escalation=analysis.mutual_escalation,
        escalation=analysis.escalation,
        total=calculate_score(analysis),
    )

    return result


async def benchmark(monitor):
    scenarios = {
        "Calm": calm_messages,
        "Swing starts": swing_starts_messages,
        "Strong swings": strong_swings_messages,
        "One side": one_sided_continuation_messages,
    }

    models = [
        "cloudflare/clef",
        "typesafe/jev-1.13",
    ]

    results = []
    original_model = config.MODEL

    try:
        for scenario, messages in scenarios.items():
            for model in models:
                result = await run_test(
                    monitor=monitor,
                    scenario=scenario,
                    messages=messages,
                    model=model,
                )

                results.append(result)

    finally:
        config.MODEL = original_model
        monitor.history.clear()

    return results


def print_summary(results):
    print("\n" + "=" * 112)
    print("                 ALERT ESCALATION BENCHMARK")
    print("=" * 112)

    print(
        f"{'Scenario':<17}"
        f"{'Model':<12}"
        f"{'Hostility':>11}"
        f"{'Impulsive':>11}"
        f"{'Repetition':>12}"
        f"{'Mutual':>11}"
        f"{'Escalation':>12}"
        f"{'Total':>9}"
        f"  Alert"
    )

    print("-" * 112)

    for r in results:
        model_name = "Clef" if "clef" in r.model else "Jev"

        print(
            f"{r.scenario:<17}"
            f"{model_name:<12}"
            f"{r.hostility:>10.1%}"
            f"{r.impulsivity:>11.1%}"
            f"{r.repetition:>12.1%}"
            f"{r.mutual_escalation:>11.1%}"
            f"{r.escalation:>12.1%}"
            f"{r.total:>9.1%}"
            f"  {'YES' if r.alert else 'NO'}"
        )

    print("=" * 112)


async def main():
    monitor = BehaviorMonitor()

    try:
        results = await benchmark(monitor)
        print_summary(results)

    finally:
        await monitor.close()
