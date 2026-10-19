# Wormhole Thread 7: MEV Amplification in Exploits

**Date:** 2026-10-18 · **Type:** read-only research (no transactions, no accounts, no outreach)
**Status:** findings below; open items flagged inline.
**Provenance:** all claims sourced from web research cited below (source: web:<url>), plus task-context claims from the parent ("claims heard from parent", untrusted by construction).

---

## 0. TL;DR answers

1. **What role do MEV bots play?** All of the above — with a bias toward acceleration. They (a) replicate public exploit transactions in the mempool, turning one attacker into a race of many; (b) routinely front-run whitehat rescue attempts because a rescue and an exploit look identical on-chain until the operator decides otherwise; (c) back-run drains to capture secondary value (priority fees, liquidations, arb). The rescue case (whitehat returns) is real but rare and operator-dependent; the default outcome of a mempool race is that the funds move faster, to whoever pays most for position.
2. **Concrete cases** (detailed in §2): Curve 2023 (whitehat rescue, 73% recovered), Blueberry 2024 (partial rescue), Limit Break/Magic Eden Sept 2026 (MEV bot front-ran for 281.66 WETH, agreed to return 90%), rsETH Safe Sept 2026 (Yoink front-ran $7.8M, *nothing returned, no commitment* — the dark case), Makina Finance $4.1M (builder 0xa6c2 front-ran, became de-facto custodian with no accountability), UNCX Oct 2026 ($86K → $1.49M, Blockaid: MEV bots + copycats joined the drain — pure amplification).
3. **0xQuit Limit Break:** the "copycat bot front-ran the attacker for ~260 WETH and returned it" story checks out with corrections: an MEV bot operator (`‹addr redacted›`) took the *first and largest* WETH transaction (281.66 WETH, 08:26 UTC 25 Sep), its payout chain split 90/10, and on 29 Sep 0xQuit said the operator agreed to return 90% (~253.49 ETH) via nftsaresafu.xyz. Whitehat MEV returns are uncommon — they come down to a handful of known operators (c0ffeebabe.eth is the repeat name), not an ecosystem norm.
4. **Whitehat MEV ecosystem:** exists, but it's split in two. The *defensive infrastructure* side (MEV Blocker, CoW Swap batch auctions/solver competition, Flashbots Protect/MEV-Share, Shutter) is real and institutional — but it protects *trade execution* from front-running; it does not rescue exploits. The *rescue* side is ad-hoc: individual searcher operators who happen to front-run an exploit and choose to return funds. There is no institutional whitehat-rescue pipeline.
5. **Monitoring:** yes — MEV-bot proximity to monitored contracts is a high-value early-warning signal, but intent is ambiguous: a front-run can be rescue or theft, and you can't tell which until the operator acts. Watch for the *race signal* (mempool replication of exploit-shaped calldata by multiple searchers), not just presence.

**Net assessment: MEV bots are net accelerant in exploits.** They compress the exploit window from hours to seconds and multiply the number of parties draining. The spectacular rescues are real, but they are the exception — and even they are a race the whitehat can lose.

---

## 1. The mechanism: the mempool race

The key insight, stated plainly by the wdguides full-chain review of the September 2026 rsETH incident:

> "If your exploit is visible in the mempool, your window is not the hours it takes to patch — it is the seconds it takes someone else to replicate your transaction."

The mechanics:
- An exploit transaction broadcast to the public mempool is **legible calldata**. Any searcher watching the mempool can simulate it, copy it, swap in their own address, and bid higher priority fees to execute first.
- This is ordinary front-running (the same code path as a sandwich bot duplicating a swap). Applied to an exploit, the searcher *becomes a second exploiter* — executing the identical drain, just faster.
- The result is an **auction over the victim's funds**: whoever pays the most for block position wins custody. In the rsETH case the searcher Yoink paid ~18.93 ETH (~$46K) to a block builder for priority — the victim effectively paid for the race.
- Whether the winner is a whitehat (returns funds), a neutral bot (keeps them), or another attacker (accelerates the drain) is **not determined on-chain**. It is a property of the operator's intent, which is invisible until they act.

This is why MEV is structurally an accelerant: it takes one exploit transaction and turns it into a competition among everyone who can read the mempool. The rescue outcome requires an extra, off-chain ingredient — a cooperative operator.

---

## 2. Concrete cases

### Case A — Curve Finance, July 2023: the canonical whitehat MEV rescue
- **What:** Vyper reentrancy bug drained ~$61.7M across Curve pools (Alchemix alETH-ETH, JPEG'd pETH-ETH, Metronome sETH-ETH).
- **MEV role:** MEV bot operator **c0ffeebabe.eth** front-ran a malicious hacker's transaction, capturing 2,879 ETH (~$5.4M) and returning it to the Curve deployer address. A *second* MEV bot front-ran the JPEG'd pool attack; its operator returned **90%** (~$11.5M equivalent, 5,495.4 WETH).
- **Outcome:** ~73% of stolen funds returned ($52.3M of $73.5M on Ethereum); net losses settled ~$20M.
- **Amplification angle:** the public discussion of the vulnerability (BlockSec/PeckShield tweets with Vyper details) simultaneously invited copycat burglars *and* whitehat front-runners. MEV was both the rescue and a symptom of the race.
- Sources: https://cointelegraph.com/news/white-hat-returns-5-million-curve-finance-hack · https://hacken.io/discover/curve-finance-liquidity-pools-hack-explained/ · https://cointelegraph.com/news/curve-hack-mev-bot-behind-61m-heist-begins-returning-funds

### Case B — Blueberry Protocol, Feb 2024: partial rescue, validator leakage
- **What:** Decimal-handling bug in Blueberry's lending contract; 457 ETH ($1.35M) drained.
- **MEV role:** c0ffeebabe.eth front-ran the attacker again; 366.6 ETH returned to the Blueberry multisig. But ~91 ETH (~$265K) leaked to **validator payments** — the priority-fee cost of winning the race.
- **Lesson for monitoring:** even a successful whitehat front-run has a ~20% tax in this case, paid to validators/builders. Rescue is not lossless.
- Sources: https://cointelegraph.com/news/defi-protocol-blueberry-pauses-after-exploit · https://www.web3isgoinggreat.com/web1?cursor=2024-01-23-0&direction=prev

### Case C — Limit Break / Magic Eden Payment Processor V2, Sept 2026: the 0xQuit case
- **What:** Unpausable Payment Processor V2 (`‹addr redacted›`) let anyone settle zero-price NFT "sales" on wallets with stale Magic Eden approvals (Feb–Oct 2024 listings). 0xQuit (Yuga Labs VP Blockchain) led a rescue of 23,155 NFTs (~$5.7M+).
- **The WETH side:** the same contract could be inverted to drain WETH — 542.1 WETH (~$1.4M) drained in ~30 minutes on the morning of 25 Sep across 6,650 transactions.
- **MEV role:** the *first and largest* WETH transaction (281.66 WETH from 25 wallets, 08:26 UTC) came from MEV bot operator **`‹addr redacted›`**. Its payout chain split the funds 90/10 (its standing pattern since late 2025); 253.49 ETH landed at `‹addr redacted›`. On 29 Sep 0xQuit reported the operator **agreed to return 90%** via nftsaresafu.xyz. PublicAML explicitly does *not* label it an attacker.
- **The rest went to real attackers:** 0xcccc6400… took 166.5 WETH (165 ETH parked untouched since; wallet now holds 223 ETH), 0xDeaD668F… took 44.8 WETH (46 ETH → Railgun, then 0.1 ETH Tornado Cash tests), and one attacker was *still draining* on 29 Sep. 660 WETH at risk was never recovered by the whitehats; 0xQuit publicly apologized for it.
- **Race note:** the MEV bot reached the WETH "before anyone else" — it front-ran both the original attacker path and the whitehat rescue. Same 90/10 keeper split as the JPEG'd 2023 MEV bot. (Whether it's the same operator is unconfirmed; flag as open question.)
- Sources: https://publicaml.org/limit-break-hack/ · https://altcoinvest.com/crypto-hacks-hit-766m-in-september-with-bitget-and-liquid-leading-losses/

### Case D — rsETH Safe module exploit, Sept 2026: the dark case (front-run ≠ rescue)
- **What:** ~2,900 rsETH (~$7.73M) drained from a Gnosis Safe (‹addr redacted›) via an ungated module entry point + flawed caller-check helper; attacker routed through an attacker-created Uniswap v4 pool with a malicious hook. Block 25,980,525, 04:38:47 UTC, 15 Sep.
- **MEV role:** searcher **Yoink** paid ~18.93 ETH to a block builder, executed at the top of the block, took 2,882.37 rsETH to its own address, swapped 17.63 rsETH → ~18.95 ETH (covering its priority payment). The attacker's tx landed later in the same block and **failed**.
- **Outcome as of reporting:** Kelp DAO (rsETH issuer) placed a 24-hour wallet-level pause on the searcher's address at 06:03 UTC (expired). **Nothing returned. No commitment to return made.** Analysts "expect" a return — the wdguides desk explicitly refuses to count expectations as recoveries.
- **Why this case matters:** it falsifies the comforting story that "an MEV front-run of an exploit is a rescue." Yoink's intervention denied the *attacker* the funds, but the funds are now held by an unaccountable searcher — and ~$46K of victim value was burned as a priority fee to decide the winner. This is MEV as *custody transfer*, not rescue.
- Sources: https://www.wdguides.com/articles/deep-analysis-the-safe-module-authorization-exploit-and-the-mev-race-a-full-chain-review.html · https://bitrss.com/mev-bot-profit-after-eth-wallet-exploit-kelp-freezes-7-7m-address-251495 · https://stocks24.co.za/2026/09/15/mev-bot-safeguards-7-8-million-from-rseth-exploit-through-front-running-on-ethereum/

### Case E — Makina Finance, $4.1M: the builder-as-custodian problem
- **What:** Flash-loan + oracle manipulation drained 1,299 ETH (~$4.13M). The attacker's drain tx was broadcast to the public mempool.
- **MEV role:** block-builder **0xa6c2** constructed a competing transaction that front-ran the exploit; the attacker's tx failed and most funds landed in **two builder-controlled addresses**.
- **Outcome:** from users' perspective, total loss was avoided. But the funds now sit with a profit-maximizing intermediary under **no on-chain obligation** — no court custodian, no pre-authorized whitehat, only informal expectations and off-chain negotiation. The followin analysis frames it as crypto's emerging emergency-response architecture being "concentrated in the hands of profit-maximizing intermediaries operating with unclear accountability."
- **Monitoring lesson:** a builder/front-runner rescue creates a *second* recovery problem: you must now negotiate with (or dox, or litigate) the intermediary. The on-chain trail ends at their address.
- Sources: https://followin.io/zh-Hant/feed/22794180 · https://www.techbuddies.io/2026/01/27/how-mev-bots-hijacked-a-4-1m-defi-exploit-and-claimed-the-power-to-decide-who-gets-repaid/

### Case F — UNCX Network Vesting V2, Oct 2026: MEV as pure amplification
- **What:** Accounting flaw in the VestingManager (release() reduced global share total without clearing a position's recorded deposit; cancel() then double-deducted). Initial drain: $86K on Ethereum (14 Oct), tokens incl. EDGEN, ZC, PEPECOIN, LO0P, PAAL.
- **MEV role:** Blockaid's revised investigation (15 Oct) found the loss had grown **~17× to $1.49M across 4 chains** (Ethereum, BNB Chain, Base, Robinhood Chain), with **"evidence of copycat attackers and MEV bots participating in the exploitation"** of the Vesting V2 contracts — 11 draining transactions, 10 tokens affected. Per the task context, the amplification was not just copycat wallets; MEV infrastructure joined the drain.
- **Outcome:** no funds returned by the original attacker or copycats as of reporting; UNCX raised flat fees to 100+ ETH then 1,000+ ETH per lock as an emergency brake.
- **Why it anchors the net assessment:** this is the cleanest "net accelerant" datapoint — MEV bots on the *attack* side, replicating the drain across chains, multiplying a small exploit into a large one. No whitehat MEV presence reported.
- Sources: https://davefinances.com/uncx-exploit-losses-jump-to-1-49-million-across-4-chains-as-copycat-attacks-emerge/ · https://blockchainreporter.net/uncx-vesting-v2-exploit-four-chains/

### Supporting: Morpho Blue frontend, April 2025
- c0ffeebabe.eth intercepted a malformed $2.6M frontend transaction (not an exploit by a malicious actor — a whitehat proving a vuln), returned funds to the user, earned a bug bounty. Third data point for the same operator.
- Source: https://thecyberexpress.com/morphoblue-vulnerability/ · https://CoinTelegraph.com/news/white-hat-intercepts-2-million-morpho-blue-hack

### Supporting: Peraire-Bueno brothers (context, not exploit-amplification)
- MIT-graduate brothers charged (2024) with a $25M MEV scheme: deploying validators to front-run *other MEV bots* in 12 seconds. Relevant as the reminder that the MEV layer itself is adversarial — searchers prey on each other, and any monitoring of "MEV wallets" must assume they are hostile-by-default economic actors.
- Source: https://www.tradingview.com/chart/ETHUSDU2025/xV9ELu2H-MEV-Bot-Exploit-by-MIT-Educated-Brothers-Leads-to-25M-Crypto/

---

## 3. Q&A against the task's questions

### Q1 — The four sub-roles
| Role | Verdict | Evidence |
|---|---|---|
| Accelerate drains by competing to extract first | **Yes — primary effect** | UNCX: MEV bots joined the drain, $86K→$1.49M. Mempool replication is the default behavior. |
| Front-run whitehat rescue attempts | **Yes — structurally** | A rescue tx and an exploit tx are indistinguishable in the mempool. In Limit Break, the MEV bot front-ran *both* the attacker path and 0xQuit's rescue for the WETH. |
| Back-run exploits to capture secondary value | **Yes** | rsETH: Yoink's 18.93 ETH priority payment and the 17.63 rsETH→ETH conversion; Blueberry: 91 ETH to validator payments; Curve week: ~$1M MEV block reward logged (per CoinTelegraph related link). Builders/searchers extract a toll on the race itself. |
| All of the above | **Yes** | — |

### Q2 — 2–3 most concrete cases
See §2: **Curve 2023** (whitehat rescue, best-documented), **rsETH Sept 2026** (front-run without rescue — the case that breaks the naive story), **UNCX Oct 2026** (MEV as pure amplification, most relevant to the graveyard scanner's threat model). Limit Break, Makina, and Blueberry are strong supporting cases.

### Q3 — The 0xQuit 260 WETH case; how common is whitehat MEV?
- **Fact check:** the task's "260 WETH" is approximately right — the MEV operator took **281.66 WETH** in the first WETH transaction (08:26 UTC, 25 Sep), kept a 10% split per its standing 90/10 payout pattern, and **agreed to return 90% (~253.49 ETH)** via nftsaresafu.xyz per 0xQuit's 29 Sep statement. PublicAML does not label the operator an attacker. Note: agreement ≠ completed return at time of reporting.
- **How common:** uncommon and operator-concentrated. The repeat whitehat name across 2023–2025 is **c0ffeebabe.eth** (Curve $5.4M, Blueberry $1.35M partial, Morpho $2.6M). The JPEG'd 2023 pool bot (returned 90% of $11.5M) and the Limit Break 2026 operator (agreed 90%) share a 90/10 keeper-split pattern — possibly the same operator, unconfirmed. Against these: Yoink (no return, no commitment) and builder 0xa6c2 (no commitment reported). So roughly: a handful of whitehat operators exist; most front-runners are silent or keep the funds. **Treat a whitehat return as a lucky draw, not a base case.**
- **Interesting regularity:** the 90/10 split appears as a de-facto "rescue fee" norm in two independent incidents. Worth tracking whether it recurs — if a front-runner's payout chain shows a 90/10 split, that may be a behavioral signature of the cooperative type.

### Q4 — Is there a "whitehat MEV" ecosystem?
**Two separate things, only one of which is an ecosystem:**
1. **Defensive MEV infrastructure (institutional, real):** MEV Blocker (CoW DAO — private mempool + AI-generated dummy txs to poison searchers + backrun rebates to users), CoW Swap solver competition + batch auctions + uniform clearing prices (orders never touch the public mempool; bonded solvers compete for best execution), Flashbots Protect RPC + MEV-Share (order-flow auctions returning ~90% of extracted value to users), SUAVE/BuilderNet (Flashbots' longer-term decentralized block building; still in development), Shutter (threshold-encryption pre-confirmations). This layer *reduces MEV extraction on trades* — it is "whitehat" in the sense of protecting users from bots. **It does not rescue exploits.**
2. **Whitehat exploit-rescue (ad-hoc, not an ecosystem):** individual searcher operators (c0ffeebabe.eth et al.) who front-run exploits and return funds. No institutional pipeline, no SLA, no accountability. The Makina case shows the failure mode: the rescuer is whoever won the auction, and you get whatever accountability they feel like offering.
- **Gap/opportunity note:** there is no standing "whitehat rescue relay" or bonded-rescuer market. A protocol offering, e.g., Flashbots-Protect-style private rescue submission to a bonded set of known-whitehat searchers would be new infrastructure. (Flag as idea, not recommendation.)

### Q5 — Should MEV-wallet proximity be a detection rule?
**Yes, with intent-ambiguity handled explicitly.** Recommended rule set for the graveyard scanner:

1. **Race signal (highest value):** multiple distinct EOAs/bots submitting *functionally identical calldata* to a monitored contract within a short window (seconds–minutes) in the mempool. One caller = possible exploit; N callers = the replication race is on. This is the earliest on-chain-visible moment of an incident and precedes confirmation.
2. **Known-searcher proximity:** maintain a labeled set of MEV bot/searcher/builder addresses (sources: EigenPhi labels, libMEV datasets, Etherscan labels, incident-specific addresses from post-mortems — e.g. c0ffeebabe.eth, Yoink's addresses, builder 0xa6c2). A known searcher interacting with a *vulnerable or drained* contract = the exploit is public and being replicated. Treat as CONFIRM of active exploitation, not as rescue.
3. **Builder priority-fee spike:** transactions touching a monitored contract suddenly carrying outsized priority fees / appearing in builder private orderflow = an auction is happening over that contract's funds.
4. **The 90/10 behavioral signature:** a front-runner's payout chain splitting 90/10 shortly after a drain is weak evidence of cooperative intent (two precedents). Useful for triage, not for trust.
5. **Issuer/pause authority mapping (from the rsETH lesson):** the only control that worked in the rsETH case was Kelp DAO's token-level address pause — which most projects don't have. For each monitored token, pre-record *whether any pause/blacklist authority exists and who holds it*; if none, the response clock is the mempool window (seconds), and the plan must assume funds move before any human reads the alert.

**Caveats:**
- **Intent ambiguity is irreducible on-chain.** A front-run of an exploit can be rescue (Curve), theft (UNCX), or indefinite custody (rsETH, Makina). The scanner should label "MEV race detected" and never "whitehat rescue in progress" until funds actually move back to victims.
- **Coverage limits:** private orderflow (Flashbots Protect, builder private relays) is invisible to mempool monitoring. A sophisticated attacker or rescuer using private submission bypasses the race signal entirely. The rule catches the *public* race, which is the common case for copycat amplification.
- **False-positive cost is low:** MEV bots touching a contract you monitor is rare enough that an alert is worth a human look.

---

## 4. Net assessment

**MEV bots are net accelerant in exploits.** The mechanism (public mempool → replication → fee auction) is direction-agnostic, but its *default* output is faster draining by more parties: UNCX is the clean example, and even the "good" cases pay a validator/builder tax (Blueberry's 91 ETH, Yoink's 18.93 ETH). Whitehat rescues are real, spectacular, and worth cultivating relationships with (the operators are identifiable and repeat players) — but they are exceptions that prove the rule: the rescue only happens when a cooperative operator *wins the same race the attackers are running*. For the graveyard scanner, the actionable takeaway is the race signal: when you see searchers replicating exploit calldata against a monitored contract, the incident has started, the window is seconds, and you should assume hostile intent until proven otherwise.

---

## 5. Open questions / follow-ups for the parent

1. **Identity of the Limit Break MEV operator** (`‹addr redacted›`): is it the same operator as the JPEG'd 2023 90/10 bot? Same split pattern; worth a cross-incident address/cluster check if the parent has labeling tooling. (Read-only: on-chain trace only.)
2. **Did the 90% Limit Break return complete?** PublicAML reported the *agreement* (29 Sep); completion unconfirmed in sources found. A re-check of `‹addr redacted›` outflows would settle it.
3. **Yoink/rsETH status:** no return commitment as of the wdguides analysis (21 Sep). If it later returned, that changes the dark-case reading — worth a re-check before citing.
4. **Makina 0xa6c2 resolution:** no reporting found on whether builder-held funds were returned. Open.
5. **The 90/10 split as a behavioral signature:** only two precedents (JPEG'd 2023, Limit Break 2026). Weak signal; do not build hard rules on it without more data.

---

## Sources (all web, retrieved 2026-10-18)

- Curve 2023 whitehat MEV: https://cointelegraph.com/news/white-hat-returns-5-million-curve-finance-hack · https://hacken.io/discover/curve-finance-liquidity-pools-hack-explained/ · https://cointelegraph.com/news/curve-hack-mev-bot-behind-61m-heist-begins-returning-funds · https://www.coindesk.com/business/2023/07/30/curve-finance-exploit-puts-100m-worth-of-crypto-at-risk
- Blueberry 2024: https://cointelegraph.com/news/defi-protocol-blueberry-pauses-after-exploit · https://www.web3isgoinggreat.com/web1?cursor=2024-01-23-0&direction=prev
- Morpho 2025: https://thecyberexpress.com/morphoblue-vulnerability/ · https://CoinTelegraph.com/news/white-hat-intercepts-2-million-morpho-blue-hack
- Limit Break / 0xQuit Sept 2026: https://publicaml.org/limit-break-hack/ · https://altcoinvest.com/crypto-hacks-hit-766m-in-september-with-bitget-and-liquid-leading-losses/
- rsETH Safe + Yoink Sept 2026: https://www.wdguides.com/articles/deep-analysis-the-safe-module-authorization-exploit-and-the-mev-race-a-full-chain-review.html · https://bitrss.com/mev-bot-profit-after-eth-wallet-exploit-kelp-freezes-7-7m-address-251495 · https://stocks24.co.za/2026/09/15/mev-bot-safeguards-7-8-million-from-rseth-exploit-through-front-running-on-ethereum/
- Makina $4.1M builder front-run: https://followin.io/zh-Hant/feed/22794180 · https://www.techbuddies.io/2026/01/27/how-mev-bots-hijacked-a-4-1m-defi-exploit-and-claimed-the-power-to-decide-who-gets-repaid/
- UNCX Oct 2026: https://davefinances.com/uncx-exploit-losses-jump-to-1-49-million-across-4-chains-as-copycat-attacks-emerge/ · https://blockchainreporter.net/uncx-vesting-v2-exploit-four-chains/ · https://news.bitcoin.com/security/an-86000-exploit-rocks-a-crypto-pool-built-to-lock-tokens/
- Defensive MEV infra: https://cow.fi/learn/what-is-frontrunning · https://cow.fi/learn/are-private-mempools-a-good-way-to-avoid-mev · https://finonity.com/mev-bots-are-eating-ethereums-scaling-gains-over-half-the-gas-on-major-l2s-goes-to-search-spam/
- Peraire-Bueno $25M MEV case: https://www.tradingview.com/chart/ETHUSDU2025/xV9ELu2H-MEV-Bot-Exploit-by-MIT-Educated-Brothers-Leads-to-25M-Crypto/
