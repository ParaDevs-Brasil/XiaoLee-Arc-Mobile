# Active Context: XiaoLee

## Foco Atual

- Polish de UI/UX: consistência visual entre todas as telas no tema claro.
- Sistema rodando em Docker com frontend, backend, PostgreSQL, Redis, Grafana e Prometheus.

## Mudancas Recentes

- **Alinhamento de tema light**: Notifications, Dashboard, Campaigns e Chat agora compartilham a mesma paleta rosa/roxo pastel kawaii.
- **Notifications**: tema migrado de cyan/blue para pink/fuchsia/purple.
- **Dashboard**: classe `dark:from-gray-900 dark:via-purple-900` removida do wrapper — light mode agora sempre exibe o fundo pastel correto.
- **globals.css**: `background-attachment: fixed` adicionado ao body.
- **ThemeProvider**: mantido sem `forcedTheme` — toggle dark/light funcional e totalmente livre.
- **Integração Gemini Refinada**: Migração do `litellm` para a SDK nativa `google.genai` (`LLMClient`), com prompts atualizados para refletir a persona bilíngue e focada da XiaoLee (Campanhas, Devnet, uso de emojis 🌸).
- **Ajustes de UI e Estado**: Melhorias de _safe parsing_ em `UserData.tsx` para evitar crashes no carregamento de estado `undefined`, além de ajustes no z-index e responsividade do `Navbar` e atualização do avatar no `ChatPanel`.

## Proximos Passos Imediatos

1. Fase 9 — Infraestrutura de produção (HTTPS, PostgreSQL/Redis gerenciado, secrets vault).
2. Auditoria de segurança dos contratos Anchor.
3. Deploy em mainnet após bloqueadores P0 resolvidos.

## Riscos Ativos

- Evitar regressao de documentacao quando novas rotas forem adicionadas.
- Evitar linguagem de readiness de producao sem validacao tecnica formal.

## Status

- Sem bloqueios técnicos. Frontend visualmente consistente e pronto para apresentação. Necessitando apenas de polimento no modo Dark e otimização de performance (modo dark atualmente não está funcionando como deveria, não consegue alternar entre light e dark).

