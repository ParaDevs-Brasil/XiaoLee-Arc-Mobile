from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import DefaultDict, List, Tuple


_lock = RLock()
_request_counts: DefaultDict[Tuple[str, str, int], int] = defaultdict(int)
_request_durations: DefaultDict[Tuple[str, str], List[float]] = defaultdict(list)

# Contadores específicos de domínio — campanhas
_campaign_counters: DefaultDict[str, int] = defaultdict(int)

# ── Traction / USDC payments (RFB-06) ─────────────────────────────────────
_usdc_total: float = 0.0
_payment_count: int = 0
_active_creators: set[str] = set()
_payment_latencies: List[float] = []
_payment_feed: List[dict] = []
_MAX_FEED = 50

# Creators registrados via /v1/creator/register (handle → {circle_wallet_id, registered_at})
_registered_creators: dict = {}

# Idempotência: intent_ids já processados — evita double-count se f0ntz chamar payment_settled duas vezes
_processed_intent_ids: set[str] = set()


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    key = (method.upper(), path, int(status_code))
    duration_key = (method.upper(), path)

    with _lock:
        _request_counts[key] += 1
        _request_durations[duration_key].append(duration_seconds)


def record_campaign_event(event: str) -> None:
    """Registra evento de campanha para observabilidade.

    Eventos válidos: 'join', 'join_duplicate', 'join_full',
                     'verify', 'claim', 'claim_duplicate', 'claim_error'.
    """
    with _lock:
        _campaign_counters[event] += 1


def register_creator(handle: str, circle_wallet_id: str) -> dict:
    """Registra creator para receber pagamentos USDC. Idempotente por handle."""
    from datetime import datetime as _dt
    handle = handle.lstrip("@").lower()
    with _lock:
        if handle in _registered_creators:
            return {"already_registered": True, **_registered_creators[handle]}
        entry = {
            "handle": f"@{handle}",
            "circle_wallet_id": circle_wallet_id,
            "registered_at": _dt.utcnow().isoformat() + "Z",
        }
        _registered_creators[handle] = entry
        return {"already_registered": False, **entry}


def is_creator_registered(handle: str) -> bool:
    with _lock:
        return handle.lstrip("@").lower() in _registered_creators


def get_registered_creator_wallet(handle: str) -> str | None:
    """Retorna o circle_wallet_id do creator registrado, ou None se não encontrado."""
    with _lock:
        entry = _registered_creators.get(handle.lstrip("@").lower())
        return entry["circle_wallet_id"] if entry else None


def get_registered_creator_count() -> int:
    with _lock:
        return len(_registered_creators)


def record_payment_settled(
    intent_id: str,
    amount_usdc: float,
    latency_ms: float,
    creator_handle: str,
    tx: str,
) -> bool:
    """
    Registra pagamento USDC confirmado. Retorna False se intent_id já foi processado (idempotente).
    Chamado pelo traction_routes ao receber payment_settled.
    """
    from datetime import datetime as _dt
    global _usdc_total, _payment_count

    with _lock:
        if intent_id in _processed_intent_ids:
            return False
        _processed_intent_ids.add(intent_id)
        _usdc_total += amount_usdc
        _payment_count += 1
        _active_creators.add(creator_handle.lstrip("@").lower())
        _payment_latencies.append(latency_ms)
        _payment_feed.insert(0, {
            "intent_id": intent_id,
            "amount": round(amount_usdc, 4),
            "creator": creator_handle,
            "tx": tx,
            "ts": _dt.utcnow().isoformat() + "Z",
            "latency_ms": round(latency_ms, 1),
        })
        if len(_payment_feed) > _MAX_FEED:
            _payment_feed.pop()
        return True


def hydrate_traction(rows: list[dict]) -> None:
    """Reconstrói o estado in-memory de tração a partir do DB — chamado no boot do app
    (lifespan), depois que `SettledPayment` é lido via repository.list_settled_payments().

    `rows` precisa vir em ordem cronológica ascendente (mais antigo primeiro), cada item
    com chaves: intent_id, amount_usdc, creator_handle, tx, latency_ms, ts.
    """
    global _usdc_total, _payment_count
    with _lock:
        for row in rows:
            intent_id = row["intent_id"]
            if intent_id in _processed_intent_ids:
                continue
            _processed_intent_ids.add(intent_id)
            _usdc_total += row["amount_usdc"]
            _payment_count += 1
            _active_creators.add(row["creator_handle"].lstrip("@").lower())
            _payment_latencies.append(row["latency_ms"])
            _payment_feed.insert(0, {
                "intent_id": intent_id,
                "amount": round(row["amount_usdc"], 4),
                "creator": row["creator_handle"],
                "tx": row["tx"],
                "ts": row["ts"],
                "latency_ms": round(row["latency_ms"], 1),
            })
        del _payment_feed[_MAX_FEED:]


def get_traction_snapshot() -> dict:
    """Retorna snapshot agregado das métricas de tração para o dashboard."""
    with _lock:
        lats = _payment_latencies[-100:] if _payment_latencies else []
        avg_lat = sum(lats) / len(lats) if lats else 0.0
        sorted_lats = sorted(lats)
        p95_idx = max(0, int(len(sorted_lats) * 0.95) - 1)
        p95_lat = sorted_lats[p95_idx] if sorted_lats else 0.0
        return {
            "total_usdc": round(_usdc_total, 2),
            "total_payments": _payment_count,
            "active_creators": len(_active_creators),
            "registered_creators": len(_registered_creators),
            "avg_latency_ms": round(avg_lat, 1),
            "p95_latency_ms": round(p95_lat, 1),
            "feed": list(_payment_feed[:20]),
        }


def render_prometheus_metrics() -> str:
    lines = [
        '# HELP xiaolee_http_requests_total Total de requests HTTP processadas.',
        '# TYPE xiaolee_http_requests_total counter',
    ]

    with _lock:
        for (method, path, status_code), count in sorted(_request_counts.items()):
            lines.append(
                f'xiaolee_http_requests_total{{method="{method}",path="{path}",status="{status_code}"}} {count}'
            )

        lines.extend([
            '',
            '# HELP xiaolee_http_request_duration_seconds_avg Tempo medio de resposta por rota.',
            '# TYPE xiaolee_http_request_duration_seconds_avg gauge',
        ])

        for (method, path), durations in sorted(_request_durations.items()):
            if not durations:
                continue
            average_duration = sum(durations) / len(durations)
            lines.append(
                f'xiaolee_http_request_duration_seconds_avg{{method="{method}",path="{path}"}} {average_duration:.6f}'
            )

        # Métricas de campanhas
        if _campaign_counters:
            lines.extend([
                '',
                '# HELP xiaolee_campaign_events_total Eventos de campanha por tipo.',
                '# TYPE xiaolee_campaign_events_total counter',
            ])
            for event, count in sorted(_campaign_counters.items()):
                lines.append(
                    f'xiaolee_campaign_events_total{{event="{event}"}} {count}'
                )

        # Métricas de tração USDC (RFB-06)
        lines.extend([
            '',
            '# HELP xiaolee_usdc_paid_total Total de USDC pago a creators (RFB-06).',
            '# TYPE xiaolee_usdc_paid_total counter',
            f'xiaolee_usdc_paid_total {_usdc_total:.4f}',
            '',
            '# HELP xiaolee_payments_total Número de nanopagamentos confirmados.',
            '# TYPE xiaolee_payments_total counter',
            f'xiaolee_payments_total {_payment_count}',
            '',
            '# HELP xiaolee_active_creators Número de creators únicos que receberam pagamento.',
            '# TYPE xiaolee_active_creators gauge',
            f'xiaolee_active_creators {len(_active_creators)}',
        ])

        if _payment_latencies:
            lats = _payment_latencies[-100:]
            avg_lat = sum(lats) / len(lats)
            lines.extend([
                '',
                '# HELP xiaolee_payment_latency_ms_avg Latência média dos pagamentos (ms).',
                '# TYPE xiaolee_payment_latency_ms_avg gauge',
                f'xiaolee_payment_latency_ms_avg {avg_lat:.2f}',
            ])

    lines.append('')
    return "\n".join(lines)


def clear_metrics() -> None:
    global _usdc_total, _payment_count
    with _lock:
        _request_counts.clear()
        _request_durations.clear()
        _campaign_counters.clear()
        _usdc_total = 0.0
        _payment_count = 0
        _active_creators.clear()
        _payment_latencies.clear()
        _payment_feed.clear()
        _registered_creators.clear()
        _processed_intent_ids.clear()