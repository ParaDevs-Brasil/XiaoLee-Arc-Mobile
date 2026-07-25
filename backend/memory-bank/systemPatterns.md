# System Patterns: XiaoLee

## Arquitetura de Camadas

- Canais (Telegram/X/Frontend) entram no backend FastAPI.
- Orquestrador centraliza intencao, resposta e chamadas de integracao.
- Persistencia em SQLAlchemy para historico, transacoes e notificacoes.
- Eventos on-chain entram por webhook Helius e viram atualizacao de estado.

## Padroes de Implementacao

- **Wallet-first nao custodial:** backend prepara, usuario assina no frontend.
- **Webhook security-first:** validacao de segredo/assinatura antes de processar payload.
- **Rate-limit in-memory:** protecao imediata para flood em canais.
- **Fallback controlado:** degradacao funcional quando IA externa indisponivel.
- **Idempotencia pragmatica:** atualizar registros existentes por `signature` quando evento se repete.

## Padroes de Frontend

- Validacao de input antes de chamar `/swap/prepare`.
- Simulacao da transacao antes de habilitar envio.
- Confirmacao explicita por checkbox para reduzir envio acidental.
- Mensagens de erro orientadas para recuperacao do usuario.

## Padroes de Teste

- Cobertura de caminho feliz e falhas criticas no fluxo da wallet.
- Mocks deterministas para provider Phantom, fetch e `@solana/web3.js`.
- Testes utilitarios para conversao de montantes e resumo de quote.
