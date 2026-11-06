# Documentation index

Everything tracked lives under one of five categories, plus the migration
records and shared assets.

## Architecture

| Document | Covers |
|---|---|
| [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) | request path, trust boundaries, workspace authorisation, internal service channel |
| [`architecture/KRAIVOR_COMPLETE_DOCUMENTATION.md`](architecture/KRAIVOR_COMPLETE_DOCUMENTATION.md) | end-to-end product/engineering reference |

## Services

| Document | Covers |
|---|---|
| [`services/AUTH_SERVICE.md`](services/AUTH_SERVICE.md) | `services/auth` (Django/DRF) |
| [`services/CORE_SERVICE.md`](services/CORE_SERVICE.md) | `services/core` (Django/DRF) |
| [`services/chat/CHAT_SERVICE.md`](services/chat/CHAT_SERVICE.md) | Core chat (Channels/WebSocket) |
| [`services/chat/CHAT_V2_OVERVIEW.md`](services/chat/CHAT_V2_OVERVIEW.md) | Chat V2 summary, topology, goals |
| [`services/chat/CHAT_V2_SYSTEM_DESIGN.md`](services/chat/CHAT_V2_SYSTEM_DESIGN.md) | Chat V2 design rationale and trade-offs |
| [`services/chat/CHAT_V2_ARCHITECTURE.md`](services/chat/CHAT_V2_ARCHITECTURE.md) | Chat V2 implementation blueprint |
| [`services/chat/CHAT_V2_WORKFLOW.md`](services/chat/CHAT_V2_WORKFLOW.md) | Chat V2 workflow |

## Development

| Document | Covers |
|---|---|
| [`development/DOCKER.md`](development/DOCKER.md) | local Docker workflow |
| [`development/CI-VS-DOCKER.md`](development/CI-VS-DOCKER.md) | CI vs Docker differences |
| [`development/CI-MIGRATION-FIXES.md`](development/CI-MIGRATION-FIXES.md) | CI migration notes |
| [`development/KRV-011.md`](development/KRV-011.md) | KRV-011 ticket record |

## Operations

| Document | Covers |
|---|---|
| [`operations/DEPLOYMENT.md`](operations/DEPLOYMENT.md) | deploy pipeline, pre-deploy checklist, rollback |
| [`operations/CODEQL-TRIAGE.md`](operations/CODEQL-TRIAGE.md) | historical CodeQL triage record (paths reflect the pre-migration layout) |

## API

| Document | Covers |
|---|---|
| [`api/postman/`](api/postman/) | Postman collections and environments |

## Migration records

[`migration/`](migration/) holds the frozen baseline, the restructure map, the
per-phase records, and the follow-up log. Start at
[`migration/MAP.md`](migration/MAP.md).

## Assets

Logos and shared imagery live in [`assets/`](assets/).
