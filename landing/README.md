# Xiaolee Landing Page

Official Xiaolee landing page — a **standalone static service**, fully decoupled
from the Next.js frontend (`frontend/`). Source design: Claude Design export
(`Xiaolee Landing Page.dc.html`), ported to self-contained vanilla HTML/CSS/JS.

## Structure

```
landing/
├── index.html          # the whole page (inline styles + vanilla JS reveal/counter)
├── Dockerfile          # static serve (node:18-alpine + serve)
└── assets/
    ├── candice-web.ttf         # brand display font
    ├── xiaolee-icon-512.png    # mascot / favicon / og:image
    └── logos/                  # "Supported by" marquee logos
        ├── superteam.svg
        ├── colosseum.svg
        ├── metapool.svg        # Meta Pool wordmark (white source, rendered as ink)
        └── parabuilders.png    # white source, rendered as ink
```

## Deploy (Railway)

Deploy point: `railway.landing.toml` at the repo root points to `landing/Dockerfile`.
Create/point the Railway landing service at this repo with that config file
(`RAILWAY_CONFIG_FILE=railway.landing.toml` or set it in the service settings).

The legacy flow (`frontend/Dockerfile.landing`, which built the whole Next app to
serve `out/landing.html`) is no longer used by the landing service.

## Local preview

```bash
cd landing && python3 -m http.server 8080
# or: npx serve .
```

## Notes

- Marquee logos are white/colored sources normalized to ink via `filter: brightness(0)`
  at 50% opacity (hover raises opacity). Drop new logos in `assets/logos/` and add an
  `<li>` in both halves of the duplicated track in `index.html`.
- Quicksand loads from Google Fonts; Candice is local (`assets/candice-web.ttf`).
- `prefers-reduced-motion` is respected (no animations, counters render final values).
