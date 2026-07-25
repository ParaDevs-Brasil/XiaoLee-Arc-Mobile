# Project Brief: XiaoLee

## Objetivo

Construir um assistente de IA multi-canal para Solana, com foco em:

- processamento de mensagens inbound,
- orquestracao de intencoes com LLM,
- fluxo de swap seguro e nao custodial,
- persistencia de historico e notificacoes.

## Escopo Atual (MVP)

- Backend FastAPI para chat, webhooks, campanhas e notificacoes.
- Integracao Gemini para classificacao de intencao e resposta.
- Integracao Solana/Jupiter para preparo de swap unsigned.
- Frontend Next.js com fluxo wallet-first: connect, simulate, confirm, sign/send.
- Reconciliacao de eventos on-chain via webhook Helius.

## Fora de Escopo (neste ciclo)

- Mainnet com selo production-ready sem auditoria formal.
- Custodia de chave privada do usuario no backend.
- Operacao SRE completa com observabilidade avancada fullstack.

## Criterios de Sucesso

- Endpoints MVP operando e documentados de forma consistente.
- Fluxo de swap wallet-first funcionando em Devnet.
- Cobertura de testes frontend para sucesso e falhas criticas.
- Documentacao central e memory-bank sincronizados com o codigo.
