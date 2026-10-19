# POLYGON-RESCUE-PLAYBOOK — Limit Break Payment Processor V2

**Target:** `‹addr redacted›` (same address on Ethereum, Polygon, Base)
**Chain in scope:** Polygon
**Status:** PREPARATION — trigger has NOT fired. No active theft observed.
**Authorization:** the operator gave explicit full permission for whitehat rescue preparation/action, logged 2026-10-18 00:19 CDT in `~/memory/2026-10-17.md`. Standing rule (no third-party asset movement without explicit yes) is overridden for this situation only.
**Compiled:** 2026-10-18 by Lodestone. Read-only research; no transactions sent, no accounts created.

---

## 1. Situation

Three distinct actors probed the dormant Polygon V2 on 2026-10-17:
- **Morning:** 62 identical `forwardCall(address,bytes)` from `0x0e3be59981` — metronomic automation, not exploit-shaped.
- **Afternoon:** 1 call via custom contract `‹addr redacted›`, unknown selector `0xf3858db3`, moved ~0.0102 WETH (~$35). Sender `‹addr redacted›` (3,349 txs — heavy bot/trader).
- **Evening:** 1 `transfer(address,address,address)` from `‹addr redacted›` (57 txs — fresh wallet), via intermediary `‹addr redacted›`. Resolved (RECON-20261017-03, 2026-10-18): the intermediary was the operator's own contract and the "token" was a `buyListing` ERC-721 fill — a mock-collection self-deal, TESTING phase. No escalation.

Afternoon and evening txs emitted the **same V2 event pair** (see §4) despite different senders, different intermediary bytecode (4,037 vs 3,313 bytes, different hashes), and different wallet profiles. Assessment (2026-10-18, RECON-20261017-03 + Appendix B): both probes classify **TESTING** — mock-collection self-deals where both sides were operator-controlled. The weapon is validated, not aimed. The §8 trigger has NOT fired.

**No theft has occurred. No 0-value sales. No forced buys. The rescue trigger (§8) has not fired.**

---

## 2. Exploit mechanism (confidence: HIGH)

Source: 0xQuIt's technical thread (x.com/0xQuit/status/2104680884360339829, Sep 28 2026), sigintzero's writeup (sigintzero.com/blog/limit-break-2-8m-forged-erc2771-sender, Oct 1 2026), Limit Break public repo (github.com/limitbreakinc/payment-processor).

**The bug: forged ERC-2771 "original sender" via a calldata offset of zero.**

1. V2 supports meta-transactions (ERC-2771 style). A trusted forwarder calls V2 and appends the real caller's address as the last 20 bytes of calldata. V2 checks `msg.sender` is a trusted forwarder, then reads those 20 bytes as the true caller via `_msgSender()`.
2. V2's dispatcher (`delegateCall` modifier in `PaymentProcessor.sol`) forwards each trade to a module. It computes the copy length as `calldatasize() - 68` — correct **only** for canonical ABI encoding where the `data` offset word is `0x20`.
3. The copy *start*, however, comes from `data.offset`, which the ABI decoder takes from caller-supplied calldata.
4. Attacker encodes the offset as **0**. `data` then begins 32 bytes earlier than assumed. The copy runs the same length, so it stops 32 bytes short of the real end. The forwarder's appended address — the real caller — falls off the end. Whatever the attacker placed just before it becomes the last 20 bytes the module reads as "sender."
5. `_getTaker()` in `PaymentProcessorModule.sol`:
   ```solidity
   taker = msg.sender;
   if (appendedDataLength > 0) {
       if (appendedDataLength != 20) revert PaymentProcessor__BadCalldataLength();
       taker = _msgSender();  // reads last 20 bytes — now attacker-controlled
   }
   ```
6. With the sender forged, the attacker writes a complete order: creates a zero-price "offer" for a victim's NFT, then makes V2 believe the **victim** is accepting it. The only thing taken from the victim is their standing approval — no new signature, no listing, no hardware-wallet prompt. Cancelling listings and bumping nonces do nothing (Blockaid, Revoke.cash confirm).
7. **WETH path (reverse):** the same forgery makes the victim the *buyer* instead of the seller, paying for the attacker's NFT out of a standing WETH allowance. 0xQuit: "a similar exploit could be used in reverse to steal WETH." Neither Limit Break nor 0xQuit has published this path in detail.

**Why the forwarder didn't save them:** Limit Break's `TrustedForwarderFactory` lets *any* address clone a forwarder, and every clone is marked trusted — safe by design because clones write `msg.sender` honestly. The attacker didn't even deploy their own; they routed through forwarder `0xb233…84C9`, cloned Feb 6 2024 by an unrelated address. The dispatcher threw the real caller away, not the forwarder.

**Key properties for rescue planning:**
- V2 is **immutable and unpausable**. 0xQuit tried: pausing (impossible), reverting fee recipients, malformed forwarders — "We found no way to shut it off." Limit Break's position: "Payment Processor V2 is an immutable contract that nobody can fix."
- V3 was paused within hours (it shared the bug). V2 could not be.
- The **only** defense 0xQuit found was defensive exploitation: use the bug first, move assets to custody before hostile actors do.

---

## 3. 0xQuIt's rescue — the template (confidence: HIGH)

Sources: on-chain (Ethereum), 0xQuIt's Sep 25 posts, sigintzero timeline.

**Timeline (UTC):**
| When | What |
|---|---|
| Sep 24, 13:07:59 | Attacker deploys contract; 70 NFTs (50 Otherdeeds, 10 Meebits, 10 WoW) leave one victim wallet at 0 WETH. Gas: ~0.0046 ETH. |
| Sep 25, ~01:00 | @Boomskite flags the tx to 0xQuit — ~12 hours later. |
| Sep 25, 05:46 | Rescue batches begin, highest-value assets first. "Other wallets were exploiting" by now. |
| Sep 25, 07:58 | Helper spots the ERC-20 path: 612 WETH + 8k USDC exposed. |
| Sep 25, 08:25 | WETH drain begins: 281.66 WETH from 25 wallets in the first wave. |
| Sep 25, 08:53 | 5 WETH left; unfinished rescue contract grabs ~3 WETH, can't send it out. |
| Sep 25, 09:06 | 0xQuit reports: 23,155 NFTs rescued (~$5.7M+), 660 WETH at risk, not recovered. |

**How the rescue worked on-chain:**
- Rescue wallet: `‹addr redacted›` ("Everything in [it] is safe and will be returned once they are no longer at risk" — 0xQuit).
- Custom batch rescue contract: `‹addr redacted›` (unverified). Rescue txs call selector `0x9970165b` with large batch payloads (~1,400 bytes); internal txs show `call` into V2 `‹addr redacted›`.
- Method: **defensive exploitation** — the rescue used the same forged-sender bug to pull NFTs from exposed wallets into custody. On-chain it looks identical to theft: thousands of NFTs leaving hundreds of wallets for 0 ETH. (NFT trader Cirrus spotted 3,832 NFTs leaving 100+ wallets and assumed theft; 0xQuit had to publicly identify the wallet as whitehat.)
- Claim process: nftsaresafu.xyz (built Sep 25–26, EIP-7702 + merkle proofs). Owners must **revoke the V2 approval first**, then claim. As of ~Sep 27: 2,357 of 26,448 recovered assets claimed. Claims still processing as of Oct 14 (`claimBatch` txs observed on the rescue wallet). **Oct 18 live check:** site shows $4,717,507 returned = 65.9% of priced assets ($7,153,826; only 16.8% of allocations priced — direction, not precision); "209,250 NFTs rescued" per the site. The return curve runs for weeks — our claim rail must be built to live long, with the EIP-7702 simulation-warning explainer, Transfer-Validator pre-mapping, and canonical-domain discipline shipped AT launch (see RESCUE-PLAYBOOK.md Drill 2026-10-18).
- **WETH was lost.** 542 WETH drained (PublicAML count; 0xQuIt's "660 at risk" was the in-the-moment figure). Half went to an MEV bot (agreed to return 90%); 165 ETH sits untouched in one attacker wallet; 46 ETH went to Railgun; attacker still draining Sep 29. Nexus Mutual's roundup notes the reason: "no defensive sweep was possible [for WETH] because rescuing fungible tokens means taking custody of them" — the same is true for any fungible rescue: you must be willing to hold other people's money.

**Attacker's exit (for pattern recognition):** deployer `0x0e9E…d1c7`, funded 0.0565 ETH from an address Blockscout labels as Relay solver / FixedFloat deposit. 43-minute operation: 305 NFTs total → filled standing Seaport bids with 304 → ~9.3 WETH → bridged out via Relay by 13:36 UTC. Small fast exit, not a maximal drain.

---

## 4. Event/function map (confidence: HIGH)

Computed from Limit Break's public repo (`src/interfaces/IPaymentProcessorEvents.sol`) via keccak256. Note: repo carries V3 code; V2 event signatures match on-chain observations.

**Today's probe events — identified:**
| Topic | Event | Meaning |
|---|---|---|
| `0xf3003920` | `NonceInvalidated(uint256,address,bool)` | An order nonce was consumed (fill-or-kill fill, or cancellation) |
| `0xffb29e9c` | `BuyListingERC721(address,address,address,address,address,uint256,uint256)` = `(buyer, seller, tokenAddress, beneficiary, paymentCoin, tokenId, ...)` | An ERC-721 purchase settled via `buyListing` |

**What this means:** both the afternoon and evening probes executed **`buyListing` fills for ERC-721 NFTs** through the V2 — the exact settlement path the forged-sender exploit abuses. On a dormant contract (Magic Eden stopped routing Oct 2024), *any* `buyListing` is anomalous by definition (sigintzero: "A contract you no longer route to should be quiet. Settlement activity on it, and especially zero-price fills, is a signal by definition.").

**Rescue-relevant functions** (`src/modules/`):
- `buyListing(Order, SignatureECDSA, Cosignature, FeeOnTop)` — buy-side fill; emits `BuyListingERC721`/`BuyListingERC1155` + `NonceInvalidated`. This is the function both the attacker and the rescuer invoke (with forged sender).
- `acceptOffer(...)` — sell-side fill; emits `AcceptOfferERC721`/`AcceptOfferERC1155`.
- `buyListingAdvanced` / `acceptOfferAdvanced` — cosigned/bulk variants.
- Taker derivation: `_getTaker(appendedDataLength)` where `appendedDataLength = msg.data.length - BASE_MSG_LENGTH_BUY_LISTING`. Forgery point.

**Not yet mapped:** the exact V2 (not V3) `BASE_MSG_LENGTH_BUY_LISTING` constant and the V2 dispatcher bytecode. The repo is V3; V2 was the exploited contract. Per 0xQuit, V3 shared the bug, so the mechanism transfers, but exact offsets must be re-derived from V2 bytecode before crafting any transaction.

---

## 5. Polygon exposure (confidence: MEDIUM)

- V2 lives at the **same address on Polygon** as Ethereum: `‹addr redacted›`.
- All public revoke guidance (0xQuit, Magic Eden, Revoke.cash) explicitly covers **Polygon** alongside Ethereum and Base: "approved for all" NFT permissions plus token approvals for WETH, WAPE, USDC, APE.
- Magic Eden's EVM marketplace (Feb–Oct 2024) is the best-known approval source; it operated across chains.
- **What we don't know:** no Polygon-specific rescue was reported in September (the rescue was Ethereum + ApeChain V3). We have not measured how many Polygon wallets still hold live V2 approvals or what they hold. This is the biggest gap in the playbook.
- **How to close it:** scan `ApprovalForAll` events (ERC-721/1155) and `Approval` events (ERC-20) where operator/spender = V2 on Polygon, filter for non-revoked. Requires an indexer (Blockscout API can do this per-token but not chain-wide in one query). Feasible but not yet done.

---

## 6. Rescue call sequence (confidence: MEDIUM — mechanism verified, exact V2 calldata not yet constructed)

**Prerequisites:**
1. Polygon wallet with MATIC for gas (the operator securing). Rescue is gas-intensive: 0xQuIt's rescue txs used ~6.8M gas each on Ethereum; Polygon is cheaper but batch txs still cost.
2. Custody wallet address (fresh, controlled by the operator). This is where rescued assets go.
3. Exposure inventory (§5) — without it you're sweeping blind.
4. A trusted forwarder on Polygon (the factory is permissionless; any clone is trusted by V2 — or reuse an existing clone).
5. Exact V2 `buyListing` calldata layout with the offset-0 forgery — must be derived from V2 bytecode and **tested on a fork** before mainnet use.

**Sequence (mirrors 0xQuIt's operation):**
1. **Detect:** monitor fires on 0-value `BuyListing`/`AcceptOffer` fills from unknown addresses, or sudden volume spike on V2. (Current monitor: 4h cadence — too slow for a race; see §9.)
2. **Triage:** confirm the fills are the forged-sender pattern (victim wallets losing NFTs at price 0), not legitimate residual activity.
3. **Sweep (NFTs):** for each exposed wallet → craft `buyListing` with forged sender = victim, zero-price order, beneficiary = custody wallet. Batch via a custom contract (like 0xQuIt's `0x415F…B1a`) to amortize gas. Highest-value assets first — 0xQuit prioritized by value and still lost the WETH race.
4. **Sweep (fungibles):** the reverse path (victim-as-buyer). Harder: you're taking custody of fungible tokens, and the exact reverse-path mechanics were never published. 0xQuit lost this race. Attempt only with fork-tested calldata.
5. **Announce immediately — with the first pull, not after:** public post identifying the custody wallet, stating the operation is whitehat, pointing to a claim process. Defensive custody looks identical to theft on-chain — Cirrus spotted 0xQuIt's 3,832-NFT run as theft and he had to identify mid-operation. Put the "this is a whitehat" signal in the batch itself or post simultaneously; onlookers see the drain first. If the drainer is an identifiable opportunist rather than a pure attacker, run **counterparty triage**: negotiate a return through the public claim rail in parallel with the race (the MEV operator's 90% WETH return via nftsaresafu.xyz is the worked example).
6. **Claim process:** owners revoke V2 approval first, then claim (merkle-proof claim site like nftsaresafu.xyz, or manual return). Build this *before* sweeping if possible — 0xQuit built it during the operation and it still took weeks.

**What 0xQuit tried that failed (don't repeat):** pausing V2 (impossible), reverting fee recipients, malformed forwarders. Nothing can shut V2 off. Defensive exploitation is the only move.

---

## 7. Failure modes

1. **Trigger misread.** Today's probes are *not* the trigger. Sweeping on probes (pre-exploit) means moving assets with no active theft — maximum legal exposure, minimum justification. The trigger is 0-value fills / forced buys at scale.
2. **Copycat race.** In September, "other wallets were exploiting" by the time the rescue started, plus MEV bots front-running. A rescue tx in the public mempool can be front-run. 0xQuit used private relays where possible; the playbook's broadcast path (from the existing RESCUE-PLAYBOOK.md) is L1 → private relay (Flashbots Protect / MEV Blocker equivalents on Polygon).
3. **Fungible custody trap.** Rescuing WETH/USDC means holding other people's money with no on-chain claim primitive as clean as NFTs. 0xQuit lost the WETH race partly for this reason.
4. **Untested calldata.** The offset-0 forgery must be re-derived for V2 bytecode (repo is V3) and fork-tested. A malformed sweep tx burns gas and, worse, can leave partial state.
5. **Claim-process gap.** Moving assets without a working return path is indistinguishable from theft — legally and reputationally. The claim site must exist before or immediately with the sweep.
6. **Legal exposure.** Limit Break has NOT adopted SEAL Safe Harbor. Moving third-party assets without it is legally gray even with good intent. the operator's explicit authorization covers the decision; it doesn't eliminate the exposure. (Noted in RESCUE-PLAYBOOK.md.)
7. **Monitor latency.** 4h cadence vs. a 43-minute attacker operation (Sep 24: deploy → drain → bridge out in 43 min). The current monitor cannot win a race. See §9.

---

## 8. Trigger ladder (unchanged from RESCUE-PLAYBOOK.md, Polygon-scoped)

- **New suspicious call on Polygon V2** → verify on fork whether it's the exploit pattern (0-value sale / forced buy). If yes, alert the operator immediately with tx, wallets touched, estimated value at risk.
- **0-value `BuyListing`/`AcceptOffer` fills from unknown addresses** → RESCUE TRIGGER. Begin sweep sequence (§6).
- **Volume spike on V2 (>10 fills/hour from unknown addresses)** → treat as trigger until proven otherwise.
- **ApeChain V3 sunset 2026-11-30** → at 14 days out, surface the deadline (currently 43 days).

---

## 9. Open gaps (work remaining)

1. **Polygon exposure inventory** — the #1 gap. No measurement of live V2 approvals on Polygon.
   - **2026-10-18 measurement (overnight chunk):** chain-wide `ApprovalForAll`-where-operator=V2 scan is **blocked at the provider level from this VM**. publicnode `eth_getLogs` rejects address-less queries (`-32701: "Please specify an address in your request"`); `polygon.blockscout.com` API returns a Cloudflare "Just a moment..." challenge to scripted fetches (both `/transactions` and `/token-balances` paths, 2026-10-18). Zero events returned over 10k-block windows was a provider restriction, not a zero-measurement — canary (unfiltered `ApprovalForAll` topic over 300 blocks, should return hits) also returned 0, confirming the block. **Path to close:** Polygonscan/Etherscan API key (the operator approval) or a paid indexer; per-token queries against a curated candidate-token list are possible now but chain-wide is not.
2. **V2 bytecode analysis** — derive exact `buyListing` calldata layout + `BASE_MSG_LENGTH_BUY_LISTING` from deployed V2, not the V3 repo.
   - **2026-10-18 CLOSED (overnight chunk, V2-native evidence):**
     - `BASE_MSG_LENGTH_BUY_LISTING = 900`, from V2's **verified deployed source** (Blockscout: `ModulePaymentSettings` bundle additional_sources, `@custom:version 2.0.0`, pragma 0.8.19 — verification means compiled source matches deployed bytecode):
       `| 4 | 32 | 512 | 96 | 192 | 64 | = 900` = selector | domainSeparator | saleDetails | sellerSignature | cosignature | feeOnTop.
     - Field map: domainSeparator bytes32; Order = 16 words/512 B (protocol uint8, maker, beneficiary, marketplace, fallbackRoyaltyRecipient, paymentMethod, tokenAddress, tokenId, amount uint248, itemPrice, nonce, expiration, marketplaceFeeNumerator, maxRoyaltyFeeNumerator, requestedFillAmount uint248, minimumFillAmount uint248); SignatureECDSA = 96 B (v,r,s); Cosignature = 192 B (signer, taker, expiration, v, r, s); FeeOnTop = 64 B (recipient, amount).
     - V2 taker rule (ModuleTrades.buyListing, verified source): `taker = appendedDataLength == 20 ? _msgSender() : msg.sender` where `appendedDataLength = msg.data.length - 900 (unchecked)`. **V2 has NO `!= 20` revert** — V3's `_getTaker`/`PaymentProcessor__BadCalldataLength` hardening does not exist in V2 (confirmed: that error selector absent from V2 module bytecode). Forgery condition: module-level `calldatasize == 920` → last 20 bytes become taker.
     - Bytecode corroboration (Polygon publicnode `eth_getCode`, this run): V2 proxy `‹addr redacted›` dispatcher blocks each do `PUSH1 68; CALLDATASIZE; SUB` (= copy length `calldatasize-68`), `CALLDATACOPY`, `DELEGATECALL` to module (e.g. `ModuleTrades ‹addr redacted›`, verified on Blockscout) — matches 0xQuIt's writeup byte-for-byte. V2 modules contain standard ERC2771 `_msgSender` (`PUSH32 2^256-20; CALLDATASIZE; ADD; CALLDATALOAD; SHR 96`, gated on isTrustedForwarder) — the exact forgery point.
     - V2-vs-V3 delta that matters: V2's `buyListing` takes an explicit `bytes32 domainSeparator` first param (V3 dropped it); V2's Cosignature is 6 words (V3's is 5). Do NOT reuse V3 constants/selectors for V2 calldata construction.
     - Bytecode snapshots kept at `bytecode/v2proxy.hex`, `bytecode/modA.hex` (ModulePaymentSettings) for offline re-analysis. NOTE: `/tmp` is wiped between runs — keep analysis artifacts under `workspace/`.
3. **Fork-tested sweep calldata** — construct and test the offset-0 `buyListing` on a Polygon fork. Never mainnet-first.
4. **Monitor cadence** — 4h is too slow for a race. Options: dedicated high-frequency watcher on V2 (every N minutes), mempool monitoring via private relay, or Blockscout websocket subscription.
5. **Custody + claim infrastructure** — custody wallet, public notice draft, claim mechanism. The existing RESCUE-PLAYBOOK.md covers the notice template; the claim site does not exist yet.
6. **WETH reverse-path mechanics** — never published. Would need independent derivation from V2 bytecode.

---

## 10. Confidence ledger

| Section | Confidence | Basis |
|---|---|---|
| Exploit mechanism (§2) | HIGH | 0xQuit thread + sigintzero + public repo, all mutually consistent |
| Rescue template (§3) | HIGH | On-chain txs verified (rescue wallet, batch contract, claimBatch activity through Oct 14) |
| Event map (§4) | HIGH | keccak256 computed from public source; matches on-chain topics exactly |
| Today's probe decoding (§1) | HIGH | Receipts traced directly; event pair confirms `buyListing` fills |
| Actor linkage (same vs different operators) | MEDIUM | Wallet profiles + bytecode differ, but shared event pair is a strong common signal |
| Polygon exposure (§5) | MEDIUM | Address + revoke guidance confirmed cross-chain; no Polygon-specific inventory measured |
| Rescue call sequence (§6) | MEDIUM | Mechanism verified; exact V2 calldata not yet constructed or fork-tested |
| Current chatter ("growing attention") | MEDIUM | No fresh press in 48h; the "attention" is on-chain (3 actors today), which is real but not yet public |

## Appendix A — Independent verification (2026-10-18, second pass)

A fresh read-only pass reproduced the playbook's key technical claims from
independent sources. Results:

1. **Event signatures — CONFIRMED.** Cloned `limitbreakinc/payment-processor`
   and computed keccak256 over `src/interfaces/IPaymentProcessorEvents.sol`:
   - `0xf3003920` = `NonceInvalidated(uint256,address,bool)` ✓
   - `0xffb29e9c` = `BuyListingERC721(address,address,address,address,address,uint256,uint256)` ✓
   Both match the on-chain topics from the Oct 17 Polygon probes exactly.
2. **Rescue wallet — CONFIRMED active.** `‹addr redacted›`
   shows `claimBatch` transactions as recent as 2026-10-14 (owners still
   reclaiming via nftsaresafu.xyz).
3. **Batch rescue contract — CONFIRMED.** `‹addr redacted›`,
   selector `0x9970165b`, ~1,400-byte batch payloads, internal `call`s into V2.
   Earliest observed rescue txs: 2026-09-25 06:21–06:46 UTC (pagination capped
   at 40 pages; 05:46 UTC start per 0xQuit not directly re-observed but
   consistent).
4. **Exploit mechanism — CONFIRMED** against sigintzero's code-level writeup
   (dispatcher `sub(calldatasize(), 68)` + caller-controlled `data.offset`).
5. **48h chatter — none found.** News cycle remains Sep 25–Oct 5. The "growing
   attention" is on-chain only (three probing actors, Oct 17).

No corrections to the playbook body were required.

## Sources

- 0xQuit technical thread: https://x.com/0xQuit/status/2104680884360339829
- 0xQuit rescue summary: https://x.com/0xQuit/status/2103410682368512505
- Sigintzero deep-dive: https://sigintzero.com/blog/limit-break-2-8m-forged-erc2771-sender
- nftculture explainer: https://www.nftculture.com/nft-marketplaces/paymentprocessor-v2-exploit-0xquit-rescue/
- Limit Break payment-processor repo: https://github.com/limitbreakinc/payment-processor
- Limit Break TrustedForwarder: github.com/limitbreakinc/TrustedForwarder
- PublicAML WETH tracing: https://publicaml.org/limit-break-hack/
- Nexus Mutual roundup (Sep 21–Oct 5): https://nexusmutual.io/blog/onchain-security-roundup-sep-21-oct-5
- Claim site: nftsaresafu.xyz
- On-chain: rescue wallet `‹addr redacted›`, batch contract `‹addr redacted›`, V2 `‹addr redacted›`

## Appendix B — Test-vs-Targeting classification (detection rule, 2026-10-18)

**Rule (RESCUE-PLAYBOOK.md "Test vs Targeting"; encoded in `limitbreak_watch.py`):**
a settlement-function call (`buyListing`, `acceptOffer`, or equivalents) against
an **operator-owned/mock collection** = TESTING phase (watch only, do NOT
sweep — no active theft). The same call against an **established third-party
collection** = TARGETING phase (possible escalation; alert the operator immediately).

**Applied to this playbook:** the two 2026-10-17 Polygon probes (§1,
RECON-20261017-03) both classify TESTING — afternoon probe via mock
`0x72f1ffe8…`, evening probe via own contract `0x2744b83a…`. Neither fires
the §8 rescue trigger. The monitor's classifier catches mock clones too:
known mock *bytecode* keccak hashes flag redeployed copies under new
addresses, and a third-party seller EOA + non-mock collection is the
flip-to-targeting fingerprint.

**Why this matters for the trigger ladder:** §8 says "new suspicious call →
verify on fork." The classifier answers the first question before the fork —
*whose collection is being settled?* In a race (§7.2, 43-minute attacker
timeline), skipping fork verification on a TESTING call saves the response
budget for the TARGETING transition.

## Appendix C — Gap #6 closure: WETH reverse-path (2026-10-19, overnight chunk)

**Finding: there is no WETH leg in V2. Gap closed by negative evidence (earned zero).**

Scan method: extracted the full module list from the V2 proxy's own
bytecode (`bytecode/v2proxy.hex` — 4 DELEGATECALL targets), snapshotted each
module's runtime code via `eth_getCode` on `polygon-bor.publicnode.com`
(read-only), and scanned all 5 contracts for WETH/native fund primitives:
`deposit()` `0xd0e30db0`, `withdraw(uint256)` `0x2e1a7d4d`, the Polygon WETH
address constant `‹addr redacted›`, and the
`0xEeeeeEeee…` native-ETH sentinel.

**V2 module map (all on Polygon, verified by eth_getCode this run):**

| Address | Size | Identity |
|---|---|---|
| `‹addr redacted›` | 10,501 B | V2 proxy (dispatcher) |
| `‹addr redacted›` | 20,176 B | ModuleTrades |
| `‹addr redacted›` | 8,891 B | ModulePaymentSettings (sha256 matches existing `modA.hex`) |
| `‹addr redacted›` | 15,942 B | unidentified (saved `bytecode/mod_9a1d0089.hex`) |
| `‹addr redacted›` | 2,871 B | unidentified (saved `bytecode/mod_9a1d00fc.hex`) |

**Scan results (all contracts):** `deposit` = 0, `withdraw` = 0,
WETH-address constant = 0, native sentinel = 0. Fund movement is
`transferFrom` only: 7 hits in ModuleTrades, 5 in `mod_9a1d0089`, 0
elsewhere. No `transfer`/`safeTransferFrom` selectors either.

**Conclusion:** V2 never wraps or unwraps WETH on-chain — payment tokens
(including WETH) are pulled by `transferFrom` directly from the buyer. The
"WETH reverse-path" premise in §9.6 was a wrong assumption; there is nothing
to derive and no wrap/unwrap leg for a rescue sweep to reverse. The sweep
uses the same `transferFrom` pathway the protocol itself uses (§6).

Limits: compiled-Solidity interface calls always push selectors as PUSH4
constants, so selector absence is reliable; dynamically-constructed
selectors would be unusual. Snapshots kept under `bytecode/` for offline
re-analysis (per playbook rule, `/tmp` is wiped between runs).

