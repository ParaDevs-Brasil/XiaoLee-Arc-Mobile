# XiaoLee — Testes de Carga com Locust

## Pré-requisitos

```bash
pip install locust
# ou, usando o venv do backend:
cd backend && ../.venv/bin/pip install locust
```

## Cenários

| Cenário | Peso | Endpoints | SLA Alvo |
|---|---|---|---|
| `XiaoLeeCriticalPath` | 3x | `/campaigns/join`, `/verify`, `/claim` | p95 < 500ms |
| `XiaoLeeReadOnly` | 5x | `/health`, `/status`, `/metrics`, `/campaigns` | p95 < 200ms |
| `XiaoLeeChat` | 1x | `/chat` | p95 < 3000ms (LLM) |

## Execução

### Modo headless (CI/CD)
```bash
cd /path/to/XiaoLee
locust -f load_tests/locustfile.py \
    --host=http://localhost:8000 \
    --users=20 --spawn-rate=4 \
    --run-time=120s --headless \
    --html=load_tests/reports/report_$(date +%Y%m%d_%H%M%S).html
```

### Interface web (desenvolvimento)
```bash
locust -f load_tests/locustfile.py --host=http://localhost:8000
# Abre: http://localhost:8089
```

### Teste de smoke rápido
```bash
locust -f load_tests/locustfile.py \
    --host=http://localhost:8000 \
    --users=5 --spawn-rate=1 --run-time=30s --headless
```

### Staging (pré-mainnet)
```bash
locust -f load_tests/locustfile.py \
    --host=https://api-staging.xiaolee.io \
    --users=100 --spawn-rate=10 \
    --run-time=600s --headless \
    --html=load_tests/reports/staging_$(date +%Y%m%d).html
```

## SLA para Mainnet

| Métrica | Target | Critério de aprovação |
|---|---|---|
| p50 (mediana) | < 200ms | ✅ Confortável |
| p95 | < 500ms | ✅ SLA principal |
| p99 | < 1000ms | ✅ Aceitável |
| Error rate | < 1% | ✅ Gatekeeping |

O script retorna **exit code 1** se p95 > 500ms ou error rate > 1% — compatível com CI/CD.

## Integração no CI (GitHub Actions)

```yaml
- name: Load Test (smoke)
  run: |
    cd backend && ../.venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000 &
    sleep 5
    locust -f ../load_tests/locustfile.py \
      --host=http://localhost:8000 \
      --users=10 --spawn-rate=2 --run-time=60s --headless
```

## Diretório de Relatórios

```
load_tests/
├── locustfile.py       ← cenários de teste
├── README.md           ← este arquivo
└── reports/            ← relatórios HTML gerados (gitignored)
    ├── report_20260424_135000.html
    └── staging_20260424.html
```

> ⚠️ A pasta `reports/` está no `.gitignore`. Armazene relatórios no S3 ou Artifact CI para auditoria de performance.
