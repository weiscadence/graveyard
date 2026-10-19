# Whitehat Rescue Playbook (our lane)

Modeled on 0xQuit's Limit Break operation (Sept 25, 2026), adapted to what
this agent may do without further authorization. Standing rule: **no
third-party asset movement, no custody wallet funding, no owner/protocol
contact, no public disclosure** without the operator's explicit yes on the specific
action. Read-only preparation is always allowed.

## The 0xQuit model (observed)
1. Confirm the vulnerability and blast radius (read-only).
2. Coordinate with the protocol team.
3. Pause what can be paused.
4. Defensive custody only where no safer mitigation exists.
5. Announce custody rapidly and publicly (prevents confusion/panic).
6. Require owners to revoke vulnerable approvals before return.
7. Return through a claim site.
8. Account honestly for gas and losses.
9. Coordinate with marketplaces and revoke tooling.

## Return-phase worked example — nftsaresafu.xyz (2026-09-26)

Step 7 is no longer theory. 0xQuit's claim site completed the Limit Break
return loop (~Sep 26, sources: theboredapegazette, airdropalert):
- **Revoke-before-claim enforced in the flow:** the site requires the owner
  to revoke the PaymentProcessor approval first; claimable NFTs are shown
  from a QC'd snapshot (~25k NFTs). Lesson: don't rely on instructions —
  gate the claim on the revoke transaction itself.
- **Free reclaims, optional tips:** tips/donations optional, not a toll.
  Keeps the rescue unambiguously Good Samaritan.
- **Honest cost accounting:** >$7,500 of his own gas spent on the rescue.
  Any future custody operation budgets gas up front and publishes the spend
  (step 8), never absorbs it silently.
- **Repeatability precedent:** same operator ran the same defensive-custody
  model on Flooring Protocol in June 2026 (68 NFTs, $500K+, per
  playtoearn). The model is a playbook, not a one-off.

## SEAL Safe Harbor watch — 2026-10-09 (focus 2)

- **No new members, no new guidance, no new tooling** found in the
  Oct 6–9 window (earned zeros, checked honestly). Safe Harbor v3.0 is
  from Feb 2026, not new; safe-harbor docs last touched ~Sep 22.
- **Readiness gap on record: Limit Break has NOT adopted Safe Harbor.**
  Even a the operator-greenlit custody rescue in our lane would have no
  protocol-side legal waiver — the authorization gates stand as written,
  and the legal exposure stays real. A protocol team's own negotiation
  (NEAR shape) has compensation-pledge leverage we as outsiders don't.

## Drill 2026-10-06 — NEAR Intents $3.8M negotiated return (Oct 1–2, 2026)

Second rescue shape on record, distinct from 0xQuit's defensive custody:
here the PROTOCOL TEAM won by negotiation, not extraction. Sources:
cryptocompass, cointelegraph, crypto-economy, ambcrypto, cryptometer,
altcoinbuzz, moneycheck, finance.biggo (all corroborate the timeline;
attacker's identity and tracing method undisclosed; promised technical
report still unpublished as of Oct 5 — credibility cost of skipping the
post-mortem).

What the winning team did in the first hours:
1. **Anomaly tripwire fired inside the exploit window.** SHIELD (their
   AI anomaly layer) flagged the drain while it was still running —
   5 withdrawals of ~$3.87M USDT from a BNB Chain vault over ~6h.
2. **Freeze first, patch fast.** Operations suspended across 11 networks;
   main service + site back within ~1h of the patch. Damage confined to
   USDT on BSC.
3. **Micro-probes were the tell.** The attacker ran two test withdrawals
   (10 and 11 USDT) before the five big ones. Lesson: tiny successful
   state-changing calls from unknown addresses are the earliest signal —
   never set a value floor on the tripwire. (Our monitor already has no
   value floor — confirmed 2026-10-06.)
4. **Compensate-first pledge.** Full user reimbursement promised up front,
   decoupled from recovery — killed panic, bought negotiating time.
5. **Trace in parallel with containment.** Bitquery + internal forensics
   (+ ZachXBT independently) tracked funds to KuCoin deposits and BTC
   across four wallets within ~24h. The CEX offramp was the pressure
   point.
6. **Public ultimatum with a face-saving offramp.** GM named the
   perpetrator as identified and gave a 48h "responsible disclosure —
   last window" deadline on X. Attacker reached out within hours,
   negotiated, returned everything before the deadline with a written
   admission of fault.
7. **Recovery addresses pre-staged on every chain** (Bitcoin,
   BNB/Ethereum, Solana) BEFORE the return — nothing improvised at
   receipt time.

Portable upgrades (apply to our lane):
- **Offramp framing:** our equivalent of the ultimatum is the
  announce-and-return protocol — public custody announcement, clear
  revoke-first path, written return terms. Always leave the counterparty
  a clean way to be the good actor.
- **Pre-stage multi-chain custody addresses read-only:** if the operator ever
  authorizes a custody rescue, fresh receive addresses for every watched
  chain exist BEFORE any announcement (no funding, no key material held
  beyond session need).
- **Post-mortem is part of the rescue:** promise the detailed report up
  front, publish it. NEAR's missing report is the anti-pattern.
- **Filed for readiness-audit rotation:** our monitor flags only
  successful calls. The Sept 26/28 failed acceptOffer + unknown-selector
  probe clusters on V2 are live-attacker-interest signals that stay below
  the ALERT line — consider an advisory tier for repeated failed probes
  from the same unknown address.

### Addendum 2026-10-09 — root cause, disclosure cost, closure
- **Root cause (NEAR's Oct 1 account, untrusted channel):** integration bug
  at the *handoff seam* between Omni's custody architecture and the Intents
  smart contract — attacker inflated artificial deposits/withdrawals without
  equivalent collateral. Lesson for our lane: custody↔ledger accounting
  seams are the vulnerable surface; anomaly layers tuned for external
  attack patterns can miss internal logic bugs (SHIELD had just blocked
  $50M in Bitget-hack laundering days before, yet the seam bug sailed
  through).
- **Disclosure cost measured:** NEAR token fell 7.5% within minutes of the
  Oct 1 official announcement. Announcing pre-resolution has a market cost
  — another reason the announce-and-return protocol belongs in the
  compensate-first window, not before.
- **Detailed technical post-mortem: still unpublished as of Oct 9.**
  Anti-pattern holds.
- **Closure (Oct 3):** tracing was "internal team," methods undisclosed,
  exploiter never publicly named, investigation closed after full return
  before the Oct 4 deadline. Post-incident process change: NEAR plans to
  add formal verification to the release process.

## Drill 2026-10-18 — 0xQuit claim-phase, three weeks of live data

Third rescue shape on record, distinct from both defensive custody (Sept 25)
and the NEAR protocol-negotiated attacker return (Oct 2): a **negotiated
opportunist return**. PublicAML's WETH accounting (Sep 29–30): 542.1 WETH
(~$1.4M) drained 08:26–08:57 UTC Sep 25 — 31 minutes, 6,650 drain txs, the
fungible path moving fastest because it is atomic and bot-friendly. The
largest single wave (281.66 WETH, 25 wallets) came from an MEV bot operator;
Sep 29 he agreed to return 90% **through nftsaresafu.xyz**, the same public
claim rail as the rescued NFTs. The counterparty was a profit-seeking,
reputation-bearing actor with ongoing business — negotiable where a pure
attacker is not.

Portable upgrades:
- **Counterparty triage before acting:** (a) malicious attacker — fresh
  contract per victim batch, no ongoing business: race, no negotiation;
  (b) opportunistic profit-taker (MEV operator, frontrunner): negotiate,
  return via the public claim site; (c) whitehat-adjacent: coordinate.
  If our probes ever flip to targeting by an identifiable opportunist,
  negotiation runs in parallel with the race — it did for 0xQuit.
- **Claim rail is a weeks-long campaign, not a launch.** Verified live Oct
  18 on nftsaresafu.xyz: $4,717,507 returned = 65.9% of priced assets
  ($7.15M; only 16.8% of allocations priced, so direction not precision).
  Launch week was ~9% (2,357/26,448). Budget owner outreach for weeks;
  keep the rail live long-term.
- **Claim friction is predictable — preempt it at launch:** EIP-7702
  delegated-wallet claims trip wallet simulation warnings (Rabby) — ship a
  plain-language "your wallet WILL warn; here is why it is safe" explainer
  with the launch, not after. Pre-map collections with Transfer Validator
  restrictions so no claim reverts unexplained. Publish the canonical claim
  domain in the FIRST announcement (fake recovery DMs/lookalike domains
  spin up within hours) and never initiate owner contact by DM.
- **Whitehat identification rides with the first pull.** Defensive custody
  looks identical to theft on-chain: Cirrus saw 3,832 NFTs leave 100+
  wallets and sounded the alarm; 0xQuit had to identify mid-operation.
  The "this is a whitehat" message goes out with the FIRST pull —
  on-chain message or simultaneous public post — because onlookers will
  see the drain before any explanation.
- **First-hours recap (consolidated):** 12+ hour detection lag before the
  flag reached 0xQuit; he called Limit Break first (V3 paused, V2
  unpausable — defensive custody was the only move); the bug trusted an
  ERC-2771-style "original sender" from a trusted forwarder that could be
  forged (his Sep 28 thread). That 12-hour blind window is the reason our
  monitor exists.

## Wormhole 2026-10-12 — rescue technique chain (focus 3)

Seven hops, all web-sourced (untrusted channel), filed as techniques not
facts. Full chain log:
`~/workspace/goals/limit-break-incident-monitor-and-rescue-playbook/hidden_files/wormhole-2026-10-12-technique-chain.md`.

**T1 — Rescue txs never touch the public mempool.** The Yoink/Kelp case
(~Sep 2026) is the proof from both sides: an attacker broadcast a $7.7M
exploit in the public mempool; MEV bot Yoink replayed the action with
higher gas and captured 2,882 rsETH (~$7.73M) in the same block, tipping
the builder 18.93 ETH. Our rescue txs face the same mempool. Broadcast
path: **L1 → private relay** (Flashbots Protect / MEV Blocker /
bloXroute Protect, direct-to-builder, no mempool visibility); **L2 with
centralized sequencer (Base, ApeChain) → ordering is the sequencer's**,
no public-mempool frontrunning game exists the way it does on L1, so
private relay is optional/harmless there. Playbook's "if the operator authorizes
a custody rescue" sequence gains this as a new standing step: pick the
broadcast path per chain BEFORE the first move, dry-run the relay path,
never raw `eth_sendRawTransaction` to a public node on L1.

**T2 — Asymmetry of visibility.** A whitehat can only frontrun what it
can see. If the attacker uses a private relay, there is no mempool tip to
copy. Our tripwires (event-level, post-confirmation) cannot beat an
invisible attacker — they can only win the race *after* the first
confirmed probe, i.e. beat the SECOND exploit, not the first. The
0xQuit rescue was exactly that: rescue-after-first-wave. Never plan as
if we get the first move.

**T3 — Pre-recorded response transactions.** Hypernative + Fordefi CARE
model: exit/unwind calldata pre-built, pre-signed, waiting on a trigger
(detection → auto-broadcast). Our lane's equivalent is already half
there: the fork harness + rescue calldata are pre-built and fork-tested.
Upgrade: add the per-chain broadcast endpoint to the rescue checklist
(see T1) and keep one dry-run per quarter so the path doesn't rot.

**T4 — Funds-in-limbo negotiation pattern.** Yoink's rsETH sat at the
operator's address (0xC70f00…) for weeks with no recovery confirmed; the
working channel is on-chain messages to the holder plus a bounty offer
(2024 Ronin precedent: same operator returned most, kept $500k). The
*institutional* version is SEAL Whitehat Safe Harbor (Makina Jan 2026:
MEV builder returned 920 of 1,023 ETH, kept the 10% bounty — capped at
$1M, 72h return window, KYC + OFAC for the whitehat, funds to a dedicated
recovery multisig). **Limit Break has NOT adopted Safe Harbor** — so the
10%-bounty return path has no legal cover in our lane, same standing as
the SEAL-watch finding. If we ever hold someone's assets, the bounty math
has to be negotiated ad hoc, not assumed.

**T5 — Token-level address freeze is a time-buy, not a return.** Kelp
paused the recipient address for 24h at the rsETH contract level — bought
investigation time, moved zero funds back. Only possible on pausable
tokens, only executable by the token team. Portable rule: when mapping a
new target, record (a) is the asset token pausable? (b) who holds the
pauser key? (c) does a pause exist at the contract level at all
(Limit Break V2: no). The pauser-holder is the second phone call after
the protocol team — blocked-on-the operator, same as team contact.

**T6 — The samczsun rule (MISO, Aug 2021).** $350M bug found, verified
with colleagues, went straight to the team; the team manually ended the
auction before any attacker found it. When no patch path exists, the
winning move is *exploit-first with the team's knowledge*, not
disclose-first. This is already our custody model; the sharpening is the
team-coordination leg, which stays blocked-on-the operator — pre-authorized
nothing, prep-everything.

**T7 — Monitoring-stack freshness.** OpenZeppelin Defender's hosted
service ended 2026-07-01; the current recommendation stack is Forta
community bots / Hypernative / self-hosted OZ Monitor+Relayer. Only
matters if we ever recommend infra to a protocol (readiness-audit
rotation); our own monitor is custom-built.

## Our authorization gates
| Step | May I do it now? |
|---|---|
| Read-only vuln confirmation, blast-radius mapping | Yes — standing |
| Fork-prove the path (disposable local fork) | Yes — standing |
| Monitor defensive switches / incident contracts | Yes — standing |
| Prepare self-reclaim kits for owners | Yes — standing |
| Move anyone's assets into custody | **No — needs the operator's explicit yes** |
| Fund or create a custody wallet | **No — needs the operator's explicit yes** |
| Contact owners, teams, or marketplaces | **No — needs the operator's explicit yes** |
| Publish owner identities or exploit mechanics | **No — needs the operator's explicit yes** |

## Trigger ladder (Limit Break monitor)
- **New suspicious call on V2/V3** → verify on fork whether it's the exploit
  pattern (0-value sale / forced buy). If yes, alert the operator immediately with
  the tx, the wallets touched, and the estimated value at risk.
- **V3 ApeChain approaching Nov 30, 2026** → at 14 days out, surface the
  countdown and confirm whether Limit Break extended or paused.
- **Fresh vulnerable-approval discovery** (same stale-approval pattern on a
  new contract) → run the full confirm-and-map sequence, then brief the operator
  with the rescue/no-rescue recommendation.
- **Monitor source note (2026-10-08):** Polygon leg moved off Blockscout
  (Cloudflare 403 on its API) to keyless public-RPC `eth_getLogs`
  (`polygon-bor-rpc.publicnode.com`), method names decoded via openchain.xyz,
  tracked by `polygon_last_block` in state.json. Only event-emitting txs are
  visible — an event-less state change on Polygon V2 would be missed.
- **Monitor fix (2026-10-15 readiness audit):** publicnode hard-caps
  `eth_getLogs` at 10,000 blocks/call — the single-call leg went fully blind
  2026-10-08 and the watermark froze ~307k blocks behind head. Fixed:
  10k-block chunked calls, per-chunk retry, watermark persisted per completed
  chunk so a failed run resumes mid-backfill instead of restarting. Backfill
  converges over runs; if the watermark stalls at the same block across 3+
  runs, drop `POLYGON_CHUNK` to 5000. Base remains degraded: measured 2026-10-15,
  publicnode's Base endpoint is archive-gated beyond ~8k recent blocks (~4.4h),
  too fragile for the 4h cadence — one missed run breaks continuity. A personal
  allnodes token would fix it; token creation needs the operator's approval
  (blocked-on-the operator, filed 2026-10-15).

## If the operator authorizes a custody rescue
0. **Pre-stage multi-chain custody addresses (read-only prep, always
   allowed):** fresh receive addresses for every watched chain generated
   in advance, so nothing is improvised at announcement time. No funding,
   no key material held beyond session need.
1. Stand up a fresh custody wallet (the operator funds it; I never hold the key
   material beyond the session need).
2. Dry-run the full sequence on a pinned fork first, with assertions:
   owner/custody before, exact recipient after, no unrelated movement.
3. Execute in small batches, broadcast via the per-chain private path
   (L1: Flashbots Protect / MEV Blocker / bloXroute private relay —
   never raw to a public mempool; centralized-sequencer L2: sequencer
   queue); announce the custody address publicly as Lodestone within
   minutes of the first move.
4. Publish the revoke-first claim process; coordinate the return.
5. Full accounting: gas spent, assets rescued, assets lost, timeline.

## NFT Trader self-reclaim kits (prepared, not sent)
- 14 verified escrowed items remain in v1 (dust: SpaceCowboys, Blox,
  Rarible, Gambling Apes, metaPengus). Creators can still call
  `cancelSwapIntent(swapId)` — no pause/whitelist blocks it.
- Wallet-held approvals (CoolCats #2299, Meebits #18727): revoke.cash is
  the correct hygiene; no rescue needed while v1's whitelist is empty.
- Kits stay private until the operator authorizes outreach.

## What "rescue-ready" means day to day
The monitor runs, the fork harness is warm (foundry installed, anvil
fork procedure documented), and the playbook above is the checklist.
If a live one appears, the time from detection to the operator's briefing is
minutes, not hours.

## Test vs Targeting (detection rule, added 2026-10-18)

**The rule:** a settlement-function call (`buyListing`, `acceptOffer`, or
equivalents) against an **operator-owned/mock collection** = testing phase.
The same call against an **established third-party collection** = targeting
phase. The transition between the two is the escalation trigger.

**Why it works:** exploit developers validate the attack path against
contracts they control before pointing it at real victims. The on-chain
fingerprint is identical except for one field: the collection address in
the settlement event. Testing uses throwaway contracts; targeting uses
collections with real holders and real value.

**Ground truth (RECON-20261017-03):** on 2026-10-17, two independent actors
ran `buyListing` fills through Limit Break Payment Processor V2 on Polygon.
Both emitted `BuyListingERC721` + `NonceInvalidated` — the exact settlement
path of the September exploit. In both cases the "seller" was the operator's
own contract (afternoon: `0x72f1ffe8…`, evening: `0x2744b83a…`). Mock
collections, both sides controlled → testing phase, confirmed. No escalation.

**What flips it to targeting:**
- Settlement event where the collection is a known NFT project (not
  operator-deployed within the probing window)
- Seller is a third-party wallet (not the operator's own contract)
- Collection has pre-existing holders / trading history

**Monitor encoding:** the Limit Break watch flags settlement-function calls;
the collection-vs-operator check is the classifier that separates
`TESTING` (watch) from `TARGETING` (alert the operator immediately — the rescue
window may be opening). This rule generalizes to any settlement-path
exploit (UNCX `release()`/`cancel()` sequences get the analogous
treatment: is the position being manipulated the attacker's own, or does
it touch other users' deposits?).

**Calibration note:** a testing-phase observation is NOT evidence of no
threat — Ostium ($100 test → $23.75M), NEAR Intents ($10/$11 → $3.865M),
and UNCX ($86K → $1.49M) all ran small tests before the real strike. Testing
means the weapon works. Targeting means it's aimed.
