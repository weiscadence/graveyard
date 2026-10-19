# Wormhole Thread 3 — Test-Before-Strike Retro
**Date:** 2026-10-18 · **Mode:** read-only research (no transactions, no accounts, no spending, no contacts)
**Question:** Does the "small test transaction before the main strike" pattern generalize beyond Ostium / NEAR Intents / UNCX / Limit Break-Polygon?
**Method:** Work backwards from 3 famous 2025–2026 exploits; look for attacker-wallet activity in the 7 days before the strike via post-mortems and forensic write-ups. No chain queries run — all findings are from published forensics.

---

## Case 1 — Cetus (Sui), May 22, 2025, ~$220–230M ✅ TEST FOUND

**Attacker:** Sui `‹tx redacted›`
(Cetus official incident report; SlowMist)
**Vector:** arithmetic overflow in `checked_shlw` (integer-mate lib) — flash loan 10,024,321.28 haSUI, crash pool price, mint outsized liquidity for ~1 token.

**Test evidence (SlowMist, May 24, 2025, MistTrack on-chain tracing):**
> "We found that the attacker prepared the Gas Fee **two days in advance** and made an **attempt before the actual attack, but it failed**."

- **What:** gas funding ≈ May 20, 2025 + one failed attack attempt before May 22.
- **When:** ~48 hours before the strike (attack began ~10:30 UTC May 22, 2025).
- **Where published:** slowmist.medium.com "SlowMist: Analysis of the $230 Million Cetus Hack" (line: "prepared the Gas Fee two days in advance and made an attempt before the actual attack, but it failed"); repeated in SlowMist's chaincatcher/bitget analyses.

**Gaps:** The failed attempt's tx hash/amount aren't visible in text form (they were screenshots in the SlowMist article). So: *test confirmed, details partial.*

This is the cleanest match to the pattern of the four seed cases — and notably a **failed** dry run, like Ostium-style probes that don't always succeed on the first try.

---

## Case 2 — Bybit (Feb 21, 2025, ~$1.4–1.5B, Lazarus/TraderTraitor) ⚠️ PARTIAL / AMBIGUOUS

**Attacker:** Lazarus Group (FBI-attributed as TraderTraitor); drain address `0x47666Fab…86E2`; 51 FBI-listed laundering addresses.
**Vector:** NOT an on-chain protocol exploit — supply-chain/infra attack. Lazarus compromised a Safe{Wallet} developer's macOS (Feb 4) → AWS session tokens (Feb 5–17) → injected malicious JS into the Safe front-end S3 bundle on **Feb 19, 2025, 15:29:25 UTC** → triggered during Bybit's routine cold→warm transfer on **Feb 21, 2025, 14:13:35 UTC** → JS reverted to clean ~2 min later.

**"Test transactions" evidence — second-hand only:**
Arkham's bounty announcement (Feb 21, 2025): "His submission included a **detailed analysis of test transactions and connected wallets used ahead of the exploit**, as well as multiple forensics graphs and timing analyses."
Multiple outlets (block.cc, coinstats/coinpedia, cryptonews.net, mitrade, newshawk.ai) quote this and gloss it as "Lazarus first made small test transactions before launching the full attack."

**Calibration — what this does NOT prove:**
1. The *primary source* (Arkham's post / ZachXBT's submission) gives no amounts, dates, or tx hashes in anything publicly retrievable. I could not find a breakdown of these test transactions.
2. The most plausible reading from context: ZachXBT used **small transfers between Lazarus-controlled wallets** to link the Bybit wallets to the Phemex hack (Jan 2025) and other Lazarus activity. These are **operational linkage transfers**, not protocol dry runs.
3. This attack class **cannot be meaningfully "tested" against the target** — the injected JS was gated to fire only on Bybit's specific cold wallet. A dry run would have been the strike. The 2-day gap between JS injection (Feb 19) and trigger (Feb 21) was the attackers **waiting for Bybit to initiate a routine transfer**, not a rehearsal.
4. So: **test-like transfers confirmed second-hand; protocol-level test = not applicable to this attack class.** The "test" vocabulary collapses two different things (wallet opsec transfers vs exploit rehearsal).

**Post-strike note:** Lazarus's laundering itself was heavily test-shaped (small THORChain/DEX hops before large moves, per later tracing) — consistent with the pattern that test transfers reappear at the cashout phase.

---

## Case 3 — Balancer V2 (Nov 3, 2025, $116–128M) ❌ PRE-STRIKE TEST NOT FOUND

**Attacker chain (Check Point research):**
- Exploit Deployer: `‹addr redacted›`
- Attack Contract: `‹addr redacted›`
- Final Recipient (Exploiter 2): `‹addr redacted›`

**Vector:** rounding error in `_upscaleArray` / EXACT_OUT swaps in Composable Stable Pools. The attack ran **atomically inside the exploit contract's constructor** — 65 three-phase swap cycles (boundary adjustment → precision-loss trigger → BPT extraction) in a *single deployment transaction*.

**Prep evidence (this is funding opsec, not a protocol test):**
- Attacker seeded via **100 ETH parked in Tornado Cash** plus small **0.1 ETH withdrawals** to fund the deployer (Conor Grogan, Coinbase). Grogan: "Since there were no recent 100 ETH Tornado deposits, likely that exploiter had funds there from previous exploits."
- Cointelegraph/cryptonews: "extensive preparation that may have taken months" — but that inference rests on funding opsec and exploit sophistication, not on observed mainnet probes.

**Test findings:**
- **Pre-strike protocol probe: none reported.** I checked Balancer's official post-mortems (Nov 5, Nov 18, 2025), Check Point's dissection, Phalcon's forensics, SlowMist's coverage, and the BIP-908 recovery forum thread. None mention any small-value or zero-value calls to Balancer vaults from the attacker wallets in the days before Nov 3.
- **Post-strike tests exist but don't count:** Arkham tracked ~1 ETH test transfers before the attacker started selling (bitcoinethereumnews); and per the BIP-908 forum post, in the April 2026 THORChain laundering the attacker made **"test transactions (0.9–1 ETH) to verify THORChain route"** before 35 ETH→BTC swaps. These are *cashout-route* tests, months after the strike — the pattern migrating to the laundering phase.
- **Structural explanation for the null:** a constructor-atomic exploit doesn't need mainnet rehearsal — you fork the chain and rehearse off-chain. The 65-cycle precision of the attack shows it was tuned *somewhere*, just not on mainnet. This is a real, checkable reason the pattern can be invisible even when it "happened" (in the fork, not on chain).

**Calibration:** "not found" ≠ "didn't happen." I searched public forensics only; I did not query an Etherscan/archive node for the deployer's pre-Nov-3 interactions with the Balancer Vault (`0xBA1`). If the attacker made zero-value `eth_call`-style probes, those leave no on-chain trace at all. A direct check would be: pull all pre-2025-11-03 transactions to the V2 Vault from the three attacker addresses.

---

## Does the pattern generalize?

**Yes, but conditionally — and the conditions are the interesting part.**

| Case | Pre-strike test | Form of test |
|---|---|---|
| Cetus (May 2025) | ✅ Found | Gas funding + **failed dry-run attempt** ~2 days before |
| Bybit (Feb 2025) | ⚠️ Ambiguous | Small wallet-to-wallet transfers exist (second-hand); **no protocol test possible** in infra-class attacks |
| Balancer V2 (Nov 2025) | ❌ Not found | Constructor-atomic attack; any rehearsal happened **on a fork**, leaving no mainnet trace |
| Ostium / NEAR / UNCX / Limit Break (seed cases) | ✅ Found | Small on-chain probes before the strike |

**Emerging rule (draft, needs more cases):**
Test-before-strike shows up on-chain **when the exploit is stateful and interactive** — the attacker needs to touch the live contract because pool state, liquidity depth, or live oracles can't be perfectly simulated (Cetus, NEAR Intents, Ostium). It **disappears** when:
1. **The attack is constructor-atomic** (Balancer) — rehearsal moves to forks, which are invisible to us. *Corollary: no mainnet probe can itself be weak evidence the attacker is highly sophisticated.*
2. **The attack is infra/supply-chain class** (Bybit) — the "test" would be the strike itself; prep takes the form of staged payloads, not probes.

**Second pattern worth chasing:** test transfers *reappear at cashout* (Balancer's 0.9–1 ETH THORChain tests; Lazarus's laundering hops; Bybit's $27M-increment ETH dispersal per Nansen). Attackers test routes they're unsure of — before the strike if the target is uncertain, before the exit if the laundering route is.

**Honest calibration on this whole thread:**
- 1 of 3 cases (Cetus) is a clean positive from a primary forensic source (SlowMist/MistTrack).
- 1 (Bybit) rests on a second-hand quote; I could not recover amounts/dates, and the attack class makes "test" semantically different. Treat as weak/ambiguous, not as a hit.
- 1 (Balancer) is a genuine null from public forensics, with a structural explanation — but it was **not** falsified by a direct on-chain check, which remains an open, cheap query for whoever has an Etherscan/archive-node seat.
- The pattern is real but **only visible with chain access or forensic write-ups** — exactly the caveat in the task brief. Two of three cases required a forensic firm's write-up; news coverage alone would have missed all three.

**Recommended follow-ups (for parent/workflow, not done here):**
1. On-chain check: Balancer deployer + attack contract + recipient vs. V2 Vault in the 7 days pre-2025-11-03 (Etherscan/archive node; subagent has no live-browser/API seat).
2. Suiscan lookup: Cetus attacker `0xe28b50…8ff06` failed tx ~May 20–21, 2025 — recover hash + amount to firm up the positive.
3. ZachXBT's Feb-21-2025 Telegram post: does he specify the "test transactions" (amounts/wallets)? Would settle the Bybit ambiguity.
4. More cases in the stateful-interactive class (reentrancy, oracle-manipulation) where the hypothesis predicts positives; and more constructor-atomic or infra cases where it predicts nulls. Falsification-ready either way.
