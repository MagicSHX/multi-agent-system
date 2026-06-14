# Circuit Breaker System
**Acme Markets · Internal** | Project Proposal · June 2026 · v0.1 Draft · Confidential

*Automated price surveillance, trade halts, and withdrawal controls across Crypto, Gold, and FX — built on an event-driven architecture*

---

## Problem Statement

As a multi-asset market maker offering **Crypto (~1,000 assets), Digital & Physical Gold (XAU/IDR), and FX (USD/IDR)** trading through a proprietary app platform, the firm operates in markets with vastly different volatility profiles — from 24/7 crypto with thin liquidity windows, to macro-sensitive FX and safe-haven gold demand spikes. Today, there is **no automated mechanism** to detect abnormal price movements or user behaviour and respond before cascading losses occur. A single volatile event can expose the platform to unhedged market-making risk, trigger irrational user behaviour, and result in regulatory and reputational damage. **Manual intervention is too slow** and operationally unsustainable at scale.

---

## Context

The firm runs an existing Kafka-based infrastructure with real-time streams for price data (mid, bid, ask per asset) and user trade executions. All prices are denominated in **IDR**. The circuit breaker system will be built as a **multi-agent, event-driven service** that consumes from these Kafka topics, evaluates configurable risk rules, and publishes enforcement decisions back to Kafka for downstream services (order management, withdrawals, notifications) to act on.

Asset coverage:
- **Crypto** — ~1,000 assets, 24/7, all quoted in IDR
- **Gold (XAU/IDR)** — combined digital & physical gold product; subject to safe-haven demand spikes and physical redemption volume surges
- **FX** — USD/IDR only at this stage

Enforcement actions in scope: `Trade Halt` `Withdrawal Freeze` `Spread Widening` `Reduce-Only Mode` `Quote Suspension` `Compliance Flag`

---

## Notes

- **No hard latency requirement.** Correctness and reliability take priority. A brief delay in enforcing a breaker is acceptable; a missed or incorrect enforcement is not.
- **Event-driven, not polling.** All detection and enforcement flows through Kafka — no scheduled jobs or database polling for the critical path.
- **Multi-agent design.** Separate agents handle price monitoring, asset-level breakers, user-level risk, and platform-wide exposure — each independently subscribable and deployable.
- **Gold is a hybrid product.** Circuit breaker rules must account for both the digital trading side and physical redemption behaviour, which have different risk profiles.
- **FX scope is narrow for now.** USD/IDR is the only pair; architecture should allow easy addition of further pairs later.
- **Audit trail required.** All breaker events (triggered, active, resolved) must be persisted to the database for compliance and post-incident review.

---

*Circuit Breaker System · Project One-Pager · Confidential · June 2026*