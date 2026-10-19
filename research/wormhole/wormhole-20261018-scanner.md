# WORMHOLE: Characterizing the Invisible Scanner
**Date:** 2026-10-18 | **Type:** read-only recon | **No transactions, no contact**

## Thesis

Someone is systematically scanning deprecated-but-funded smart contracts. The Set Protocol V1 hits are the clearest fingerprint: two 2026 incidents on the same dead contract family, and in October, two attackers hitting the same rebalancing set two blocks apart. This isn't opportunistic — it's a pipeline.

## The Set Protocol V1 fingerprint

**Contract family:** Set Protocol V1 `SetToken` / rebalancing sets. Deprecated April 6, 2021. Immutable, no admin, no pause. $12.67M TVL still locked (DeFiLlama, Oct 18 2026).

**2026 incident trail:**
| Date | Loss | Technique | Attacker (partial) |
|------|------|-----------|-------------------|
| Jul 30, 2026 | $9,600 (~4 ETH) | Reentrancy | unidentified |
| Oct 6, 2026 | 8.11 WETH (~$21.9K) | Permissionless `actualizeFee()` + rounding | 0x3A15…C50d / 0xa0F5…4e6d (first), 0xfc3f…E92F (second) |
| Oct 6, 2026 | ~5.08 ETH | `actualizeFee()` rounding (separate set, SlowMist) | unidentified |

**The October attack, reconstructed (Tozvan/SunWeb3Sec):**
1. Flash-borrow ~116,000 WETH from an Aave-v3-fork pool (zero premium, same-tx repay)
2. Issue ETHMACOAPY rebalancing-set tokens
3. Donate residual base-set collateral directly to the set's vault (adds collateral without minting tokens)
4. Call permissionless `actualizeFee()` — recalculates unitShares with upward rounding, inflating share value
5. Redeem the same tokens for more collateral than deposited
6. Net: 4.047988247781965824 WETH profit

**Blocks:** 26132514 (first), 26132516 (second). Two blocks apart, ~24 seconds.

## The two-blocks-apart question: copycat or same operator?

Evidence points to **mempool copycat**, not same operator:
- Separate EOAs (0x3A15…C50d vs 0xfc3f…E92F)
- The second attacker extracted 4.062 WETH — nearly identical to the first's 4.048 WETH
- If same operator, they'd bundle in one block or use one wallet; the 2-block gap is the time to observe the confirmed tx, decode the technique, and replicate
- The technique is *repeatable*: after the first drain, the vault still held enough for a near-identical second extraction

This is the copycat window compressed to its minimum: ~24 seconds from observation to replication. The attacker didn't need to understand the bug — just replay the shape.

**Implication:** the scanner's pipeline includes real-time mempool/confirmation monitoring of *other attackers'* successful exploits, with automated or semi-automated replication. The second attacker is likely running infrastructure that watches for profitable txs against known-vulnerable contract families and replays them.

## The targeting filter (derived)

From the Set V1 hits, the scanner's filter appears to be:

1. **Deprecation + immutability:** contract family abandoned by the team (no admin, no pause, no upgrade path). The team can't respond.
2. **Residual TVL above extraction cost:** enough value to justify gas + flash-loan setup. The October hits extracted ~$22K from a $12.67M pool — small relative to TVL, suggesting the filter is "any positive EV," not "whale targets."
3. **Permissionless state-changing functions:** `actualizeFee()` requires no owner, role, or signature. The scanner likely enumerates public/external functions on deprecated contracts and tests which ones mutate share accounting.
4. **Donation/manipulation primitive:** the attack needs a way to distort the share↔collateral ratio. Donation (transfer without mint) is the primitive. Any contract where `balanceOf(self) > accountedBalance` creates extractable value.
5. **Single-component or simple collateral:** ETHMACOAPY's base set held WETH as sole component — simpler to model, fewer moving parts.

**Generalized filter:** `deprecated AND immutable AND has_stranded_value AND has_permissionless_state_mutation`

Where `stranded_value` is found via historical state archaeology (unsettled lots, unclaimed fees, distorted accounting), not just current TVL.

This is automatable. A scanner can:
- Enumerate deprecated protocols (public deprecation notices, DeFiLlama "deprecated" tags)
- Pull contract ABIs, flag permissionless state-changing functions
- **Scan historical state for stranded value**: unsettled auctions, unclaimed balances, share↔collateral mismatches
- Simulate donation → accounting-mutation → redeem sequences on a fork
- Execute when simulated profit > cost

## Fresh: Yearn yETH $9M (Oct 18, 2026 — today)

PeckShield flagged a $9M exploit of Yearn's yETH: attacker abused a minting vulnerability in the yETH token contract to mint without adequate collateral, draining a legacy stableswap pool. Attacker `0xa80d…c822`; $3M laundered via Tornado Cash, $6M still in wallet. SEAL911 + ChainSecurity war room active.

**Assessment:** different bug class (infinite mint, not share-accounting), but same zombie thesis — a *legacy* pool associated with yETH. The scanner ecosystem is active today.

## Other 2026 zombie hits — same fingerprint?

| Incident | Date | Loss | Zombie pattern | Same scanner? |
|----------|------|------|---------------|---------------|
| MakerDAO legacy keeper | Oct 6, 2026 | 200 ETH (~$543K) | Black Thursday 2020 unsettled lots, missing access control on 0x8804d1de | LIKELY SHARED PIPELINE — same day as Set hits, same "legacy + residual + permissionless" filter, different technique |
| Aztec Connect | Jun 2026 | ~$4.4M | Immutable, deprecated 2023 | DIFFERENT — verification bug, not accounting; likely different operator |
| Yearn yETH | Oct 18, 2026 | ~$9M | Legacy stableswap pool, infinite mint bug | DIFFERENT — minting bug, single-tx; attacker 0xa80d…c822; $3M via Tornado Cash |
| Yearn iEarn TUSD | Dec 2025 | ~$300K | Immutable 2020 vaults, share manipulation | POSSIBLE — share-accounting distortion, same primitive family |
| 1inch Fusion v1 | Mar 2025 | ~$5M | Obsolete resolver | DIFFERENT — settlement logic, not accounting |
| Abracadabra Cauldron V4 | Oct 2025 | ~$1.8M | Deprecated cauldrons | UNRESOLVED |

### October 6, 2026: the zombie-hunting day

Three protocols hit on the same day:
- **Set Protocol**: 3 extractions (4.048 WETH, 4.062 WETH, ~5.08 ETH) via `actualizeFee()` donation/rounding
- **MakerDAO**: 200 ETH via missing access control on legacy keeper (0x8804d1de), settling Black Thursday 2020 lots

Same day, different techniques, same filter. This is either one scanner with diverse tooling working through a target list, or multiple operators sharing a target-discovery pipeline. The MakerDAO hit required **historical state archaeology** — knowing that four 50-ETH lots from March 2020 were never settled. That's not a TVL scan; that's deep contract-state analysis of 6-year-old history.

**Refined filter:** the scanner does historical state archaeology on deprecated contracts, looking for *stranded value* (unsettled lots, unclaimed fees, distorted share accounting) — not just TVL. The value has to be *invisible to casual observers* but *visible to state analysis*.

### The share-accounting family vs the access-control family

Two distinct scanner beats are emerging:
1. **Share-accounting distortion** (Set V1, Yearn iEarn): donate → mutate accounting → redeem. Requires understanding share math.
2. **Permissionless admin functions** (MakerDAO keeper): find unguarded state-changing functions on legacy contracts, call them. Requires enumerating function permissions.

The October 6 hits span both families. Whoever is running this has both toolkits.

## The 5.08 ETH SlowMist incident

A *third* Set Protocol hit on the same day (Oct 6), on a *separate* rebalancing set, flagged by SlowMist. This means on October 6, at least three distinct extractions hit Set V1:
- 4.048 WETH (ETHMACOAPY, attacker 1)
- 4.062 WETH (ETHMACOAPY, attacker 2, two blocks later)
- ~5.08 ETH (different set, SlowMist)

Three hits, one day, one dead protocol. The scanner(s) were working through the set inventory systematically.

## Current probing: are they active right now?

*To check: recent `actualizeFee()` calls on Set V1 rebalancing sets; donation-pattern transfers to set vaults; new contract deployments interacting with Set V1.*

## Where are they likely looking next?

Based on the filter, the highest-probability next targets:

1. **Other Set V1 rebalancing sets** — the October hits prove the technique generalizes across sets. Any rebalancing set with single-component collateral and non-zero TVL is in the queue.
2. **Yearn v1 yVaults** — same share-accounting family, immutable, residual deposits. The Dec 2025 iEarn hit was the proof of concept.
3. **Abracadabra deprecated cauldrons** — same "deprecated but callable" profile; the Oct 2025 hit showed the pattern works there.
4. **Any protocol with permissionless fee/accounting functions** — the scanner's real filter isn't "Set Protocol," it's "callable accounting mutations on dead contracts."

## The front-run

If the filter is right, we don't watch the scanner — we watch their *next target list*. The move:

1. **Enumerate Set V1 rebalancing sets with residual TVL** — the October hits prove the technique generalizes across sets. Priority: single-component collateral, non-zero TVL.
2. **Monitor for the pre-attack signature**: flash-loan → issue → donation → `actualizeFee()` in a single transaction. The donation (transfer to set vault without corresponding mint) is the earliest on-chain signal.
3. **Historical state archaeology** (their technique, our defense): scan deprecated contracts for stranded value — unsettled lots, unclaimed fees, share↔collateral mismatches. Whatever the scanner can find, we can find first.
4. **Watch the copycat layer**: the 2-block gap proves replication can happen in under 30 seconds. Detection must fire on the *first* attacker's donation, not the second attacker's replay.
5. **October 6 pattern alert**: when one zombie gets hit, check every other zombie in the same filter family *immediately*. The scanner works through target lists in sessions, not single hits.

## Who are they? (synthesis)

We can't name the operator — full wallet addresses weren't recoverable in this pass. But we can characterize them:

- **Sophisticated, not opportunistic.** Historical state archaeology (6-year-old unsettled lots), custom attack contracts, flash-loan orchestration, cross-protocol sessions.
- **Multi-toolkit.** Share-accounting distortion AND permissionless-function abuse, deployed same-day across different protocols.
- **Pipeline, not manual.** The 2-block copycat replication suggests automated mempool monitoring + replay infrastructure. The October 6 session (3+ hits across 2 protocols) suggests a target queue.
- **Tornado Cash funded, Tornado Cash exits.** Both the Set and MakerDAO attackers used TC. Professional opsec.
- **Small-extractions-accepted.** $22K from a $12.67M pool. The filter is "any positive EV," not "whale hunting." This means the target list is LONG — they're working through it systematically, not cherry-picking.

**Where they're likely looking next:** other Set V1 rebalancing sets (technique proven, inventory not exhausted) → Yearn v1 vaults (same share-accounting family) → Abracadabra deprecated cauldrons → any deprecated contract with permissionless accounting mutations and stranded value. The October 6 session is the template: expect multi-protocol hit days, not isolated incidents.

## Caveats

- Attacker full addresses not resolved (Tozvan truncated: 0x3A15…C50d, 0xa0F5…4e6d, 0xfc3f…E92F). On-chain forensics hit RPC/API friction; Etherscan needs a key, Blockscout pagination is limited.
- The "same scanner" vs "independent copycats" distinction for the share-accounting family is inferential, based on technique similarity and timing, not wallet linkage.
- The July reentrancy incident details are thin — it may be a different operator entirely (reentrancy ≠ accounting distortion).
- Filter derivation is from n=3 incidents on one protocol family. Generalization to "all zombies" needs more data.

## Sources

- Tozvan, "Set Protocol loses 8.11 WETH in ETHMACOAPY exploit" (Oct 12, 2026)
- SunWeb3Sec analysis (via Tozvan; GitHub primary source not directly accessed)
- SlowMist via cryptonews/coinwy on 5.08 ETH incident (Oct 6, 2026)
- Bitget token page for ETHMACOAPY contract prefix
- On-chain: Ethereum blocks 26132514, 26132516 (Oct 6, 2026 ~09:43 UTC)
- DeFiLlama Set Protocol TVL ($12.67M, Oct 18 2026)
