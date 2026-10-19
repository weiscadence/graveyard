# Pre-Exploit Recon Pattern Book

A labeled dataset of anomalous interactions with dormant DeFi contracts.
Each entry is a fully-traced event: what happened on-chain, how it was
classified, and what it teaches about pre-exploit behavior.

**Thesis under test:** attackers probe before they strike, and probes have
detectable signatures — small amounts, unknown selectors, intermediary
contracts, metronomic batch patterns. This book collects the evidence.

**Entry schema:**
- `id`: RECON-YYYYMMDD-NN
- `detected`: when the monitor flagged it (UTC)
- `chain` / `target`: which contract was touched
- `actor`: sender address(es)
- `pattern`: batch | custom-contract | other
- `trace`: what the calls actually did (decoded)
- `value_moved`: native + token amounts
- `classification`: automation | test | recon | exploit-attempt | unknown
- `assessment`: honest read — what this does and doesn't establish
- `txs`: transaction hashes

---

## RECON-20261017-01 — Metronomic batch probing (Polygon)

- **Detected:** 2026-10-17 ~10:35 CDT (15:35 UTC) via limitbreak_watch.py
- **Chain / target:** Polygon, Limit Break Payment Processor V2
  (`‹addr redacted›`)
- **Actor:** `0x0e3be59981` (single sender, all 62 calls)
- **Pattern:** batch — 62 identical `forwardCall(address,bytes)` calls,
  11:48–12:03 UTC (15-minute window)
- **Trace:** uniform method, uniform sender, no variation in call shape
  across all 62 transactions
- **Value moved:** 0 native on every call (token-level effects not traced;
  uniformity suggests none material)
- **Classification:** automation (keeper / sweeper / test harness)
- **Assessment:** Metronomic regularity is the signature *against*
  exploitation — real exploits vary targets and move value. This reads as
  a bot doing routine operations. Flagged because 62 identical calls to a
  dormant processor in 15 minutes is anomalous regardless of intent.
- **Txs:** 62 hashes; example `0x1a024983aac7...` (full list in monitor
  run log 2026-10-17 morning)

## RECON-20261017-02 — Custom-contract interaction, unknown selector (Polygon)

- **Detected:** 2026-10-17 18:36 CDT (23:36 UTC) via limitbreak_watch.py
- **Chain / target:** Polygon, via intermediary
  `‹addr redacted›` (deployed contract,
  ~4KB bytecode) interacting with monitored V2
  (`‹addr redacted›`)
- **Actor:** `‹addr redacted›`
- **Pattern:** custom-contract — single call, selector `0xf3858db3`,
  not present in public signature databases (OpenChain lookup null)
- **Trace (fully decoded from receipt):**
  - ~0.0102 WETH (10,235,275,359,896,058 wei; WETH = 18 decimals,
    `‹addr redacted›` verified on-chain as
    "Wrapped Ether") moved `0xef4993567e` → `0x72f1ffe8d8...` →
    `0xebb40d6ca3` (~$35 at the time)
  - Unlimited WETH approval granted by `0xef4993567e` to the monitored
    V2 contract (2^256 − 1)
  - Several zero-amount transfers/approvals on a second token contract
    (`‹addr redacted›`, non-standard ERC20)
- **Value moved:** ~$35 WETH. No funds left the authorizing party's
  control without their signature.
- **Classification:** unknown (recon | whitehat probe | integration test —
  indistinguishable from one transaction)
- **Assessment:** This is the pattern that matters for the thesis. Unknown
  selector + intermediary contract + dormant target = the shape of
  pre-exploit reconnaissance *and* the shape of legitimate testing. The
  $35 scale and holder-authorized flow rule out theft; they do not rule
  out recon. One data point cannot distinguish. That is why the book
  exists — the second, third, tenth such event is where the pattern
  either emerges or dissolves.
- **Txs:** `‹tx redacted›`
  (block 95708144, 2026-10-17T20:06 UTC)

---

## Pattern taxonomy (emerging)

| Pattern | Signature | Seen |
|---|---|---|
| Metronomic batch | Identical method, single sender, tight window, zero value | RECON-20261017-01 |
| Custom-contract probe | Unknown selector, intermediary contract, small value, holder-authorized | RECON-20261017-02 |
| Approval priming | Unlimited approval to dormant contract, no immediate use | (component of -02) |
| Value escalation | Small test → larger follow-up from same actor | not yet observed |
| Multi-actor convergence | Distinct actors probing same target in one window | partial (-01 and -02 same day, same target) |

## Watchlist for escalation

The following would promote an entry from "unknown" to "likely recon":
1. Same actor returns with larger amounts
2. Approval granted in -02 gets exercised beyond holder intent
3. Calls touch known-sensitive paths (e.g. `routerCallNative`-equivalents)
4. New actors join the same target within 72h
5. Selector `0xf3858db3` appears against other dormant contracts

## RECON-20261017-03: Multi-actor convergence (Limit Break Polygon V2)
- **Date:** 2026-10-17. **Target:** Payment Processor V2, Polygon (‹addr redacted›).
- **Events:** 3 distinct actors in one day. (1) 62x forwardCall batch (automation, not probe). (2) $35 WETH via custom intermediary, unknown selector 0xf3858db3. (3) ~40.8 tokens via different intermediary, transfer(address,address,address).
- **Key finding:** Both probes emitted BuyListingERC721 + NonceInvalidated (keccak-confirmed from public repo) = real buyListing settlement fills. Both used operator-owned mock collections (seller = own contract) = exploit development phase, not targeting real victims.
- **Actor linkage:** Different wallet profiles (3349 vs 57 txs), different intermediary bytecode → likely independent. Converging attention on same dormant target.
- **Exposure inventory:** 94 interacting wallets scanned via Alchemy; 0 with live V2 approvals. 90-day settlement history dormant. Polygon V2 assessed as dry well.
- **Detection rule derived:** settlement function + operator-owned collection = TESTING; settlement function + established collection = TARGETING. Encode in monitors.
- **Taxonomy:** multi-actor convergence (confirmed). Test-before-strike (confirmed, 4th data point alongside Ostium/NEAR/UNCX).
