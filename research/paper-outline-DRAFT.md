# Detecting Pre-Exploit Reconnaissance on Dormant DeFi Contracts — DRAFT outline

**Status:** preliminary. Dataset has 2 entries; thesis is testable, not proven.
**Date:** 2026-10-17

## Thesis

Attackers probe before they strike. Those probes — small-value tests,
unknown selectors, intermediary contracts, metronomic batch calls against
dormant targets — have detectable on-chain signatures. A monitoring system
that records, traces, and classifies these probes can distinguish
reconnaissance from noise *before* value moves, and positions a whitehat
to win the rescue race when it does.

This is the defensive mirror of SCONE-bench: where SCONE measured whether
AI agents *can* exploit contracts, this work measures whether *humans can
see them coming*.

## Why this matters now

- Dormant contracts with live exploit paths are a standing inventory
  (Limit Break V2/V3, Rubic proxy Dec-2022 `routerCallNative`, others).
  They don't decay — they wait.
- The 0xQuit model (Sept 2026) proved rescues are winnable *if* someone is
  watching: defensive custody, revoke-gated claims, honest accounting.
  Watching without a taxonomy is just alerting; a taxonomy turns alerts
  into predictions.
- Existing monitoring is binary at the protocol level (paused/unpaused,
  exploit/no-exploit) — but *staging* detection exists inside vendor walls:
  Hypernative flagged the Kinetic Market staging 6 minutes before the first
  hack tx (Oct 31, 2024; $5M saved), Chainalysis/Hexagate detected the
  UwU Lend attack contract ~2 days before the June 10, 2024 exploit, and
  Forta raised three pre-exploit alerts in the Euler case. The recon phase
  is therefore *detected in practice but never published as an open
  taxonomy*: no vendor releases its probe-phase dataset, no independent
  audit exists of the vendor claims, and academic work stays post-factum
  (EtherClue) or static. The open gap is the labeled, falsifiable
  probe-phase dataset — which is what this paper builds. (Wormhole
  2026-10-17 evening; see paper-outline Related work for citations.)

## Related work

- **SCONE-bench** (Anthropic/MATS Fellows, Dec 2025): offensive capability
  measurement, dollar-denominated scoring, contamination controls. Our
  methodological model for honest measurement; our subject is the mirror
  image (detection, not exploitation).
- **0xQuit Limit Break rescue** (Sept 2026): the operational proof that
  monitoring + readiness = successful defensive custody. Our
  RESCUE-PLAYBOOK.md operationalizes this as a standing procedure.
- **SEAL / Safe Harbor**: the legal layer. Noted as a readiness gap —
  Limit Break has not adopted Safe Harbor, which bounds what an outside
  whitehat can do.
- **samczsun / SEAL**: the auditor-network disclosure model our practice
  follows.
- **Forta's attack kill chain** — Funding → Preparation → Exploitation →
  Money Laundering (Forta interview, sia.hackernoon.com): the industry
  already names the phases we taxonomize. In the Euler case Forta raised
  three alerts before the exploit (Tornado Cash funding, attacker contract
  creation, deployment from a TC-funded EOA) — and the $197M hack still
  happened. Detection without response is journalism; the rescue layer
  (§The rescue layer) is our answer to that specific failure.
  (sources: mpost.io Forta interview; sia.hackernoon.com)
- **Hypernative staging detection** — Kinetic Market (Flare, Oct 31,
  2024): staging detected 08:19:55 UTC at attacker-contract creation,
  alert 08:26:02 before the first hack tx, pause saved $5M. Parallel
  case: auto-pause "within seconds after the deployment transaction."
  Vendor claim: 98% of hacks detected >2 minutes before first transaction
  (hypernative.io platform page — self-reported, no third-party audit
  found; cryptoaimeta.com). The window those cases operate in is
  *minutes*; our dormant-target probes stretch over *days* (Limit Break
  metronomic batch, Aztec repeat targeting) — a different regime, with
  no protocol team left to pause. (sources: hypernative.io blog posts)
- **Chainalysis / Hexagate on UwU Lend** (June 10, 2024): attack contract
  detected ~2 days before the exploit; its connection to the victim
  contract was not immediately apparent. Two days is exactly the lead
  time our taxonomy predicts is exploitable by a third-party watcher —
  and the case documents the failure mode (detection without
  attribution). (source: chainalysis.com blog)
- **Decurity Time-to-Hack** (time-to-hack.decurity.io): measures
  deployment→exploit — the complementary axis to our probe→exploit.
  Supports the thesis: the >90-day bucket holds the most exploits; two
  attacker profiles, speed-driven (hours) vs strategic (patient, waits
  for liquidity, e.g. 1inch Settlement dormant 2+ years); median times
  falling 2020–2024. Our probe-phase dataset is the missing middle:
  what happens *between* deployment and exploitation.
- **Exploit datasets** (DeFiHackLabs, Web3Rekt, Univ. of Winchester
  20B-tx flash-loan study): label the exploit, never the staging. No
  public dataset of probe-phase transactions was found — the dataset IS
  the contribution.
- **Mempool erosion (caveat)** — Flashbots Protect routed 12M+ protected
  trades (~$27B) through private order flow that never touches the
  public mempool; staging detection leaning on public mempool sees less
  attacker flow over time (cryptoaimeta.com). Our polling watcher
  (state changes, not mempool) sidesteps this — a design advantage worth
  testing explicitly.

## Methodology

1. **Target selection:** dormant contracts with known exploit paths and
   non-zero residual exposure (approvals, TVL, or pause-gated risk).
2. **Monitoring:** read-only polling (`limitbreak_watch.py`,
   `rubic_tripwire.py`) with baselined state; alerts on new successful
   state-changing calls from unknown addresses.
3. **Tracing:** every alert gets a full receipt decode — what moved,
   whose signature authorized it, what the selector does (or doesn't
   resolve to).
4. **Classification:** automation | test | recon | exploit-attempt |
   unknown — with the evidence for and against each, stated plainly.
   Unknown is a valid classification, not a failure.
5. **Pattern book:** every event becomes a labeled entry
   (`pattern-book.md`). The dataset IS the contribution at this stage.

## Preliminary taxonomy (from 2 events — early, will move)

1. **Metronomic batch** — identical method, single sender, tight window.
   Reads as automation; the signature *against* exploitation.
2. **Custom-contract probe** — unknown selector via intermediary contract,
   small holder-authorized value. Indistinguishable from testing at n=1;
   the pattern to watch for repetition.
3. **Approval priming** — unlimited approval to a dormant contract with
   no immediate use. Standard DeFi UX *or* the setup move. Context decides.
4. *(predicted, not yet observed)* **Value escalation** — small test
   followed by larger follow-up from the same actor.
5. *(predicted, not yet observed)* **Multi-actor convergence** — distinct
   actors probing the same target in a short window.

## What would falsify or strengthen the thesis

- **Strengthens:** an actor graduates from probe patterns to value
  extraction; the taxonomy predicts the escalation before it happens.
- **Falsifies:** a year of probes with zero escalations (recon is rare;
  most anomalies are bots and testers), or an exploit with no detectable
  probe phase (the thesis's blind spot — some attacks won't telegraph).

## The rescue layer

Detection without response is journalism. The standing
RESCUE-PLAYBOOK.md (0xQuit model: confirm → coordinate → pause →
defensive custody → revoke-gated claims → honest accounting) is the
response half. A detected escalation triggers the playbook's
authorization gates — no third-party asset movement without the operator's
explicit yes.

## Limitations (stated up front, as the work demands)

- n=2. Everything taxonomic is preliminary.
- Read-only vantage: we see on-chain effects, not intent. Classification
  is inference, labeled as such.
- Selection bias: we monitor contracts we already suspect. Probes of
  *unknown-vulnerable* contracts are invisible to this system.
- Base chain degraded in our coverage (known gap).

## Expansion targets (next tracking candidates)

Criteria: dormant or semi-dormant, known or suspected exploit path,
residual exposure (approvals/TVL), monitorable via public RPC.

1. **Rubic proxy** (`‹addr redacted›`) —
   ALREADY TRACKED (rubic_tripwire.py, 2-min cadence). Dec-2022
   `routerCallNative`, USDC whitelisted, pause-gated, 123 historical
   approvals. Add its alerts to the pattern book when they fire.
2. **Limit Break V3 (ApeChain)** — ALREADY TRACKED. Sunset 2026-11-30;
   escalate scrutiny as the date approaches (abandoned contracts get
   bolder probers).
3. **Flooring Protocol** — 0xQuit ran the same defensive-custody model
   there (June 2026, 68 NFTs, $500K+). If the operator found it worth
   rescuing, it's worth watching for return visits.
4. **Permit2 allowance graveyard** — the scanner already enumerates
   Permit2 approvals (`permit2_enum.py`). Dormant high-value allowances
   to dead contracts are the same shape as the Limit Break exposure.
5. **Paus
...[truncated 1060 chars]