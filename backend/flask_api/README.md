# flask_api/ — ARQUIVADO (2026-07-10)

App Flask legado. Não tem entrypoint nenhum: `Makefile`, `railway.toml` e
`backend/Dockerfile` só sobem `server.app:app` via uvicorn (FastAPI). Nada
neste diretório roda em produção nem em dev local via `make dev`.

Único consumidor vivo era `ai/response_generator.py`, também arquivado
(ver header do arquivo). O caminho vivo de chat é
`backend/server/orchestration/service.py` + `backend/chat_agent.py`.

Não usar como referência nem reconectar sem antes ler
`docs/CONSISTENCY_ROADMAP.md` (seção 1, DoD "fonte única de verdade").
