# WORMHOLE Shift 5, Thread 4: MEV Searcher Behavior — the closest known analog to the zombie scanner
**Date:** 2026-10-18 | **Type:** read-only research (web search + page fetch) | **No transactions, no contact**

**Thesis link:** The "zombie scanner" — an unknown operator systematically probing deprecated-but-funded contracts — is behaviorally a searcher with a different profit function. This paper documents how MEV searchers find opportunities, filter them, and execute, then extracts the detection playbook for a scanner-like operator and the mempool visibility we'd need to see what they see.

---

## 1. The searcher pipeline: signal → simulation → bundle → submission

The canonical searcher workflow has four stages (documented across the MEV Book, ChainScore, CoinStats, and an industrial Polygon searcher architecture paper):

**Stage 1 — Signal (opportunity identification).** Searchers run high-performance nodes to access low-latency data feeds from the public mempool and private transaction pools. They monitor pending transactions and current on-chain state for opportunities: DEX arbitrage, liquidations, sandwich setups. The raw signal is the mempool itself — pending transactions decoded by function selector, plus on-chain state (pool reserves, oracle prices, lending health factors). (https://chainscorelabs.com/glossary/mev-and-transaction-supply-chain/mev-detection-and-quantification/searcher-strategy; https://arxiv.org/html/2510.14642v1)

**Stage 2 — Simulation.** The searcher tests the candidate strategy against a **local fork of chain state** ("local simulation") to predict the outcome and verify the bundle will be profitable and valid — crucially, that it won't revert. Simulation must be deterministic against a local EVM copy; stale state is the main failure mode, so serious searchers re-validate opportunities immediately before submission. (https://chainscorelabs.com/glossary/mev-and-transaction-supply-chain/mev-detection-and-quantification/searcher-strategy)

**Stage 3 — Bundle construction.** The searcher builds a **bundle**: a list of ≥1 transactions that execute atomically in the exact order given, or not at all (Flashbots semantics: any revert voids the whole bundle unless reverts are explicitly allowed). Sandwiches embed the victim's tx inside the bundle (frontrun + victim + backrun); liquidations combine the price update and the liquidation tx. (https://calblockchain.mirror.xyz/c56CHOu-Wow_50qPp2Wlg0rhUvdz1HLbGSUWlB_KX9o)

**Stage 4 — Submission.** Bundles go **privately to block builders** (not to the public mempool) — via Flashbots relay, MEV-Share, MEV Blocker, or direct builder endpoints — with an attached bid: a priority-fee tip and/or direct coinbase transfer to the builder. Builders aggregate bundles + user txs, optimize the full block, and bid it through relays to the proposer; the proposer takes the highest-paying valid block header. Searchers retain **~10–50%** of extracted value; the rest goes to builders and validators as tips. Competition compresses margins on contested opportunities. (https://www.blockchain-council.org/blockchain/mev-supply-chain/; https://dev.to/vathsaman/mempool-monitoring-for-mev-bots-technical-implementation-guide-4k38)

Post-Merge this is all under the proposer-builder separation (PBS) architecture: searchers never need 32 ETH or to be selected as proposer; they rent inclusion from builders who rent blockspace from proposers. (https://arxiv.org/html/2403.19077v1)

**Mapping to the scanner.** Replace "pending swap that moves a price" with "deprecated contract holding stranded value," and the pipeline is identical: the scanner's filter is Stage-1 targeting, its testnet/fork simulation is Stage 2, and its on-chain execution (flash-loan → donate → `actualizeFee()` → redeem) is the bundle. The profit function differs; the machinery rhymes. (see `wormhole-20261018-scanner.md`: the Set V1 October attack is a flash-borrow/donate/mutate/redeem sequence executed atomically — exactly a bundle.)

---

## 2. How searchers decide what to simulate — the targeting filter

This is the closest known analog to the scanner's targeting filter. Searchers cannot simulate everything (a full Ethereum mempool is ~1–2M txs/day, and simulation is expensive), so they run a **cheap pre-filter before expensive simulation**:

1. **Mempool decode by function selector.** Pending transactions are decoded using the 4-byte selector (`data[0:4]`) matched against known ABIs (4byte.directory). Searchers maintain an **allowlist of selectors**: swap functions on known DEX routers, liquidation entry points, oracle updates. A tx whose selector isn't on the allowlist never reaches simulation. (https://www.nadcab.com/blog/mempool-monitoring-mev-bot-technical-implementation-guide; https://magnushansson.xyz/blog_posts/crypto_defi/2024-01-15-parse_mempool_data)

2. **State-threshold pre-checks, not full simulation.** Documented arbitrage-bot implementations filter on cheap heuristics: minimum pool-reserve thresholds (e.g., ~$1,000/pool derived from gas-profitability math), inactivity pruning (pools with no recent swaps dropped), token-focus lists (high-liquidity tokens first, graph limited to ~50 nodes), max hop depth (3–5), minimum profit threshold net of gas. These heuristics prune the candidate set ~70% before any simulation runs. (https://deepwiki.com/darkhorse-techsolution/arbitrage-bot/3.2-arbitrage-detection-engine; https://deepwiki.com/darkhorse-techsolution/mev-lib/8.3-arbitrage-detection)

3. **Event-driven state tracking.** Instead of re-reading all state per block, searchers subscribe to `Sync` events for real-time reserve updates and only re-evaluate cycles containing pools that changed. Incremental updates, cached gas estimates, pre-computed log rates. (https://deepwiki.com/darkhorse-techsolution/mev-lib/8.3-arbitrage-detection)

4. **Decision pipeline.** Documented as a staged funnel: Price Detection (difference > threshold) → Liquidity Validation (reserves support trade size) → Gas Cost Analysis (net profit > gas + buffer) → Risk Assessment → Execution Timing → only then simulation. Each stage is cheaper than the next. (https://deepwiki.com/anthonyrs06/web3jumpstart/4.1-arbitrage-algorithms)

5. **Strategy specialization.** No searcher simulates "everything." Sandwich specialists (Jaredfromsubway.eth) watch for large swaps on known routers; liquidation bots watch lending health factors; Chainlink SVR searchers listen to the MEV-Share event stream and filter for a single function selector (`6fadcf72`) on a single aggregator address. The filter is narrow by design. (https://docs.chain.link/data-feeds/svr-feeds/searcher-onboarding-ethereum)

**Implication for the scanner.** The scanner's filter (`deprecated AND immutable AND has_stranded_value AND has_permissionless_state_mutation`, per `wormhole-20261018-scanner.md`) is structurally identical to a searcher's allowlist+threshold funnel — but its Stage-1 signal is **static state archaeology** (historical lots, share accounting, unclaimed balances), not mempool flow. That distinction is the detection key: searcher activity correlates with mempool/price events; scanner activity correlates with nothing except its own target inventory. A wallet interacting with deprecated contracts with no preceding mempool trigger is behaving like a searcher whose opportunity set is frozen state.

---

## 3. Infrastructure and cost

**Node layer (non-negotiable for serious operations):**
- Own full node(s), typically **geth** (robust txpool, extensive RPC) — configured with enlarged mempool capacity and tuned peer counts. Some run **Erigon** alongside for archive-data access and a different mempool view. (https://dev.to/vathsaman/mempool-monitoring-for-mev-bots-technical-implementation-guide-4k38)
- The bot co-locates with the node and subscribes to IPC/WebSocket feeds of **pending transactions and event logs**, plus on-demand state reads — minimizing end-to-end latency. All strategy components run as high-performance services (Rust/C++). (https://arxiv.org/html/2510.14642v1)
- Key fact: **there is no global mempool.** Each node's mempool is local; transactions gossip peer-to-peer, so a well-connected, well-positioned node sees transactions milliseconds before others — the entire latency arms race is about this. (https://www.monoceros.com/insights/maximal-extractable-value-book?ref=bankless.ghost.io)

**Data/orderflow feeds:** bloXroute, Chainbound Fiber (private mempool access), plus private-orderflow routes: Flashbots Protect RPC, MEV-Share, MEV Blocker, Blink, Merkle. These carry transactions that **never appear in the public mempool** — a searcher without these feeds is blind to a large share of flow.

**Submission layer:** mev-boost relays connecting builders to proposers; >90% of Ethereum blocks flow through this path. Builders optimize blocks from searcher bundles + private orderflow + public mempool txs.

**Costs:**
- DIY searcher node infra: **~$500–2,000/month** (node server $150–500, archive storage $500–2,000, bandwidth $100–300, data feeds $100–500, RPC $50–300) — before failed-tx gas costs. (https://dev.to/vathsaman/mempool-monitoring-for-mev-bots-technical-implementation-guide-4k38; https://www.dwellir.com/blog/mev-arbitrage-bot-infrastructure)
- Managed RPC at MEV scale is priced per compute-unit; `debug_traceTransaction` costs 10+ CU vs 1 CU for `eth_call`; a single day of testing can exhaust free tiers. (https://www.dwellir.com/blog/mev-arbitrage-bot-infrastructure)
- Builders (one level up): **>$30K/month** + multiple dev salaries, per the MEV Book's builder interviews. (https://www.monoceros.com/insights/maximal-extractable-value-book?ref=bankless.ghost.io)

**Takeaway:** A competitive *searcher* is cheap to start (a beefy VPS + feeds, low thousands/month) and the expensive part is gas burned on failed/contested attempts. A scanner operator probing zombie contracts has even lower infra needs — no latency race against other searchers on the same mempool trigger, no PGA bidding wars. A single geth node + scripts suffices. Don't expect scanner infra to look "expensive"; expect it to look *patient*.

---

## 4. Searcher behavioral signatures — detecting a searcher from on-chain data alone

Established detection methods and their signatures:

**A. Transaction-graph / pattern signatures (rule-based MEV classifiers):**
- **Sandwich:** same searcher EOA/contract with transactions immediately before AND after a victim swap in the same block, touching the same pools/tokens. Detection algorithms: find duplicate senders/contract calls, verify pool overlap and token intersection with the in-between victim txs. (https://deepwiki.com/jinmel/brontes/2.3-mev-detection-and-analysis)
- **Atomic arbitrage:** single tx with a continuous token path A→B→C→A across DEX protocols, or cross-pair stablecoin cycles. (https://deepwiki.com/jinmel/brontes/2.3-mev-detection-and-analysis)
- **Liquidations:** calls to lending-protocol liquidation entry points when health factors cross thresholds.
- Tooling: **EigenPhi** (real-time tx labeling, free tier; covers mainnet + L2s + BNB), **Flashbots MEV-Inspect-py** (open-source, needs own archive node/RPC), **Brontes** (Rust inspectors: AtomicArb, Sandwich, Liquidation), **libmev** (self-hosted dashboard), Etherscan's MEV address labels + block-level MEV view. (https://dev.to/frb_research/how-to-detect-mev-in-your-trades-2026-a-practical-guide-1okd)

**B. Economic/behavioral signatures:**
- **Gas bidding anomalies:** sudden gas-price spikes around a block (bidding wars), txs paying tips far above the base fee — the tip is the bid for ordering. Identical-parameter txs with escalating gas = frontrunning race. (https://www.7blocklabs.com/blog/detecting-mev-in-your-protocol)
- **Time-to-execution deltas, gas deviation from network median, sender MEV-reputation** are the recommended ML features for catching what rule-based systems miss. (https://clawdbytes.com/article/2026-10-01-mev-detection-with-ai-a-practical-guide)
- **Failed-tx rate:** searchers historically left reverted txs on-chain (pre-bundles, this was the PGA era: bots bid fees up in priority gas auctions and the losers' transactions still landed or reverted, paying gas). Flash Boys 2.0 documented these priority gas auctions as the dominant competition mode for DEX arbitrage bots. (https://arxiv.org/abs/1904.05234) Bundles changed this: Flashbots bundles are all-or-nothing and any revert invalidates the bundle unless the hash is listed as allowed to revert (https://docs.flashbots.net/flashbots-auction/advanced/understanding-bundles), and Flashbots Protect only includes transactions that do not revert, so users pay nothing for failures (https://docs.flashbots.net/flashbots-protect/overview). Consequence for detection: a modern searcher's failures mostly never reach the chain, so a low on-chain revert rate is not evidence against searcher-like behavior. A *high* rate of public reverts on one target family suggests the operator is probing through the public mempool or plain RPC rather than a bundle path.

> **Reconstructed 2026-11-17:** the original text after this point was lost to a write-time truncation (the file was cut mid-sentence on 2026-10-18; no intact copy exists). Everything below was rewritten from the cited sources on 2026-11-17, not recovered. Section numbering and content may differ from the original.

**C. Signatures that distinguish a scanner from a searcher.** (Analytical section; the premises are cited, the comparison is this paper's inference.)
- A searcher's trigger is external and recent: a pending transaction, an oracle update, a price move. Searchers watch pending transactions and react to them (https://arxiv.org/html/2510.14642v1; https://docs.flashbots.net/flashbots-auction/advanced/understanding-bundles shows a bundle that embeds a mempool oracle update). A scanner's trigger is internal: its own target inventory. So the first discriminator is **trigger absence**: interactions with a dormant contract that follow no relevant mempool event and no price or oracle movement.
- Searchers specialize narrowly (one selector on one address in the Chainlink SVR example, https://docs.chain.link/data-feeds/svr-feeds/searcher-onboarding-ethereum). A scanner that touches many unrelated deprecated contracts with the same read-then-simulate pattern is the opposite of that specialization, and looks more like a "generalized" actor. Paradigm describes generalized frontrunners that copy any profitable transaction by swapping in their own address and even replay execution traces, which is the closest documented searcher behavior to indiscriminate scanning. (https://www.paradigm.xyz/writing/ethereum-is-a-dark-forest)
- Permissionless-state hazards are known to attract this class of bot. In the Paradigm account, an unclaimed balance recoverable by anyone calling a public `burn` function sat undetected on-chain for about eight hours, but any attempt to claim it publicly risked being copied and front-run in flight. (https://www.paradigm.xyz/writing/ethereum-is-a-dark-forest) The same asymmetry applies to stranded value in deprecated contracts: stale state is quiet, a visible claim is not.

---

## 5. Detection playbook for a scanner-like operator

Design rule: assume the operator is patient, cheap to run (section 3), and acts through private paths when it acts. Detect the *inventory-driven reconnaissance*, not the exploit.

**5.1 Observable layer 1: read-side reconnaissance (weak, high volume).** Repeated `eth_call` and trace-style reads against deprecated contracts are invisible on-chain, but they leave footprints at RPC providers, not on the chain. Managed RPC providers meter trace calls much more heavily than plain `eth_call` (https://www.dwellir.com/blog/mev-arbitrage-bot-infrastructure), so a provider-side view is where read recon would show up, and we do not have that view. Treat read-side recon as unobservable from public data. (OPEN, see section 7.)

**5.2 Observable layer 2: write-side probes (the main signal).** What is visible is what lands on-chain:
1. *Wallet-to-target graph.* Maintain, for each watched deprecated contract, the set of external callers. Flag callers that touch more than one unrelated deprecated contract within a window. Single-target callers are users or owners; multi-target callers with no shared product relationship are scanner candidates. This is the analog of the searcher classifiers' duplicate-sender and pool-overlap checks. (https://deepwiki.com/jinmel/brontes/2.3-mev-detection-and-analysis)
2. *Trigger test.* For each flagged call, check the preceding blocks for a relevant mempool or price event. No trigger plus a state-mutating call on a dormant contract is the section 2 discriminator.
3. *Atomic-sequence shape.* Within one transaction, the borrow, deposit or donate, mutate, redeem pattern from `wormhole-20261018-scanner.md` is the bundle shape from section 1. Brontes-style inspectors already label atomic arbitrage and liquidation paths; a custom inspector for "flash-loan wrapped call into a deprecated contract" is the missing piece. (https://deepwiki.com/jinmel/brontes/2.3-mev-detection-and-analysis)
4. *Gas posture.* Competitive searchers show tips far above base fee; a scanner with no competition should show **median-or-below** gas deviation. Unusually *calm* gas on an otherwise searcher-shaped transaction is itself a weak flag. Gas deviation from the network median and time-to-execution deltas are the recommended features. (https://clawdbytes.com/article/2026-10-01-mev-detection-with-ai-a-practical-guide; https://www.7blocklabs.com/blog/detecting-mev-in-your-protocol)
5. *Funding trail.* Fresh wallet, funded shortly before first probe, same funder across wallets. This is standard attribution practice; no source in this paper's set quantifies it, so treat it as a heuristic to validate, not a finding.

**5.3 Observable layer 3: tooling.** EigenPhi labeling, Brontes, MEV-Inspect-py and Etherscan MEV labels cover sandwich, arbitrage and liquidation, not "dormant-contract probing". Expect the scanner's transactions to be **unlabeled** by these tools, so absence of an MEV label is the default, not exculpatory. (https://dev.to/frb_research/how-to-detect-mev-in-your-trades-2026-a-practical-guide-1okd)

**5.4 Scoring sketch (inference, not from a source).** Score a wallet on: number of distinct unrelated deprecated targets touched; fraction of calls with no preceding trigger; presence of atomic flash-loan-wrapped sequences; gas calmness; shared funder with other flagged wallets. Review manually above a threshold; never auto-act. Calibrate on known searcher wallets first, so the baseline false-positive rate against ordinary MEV bots is measured rather than guessed.

---

## 6. Mempool visibility needed to see what the operator sees

**6.1 The public mempool is a partial view.** There is no global mempool; each node holds its own and transactions gossip peer to peer (https://www.monoceros.com/insights/maximal-extractable-value-book?ref=bankless.ghost.io). A live feed built on a single node concedes this itself: a transaction that reached other nodes but not that one is counted as never seen, which the author names as the largest unquantified source of error, and a hash is only remembered for five minutes. (https://darkflow.martincasais.com/)

**6.2 Most DeFi flow does not touch it.** One benchmark study of private RPCs cites about 80 percent of DeFi interactions using private RPCs post-merge, which submit directly to builders and skip the public mempool (https://arxiv.org/html/2505.19708v1). Flashbots Protect states the same design: transactions go to a private mempool hidden from front-running and sandwich bots. (https://docs.flashbots.net/flashbots-protect/overview) A 2022 empirical study on private transactions describes the same property, that such a transaction is sent directly to miners and does not appear in the mempool of normal nodes. (https://arxiv.org/pdf/2208.02858) Paradigm's rescue is a worked example of why a careful actor goes private or obfuscated: they split the action into a set transaction and a get transaction in the same block, with the burn buried as an internal call, to avoid being copied. (https://www.paradigm.xyz/writing/ethereum-is-a-dark-forest)

**6.3 What this means for us.** If the scanner operator acts the way the careful actors above do, the exploit transaction will be **first visible when the block lands**. Mempool watching therefore cannot give pre-warning on the final step. What it can still do:
- Catch *unprivate* probing: test transactions, early failed attempts, and anything the operator sends via plain RPC (section 4B, failed-tx rate).
- Provide a *negative* signal: a landed transaction with no prior public sighting is consistent with private submission. This is an upper bound on private flow, not a count, for the single-vantage reasons in 6.1.
- Let us compare vantage points: two nodes with different peer sets, or a public mempool archive, turn the "never seen" figure into an estimate, as the darkflow author says of their own tool. (https://darkflow.martincasais.com/)

**6.4 Minimum viable visibility, in order of cost.**
1. Block-level only: a labeled-transaction feed plus our own inspector (section 5.2). Cheapest, catches post-hoc.
2. One well-peered geth node with an enlarged txpool and a pending-transaction subscription (the setup in section 3). Adds public-mempool pre-sighting for non-private probes. (https://dev.to/vathsaman/mempool-monitoring-for-mev-bots-technical-implementation-guide-4k38)
3. Second vantage point, to measure propagation error.
4. Private orderflow feeds (MEV-Share event stream, builder data): the only route to see flow a searcher with feed access sees. These are access-gated and carry terms of use; do not assume they are available to us. The Chainlink SVR example shows searchers consuming the MEV-Share event stream. (https://docs.chain.link/data-feeds/svr-feeds/searcher-onboarding-ethereum)

---

## 7. Open items and limits

- **Provider-side recon is not observable** from public data (5.1). Only an RPC vendor could see read-pattern anomalies.
- **No baseline** for how many ordinary wallets touch multiple deprecated contracts. Without it the multi-target discriminator (5.2) has an unknown false-positive rate.
- **Funding-trail and gas-calmness heuristics** are inferences here; no cited source validates them for this use.
- **Percent figures** (about 80 percent private RPC share, 10 to 50 percent searcher retention) come from single sources and may be dated; recheck before quoting.
- **Policy:** this paper contains no live target list. Target lists for deprecated-but-funded contracts are withheld from this public repo by policy.
