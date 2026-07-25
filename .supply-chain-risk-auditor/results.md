# Supply Chain Risk Report

---

## Metadata

- **Scan Date**: 2026-05-22
- **Project**: XiaoLee (StellarAdapt)
- **Repositories Scanned**: 28 repositories
- **Total Dependencies**: 29 direct dependencies (17 Python, 12 JS/TS)
- **Manifests**: `backend/requirements.txt`, `backend/requirements.mcp.txt`, `frontend/package.json`

---

## Executive Summary

The XiaoLee dependency graph has **5 packages with 2 or more risk factors** and **6 packages with 1 risk factor**. The most critical finding is that `google-generativeai` — used for AI query responses — is **archived and deprecated**, with the maintainer explicitly directing users to migrate to `google-genai`. The `solders` package, which handles Solana PDA derivation and keypair operations, combines low popularity with single-maintainer risk and FFI (Rust bindings), making it a high-value supply-chain attack target in the crypto context. `react-draggable` has not cut a GitHub release since 2016 while accumulating 221 open issues. `python-multipart`, which parses all multipart form data at the HTTP boundary, is maintained by a single individual with only 497 stars.

### Counts by Risk Factor

| Risk Factor | Dependencies | Total |
|-------------|--------------|-------|
| Single maintainer | `solders`, `next-themes`, `python-multipart`, `react-toastify`, `python-dotenv`, `PyJWT` | 6 |
| Unmaintained / archived | `google-generativeai` (archived), `react-draggable` (no release since 2016) | 2 |
| Low popularity | `solders` (~440★), `@stellar/freighter-api` (~112★), `python-multipart` (~497★), `@web3auth/*` (~489★) | 4 |
| High-risk features (FFI / boundary parsing) | `solders` (Rust FFI), `python-multipart` (HTTP body parsing) | 2 |
| Absence of security contact | `solders`, `next-themes`, `asyncpg`, `@web3auth/web`, `react-toastify`, `react-draggable` | 6 |
| **Total unique flagged** | — | **11** |

### High-Risk Dependencies (2+ risk factors)

| Dependency | Risk Factors | Notes | Suggested Alternative |
|---|---|---|---|
| `google-generativeai` | Unmaintained, Absence of security contact | Repository **explicitly archived** by Google on 2025-12-16. README directs users to migrate to `google-genai`. 95 open issues, no new security patches. Used to power AI responses at the core of the product. | **`google-genai`** — the official successor SDK (`googleapis/python-genai`), drop-in API migration, actively maintained by Google. |
| `solders` | Single maintainer, Low popularity, High-risk features | ~440 GitHub stars, maintained by one individual (`kevinheavey`, User account). Wraps Rust cryptographic primitives via PyO3 FFI — memory-safety boundary. No security policy. Last release Nov 2025. Used for Solana PDA derivation and keypair operations. | **`solana-py`** (`michaelhly/solana-py`) or direct use of the official `@solana/web3.js` on the JS side. For Python, prefer `construct` + `base58` with explicit key handling rather than opaque FFI bindings if solders usage is minimal. |
| `react-draggable` | Unmaintained, Absence of security contact | Last **GitHub release** was v2.2.3 in **December 2016**. The npm package continues at v4.5.0 but 221 open issues remain unaddressed, including compatibility failures with latest React. No security policy. No GitHub Discussions. | **`@dnd-kit/core`** — actively maintained by the Clauderic organization, security policy present, ~13k stars, designed for React 18/19. |
| `next-themes` | Single maintainer, Absence of security contact | Maintained solely by `pacocoursey` (User account). 64 open issues, no security policy, last push Feb 2026 (3 months stale). Used for dark/light mode toggling across the entire frontend. | **`@mui/material` ThemeProvider** or **`@radix-ui/themes`** — organization-backed, active maintenance, security policies present. |
| `python-multipart` | Single maintainer, Low popularity, High-risk features | Maintained by `Kludex` (User account), ~497 stars. Parses all multipart/form-data at the HTTP security boundary (file uploads, form fields) — a category historically prone to DoS and injection CVEs. FastAPI depends on it for any `Form` or `File` endpoint. | No direct drop-in alternative for FastAPI; however, pinning to a specific version and monitoring `Kludex/python-multipart` releases closely is essential. Consider advocating for FastAPI to accept `multipart` (the older, more battle-tested library) as an alternative. |

---

## Suggested Alternatives

### `google-generativeai` → `google-genai`

The migration from `google-generativeai` to `google-genai` is documented at https://github.com/googleapis/python-genai. The new SDK unifies Gemini and Vertex AI under one interface. The API surface changes (client instantiation, model names) but the core `generate_content` flow is equivalent. Priority: **immediate** — the archived package will not receive security patches.

### `react-draggable` → `@dnd-kit/core`

`@dnd-kit/core` provides equivalent draggable behavior with accessibility support, React 19 compatibility, and active maintenance by the Clauderic organization (~13k stars, security policy). Migration requires replacing `<Draggable>` with `useDraggable` hook but gives significantly better touch and keyboard support.

### `solders` — risk mitigation

If the project only uses `solders` for PDA derivation and public key parsing (not signing), consider replacing with pure-Python base58 + SHA256 for the minimal operations needed. If Solana signing is required on the backend, evaluate `nacl` (`PyNaCl`, which is also FFI but from the well-audited libsodium) combined with manual serialization. If `solders` must be kept, open a security contact issue on the repo and pin to a verified release hash in requirements.

### `next-themes` — risk mitigation

If dark/light mode is a small part of the codebase, consider implementing it directly via CSS variables and `localStorage` without a library dependency. This eliminates the single-maintainer risk for functionality that is inherently low-complexity.

### `python-multipart` — risk mitigation

Pin to an exact version (already done: `python-multipart==0.0.20`) and subscribe to security advisories on the repo. Set up Dependabot for this dependency specifically.

---

## Recommendations

1. **Migrate off `google-generativeai` immediately.** The package is archived, receives no security patches, and the maintainer explicitly directs users to `google-genai`. This is the highest-priority action.

2. **Review `solders` usage and scope.** With 440 stars, a single maintainer, and Rust FFI, this is the highest supply-chain risk in the dependency graph for a crypto product. Determine if usage can be eliminated or replaced with a more audited library. At minimum, pin to a specific commit hash.

3. **Replace `react-draggable`.** The last formal GitHub release in 2016 with 221 unresolved issues is a strong unmaintained signal. Migrate to `@dnd-kit/core` during the next frontend sprint.

4. **Add Dependabot or Renovate** for all three manifests (`requirements.txt`, `requirements.mcp.txt`, `frontend/package.json`). The project currently has no automated dependency update tooling visible in the repo.

5. **Monitor `python-multipart` and `asyncpg` closely.** Both sit at the network/database boundary with either single-maintainer or no-security-policy risk. Keep pinned versions and check changelogs before upgrading.

6. **`@stellar/freighter-api`** has only 112 stars. Since it handles wallet transaction signing (critical path), review its source on each version update before upgrading. It is Stellar-organization-maintained which reduces but does not eliminate risk.

---

## Report Generated By

Supply Chain Risk Auditor Skill  
Generated: 2026-05-22
