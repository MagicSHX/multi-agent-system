# Gamified Trading Cards
**Pluang Markets · Internal** | Project Proposal · June 2026 · v0.1 Draft · Confidential

*FIFA-style trading personality cards that turn each user's real trading history into a shareable, gamified profile — driving financial literacy, positive trading behaviour, and organic social growth*

---

## Problem Statement

As a multi-asset platform offering **Crypto (~1,000 assets), Digital & Physical Gold (XAU/IDR), and FX (USD/IDR)**, the firm holds rich data on how every user actually trades — yet users receive **no feedback on their own behaviour**. Most retail users trade without understanding their patterns: they chase pumps, panic-sell, over-concentrate, or sit dormant, with no mirror held up to reflect what they are doing or how to improve. There is currently **no engaging mechanism** to teach users about the markets, nudge them toward healthier trading habits, or give them a reason to share the platform with friends. The result is low financial literacy, weak retention, and minimal organic growth. **Education delivered as dry content does not land** — it needs to be personal, visual, and fun. Most people think they know their own trading behaviour and patterns. However, reality might be different. This 
trading analytics engine will come in very handy for our users.

---

## Context

The system generates a personalised, FIFA-style **trading card** for each user — a single shareable graphic carrying an overall rating, a play-style archetype (e.g. *High-Conviction Accumulator*, *Conservative*), behavioural trait tags (e.g. *Lets winners run*, *Stock heavy*, *Concentrated*), and headline stats (win rate, win/loss ratio, assets held, trades/week, open losers, top-up trends).

Producing each card requires a pipeline of analysis from **BigQuery tables of user trades** plus **latest market news**, orchestrated as a **multi-agent workflow**. At a high level, we need to:

— compute per-user trading metrics from BQ: win rate, win/loss, holding periods, concentration, dormancy, top-up flows
- derive the overall rating + archetype, benchmark the user against cohorts, contextualise with market news
- translate metrics into plain-language insights, trait tags, and educational nudges
— design the shareable card visual and the social mechanics (sharing, friend comparison, leaderboards) to drive organic reach

Asset coverage spans all products users actually trade — Crypto, Gold (XAU/IDR), and FX (USD/IDR), all denominated in **IDR**.

---

## Notes

- **Education is the goal, gamification is the vehicle.** The card exists to make users more informed and more deliberate traders — ratings and archetypes are the hook, the insights are the payload.
- **Encourage positive behaviour.** Scoring and trait design should reward healthy habits (diversification, discipline, letting winners run) and gently flag risky ones — never shame users or incentivise overtrading.
- **Built to be shared.** The card is a marketing asset by design: friend comparison, leaderboards, and one-tap social sharing turn each user into a distribution channel.
- **Multi-agent design.** Two data analysts split the work — one on behavioural metrics, one on scoring and market context — feeding a writer and a marketing agent. Each agent is independently runnable.
- **Metrics must be explainable.** Every number and tag on a card must trace back to a defined BQ query and a transparent scoring formula — no black-box ratings.
- **Privacy & accuracy first.** Cards expose a user's own data only; shared cards must never leak position sizes or balances, and every stat must be verified before it reaches a user.

---

*Gamified Trading Cards · Project One-Pager · Confidential · June 2026*