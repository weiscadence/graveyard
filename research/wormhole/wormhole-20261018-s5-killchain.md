# WORMHOLE SHIFT 5, Thread 3 — APT Kill Chain → DeFi Kill Chain
**Date:** 2026-10-18 · **Mode:** read-only research (web search + page fetch; no contacting anyone, no transactions)
**Question:** Take the infosec world's kill-chain frameworks and map them onto DeFi exploits — what transfers, what breaks, and what should our pre-exploit scanner steal?

**Sibling threads in this series:** `wormhole-20261018-test-before-strike.md` (the probe pattern retro), `wormhole-20261018-eip7702.md` and `wormhole-20261018-s4-7702-casefile.md` (EIP-7702 delegation), `wormhole-20261018-graveyard-inventory.md`.

**Case studies used for the mapping:**
- **UNCX VestingManager (Oct 14–16, 2026):** accounting flaw in Vesting V2's `release()` — double-counted shares let the attacker mint a leftover position draining other users' deposits. $86K first drain → $1.49M across 4 chains, 11 drain txs, copycats + MEV bots joined. Blockaid/ExVul traced it.
- **Limit Break Payment Processor V2 (Sep 24–25, 2026):** forged ERC-2771 sender (calldata offset of zero) let the attacker act as any wallet that still approved the contract — legacy Magic Eden approvals from Feb–Oct 2024 were the persistent access. ~$2.8M confirmed (660 WETH + 3,832 NFTs at zero price); 0xQuit-led whitehats rescued 23,155 NFTs (~$5.7M). Attacker still draining on Sep 29; 46 ETH went into Railgun.
- **sven.eth EIP-7702 drain (Oct 14, 2026):** victim-signed EIP-7702 authorization → attacker-sponsored type-4 tx → delegated code swept 9.1231 ETH + 1.69 TAPEETH. Same day as UNCX detection.

---

## Part 1 — Lockheed Martin Cyber Kill Chain → DeFi

The original 7-stage model (Lockheed Martin, 2011): **Reconnaissance → Weaponization → Delivery → Exploitation → Installation → Command & Control (C2) → Actions on Objectives.** The model's promise: the attacker must complete all seven stages; the defender only needs to break one (sources: Trend Micro, Picus Security explainers). Here's each stage mapped onto DeFi, with the misfits marked honestly.

### Stage 1 — Reconnaissance
**Infosec:** gather target info — network scans, OSINT, employee emails (per the Lockheed model, entirely pre-touch).
**DeFi mapping:** reading the target's verified contract source on Etherscan, pulling bytecode, mapping storage slots, enumerating token holders/approvers, checking fork state on Tenderly.
**Misfit #1 (the big one): passive on-chain recon is free, instant, and *undetectable*.** In APT-land, recon is the stage the defender most wants to catch but often can't because it happens off-premise. On-chain it's worse: the "target's internal network map" is *published by the victim*. There is no scan to detect — reading a contract costs nothing and leaves no trace. `eth_call` probes never hit the chain. Fork-based rehearsal (Foundry/Anvil) is completely invisible.
**What IS detectable:** *active* recon that touches the chain — which is exactly our test-before-strike pattern (see sibling retro). The sibling thread established the rule: probes show up on-chain when the exploit is **stateful and interactive** (Cetus May 2025: failed dry run ~2 days before; UNCX/Ostium/NEAR Intents positives), and vanish when the attack is **constructor-atomic** (Balancer V2 Nov 2025: 65-cycle exploit tuned on a fork, zero mainnet probes) or **infra-class** (Bybit Feb 2025: the test would have been the strike). So: *recon-stage detection on-chain only sees the subset of attackers who need live state — which is exactly the subset our zombie-contract scanner cares about.*

### Stage 2 — Weaponization
**Infosec:** build the malware + exploit package (compile timestamps, builder artifacts are the indicators).
**DeFi mapping:** writing the exploit contract, tuning it against a mainnet fork, assembling the calldata. The Balancer V2 attacker "rehearsed on a fork" — weaponization happened entirely off-chain.
**Misfit #2:** weaponization is *completely* invisible on-chain. No compile timestamps leak, no builder artifacts exist on the ledger. The first visible artifact is deployment — which infosec would already call *delivery*.
**What IS detectable:** the *funding* of weaponization. Tornado Cash withdrawals → fresh EOA → contract deployment is the on-chain shadow of weaponization (Balancer: 100 ETH parked in Tornado, 0.1 ETH withdrawals to fund the deployer — Conor Grogan's tracing). Forta's "Exploiter Addresses" and "Chainalysis Sanctioned Addresses" bots are, in kill-chain terms, **weaponization-stage infrastructure detectors** — they don't see the weapon being built, they see the armory being stocked.

### Stage 3 — Delivery
**Infosec:** transmit the weapon — phishing email, drive-by download, USB drop. The canonical detection point: the email gateway.
**DeFi mapping — two sub-cases, and they diverge hard:**
- **(a) Protocol exploits (UNCX, Limit Break, Balancer): there is no delivery to a victim system.** The attacker deploys their own contract and calls the public target directly. The "weapon" never crosses a defensive boundary because there is no boundary. *The kill chain's most detection-rich stage simply doesn't exist for this attack class.* This is the model's worst misfit.
- **(b) Wallet-draining (EIP-7702, ice phishing, permit phishing): delivery is real and looks exactly like infosec delivery.** The malicious authorization/signature request is delivered to the *user* via phishing site, poisoned address history, or social engineering. The sven.eth case: the victim signed an EIP-7702 authorization — the "payload" was a signature, delivered through deception. Forta's "Ice Phishing Detection Bot" is literally a delivery-stage detector.
**On-chain delivery analog for case (a):** the closest thing is *deployment of the attack contract* — a public, timestamped, content-addressed event. Infosec delivery is designed to be stealthy; on-chain deployment is *broadcast to the world*. And mempool surveillance (Blocknative-style, Forta's FlashBots Detector) is the on-chain "email gateway" — the one place you can see the weapon in transit before it executes. The misfit: private mempools / Flashbots bundles are the "encrypted email" the gateway can't read (Limit Break's attacker, UNCX copycats, and MEV bots all had private-orderflow options).

### Stage 4 — Exploitation
**Infosec:** the payload executes against a vulnerability (CVE in logs, shellcode artifacts).
**DeFi mapping:** the attack transaction executes. This is the *best* fit in the whole model — the exploit tx is atomic, deterministic, fully replayable, and permanently recorded. Every DeFi exploit is exploitation-stage by construction.
**Misfit #3 (atomicity):** infosec assumes exploitation is a *moment inside a campaign* — the attacker's foothold then enables the later stages. A flash-loan exploit compresses **all seven stages into one transaction** (~12 seconds). Recon→weaponization→delivery→exploitation→installation→C2→actions happen inside a single block, and the "left of boom" window for stages 1–6 can be literally zero. The kill chain's core promise — "break any one stage and the attack fails" — degrades when six stages are off-chain/invisible and the seventh is atomic. The exception that proves the rule: Hypernative flagged the Kinetic Market (Flare) staged exploit ~6 minutes after the attacker's first on-chain move and the team paused in time to save $5M — staged, multi-tx attacks *do* expose a kill chain; atomic ones don't.

### Stage 5 — Installation
**Infosec:** establish persistence — scheduled tasks, registry run keys, web shells.
**DeFi mapping — this is where EIP-7702 lives, and the answer to the task's question is YES:**
- **EIP-7702 delegation is *literally* the installation stage.** Signing an authorization sets the EOA's code to `0xef0100 || <delegate>` — a persistent backdoor that survives the theft itself (the sven.eth delegation *remained active after the drain*, leaving the wallet open to re-draining until cleared). Our delegation scanner is, in kill-chain terms, an **installation-stage detector**. The Medium/2026 survey finding — 8,200 EOAs delegated to Wintermute's exposed `Poisoner` contract, the biggest 7702 "use case" being address poisoning — reads exactly like an APT persistence census.
- **Limit Break is the deeper case:** the "installed" persistence wasn't placed by the attacker at all — it was *two-year-old token approvals* granted during normal Magic Eden use (Feb–Oct 2024). The attacker didn't need an installation stage; the victim had pre-installed the backdoor themselves. Kill-chain implication: **on DeFi, installation often precedes weaponization by years**, which inverts the model's temporal assumption. Detection analog: approval-age monitoring — "this wallet granted operator rights to a deprecated contract 700 days ago" is the on-chain version of "this host has a scheduled task from 2022."
- Other installation primitives: CREATE2-counterfactual deployments (precomputed addresses as dormant infrastructure), proxy implementation slots (upgrade = re-installation), malicious token contracts users were induced to approve.
**Transferable detection (direct from infosec):** EDRs detect installation by watching for *new persistence mechanisms*, not by understanding the payload. Same rule works on-chain: alert on *state transitions that create persistence* — delegation designator set, new unlimited approval to an unverified contract, proxy admin changed — regardless of whether the target "looks malicious" yet. Our scanner should treat these as installation-stage events with high prior weight.

### Stage 6 — Command and Control
**Infosec:** beaconing, DNS tunneling, C2 frameworks (Cobalt Strike/Sliver signatures) — the canonical network-detection stage.
**DeFi mapping — mostly a misfit, with one real analog:**
- **Misfit #4:** smart-contract exploits are **fire-and-forget**. There is no compromised host to command, no beaconing, no exfil channel to maintain. The blockchain itself is the execution environment; the attacker issues one transaction and the chain does the rest. The entire C2 stage collapses into the exploitation transaction.
- **The real analog: the mempool/private-orderflow layer as C2 infrastructure.** What the attacker *does* need is transaction delivery with ordering guarantees — Flashbots bundles, private relays, block-builder relationships. Forta's FlashBots Detector ("alerts when a transaction bypasses the mempool") is, functionally, a **C2-channel detector**: it flags use of the hidden command path. And post-exploit, the "C2" becomes the laundering coordination — but that's exfiltration, not C2.
- **Where C2 genuinely reappears:** infra-class attacks (Bybit/Lazarus — the Safe front-end JS injection was staged, triggered, and reverted via attacker-controlled infrastructure) and drainer-as-a-service kits with on-chain config. For pure protocol exploits, drop the stage.

### Stage 6.5 — Where test-before-strike sits
The task asked explicitly. Answer: **it straddles Reconnaissance and Weaponization-testing, and it is the single most detectable pre-exploitation stage on-chain.** In infosec terms it's "active scanning" (T1595) meets "weapons testing" — the adversary validating the exploit against live target state because simulation is insufficient (the sibling retro's rule: stateful/interactive exploits need live state). Infosec's detection guidance for recon-stage activity is "look for the probe, then watch the prober" — which is precisely Forta's Attack Detector Feed pattern: *combine past alerts under a common address to emit a high-precision alert around protocol attacks.* The kill-chain framing upgrades the test-before-strike retro from "interesting pattern" to "the designated pre-exploitation detection stage" — everything before it is invisible by construction, everything after it is the strike.

### Stage 7 — Actions on Objectives
**Infosec:** data theft, ransomware, destruction.
**DeFi mapping:** the drain itself (funds leaving the victim contract), then laundering: mixer deposits (Railgun — Limit Break attacker put 46 ETH in), bridging to other chains (UNCX: 4 chains; this is *cross-chain lateral movement* as exfil), peel chains, CEX cashout.
**Fit:** this is the second-best fit after exploitation. UNCX's 11 drain transactions across 4 chains with copycats and MEV bots piling on is "actions on objectives" with perfect public telemetry. Infosec's exfil-stage detections (DLP, egress monitoring) map to: large-balance-decrease alerts (Forta's Large Balance Decreases bot), mixer-interaction alerts, bridge-outflow monitoring. **Transferable idea:** infosec sizes exfil alerts by *deviation from baseline egress* — same math works for TVL outflow velocity per contract.

### Kill-chain critique worth importing: the Unified Kill Chain
Paul Pols' Unified Kill Chain (2017, Fox-IT/Leiden) merged the Lockheed model with ATT&CK into 18 ordered phases precisely because the original is too linear, too perimeter-biased, and too malware-centric — the same three criticisms our mapping just produced independently (no perimeter, non-linear/atomic, no-malware protocol exploits). The UKC's "Get In / Through / Out" structure is arguably a *better* native fit for DeFi: most protocol exploits are all "Through" (no perimeter to get in through) — which tells you the defensive investment belongs in the middle of the chain, not at the edges. Worth knowing it exists before we reinvent it. (Source: Wikipedia "Cyber kill chain" + Pols' thesis.)

---

## Part 2 — MITRE ATT&CK → DeFi analogs

ATT&CK is not a kill chain — it's a behavior matrix (tactics = the "why," techniques = the "how," IDs = the shared vocabulary). The current Enterprise matrix has 14–15 tactics (v19 split the old Defense Evasion TA0005 into **Stealth** TA0005 and **Defense Impairment** TA0012/TA0112). MITRE also shipped **AADAPT** (Adversarial Actions in Digital Asset Payment Technologies, July 2025) — an ATT&CK-modeled matrix specifically for crypto, with 11 tactics and 38 techniques covering consensus, smart contracts, and digital-asset fraud. That MITRE itself built the crypto matrix is strong evidence this mapping exercise is legitimate, not analogy-abuse. (Sources: attack.mitre.org tactics page; MITRE press release July 14, 2025; KPMG/Infosecurity Magazine coverage.)

Technique-by-technique, with on-chain parallels. IDs grounded in ATT&CK sources:

### TA0043 Reconnaissance
- **T1595 Active Scanning** (sub-techniques T1595.001 Scanning IP Blocks, T1595.002 Vulnerability Scanning, T1595.003 Wordlist Scanning): the on-chain parallel is *contract scanning* — systematically probing deprecated contracts for known-vulnerable patterns. Our zombie-contract scanner **is** T1595.002 stood up as a defensive tool; the unknown operator's campaign is the offensive version of the same technique. T1595.003 (wordlist) ≈ fuzzing function selectors / storage slots.
- **T1596 Search Open Technical Databases**: Etherscan, Dune, Tenderly sims, GitHub — passive, invisible, free.
- **T1589 Gather Victim Identity Information** (T1589.002 Email Addresses etc.): ENS names, address labeling, Nansen-style clustering. sven.eth's ENS name made the victim *more* legible, not less.
- **T1591 Gather Victim Org Information**: mapping a protocol's multisig signers, timelock delays, admin roles — the "org chart" is on-chain.
- **Honest note:** ATT&CK recon techniques sit on the PRE platform (outside the victim environment) — which is *everywhere* on-chain. The tactic transfers; the "detect the scan" guidance mostly doesn't (see Misfit #1).

### TA0042 Resource Development
- **T1583 Acquire Infrastructure**: funding attacker EOAs (Tornado Cash → fresh wallet hops — the Balancer 0.1 ETH funding pattern).
- **T1587 Develop Capabilities / T1588 Obtain Capabilities**: writing or buying exploit contracts; drainer-kit-as-a-service.
- **T1608 Stage Capabilities**: deploying the attack contract ahead of the strike — *visible on-chain*, unlike infosec staging.

### TA0001 Initial Access
- **T1190 Exploit Public-Facing Application**: *the* canonical DeFi technique — the exploit transaction against the vulnerable contract. UNCX's `release()`-then-`cancel()` sequence and Limit Break's forged-sender call are both T1190 procedures.
- **T1566 Phishing** (T1566.001 Spearphishing Attachment, .002 Link): ice phishing → malicious signature/authorization requests; the EIP-7702 Poisoner delegation flow is T1566 with the "attachment" being an authorization tuple.
- **T1078 Valid Accounts**: compromised deployer/admin keys (the Bybit-class precursor; every "rug" that was actually a key theft).
- **T1133 External Remote Services**: abused relayer/meta-transaction infrastructure — Limit Break's trusted-forwarder forgery is a perverse T1133 (the "remote service" was the protocol's own relayer).

### TA0002 Execution → TA0003 Persistence
- **Execution** on-chain is trivially the transaction itself — no useful sub-mapping; the EVM *is* the command interpreter.
- **Persistence** is where the money is (see Kill Chain Stage 5): EIP-7702 delegation designators, stale ERC-20/721 approvals (Limit Break's 2024 approvals), CREATE2 dormant deployments. ATT&CK's persistence-detection guidance — *"alert on new persistence mechanisms, then investigate"* — is directly importable.

### TA0005 Stealth (ex-Defense Evasion) — the richest tactic for DeFi
ATT&CK v19 moved T1027, T1036, T1070, T1055 et al. under **Stealth** (defenses still work; the adversary blends in) vs **Defense Impairment** (breaking the defenses). The distinction is useful on-chain:
- **T1027 Obfuscated Files or Information** (subs include T1027.002 Software Packing, T1027.005 Indicator Removal from Tools): unverified contracts, flattened-but-misleading source, CREATE2 metamorphic contracts, stripped metadata. *The* reason "verified on Etherscan" is a trust signal.
- **T1036 Masquerading**: address poisoning — lookalike addresses (the Wintermute-exposed `Poisoner` contract's entire business model, 8,200 delegated EOAs), fake tokens mimicking legit ones.
- **T1070 Indicator Removal**: mixers and privacy pools as trail-deletion. Limit Break's 46 ETH → Railgun is T1070 as a post-exploit procedure. Note the irony: on-chain, indicator removal happens *after* the indicators are permanently recorded — it's deletion of *linkability*, not of evidence.
- **T1497 Virtualization/Sandbox Evasion**: exploit contracts that detect forked-chain simulation (e.g., reverting when `tx.origin` is a known whitehat/simulator address) — real, observed behavior in MEV/drainer contracts.
- **T1110 Brute Force** (Credential Access, but relevant): vanity-address grinding for poisoning; private-key grinding is the limiting case.
- **Defense Impairment analog:** attacks on the *monitoring itself* — e.g., exploiting during known monitor downtime, or the UNCX response pattern where the team raised fees to 1,000 ETH to brick the contract's usability (defender impairing the *attacker's* tooling — impairment cuts both ways).

### TA0007 Discovery
- **T1046 Network Service Discovery**: enumerating which wallets approved a zombie contract — the attacker's pre-strike target list (revoke.cash's checker does this defensively; the Limit Break attacker did it offensively).
- **T1083 File and Directory Discovery**: storage-slot enumeration, mapping a proxy's implementation slots.
- Our scanner's inventory pass (`graveyard-inventory.md`) is defensive T1046/T1083.

### TA0010 Exfiltration
- **T1048 Exfiltration Over Alternative Protocol** (subs .001/.002 symmetric/asymmetric encrypted non-C2): bridging stolen funds to another chain (UNCX's 4-chain spread), Railgun/private-pool deposits as the *encrypted* alternative channel.
- **T1020 Automated Exfiltration**: the drain transaction itself — fully automated, no human in the loop.
- **T1030 Data Transfer Size Limits**: splitting drains to stay under monitoring thresholds — UNCX's 11 drain transactions (attacker + copycats) have this shape; Balancer's 0.9–1 ETH THORChain test transfers before 35 ETH swaps (sibling retro) are T1030-shaped cashout behavior.
- **T1041 Exfiltration Over C2 Channel**: withdrawing through the *same* contract/path as the attack (the Limit Break WETH drain "inverted" the same V2 logic — exfil over the attack channel).

### TA0040 Impact
- Fund loss is the impact; **oracle manipulation** is the closest thing to ATT&CK's data-manipulation techniques; governance attacks (passing malicious proposals) are the DeFi-native impact technique with no clean ATT&CK parent — a genuine gap worth proposing upstream (or into AADAPT).

### What AADAPT adds
AADAPT's tactic list (Reconnaissance, Resource Development, Initial Access, Execution, Privilege Escalation, Defense Evasion, Credential Access, Lateral Movement, Collection, Impact, **Fraud**) confirms the industry mapping and adds **Fraud** as a first-class tactic — the thing ATT&CK lacks for pig-butchering, fake-exchange, and drainer-kit economics. For our scanner, AADAPT is the matrix to watch; ATT&CK is the vocabulary to borrow.

---

## Part 3 — Diamond Model → the zombie-contract scanner

The Diamond Model (Caltagirone, Parker, Weidman 2013): every intrusion event is an **adversary** using a **capability** over **infrastructure** against a **victim**, with meta-features (timestamp, phase, result, direction, methodology, resources) and per-feature confidence values. The analytic move is **pivoting**: start from the vertex you know, pivot to the ones you don't. ("You know the victim and found a C2 domain — that's infrastructure. Search for other victims that touched it… cluster enough and you have an adversary." — skillthropic explainer.)

Applied to our unknown operator systematically hitting deprecated contracts:

| Vertex | Zombie-scanner instantiation |
|---|---|
| **Adversary** | Unknown — the operator cluster we're trying to build. Currently a null vertex with low confidence; the *output* of the analysis, not the input. |
| **Capability** | The exploit procedures: forged ERC-2771 sender (Limit Break), share-accounting double-count (UNCX), EIP-7702 delegation abuse. Observable in calldata and trace. *Highest-confidence vertex* — the chain records it perfectly. |
| **Infrastructure** | Attacker EOAs, deployed attack contracts, funder wallets, Tornado/Railgun withdrawal → deployment funding chains, Flashbots/private-relay usage, the deprecated contracts themselves as *delivery surface*. Pivotable via funding-graph analysis. |
| **Victim** | The zombie contracts + their lingering approvals/TVL. *Known vertex* — our inventory (`graveyard-inventory.md`, `expansion-targets.md`) is literally the victim list. |

**Why the Diamond Model fits this problem better than the kill chain does:**
1. **Pivoting is the job.** We start with victim (inventory) + capability (exploit pattern from forensics) and need infrastructure → adversary. The model's whole point is formalizing exactly that walk. Each pivot is a concrete query: *which EOAs called this function signature on these contracts? → which funder wallets fed those EOAs? → which other contracts did that funder cluster touch?*
2. **Confidence values are honest.** The model *requires* per-vertex confidence — which matches our epistemic state: capability ~certain (on-chain trace), victim certain (our inventory), infrastructure medium (funding graphs are noisy), adversary low (a cluster, not a name). Most scanner outputs pretend all four are equally known; the diamond forces the honesty.
3. **Meta-feature "phase" links Diamond → Kill Chain.** Each diamond event carries its kill-chain phase, so a pivot that lands on "funding EOA activated" is automatically a stage-2/3 detection, and "probe tx to zombie contract" is a stage-1/6.5 detection. This is the integration the frameworks were designed for (the triple-combination practice: kill chain for flow, ATT&CK for behavior detail, Diamond for attribution).
4. **Activity threads = the campaign.** The operator's hits across multiple zombie contracts form an activity thread — ordered diamond events sharing infrastructure/capability vertices. *Our scanner's end state shouldn't be "a list of vulnerable contracts," it should be "a set of activity threads, each resolving toward an adversary cluster."* That's the upgrade this model offers.
5. **The on-chain advantage the model doesn't assume:** in infosec, infrastructure pivoting is hard because infra is hidden (bulletproof hosters, fast-flux). On-chain, the infrastructure graph is *public and permanent* — funding chains, deployer links, and contract interactions are all queryable forever. Diamond pivoting on-chain is strictly easier than the model was designed for; the residual hardness is all in the adversary vertex (pseudonymity), not the infrastructure vertex.

**Misfit:** the model's "victim" vertex assumes a victim *organization* with an internal network the adversary moves through. Our victims are *contracts* — code with no interior. There's no lateral movement inside a victim, no privilege escalation within it; the "network" is the whole chain and it's flat. The victim vertex still works (it's the target), but the edges adversary→victim and infrastructure→victim are thinner than the model expects — most analytic leverage is on the adversary→capability→infrastructure triangle.

---

## Part 4 — Detection per stage: what infosec recommends, what transfers

| Kill-chain stage | Infosec detection doctrine | On-chain transfer | Verdict |
|---|---|---|---|
| Recon | Detect scanning (IDS); reduce exposed surface | Passive reading undetectable; **detect active probes** (test-before-strike txs); monitor *new* contracts making view-call patterns against watched targets | Partial — only the active subset |
| Weaponization | Malware sandboxing, compile artifacts | Invisible off-chain; **detect the shadow**: mixer→fresh-EOA funding chains, attack-contract deployments interacting with watched targets (Forta Exploiter-Addresses pattern) | Shadow-only |
| Delivery | Email gateway filtering | **Mempool surveillance** as the gateway (Blocknative-style); Flashbots/private-orderflow as the encrypted channel you can't read (Forta FlashBots Detector flags its *use*) | Transfers with a known blind spot |
| Exploitation | EDR behavioral rules | **On-chain runtime monitors** (Forta, Hypernative, OZ Defender); function-signature + asset-flow anomaly detection; the atomic-tx problem means this is often *post*-exploitation | Transfers; speed is the issue |
| Installation | New persistence mechanisms (run keys, scheduled tasks) | **Alert on persistence-creating state transitions**: EIP-7702 delegation designator set (our scanner!), new approvals to risky contracts, proxy admin changes — *regardless of payload judgment* | Strong transfer — best in class |
| C2 | Beaconing/DNS-tunnel detection | Mostly N/A (fire-and-forget); **detect private-orderflow usage** and repeated-caller patterns as the residual analog | Weak — don't over-invest |
| Actions/Objectives | DLP, egress baselining | **TVL-outflow velocity alerts** (Forta Large Balance Decreases), mixer-deposit alerts, bridge-outflow monitoring; size by deviation from baseline like DLP does | Strong transfer |

**The meta-lesson from infosec:** mature SOCs don't try to win at every stage — they pick the stages where *their* telemetry is richest and build "progression" logic across stages (the EDR that raises severity when recon→delivery→execution chain to the same host). Our telemetry is richest at **Installation** (state transitions are permanent and semantic), **Exploitation** (full traces), and **Actions** (value flows) — and uniquely, at **test-before-strike** (the visible slice of Recon). The scanner's detection budget should weight those four and treat the rest as pivot material, not alert material.

---

## The misfits, collected (as valuable as the fits)

1. **Recon visibility is inverted.** APT recon is stealthy-but-detectable-in-principle; on-chain passive recon is *impossible* to detect and the target's "network map" is public. The defender's advantage flips: everything *after* weaponization is public.
2. **Atomicity collapses the chain.** Six stages can live inside one transaction. "Break any one stage" fails when the only visible stage is the last one.
3. **Delivery often doesn't exist.** No victim system to deliver to in protocol exploits — the model's most detection-rich stage vanishes for our primary threat class. (It reappears for wallet-draining, where the model fits well.)
4. **Installation can precede weaponization by years.** Limit Break's 2024 approvals were persistence installed before the exploit was conceived. The model's temporal ordering breaks; approval-age becomes a risk dimension the model doesn't name.
5. **No perimeter, no interior.** No lateral movement inside a victim, no privilege escalation within it — the chain is flat. Half of ATT&CK's mid-chain tactics (Lateral Movement, Privilege Escalation *within* the target) have thin analogs.
6. **C2 is vestigial** for protocol exploits; the chain is the execution environment.
7. **Attribution asymmetry flips.** Infosec: infra hidden, victim interior visible. On-chain: infra public and permanent, adversary identity pseudonymous. Diamond pivoting is *easier* on-chain except for the final vertex.
8. **Copycats break the single-adversary assumption.** UNCX went from 1 attacker to 11 drain txs with copycats + MEV bots in ~48 hours. The kill chain models *an* adversary; DeFi exploits are *broadcast vulnerabilities* — the "campaign" is a mempool-wide race. Detection must assume N adversaries, including whitehats running the same capability (0xQuit's rescue used the identical exploit path).

---

## Sources

**Frameworks:**
- Lockheed Martin Cyber Kill Chain stages: https://www.trendmicro.com/en/what-is/cyber-attack/cyber-kill-chain.html ; https://www.picussecurity.com/resource/blog/cyber-kill-chain-explained
- Kill-chain per-stage indicators + ATT&CK integration workflow: https://eliteai.tools/agent-skills/analyzing-cyber-kill-chain
- Kill-chain critiques, Unified Kill Chain (Paul Pols 2017, 18 phases): https://en.wikipedia.org/wiki/Cyber_kill_chain ; https://www.stormshield.com/news/kill-chain-learn-more-to-protect-yourself-better/
- Framework comparison (Kill Chain / ATT&CK / Diamond / UKC): https://www.xn--zb0bow85w7idd5f0pc46q.com/t/en/cyber-kill-chain.html
- MITRE ATT&CK Enterprise tactics (incl. v19 Stealth TA0005 / Defense Impairment TA0112 split): https://attack.mitre.org/tactics/enterprise/
- Tactic IDs + technique ID system: https://www.kandibrian.com/articles/mitre-technique-codes.html
- T1595 Active Scanning: https://attack.mitre.org/techniques/T1595/ (subs .001/.002/.003)
- PRE matrix recon techniques: https://attack.mitre.org/matrices/enterprise/pre/
- T1027 Obfuscated Files or Information: https://attack.mitre.org/versions/v4/techniques/T1027/ ; v19 Stealth reassignment: https://breachsimrange.io/blog/defense-evasion-is-dead/
- Exfiltration techniques (T1020/T1030/T1041/T1048): https://attack.mitre.org/versions/v14/tactics/TA0010/
- MITRE AADAPT launch (July 14, 2025): https://www.mitre.org/news-insights/news-release/mitre-introduces-aadapt-cybersecurity-framework-cryptocurrency ; https://www.infosecurity-magazine.com/news/mitre-launches-new-framework/ ; https://kpmg.com/in/en/insights/2025/11/adversarial-actions-in-digital-asset-payment-technologies-aadapt.html
- Diamond Model (Axiom 1, core features, meta-features, pivoting): https://threatintel.academy/wp-content/uploads/2020/07/diamond-model.pdf ; https://www.skillthropic.com/blog/kill-chain-diamond-model-attack-frameworks

**Cases:**
- UNCX VestingManager exploit ($86K → $1.49M, 4 chains, 11 txs, copycats): https://cryptocompass.com/articles/uncx-vesting-v2-exploit-drains-1-49m-across-four-chains ; https://blockchainreporter.net/uncx-vesting-v2-exploit-four-chains/ ; https://news.bitcoin.com/security/an-86000-exploit-rocks-a-crypto-pool-built-to-lock-tokens/
- Limit Break Payment Processor V2 (Sep 24–25, 2026, forged ERC-2771 sender, ~$2.8M, 0xQuit rescue): https://sigintzero.com/blog/limit-break-2-8m-forged-erc2771-sender ; https://www.credora.network/blog/posts/risk-in-defi-september-post-mortem/ ; https://publicaml.org/limit-break-hack/ ; https://shattered.io/magic-eden-limit-break-exploit-2-8-million-2026/
- sven.eth EIP-7702 drain (Oct 14, 2026): https://crypto.news/ethereum-user-loses-22k-in-eip-7702-wallet-attack/ ; https://en.coinotag.com/exvul-ethereum-eth-wallet-drained-9-1231-eth-eip-7702
- EIP-7702 Poisoner census (8,200 EOAs) + delegation-as-persistence: https://medium.com/@yoyoginosakura/hunted-eip-7702-delegations-on-ethereum-mainnet-for-a-month-most-werent-wallets-e8320993d864 ; https://dev.to/kaminariresearch/the-wallet-looked-normal-on-the-explorer-six-eip-7702-signatures-said-otherwise-2lg1

**Detection practice:**
- Real-time monitoring limits (Hypernative Kinetic Market 6-min save; KelpDAO 46-min pause; ERC-7265): https://cryptoaimeta.com/ai/smart-contract-auditing/
- Forta DeFi + Stablecoin threat detection kits (bot catalog incl. Attack Detector Feed/alert combiner, FlashBots Detector, Ice Phishing, Large Balance Decreases): https://docs.forta.network/en/latest/defi-starter-kit/ ; https://docs.forta.network/en/latest/stablecoin-starter-kit/
- FlashGuard dusting counterattack (mempool-pattern disruption): https://encrypthos.com/guide/secure-your-funds-from-flash-loan-exploits.md
- Sibling thread: `wormhole-20261018-test-before-strike.md` (Cetus/Bybit/Balancer retro — the empirical base for the stage-6.5 claim)
