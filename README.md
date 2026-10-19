# graveyard

**A defensive map of an attack surface that standard taxonomies cannot see.**

Dormant DeFi contracts with stranded value — deprecated, immutable, unpausable,
but still funded and still callable — are an unmapped attack surface. Exploit
databases have **no "zombie contract" category**: the class is invisible in the
standard taxonomies, so the risk is systematically under-counted. This repo is
the defensive response: live detection monitors, the whitehat rescue
methodology, and the research behind the pattern of the race.

**Thesis.** Pre-exploit reconnaissance against dormant contracts is *detectable*,
and detecting it buys the only thing that matters once a contract is already
frozen and immutable: **time**. The copycat window after a first exploit is
short — often hours, sometimes a single block (~24s). Nothing here prevents an
exploit. Everything here exists to see the race start and spend that window
well: warn holders, trigger a whitehat rescue, raise the next alarm.

## What this is

- **Detection** — read-only, keyless watch scripts that fingerprint known
  exploit patterns and flag anomalous activity on dormant contracts.
- **Rescue** — whitehat response playbooks (the 0xQuit / SEAL-911 model):
  how to detect, classify TESTING-vs-TARGETING, and respond — never mainnet-first.
- **The pattern of the race** — the pre-exploit recon taxonomy, the copycat-window
  finding, the "disclosure accelerates the wave" finding, and the research notes
  that produced them.

## What this is NOT

- **Not a target list.** The live watchlists — which specific contracts and
  wallets are at risk right now — are intentionally **withheld**. Every
  `*-targets.json` here is a `*-targets.example.json` schema with placeholder
  addresses. Point the monitors at your own authorized targets.
- **Not a how-to.** There is no exploit code, no step-by-step against any live
  contract. Specific still-live addresses, victim wallets, and residual-exposure
  figures are redacted (`‹addr redacted›` / `‹wallet redacted›`). See
  [RESPONSIBLE-DISCLOSURE.md](RESPONSIBLE-DISCLOSURE.md).
- **Not a shield.** Polling cadence is minutes, not blocks. These tools *record*
  and *early-warn*; they cannot front-run an exploit in flight.

## Monitors (`monitors/`)

Read-only. No transactions, no private keys, no API keys (free public RPCs with
rotation; see `rpc_rotation.py`). **Every monitor states what it cannot see.**

| script | watches | stated blind spot |
|---|---|---|
| `uncx_watch.py` | Vesting V2 create→release→cancel accounting pattern (multi-chain) | contract-routed (intermediary) calls are invisible to tx lists; Robinhood Chain has no public RPC |
| `limitbreak_watch.py` | Payment-processor settlement calls, classified TESTING vs TARGETING | cannot see private orderflow; mock-vs-real is a heuristic |
| `setv1_watch.py` | permissionless `actualizeFee()` rounding fingerprint | 30-min polling cannot beat a ~24s copycat; private submission gives zero warning |
| `blast_snapshot.py` | pre-shutdown bridge balances (baseline for later anomaly detection) | a snapshot is not a stream; bridge addresses are operator-supplied |
| `zerolend_snapshot.py` | withdrawal-only markets on dead/exited chains | dead-chain RPCs are flaky; pool addresses are operator-supplied |
| `aztec_proxy_watch.py` | frozen rollup proxy upgrade/admin events (any event is anomalous) | only sees `Upgraded`/`AdminChanged`; target proxy is operator-supplied |
| `classifier_canary.py` | canary tests for the settlement classifier vs known ground truth | tests logic, not live coverage |

```bash
cd monitors
python3 classifier_canary.py   # 7/7 against October 2026 ground truth
python3 uncx_watch.py          # reads uncx-targets.example.json; exit 0 = clean, 2 = alert
```

The monitors read their targets from `*-targets.example.json`. **The live
watchlists are not published** — copy the example, fill in contracts you are
authorized to monitor.

## Research (`research/`)

- `pattern-book.md` — the pre-exploit recon taxonomy (metronomic batch,
  custom-contract probe, approval priming, value escalation, multi-actor
  convergence). Each pattern has a detection rule and a falsification criterion.
- `paper-outline-DRAFT.md` — thesis, the defensive mirror of benchmark-style
  evaluation, limitations up front. DRAFT means draft.
- `wormhole/` — dated research notes: copycat dynamics, EIP-7702 delegation
  abuse, MEV amplification, scanner characterization, kill-chain modeling,
  fraud-industry parallels, whitehat methodology and ecosystem. Specific live
  targets are scrubbed; mechanisms and findings are kept.

## Playbooks (`playbooks/`)

`RESCUE-PLAYBOOK.md`, `POLYGON-RESCUE-PLAYBOOK.md` — whitehat defensive
methodology only: detect, classify, respond. Specific exploitable targets and
victim wallets are redacted; the method stays.

## Honest status

- Monitors are detection-only; none can front-run an exploit.
- Coverage gaps are documented in the scripts (archive gating, no-public-RPC
  chains, intermediary-routed calls invisible to tx lists).
- Research marked DRAFT is draft. The paper is not finished.
- Every claim names the command that would falsify it; canary inputs with known
  answers gate every "zero findings."

## License

MIT (see [LICENSE](LICENSE)). Built by Jiggy's AI agents — **Cadence**,
**Aperture**, and **Lodestone** — directed by **Jiggy**. Every monitor states
its blind spot.
