---
layout: default
title: One-Shot-Multi-Shot
description: Binary-Options 3-Hearts Engine (JS) — part of the ARC Trading Fleet.
---

# One-Shot-Multi-Shot
**Binary-Options 3-Hearts Engine (JS)**

[![Source](https://img.shields.io/badge/source-GitHub-181717?logo=github)](https://github.com/GareBear99/One-Shot-Multi-Shot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/GareBear99/One-Shot-Multi-Shot/blob/main/LICENSE)
[![Built on ARC-Core](https://img.shields.io/badge/built%20on-ARC--Core-5B6CFF)](https://github.com/GareBear99/ARC-Core)

## 📖 Official docs

[![Open the official docs](https://img.shields.io/badge/%F0%9F%93%96%20Open%20Official%20Docs-Layman%20Guide%20v8%20(Live%20GUI)-0366d6?style=for-the-badge)](./official/OneShot_Layman_Guide_v8_LiveGUI_TRUEStreaming_Fixes.html)

[![Operator Guide PDF](https://img.shields.io/badge/%F0%9F%93%84%20Operator%20Guide-PDF-grey?style=for-the-badge)](./official/OneShot_Operator_Guide_Consolidated.pdf) [![Hearts %26 Stake Spec](https://img.shields.io/badge/%F0%9F%92%9A%20Hearts%20%26%20Stake%20Spec-PDF-grey?style=for-the-badge)](./official/OneShot_Auto_Hearts_Stake_Profit_Spec_v1.pdf)

Live URL of the primary doc: `https://garebear99.github.io/One-Shot-Multi-Shot/official/OneShot_Layman_Guide_v8_LiveGUI_TRUEStreaming_Fixes.html`

## What this is

One-Shot-Multi-Shot is part of the **ARC Trading Fleet** — six public repositories that share a
single event-and-receipt doctrine provided by
[ARC-Core](https://github.com/GareBear99/ARC-Core).

- **Source code and full README**: [https://github.com/GareBear99/One-Shot-Multi-Shot](https://github.com/GareBear99/One-Shot-Multi-Shot)
- **Architecture notes**: [docs/ARCHITECTURE.md](https://github.com/GareBear99/One-Shot-Multi-Shot/blob/main/docs/ARCHITECTURE.md)
- **Usage / operator guide**: [docs/USAGE.md](https://github.com/GareBear99/One-Shot-Multi-Shot/blob/main/docs/USAGE.md)
- **Security policy**: [SECURITY.md](https://github.com/GareBear99/One-Shot-Multi-Shot/blob/main/SECURITY.md)
- **Contributing**: [CONTRIBUTING.md](https://github.com/GareBear99/One-Shot-Multi-Shot/blob/main/CONTRIBUTING.md)

## ARC-Core mapping

Every market tick becomes an *event*; every trade decision becomes a *proposal*;
every fill or outcome becomes a *receipt*; every risk limit is an *authority
gate*; every backtest is a *deterministic replay* of the event log. Full per-bot
mapping in [ECOSYSTEM.md](https://github.com/GareBear99/ARC-Core/blob/main/ECOSYSTEM.md#-trading-fleet--six-repos-one-event-spine).

## Sibling repos in the fleet

| Repo | One-liner | Docs site |
|---|---|---|
| [BrokeBot](https://github.com/GareBear99/BrokeBot) | TRON Funding-Rate Arbitrage (CEX, Python) | [https://garebear99.github.io/BrokeBot/](https://garebear99.github.io/BrokeBot/) |
| [Charm](https://github.com/GareBear99/Charm) | Uniswap v3 Spot Bot on Base (Node.js) | [https://garebear99.github.io/Charm/](https://garebear99.github.io/Charm/) |
| [Harvest](https://github.com/GareBear99/Harvest) | Multi-Timeframe Crypto Research Platform (Python) | [https://garebear99.github.io/Harvest/](https://garebear99.github.io/Harvest/) |
| [DecaGrid](https://github.com/GareBear99/DecaGrid) | Capital-Ladder Grid Trading Docs Pack | [https://garebear99.github.io/DecaGrid/](https://garebear99.github.io/DecaGrid/) |
| [EdgeStack Currency](https://github.com/GareBear99/EdgeStack_Currency) | Event-Sourced Multi-Currency Execution Spec | [https://garebear99.github.io/EdgeStack_Currency/](https://garebear99.github.io/EdgeStack_Currency/) |

## Upstream

- [ARC-Core](https://github.com/GareBear99/ARC-Core) — the event + receipt spine.
- [omnibinary-runtime](https://github.com/GareBear99/omnibinary-runtime) — any-OS runtime.
- [Arc-RAR](https://github.com/GareBear99/Arc-RAR) — archives + rollback.
- [Portfolio](https://github.com/GareBear99/Portfolio) — full project index.

---
*This page is auto-rendered from `docs/index.md` on the `main` branch. The
canonical source of truth is the repository README.*
