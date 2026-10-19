# Wormhole Shift 5, Thread 1: Whitehat Methodology
**Date:** 2026-10-18 · **Mode:** read-only research (web search, page fetches; no transactions, no contact)
**Question:** How do the best whitehats actually *operate* — not their rescues, their methods? What do they do that a two-person team with monitors doesn't?

**Provenance:** All claims below are from public web sources fetched 2026-10-18 (search snippets, opened pages). No interviews, no private channels. Where a fact rests on one source, the source is named inline.

---

## 1. samczsun — find it before the bots do, prove it with a PoC, submit privately

### 1.1 The discovery engine: a private TVL watchlist with real-time alerts
samczsun runs a self-built tool that **monitors large-TVL contracts and issues real-time alerts**. In his own telling, the $9.6M Lien Finance rescue started because he got one of those alerts and decided to look at it before going to sleep — "I have a tool that monitors large TVL contracts and can issue alerts in real-time... When you realize that all the money staked in the protocol is at risk, you really feel like the world is just seconds away from exploding." (chaincatcher interview, ~2020)

Transferable shape: **target selection is by money-at-risk, not by who hired you.** The watchlist is the instrument.

### 1.2 The loop: read code → build working exploit → peer-verify → coordinate
Across his writeups the loop is consistent:
1. **Read the contract code directly.** The Miso ($350M) case began with him examining the BitDAO token-sale contracts on SushiSwap's launchpad; he found functions lacking access controls, then realized an attacker could reuse the same ETH over and over to "bid in the auction for free" and trigger refunds past the hard cap. (Cointelegraph, Aug 2021)
2. **Write a successful exploit before telling anyone.** "Samczsun tested the vulnerability with a successful exploit before contacting colleagues Georgios Konstantopoulos and Dan Robinson to take a look and double-check the findings." PoC-in-hand is the gate before escalation.
3. **Assemble a war room by function, not by org.** Lien took ~7 hours and recruited: someone with a line to the protocol team, someone with a line to a major miner, someone to review. He credits Alex Wade, Scott Bigelow, Tina Zhen, Georgios Delkos, and SparkPool — "Saving Private Ryan" style. The skill is *knowing which specialist solves which minute*.
4. **Submit the rescue transaction through a private channel.** The Lien rescue txs were never broadcast to the mempool; they were fed directly to SparkPool's private submission endpoint (the Taichi Network). ~15 blocks later: mined, in order, not reverted. (Decrypt, Sep 2020; Coindesk, Oct 2020) The whole dark-forest problem — generalized frontrunning bots that simulate pending txs for profit and copy them — is defeated by never entering the public mempool at all.

### 1.3 His time budget (from his own mouth)
On Unchained Ep. 579 he described his Paradigm split as three parts: (1) protecting Paradigm itself — "it would be quite embarrassing if Paradigm were to be hacked," (2) protecting portfolio companies (security asks, code review, audit help), (3) the broader ecosystem. (podscripts transcript) Note: even the most famous whitehat spends most time on *defense of his own principals*, not on hunting.

### 1.4 The strategic thesis: passive defenses lose; re-audit live code
In his 2026 writeup "The Key to Crypto Protocol Security Lies in Proactive Re-Auditing" he argues bug bounties are *passive*; the incidents at Yearn, Balancer V2, Abracadabra and 1inch show even audited protocols get hit. The implication for a monitor team: **the watchlist must track live code and live state, not point-in-time audits.** Upgrades and config changes are where the bugs enter (cf. Morpho's fatal front-end update, §4).

### 1.5 His entry path (how he learned to see bugs)
He started by reading old vulnerability writeups — the Parity multisig bug, the DAO-style reentrancy classes, `delegatecall` — and "slowly work[ed] his way up." (Unchained Ep. 579) Methodologically: he built a library of *bug shapes* and pattern-matched new code against them.

---

## 2. 0xQuit — the Limit Break rescue as a repeatable pipeline

0xQuit (VP of Blockchain at Yuga Labs; builder background — founder of the oSnipe NFT sniper) executed the largest whitehat NFT rescue on record on 2026-09-25. Decompose it as a pipeline any team can copy:

### 2.1 Detect (accept the lag, shrink what follows)
- First exploit at 9 AM EST: 10 Meebits, 50 Otherdeeds, 10 World of Women, 235 Desperate Apewives stolen via the PaymentProcessorV2 bug.
- **It took 12+ hours before anyone flagged it to him** (tipped by @Boomskite). He does not pretend to have caught it live — the honesty about detection lag is itself part of the method: the response is designed to work *after* the fact.

### 2.2 Triage: generalize the vuln, enumerate the whole exposure set
- Root cause identified: the processor trusted an **ERC-2771-style "original sender" supplied through a trusted forwarder — and that sender could be forged**.
- He then mapped *everything* exposed to the same path, across chains: Ethereum, Polygon, Base (V2), ApeChain (V3). Not just what was already hit — what *could* be.

### 2.3 Contain: coordinate the pause with the project team first
- Contacted Limit Break → **Payment Processor V3 paused immediately** (it carried the same bug). V2 was *not pausable* — that fact, not indecision, is what forced the next step. ApeChain V3 was temporarily unpausable too.
- Method rule: **the first call after confirming the bug is to the one person who can pause**; the rescue op is the fallback for contracts that can't be stopped.

### 2.4 Execute: the whitehat sweep
- Moved **23,155 NFTs (~$5.7M)** out of hundreds of wallets across multiple chains into one published custody wallet (`‹addr redacted›`), through the night. Multi-operator crew: @coffeedev, @0xjustadev, @whiteoakkong assisted.
- When the pattern repeats across chains, run it the same way on each chain in parallel.

### 2.5 Communicate: public, on-chain, and honest about the miss
- As soon as the transfers were spotted (trader Cirrus flagged them), he publicly identified the custody wallet: "everything in [address] is safe and will be returned once they are no longer at risk."
- Published the exact contract addresses (V2 `‹addr redacted›` on Ethereum/Polygon/Base; V3 `‹addr redacted›` on ApeChain) and directed owners to revoke.cash.
- **Disclosed the failure in the same breath:** the bug could also be inverted to drain WETH; 660 WETH (~$1.7M) was lost because he wasn't fast enough. "All I'll be able to think about is the $1.7M in WETH I wasn't fast enough for."
- Return mechanics: owners reclaim **after revoking** the vulnerable approval — otherwise the tokens re-expose on arrival. Claim process via nftsaresafu.xyz; ~$3.4M of $6.6M at risk returned.

**The 0xQuit pipeline, compressed:** exploit-tx → generalize vuln → enumerate full exposure set (multi-chain) → pause-coordination with the team → pre-published custody address → bulk sweep → public comms + revoke instructions → return-after-revoke → honest loss accounting.

---

## 3. SEAL 911 — the triage machine

### 3.1 Intake: a Telegram bot with a structured questionnaire
SEAL 911 is a 24/7 emergency hotline run as a Telegram bot. Per samczsun, it is an "experimental solution" to "the hardest part of responsible disclosure: finding the right person to talk to." An **automated system asks the reporter questions and forwards the answers to the responder team**. The design insight: triage starts with *structured intake*, not with a phone call. (Cointelegraph, Aug 2024; DL News, Mar 2025)

### 3.2 The responder pool (public member list, invite-only with vouching)
The GitHub roster shows ~40 responders spanning: independents (samczsun, pcaversaccio, **0xc0ffeebabe**, Nick, Ross, Tay, Lotem), audit firms (OtterSec, DefiHackLabs), on-chain investigators (Elliptic, Tracelon, Cryptoforensic Investigators, zeroShadow, Pangolin Intelligence), monitoring (Hypernative), protocols (Binance, Wintermute, Monad, 1inch, Sui Foundation, Privy). Commercial orgs are capped at two members; membership requires a vouch. This is the "who to call" graph made explicit. (security-alliance/seal-911 README)

### 3.3 The first-hour shape (from the dice9win case, the first live save)
A tip came in that a hacker had already taken $25,000 with $200,000 more at risk. **"Everything happened within minutes":** responders (pcaversaccio + Wintermute's Igor Igamberdiev) confirmed the bug together, contacted a dice9win team member directly, who withdrew funds and deployed a patch. First-hour playbook, extracted: (1) **two-person independent bug confirmation**, (2) **direct line to the one person who can pause/withdraw**, (3) act before writing anything up. (DL News, Mar 2025)

### 3.4 Anti-spoofing as a first-class step
The README mandates an impersonation check: before trusting anyone who claims to be a SEAL 911 member, share an **unguessable keyword sentence, then open a ticket in the official bot and ask the member to repeat the keyword** through it. In war-room conditions, identity verification is a protocol step, not an afterthought. (seal-911 README)

### 3.5 The legal enabler: Safe Harbor
Protocols adopt an **on-chain agreement that pre-authorizes whitehat interventions during active exploits**. Rules: rescued funds returned within **72 hours**, bounty **10% of recovered funds capped at $1M**, whitehat completes KYC/OFAC before payout; a Security Research Legal Defense Fund backs researchers. This is what converts "I found an exploit" into "I can legally take the funds before the hacker does." (securityalliance.org/our-work; Cointelegraph)

### 3.6 Drilling: SEAL Wargames (the Chaos Team playbook)
Wargames pressure-test detection, coordination, and response *before* a real attack. Three phases:
1. **Reconnaissance** — analyze the protocol, its external dependencies (oracles), versions/upgrades, docs, and public comms; list and validate every assumption.
2. **Tabletop simulation** — walk the team through scenarios under time pressure; check division of responsibilities and escalation paths.
3. **D-Day live exercise** — a real-time war room with a simulated attack on a **Tenderly Virtual TestNet replicating production state**, block explorer and debugging tools included; **Silverback bots** run monitoring, impersonate accounts, and execute the scenario; **Telegram channels carry monitoring alerts** to the team.
Internally they prototype on a local fork (Hardhat/Foundry): simulate an EOA compromise and a malicious tx, watch what happens, then migrate the orchestration scripts to Silverback. "In a war room, every second counts." (blog.tenderly.co, 2025)

### 3.7 Threat intel: SEAL Intel / ISAC and beyond
- **SEAL-ISAC** (Apr 2025): free threat-sharing platform on OpenCTI; ~two dozen early participants (Ethereum Foundation, Polygon, Uniswap Labs, Chainalysis, MetaMask).
- **SEAL Intel**: real-time alerts on phishing campaigns, wallet drainers, state-sponsored attackers.
- **Verifiable Phishing Reporter** (Oct 2025): uses **TLS attestations** so a reported phishing page's content is cryptographically verifiable — defeats cloaking scanners; 79 volunteers.
- Proof it works at scale: the Sep 2025 npm supply-chain incident was triaged and remediated fast enough that crypto damage was **under $50 in the first 24 hours**.

### 3.8 Capacity honesty
The README is explicit: volunteer bandwidth is finite; tickets needing long tracing are referred to professional firms (Tracelon, Cryptoforensic Investigators, zeroShadow). They keep a **public incident resolution log** (ACTIVITY.md) and a data retention policy. Accountability is built into the artifact set.

---

## 4. c0ffeebabe.eth — the mempool predator that works for the good guys

### 4.1 The behavioral pattern: generalized front-running as defense
c0ffeebabe.eth (pseudonymous, listed as "0xc0ffeebabe (Independent)" on the SEAL 911 roster) runs an **always-on MEV bot keyed on profit signatures in the public mempool**:
- It **simulates pending transactions on current state**; when a pending tx yields a net balance increase to its sender (i.e., it's a profitable drain), the bot **copies the transaction, swaps the beneficiary to its own address, re-simulates to confirm profit, and submits with higher gas** — landing the funds in its wallet instead of the hacker's. This is the textbook generalized-frontrunner architecture (simulate → replicate → substitute address → verify → outbid) described in the Flash Boys 2.0 lineage.
- The exploiter's own transaction is the signal. **No advance knowledge of the bug is needed** — the drain's pending tx announces itself by being profitable.
- Then it returns the funds: Curve, July 2023 — ~2,880 ETH / **$5.4M** returned to the deployer address (banteg's public thanks); SushiSwap, early 2023 — **300 ETH** recovered; Blueberry, 2024 — all stolen funds intercepted and returned; Morpho App, Apr 2025 — **$2.6M** front-end-update bug intercepted, funds parked at `0x1A5B…C742`.

### 4.2 The record: repeat, pseudonymous, cross-year
2023 → 2024 → 2025, same operator, same pattern, same ethic (intercept → park → return). SEAL reports 79 volunteers and names c0ffeebabe as the famous one; the Morpho case shows they react within a day of a config change introducing a bug.

### 4.3 The mirror image of samczsun
samczsun's Lien move was to **never enter the mempool** (private submission to SparkPool). c0ffeebabe's move is to **weaponize mempool visibility** (whoever enters it first with a profitable tx gets copied). Together they define the two poles of whitehat MEV: avoid the dark forest, or hunt inside it.

---

## 5. The delta: what these operators do that a two-person team with monitors doesn't

A typical two-person monitor stack detects known patterns and pages a human. These operators close the loop:

1. **Money-keyed discovery, not pattern-keyed.** samczsun's watchlist is ranked by TVL, not by signature; c0ffeebabe's trigger is *any* profitable pending tx, even for bugs nobody has seen before. Monitors look for the attacks they can name; these operators look at where money concentrates and let the anomaly reveal the attack.
2. **PoC-before-escalation.** samczsun builds a working exploit on a fork *before* calling anyone; SEAL 911's first-hour norm is two-person independent bug confirmation. A monitor fires "something is wrong"; these operators fire "here is the reproducible drain and the exposure set."
3. **Exposure enumeration, not single-incident triage.** 0xQuit's move was to generalize one exploit tx into *every wallet and chain* carrying the same approval — 23,155 NFTs, not 305. Triage = scope the full blast radius first, then sweep it.
4. **An execution channel for acting, not just alerting.** samczsun's private-relay submission; c0ffeebabe's front-run submission; 0xQuit's published custody wallet + bulk sweep scripts. Detection without a transact path loses to whoever has one.
5. **Legal pre-authorization.** Safe Harbor turns "taking someone else's funds" from a liability event into a pre-approved rescue with a 10%/$1M bounty and 72-hour return rule. Monitors without a legal path have to watch.
6. **A human network with trust rituals, on speed dial.** Invite-only vouching, keyword-challenge anti-spoofing, direct pause-coordination with protocol teams, multi-operator crews — and it's all been *drilled* (Wargames tabletop + live-fire on production-state forks).
7. **Honest accounting as doctrine.** 0xQuit published the 660 WETH he lost in the same post as the 23,155 NFTs he saved; SEAL keeps a public resolution log. The reputation is built on the misses too.

## 6. The 3 most transferable methods/tools for our team

### #1. Profit-signature mempool simulation (the c0ffeebabe loop, read-only version)
Build a **generalized-frontrunner observer, not actor**: subscribe to the public mempool, **simulate each pending tx against current state** (anvil/Foundry fork or `eth_call` bundles), and **alert when any pending tx yields an anomalous net balance gain to its sender or drains a watched contract** — regardless of whether the bug is known. The simulated trace *is* the alert payload. This catches unknown exploits in flight; our current monitors can only catch patterns we've already named. Downstream: feed straight into the SEAL 911 bot intake when the exposure set is large. (Technique basis: generalized frontrunning, Flash Boys 2.0 lineage; c0ffeebabe's record 2023–2025.)

### #2. samczsun's TVL watchlist + PoC-first triage + Safe Harbor check
(a) Maintain a **ranked watchlist of high-TVL contracts** with alerting on upgrades/config changes (most post-audit bugs enter via changes — Morpho's front-end update, Balancer V2, Yearn). (b) On any alert, **replicate the exploit on a local fork before escalating** — PoC-in-hand is what turns a monitor page into an actionable war-room. (c) Track **which watched protocols have adopted SEAL's Safe Harbor**; pre-authorization is half the rescue. (Basis: samczsun's alert tool and Miso/Lien loop; samczsun's proactive re-auditing thesis; Safe Harbor terms: 72h return, 10%/$1M, KYC/OFAC.)

### #3. A pre-built war-room kit, drilled once on a production-state fork
Copy SEAL's Wargames preparation as a standing capability: (a) **pre-staged custody addresses per chain** (read-only, no keys needed until action); (b) **private-relay submission config ready** (Flashbots Protect / builder endpoints that accept non-mempool txs — the modern equivalent of samczsun's SparkPool endpoint); (c) a **triage intake checklist modeled on SEAL 911's bot questionnaire** plus the **keyword-challenge anti-spoof ritual** before trusting any contact; (d) run the whole sequence **once as a live drill on a Tenderly Virtual TestNet fork** with Silverback-style monitoring bots and Telegram alerting — the two of us in the war room, a simulated drain, pause-coordination rehearsed. "In a war room, every second counts" — the first run should not be the real one. (Basis: SEAL Wargames phases and tooling; SEAL 911 README; 0xQuit's custody+comms conduct.)

## 7. What I could not verify (honest gaps)
- The implementation details of samczsun's TVL monitoring tool are private — its *existence and alert semantics* are from his interview, the code is not public.
- c0ffeebabe's bot internals (infrastructure, latency, relay choices) are not public; the generalized-frontrunner description is the standard architecture consistent with observed behavior, not a disclosure from the operator.
- SEAL 911's internal first-hour SLAs, bot questionnaire wording, and responder on-call rotation are not published; the triage shape above is inferred from the GitHub README and the documented cases (dice9win, npm incident).
- 0xQuit's sweep tooling specifics (batching, gas strategy, multi-operator coordination channels) are not published beyond the X threads; the pipeline is reconstructed from his public post-mortems.

## 8. Sources (all fetched 2026-10-18)
- samczsun interview (TVL alert tool, dark forest): https://www.chaincatcher.com/en/article/2075441
- Unchained Ep. 613 (SEAL, Safe Harbor, Wargames, audit advice): https://podscripts.co/podcasts/unchained/famed-white-hat-hacker-samczsun-on-how-to-improve-crypto-security-ep-613
- Unchained Ep. 579 (Paradigm time split, entry path): https://podscripts.co/podcasts/unchained/the-chopping-block-top-white-hat-hacker-samczsun-discusses-the-state-of-crypto-security-ep-579
- samczsun, "Proactive Re-Auditing" (passive bounties vs proactive): https://www.bitget.fit:443/news/detail/12560605106731
- Miso $350M writeup coverage (PoC-before-escalation loop): https://cointelegraph.com/news/white-hat-potentially-saves-sushiswap-350m-by-finding-obvious-exploit
- Lien/Dark Forest rescue (SparkPool private submission, war room): https://decrypt.co/42933/hacker-saves-10-million-in-ethereum-from-inevitable-theft ; https://www.coindesk.com/tech/2020/10/01/defi-has-a-front-running-problem-sparkpools-potential-fix-is-launching-this-month/
- 0xQuit Limit Break rescue — technical + comms: https://www.nftculture.com/nft-marketplaces/paymentprocessor-v2-exploit-0xquit-rescue/ ; https://egamers.io/whitehats-rescue-23155-nfts-from-stale-magic-eden-approvals-but-660-weth-lost-in-payment-processor-exploit/ ; https://cryptobriefing.com/whitehats-rescue-5-7-million-in-nfts-after-limit-break-payment-processor-exploit/
- SEAL 911 GitHub (members, anti-spoof ritual, capacity, resolution log): https://github.com/security-alliance/seal-911
- SEAL 911 launch + triage model: https://cointelegraph.com/magazine/seal-911-team-white-hat-forms-fight-crypto-hacks-real-time ; https://www.dlnews.com/articles/defi/seal-911-team-stops-dice9win-exploit-mid-hack/
- SEAL 911 frontlines (Dedaub responder account): https://dedaub.com/blog/seal-911/
- SEAL initiatives (Safe Harbor, Wargames, Intel, phishing reporter): https://securityalliance.org/our-work
- SEAL Wargames tooling (Tenderly Virtual TestNets, Silverback, Telegram alerting): https://blog.tenderly.co/how-seal-drills-ensure-protocol-resiliency/
- SEAL ISAC launch: https://coinmarketcap.com/community/articles/661fd82450fb9a41bcaeddc2/
- c0ffeebabe rescues (Curve $5.4M, Morpho $2.6M, SushiSwap 300 ETH, Blueberry): https://coinmarketcap.com/community/articles/68dca85cbf63c90bcafe6169/ ; https://cointelegraph.com/news/white-hat-intercepts-2-million-morpho-blue-hack ; https://coinmarketcap.com/community/articles/64c7f7c5010ea907cbe5fa10/
- Generalized frontrunner architecture: https://calblockchain.mirror.xyz/c56CHOu-Wow_50qPp2Wlg0rhUvdz1HLbGSUWlB_KX9o ; https://www.odaily.news/en/post/5183514
