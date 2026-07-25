"""
Batch 3/N — corretude das métricas de tração sob volume (server/metrics.py).

O júri do hackathon vai olhar total_usdc / avg_latency_ms / p95_latency_ms no dashboard
ao vivo — esses números precisam estar certos sob carga, não só no caminho feliz de 1
pagamento. Foco em corretude (contra implementação de referência), não em benchmark de
throughput (isso já existe via `make load-test-smoke`, locust).
"""
import statistics

from server.metrics import clear_metrics, get_traction_snapshot, hydrate_traction, record_payment_settled


def _reference_p95(latencies: list[float]) -> float:
    """Replica o cálculo de get_traction_snapshot p/ comparação (mesmo algoritmo,
    não uma lib de estatística diferente — o objetivo é travar a fórmula, não
    re-testar se ela é 'a' definição correta de p95)."""
    if not latencies:
        return 0.0
    sorted_lats = sorted(latencies)
    idx = max(0, int(len(sorted_lats) * 0.95) - 1)
    return round(sorted_lats[idx], 1)


def _seed(n: int, base_latency: float = 100.0) -> None:
    for i in range(n):
        record_payment_settled(
            intent_id=f"perf-{i}",
            amount_usdc=0.01,
            latency_ms=base_latency + i,
            creator_handle=f"@creator_{i % 7}",
            tx=f"0x{i:064x}",
        )


class TestLatencyAggregationUnderVolume:
    def setup_method(self):
        clear_metrics()

    def test_avg_latency_correct_for_100_payments(self):
        _seed(100)
        snap = get_traction_snapshot()
        expected_avg = round(statistics.mean(100.0 + i for i in range(100)), 1)
        assert snap["avg_latency_ms"] == expected_avg

    def test_p95_latency_matches_reference_formula_for_100_payments(self):
        _seed(100)
        snap = get_traction_snapshot()
        latencies = [100.0 + i for i in range(100)]
        assert snap["p95_latency_ms"] == _reference_p95(latencies)

    def test_latency_window_caps_at_last_100_even_with_more_payments(self):
        """avg/p95 usam só as últimas 100 latências (_payment_latencies[-100:]) —
        com 250 pagamentos, os primeiros 150 não podem influenciar o cálculo."""
        _seed(250)
        snap = get_traction_snapshot()
        last_100 = [100.0 + i for i in range(150, 250)]
        assert snap["avg_latency_ms"] == round(statistics.mean(last_100), 1)
        assert snap["p95_latency_ms"] == _reference_p95(last_100)

    def test_single_payment_p95_equals_its_own_latency(self):
        record_payment_settled(intent_id="one", amount_usdc=1.0, latency_ms=42.0, creator_handle="@c", tx="0x1")
        snap = get_traction_snapshot()
        assert snap["p95_latency_ms"] == 42.0
        assert snap["avg_latency_ms"] == 42.0

    def test_zero_payments_reports_zero_not_crash(self):
        snap = get_traction_snapshot()
        assert snap["avg_latency_ms"] == 0.0
        assert snap["p95_latency_ms"] == 0.0


class TestTotalUsdcAccuracyUnderVolume:
    def setup_method(self):
        clear_metrics()

    def test_total_usdc_exact_sum_for_200_micropayments(self):
        n = 200
        for i in range(n):
            record_payment_settled(
                intent_id=f"usdc-{i}", amount_usdc=0.0355, latency_ms=1.0,
                creator_handle=f"@c{i % 5}", tx=f"0x{i}",
            )
        snap = get_traction_snapshot()
        assert snap["total_usdc"] == round(0.0355 * n, 2)
        assert snap["total_payments"] == n

    def test_active_creators_deduplicates_case_and_at_symbol(self):
        record_payment_settled(intent_id="a", amount_usdc=1.0, latency_ms=1.0, creator_handle="@Music_NFT", tx="0x1")
        record_payment_settled(intent_id="b", amount_usdc=1.0, latency_ms=1.0, creator_handle="music_nft", tx="0x2")
        record_payment_settled(intent_id="c", amount_usdc=1.0, latency_ms=1.0, creator_handle="@MUSIC_NFT", tx="0x3")
        snap = get_traction_snapshot()
        assert snap["active_creators"] == 1
        assert snap["total_payments"] == 3  # 3 pagamentos, mas 1 creator único

    def test_duplicate_intent_id_under_volume_does_not_inflate_total(self):
        for _ in range(50):
            record_payment_settled(intent_id="same-intent", amount_usdc=5.0, latency_ms=1.0, creator_handle="@c", tx="0x1")
        snap = get_traction_snapshot()
        assert snap["total_usdc"] == 5.0
        assert snap["total_payments"] == 1


class TestFeedBoundedUnderVolume:
    def setup_method(self):
        clear_metrics()

    def test_snapshot_feed_capped_at_20_even_with_500_payments(self):
        _seed(500)
        snap = get_traction_snapshot()
        assert len(snap["feed"]) == 20

    def test_snapshot_feed_shows_most_recent_first(self):
        _seed(30)
        snap = get_traction_snapshot()
        assert snap["feed"][0]["intent_id"] == "perf-29"
        assert snap["feed"][-1]["intent_id"] == "perf-10"

    def test_internal_feed_buffer_capped_at_max_feed_with_600_payments(self):
        """_payment_feed interno (não só o snapshot de 20) também tem teto —
        senão o processo vaza memória com o histórico completo de pagamentos."""
        import server.metrics as metrics_module
        _seed(600)
        assert len(metrics_module._payment_feed) <= metrics_module._MAX_FEED


class TestHydrateTractionUnderVolume:
    def setup_method(self):
        clear_metrics()

    def test_hydrate_300_rows_matches_incrementally_recorded_equivalent(self):
        rows = [
            {
                "intent_id": f"h-{i}",
                "amount_usdc": 0.1,
                "creator_handle": f"@c{i % 10}",
                "tx": f"0x{i}",
                "latency_ms": float(i),
                "ts": f"2026-06-29T20:{i % 60:02d}:00+00:00",
            }
            for i in range(300)
        ]
        hydrate_traction(rows)
        snap = get_traction_snapshot()
        assert snap["total_payments"] == 300
        assert snap["total_usdc"] == round(0.1 * 300, 2)
        assert snap["active_creators"] == 10

    def test_hydrate_is_reasonably_fast_for_1000_rows(self):
        """Sanidade de performance no boot — 1000 linhas hidratando não pode travar
        o startup do backend por segundos. Margem generosa (5s) pra não ser flaky."""
        import time
        rows = [
            {
                "intent_id": f"perf-hydrate-{i}",
                "amount_usdc": 0.01,
                "creator_handle": f"@c{i % 20}",
                "tx": f"0x{i}",
                "latency_ms": 1.0,
                "ts": "2026-06-29T20:00:00+00:00",
            }
            for i in range(1000)
        ]
        t0 = time.monotonic()
        hydrate_traction(rows)
        elapsed = time.monotonic() - t0
        assert elapsed < 5.0, f"hydrate_traction(1000 rows) levou {elapsed:.2f}s — investigar regressão de performance"


class TestTractionStatsEndpointUnderVolume:
    def setup_method(self):
        clear_metrics()

    def test_get_traction_stats_endpoint_responds_quickly_with_full_feed(self):
        import time
        import importlib
        from fastapi.testclient import TestClient
        app_module = importlib.import_module("server.app")
        client = TestClient(app_module.app)

        _seed(500)
        t0 = time.monotonic()
        resp = client.get("/v1/traction/stats")
        elapsed = time.monotonic() - t0
        assert resp.status_code == 200
        assert elapsed < 2.0, f"GET /v1/traction/stats levou {elapsed:.2f}s com 500 pagamentos"
