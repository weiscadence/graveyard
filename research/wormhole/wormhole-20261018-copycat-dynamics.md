# Wormhole Thread 1: Copycat Dynamics — How Fast Do They Move?

**Date:** 2026-10-18 · **Type:** read-only research (no transactions, no accounts, no contact)
**Question:** How fast do copycats move after an exploit is detected/disclosed? Is the window predictable? How fast must defenders respond?

---

## TL;DR

Across 5 incidents (2022–2026), the copycat response has a predictable structure with **three tiers**:

| Tier | Actors | Typical window after first exploit | Examples |
|------|--------|------------------------------------|----------|
| **T1 — mempool/MEV frontrunners** | bots copying the attacker's pending tx | **minutes** (same block → ~1 hr) | Curve/Vyper Jul 2023 (c0ffeebabe, ~40 min); Kelp DAO Sep 2026 ("Yoink", same block) |
| **T2 — independent copycat wallets** | new human/bot actors re-running the attack | **~12–24 hours** | UNCX Oct 2026 (~15 hr, 17x); Aztec Connect Jun 2026 (15.5 hr); Limit Break Sep 2026 (≤48 hr) |
| **T3 — inspired second hits** | different actors, adjacent contracts/vulns | **3–4 days** | Aztec 2.0 after Connect (3 days); UwU Lend repeat 3 days (same attacker); Conic→Curve 9 days (different bug) |

**Best estimate for the defender's critical window: the first 12–24 hours.** By hour ~15 the copycat wave is typically already in full swing. If the contract is immutable/unpausable, fee-gating or rescue must start inside that window — UNCX raised lock fees to 100 ETH and then >1,000 ETH within hours, and the wave still ran to $1.49M across 4 chains.

---

## Case 1 — UNCX VestingManager V2 (Oct 14–15, 2026): the 17x copycat wave

**First exploit.** Oct 14, 2026, 11:49:59 a.m. ET (15:49:59 UTC): a single Ethereum transaction drained ~$86K in 5 tokens from a shared vesting pool via an accounting flaw — `release()` lowered the pool's global share count without clearing the position's recorded deposit, so a later `cancel()` double-deducted shares. *(sources: web — tokenpost.com; news.bitcoin.com; blockchainreporter.net)*

**Detection/disclosure.** Blockaid reported it Oct 14, flagged the attack **"ongoing"** ($3.25M still sitting in the affected contract), and — critically — **published the exploiter addresses and a sample transaction publicly**. ExVul researchers analyzed the first tx and described the exact sequence (create positions → release → donate → top-up → cancel → withdraw). UNCX acknowledged on X, blocked new vesting positions, and raised flat fees to 100 ETH (then >1,000 ETH per lock) on Oct 14 evening.

**Copycat wave.** By 2:19 a.m. ET Oct 15 (~14.5 hours later): **11 draining transactions across 4 chains** (Ethereum, BNB Chain, Robinhood Chain, Base) totaling ~$1.49M — **17.3x the first drain**. Breakdown: ~$969K BNB Chain, $242K Ethereum, $169K Robinhood Chain, $114K Base. Blockaid identified **copycat wallets and MEV bots** joining the attack; 10 tokens affected. Neither the original attacker nor the copycats returned funds.

**Timeline:** 15:49:59 UTC Oct 14 ($86K, 1 tx) → 06:19 UTC Oct 15 ($1.49M, 11 txs, 4 chains). **Window to peak copycat activity: ~14.5 hours.**

**Trigger analysis.** Three compounding signals: (1) Blockaid's disclosure handed copycats the recipe (sample tx + addresses); (2) the full attack sequence was replayable on-chain by anyone who could read the tx; (3) $3.25M in remaining TVL was a visible honeypot, and the contract couldn't be cleanly stopped — UNCX's fee-gating was outpaced by cross-chain spread (copycats simply went to BNB/Robinhood Chain/Base where the same V2 code sat exposed). The copycat count is not precisely published ("11 draining transactions" — Blockaid cited copycat wallets + MEV bots, plural, undated beyond the window).

---

## Case 2 — Aztec Connect + Aztec 2.0 (Jun 14–18, 2026): the textbook copycat pair

**First exploit.** Jun 14, 2026, 12:26 UTC: attacker drained **~$2.19M** from the deprecated Aztec Connect rollup contracts on Ethereum in a **single transaction** — proof/settlement desync (valid ZK proof for one tx set, execution of a different one). Funds routed through Tornado Cash. *(source: aztec-labs.com June-2026 incidents postmortem; pulsechain.nexus)*

**Copycat #1.** Jun 15, 2026, beginning **04:00 UTC** — ~15.5 hours later — **a second actor** hit the same Aztec Connect vulnerability, extracting ~$88K of residual value across 14 transactions (`rollupId 13291–13304`). Aztec Labs' postmortem names it explicitly: "a second actor extracting approximately $88k of residual value the following day."

**Second contract, same pattern.** Jun 17–18, 2026: a separate attacker drained **~$2.2M** from the older Aztec 2.0 rollup contract via a soundness bug in the `escapeHatch()` verifier, "followed by a copycat actor sweeping the remaining 0.76 ETH the next morning" — Aztec Labs' own words.

**Amplification.** Small in dollar terms (copycats swept residual value: $88K and 0.76 ETH), because the first actors took the bulk. The pattern matters more than the multiplier: **copycat windows of ~15.5 hr (T2) and ~24 hr, with a T3 "inspired" hit on an adjacent deprecated contract 3 days later.**

**Trigger analysis.** Both contracts were deprecated, immutable, and had admin roles renounced in April 2024 — nobody could pause or patch. The first attack was publicly analyzed within hours (BlockSec confirmed the mechanism; SlowMist published escape-hatch analysis), so the method was open knowledge. **The trigger was on-chain visibility + published postmortems, combined with unpausable contracts holding legacy funds.** Aztec's case is the cleanest evidence that the ~15-hour copycat window recurs independently.

---

## Case 3 — Limit Break Payment Processor V2 (Sep 24–26, 2026): copycat bot front-runs the attacker

**First exploit.** Sep 24, 2026, 13:07:59 UTC: an attacker deployed a contract abusing a forged ERC-2771 "original sender" in Limit Break's Payment Processor V2, taking 50 Otherdeeds, 10 Meebits, 10 World of Women from one wallet at 0 WETH — spending token approvals Magic Eden users granted back in Feb–Oct 2024. *(sources: sigintzero.com; nexusmutual.io roundup; nftculture.com)*

**The race.** Whitehat 0xQuit was flagged the morning of Sep 25 (12+ hours after the first thefts — Boomskite flagged the initial tx). V3 was pausable and got paused; **V2 was not pausable**, so 0xQuit + helpers ran a defensive whitehat sweep: 23,155 NFTs (~$5.7M) moved to a rescue wallet. The attacker pivoted to the WETH path (same bug, reversed): ~660 WETH at risk.

**Copycat enters.** Per Nexus Mutual's roundup: **"a copycat bot front-ran the attacker and took 260 WETH, which it has since been returning to victims."** Cryptoticker counted **530.7 WETH taken from 911 wallets by Sep 26** — roughly 48 hours after the first exploit. Revoke.cash put total losses at ~$2.8M across chains.

**Timeline:** 13:07 UTC Sep 24 (first tx) → Sep 25 morning (public flag + whitehat race) → Sep 26 (530.7 WETH gone across 911 wallets, copycat bot among the takers). **Window: copycat activity within ~24–48 hours; the damage curve was steepest once the method was publicly understood.**

**Trigger analysis.** This case shows the full arms race in one frame: attacker → whitehat rescue → copycat bot front-running the attacker's own drains. The trigger was the public flagging (Sep 25) combined with an **unpausable contract** — defense could only compete by out-running, not by stopping. Note the copycat here behaved like a T1/T2 hybrid: automated, but arriving a day after the initial exploit rather than in the same mempool.

---

## Reference archetypes (context, not counted in the 3)

- **Nomad Bridge (Aug 1, 2022).** The canonical copycat frenzy: first attacker found that the trusted root initialized to zero made `process()` accept any message; calldata was visible on-chain, samczsun noted it became "copy and paste" — dozens to hundreds of wallets replayed the tx with their own recipient address. **$190M drained within hours.** Trigger: trivially replayable calldata + on-chain transparency. *(sources: encrypthos.com; nomoslabs.io)*
- **Curve/Vyper (Jul 30, 2023).** First attack ~1:10 p.m. UTC (JPEG'd pETH, ~$11M); **~40 minutes later** the msETH pool was hit by a different actor; MEV bot c0ffeebabe frontran the original attack tx itself. A whitehat/blackhat arms race ran all afternoon across JPEG'd, Alchemix ($13.6M), Metronome, Pendle, CRV-ETH pools. Net ~$50–70M. *(sources: metronomedao.medium.com postmortem; blog.dragonscale.ai)* The 40-minute window is the fastest documented independent-copycat case.
- **Kelp DAO (Sep 15, 2026).** Attacker exploited a Safe-module authorization flaw for rsETH; MEV searcher "Yoink" **copied the pending transaction, paid ~19 ETH in priority fees, and got its copy mined first in block 25,980,525 — the original reverted.** ~2,882 rsETH (~$7.7M) to the copycat, within minutes. *(source: defiinger.com)* The limiting case: at T1 speed, the "copycat" beats the original.
- **Negative case — Balancer V2 (Nov 3, 2025).** $70.9M → $116.6M → $128.64M across 6 chains **within a few hours by one actor** (access-control/callback flaw in composable pools); Berachain forked defensively. No documented copycat wave — the original actor drained everything before copycats could matter. Lesson: **copycats need (a) residual TVL and (b) time; a fast, thorough first actor leaves nothing to copy.**

---

## What signals the wave is starting (early-warning checklist)

1. **Drain txs from new, unrelated wallets** executing the same/similar call sequence — the wallet-diversity signal. UNCX: 1 tx → 11 txs across 4 chains.
2. **Public disclosure with technical detail.** Blockaid publishing the sample tx + addresses (UNCX); samczsun's "copy and paste" thread (Nomad). Each disclosure is a fork in the road: defenders get the recipe, and so does everyone else.
3. **Original txs getting frontran in the mempool** (Curve c0ffeebabe, Kelp "Yoink", Limit Break copycat bot). If bots are racing the attacker, human copycats are 12–24 hr behind them.
4. **Remaining TVL > 0 in an unpausable/immutable contract.** Blockaid's "ongoing" flag on UNCX ($3.25M still at risk); Aztec's renounced-admin contracts; Limit Break's unpausable V2. The honeypot amount is the wave's fuel gauge.
5. **Cross-chain spread of the same bytecode.** UNCX: Ethereum-only disclosure → BNB/Robinhood Chain/Base drains within 15 hr. Forks and multi-chain deployments are the copycat's path of least resistance (also seen: Berachain forking defensively after Balancer).

## Triggers, ranked by how reliably they start a wave

1. **On-chain visibility of the exploit** (calldata in explorers, mempool txs) — necessary and nearly sufficient; drives T1 (minutes).
2. **Security-firm disclosure naming the mechanism + sample tx** — accelerates T2 from days to hours (UNCX is the cleanest demo: 15 hr to 17x).
3. **Unpausable contract + visible residual TVL** — determines whether the wave *can* happen at all.
4. **Social amplification** (CT threads explaining the bug) — widens the actor pool (Nomad's hundreds of wallets).

## Implications for the graveyard scanner

- **The scanner's alert-to-action budget is ~12 hours, not 24.** By hour 15 the T2 wave is typically at peak; MEV copycats (T1) act in minutes.
- **Track the "honeypot remainder":** post-exploit TVL in the vulnerable contract is the single best predictor of wave size. UNCX's $3.25M remainder → $1.49M wave.
- **Watch for wallet-diversity in drain txs** as the wave-start signal: second and third distinct attacker wallets = the copycat phase has begun.
- **Multi-chain same-bytecode deployments are the highest-risk topology** for amplification (UNCX 4 chains; Nomad multi-chain; Balancer 6 chains) — a first-exploit alert on one chain should immediately flag sibling deployments on other chains, because copycats will find them faster than the protocol team can pause them.
- **Disclosure design matters:** Blockaid's UNCX disclosure (sample tx published) likely accelerated the copycat wave. For the scanner's own alerting: share indicators (addresses, affected contracts) widely, but consider delaying full exploit-recipe detail until pauses are confirmed — the recipe is what compresses T2 from days to hours.

## Caveats

- Copycat *counts* (distinct wallets) are underreported in public sources: UNCX ("copycat wallets and MEV bots," plural, no count), Aztec ("a second actor," "a copycat actor"), Limit Break ("a copycat bot"). On-chain forensics could pin these down, but the public record gives windows and amplification, not actor headcounts.
- UwU Lend (Jun 10 → Jun 13, 2024, $20M → $3.7M) looks like a copycat pattern but was the **same attacker** reusing sUSDe collateral — filed here as a "repeat-drain" confounder, not a copycat case.
- All amplification figures mix first-actor and copycat value; reports rarely separate them. The UNCX 17x is first-exploit $ → total $.
- Nomad (2022) and Curve (2023) predate the requested 2024–2026 range and are used only as mechanism archetypes.
