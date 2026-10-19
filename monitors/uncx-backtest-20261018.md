# UNCX monitor backtest — 2026-10-18

**Question:** would `uncx_watch.py` have fired on the real October 14–15, 2026
VestingManager V2 exploit?

**Answer: no — on the Ethereum leg, and the reason is the data source, not the
classifier.**

## Method

Paged the full direct-tx history of the Ethereum V2 contract
(`‹addr redacted›`) from eth.blockscout.com
(newest first, cursor pagination, 2 pages, ~124 txs, complete per
`next_page_params`), filtered to the incident window 2026-10-14T00:00Z–
2026-10-16T12:00Z, grouped by wallet, and ran the monitor's own
`is_exploit_sequence()` (create+release+cancel within 24h) over each wallet.
Repro: `/tmp/uncx_backtest.py` (imports the detector from `uncx_watch.py`).

## Findings

1. **Zero exploit-shaped direct activity.** In-window: exactly 2 txs, both plain
   `release(uint256)` from `0x70473891255e` (11:54:47Z and 11:55:23Z Oct 14) —
   a wallet doing routine releases since Sep 13. The monitor correctly ignores
   them (no create/cancel family present). No false positive.
2. **`cancel()` has never been called directly on this contract.** Full history:
   `release` × ~120, `createVesting` × 16, `transferVesting` × 2,
   `transferOwnership` × 1, `cancel` × 0. The exploit's core step is
   `cancel()` — so every incident cancel was an *internal* call.
3. **Inference (marked): the attacker routed through their own contract.**
   Consistent with all evidence; not directly confirmed (archive-gated RPCs
   block the eth_getLogs check that would prove it — publicnode requires a
   token for blocks that old).

## The blind spot

`uncx_watch.py`'s Ethereum leg polls the Blockscout **tx list** — direct
`to`/`from` only. Contract-routed attacks are invisible to it. The Base/BNB
legs already use `eth_getLogs` (event-based), which fires regardless of
caller. The Ethereum leg must move to logs too.

**Prescribed fix:** switch the Ethereum leg from Blockscout tx-list to
`eth_getLogs` on the V2 address (Etherscan proxy API + vault key covers
Ethereum on the free tier; events needed: vesting-created / released /
cancelled). The `donate` step is a plain ERC-20 transfer *into* V2 — visible
only in token logs, not V2's; the detector's create→release→cancel triple
remains the alertable shape.

## General lesson (pattern-book candidate)

"The attacker never touches the target directly." Tx-list polling misses
contract-routed attacks by construction. Event/log monitoring is the robust
primitive for zombie-contract defense; tx lists are a convenience feed, not a
security feed.

## Status

Finding only — no monitor code changed. Fix proposed to the trio on the wire
2026-10-19T01:5xZ; implementation pending review.
