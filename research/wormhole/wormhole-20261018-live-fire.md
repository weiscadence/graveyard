# WORMHOLE THREAD 2: LIVE FIRE — Oct 15–18, 2026

**Date:** 2026-10-18 (read-only research; no transactions, no accounts, no contact)
**Sources swept:** Blockaid alerts, SEAL 911/samczsun, CertiK, PeckShield, SlowMist, Cyvers, QuillAudits/ExVul, Rekt News, DeFiHackLabs-adjacent coverage, SlowMist TI feed, ZachXBT/Specter/Salus on-chain trackers, BitRss aggregator (used with caution — it recycles old news; every incident below was dated by its own publication/on-chain timing).

**Methodological note (canary):** aggregators republished several OLD hacks as if fresh during this window — SwissBorg $41.5M (actually **Sept 8**), Makina $5M (**Jan 2026**), Saga EVM $7M (**Jan 2026**), Limit Break V2 / Magic Eden (Sept 24, our existing watch). All four were verified against original timestamps and are filed under "background," not fresh incidents. A zero-fresh-items check was run against that risk before writing this report.

---

## FRESH INCIDENTS (Oct 15–18, 2026)

### 1. UNCX Network — Smart Token Vesting V2 cross-chain exploit ⚠️ WATCHLIST HIT
- **What / how much:** Accounting flaw in the **VestingManager** shared pool. ExVul's read of the first Ethereum tx: `release()` reduced the *global* share total without removing released shares from the position's recorded deposit → a later `cancel()` deducted the same shares a second time. Sequence: open positions → release large one → donate tokens back → cancel a topped-up position → tiny leftover position withdraws *other users'* deposits.
- **Scale:** Blockaid (Oct 14 alert: ~$86K on Ethereum, 1 drain tx, flagged **ongoing**) revised (Oct 15) to **~$1.49M across 4 chains, 11 drain txs** — BNB Chain ~$969K, Ethereum ~$242K, Robinhood Chain ~$169K, Base ~$114K. **Copycat wallets and MEV bots joined** the attack, growing it 17×. UNCX's official incident report (Oct 17) verifies **~$807,600** across **10 tokens** (pepecoin, EDGEN, ZC, X, LO0P, PAAL on Ethereum; IMO on Base; BTCLE on BSC; CASHCAT, RKST on Robinhood Chain).
- **Status:** NOT fully contained by fix — contained by *deterrence*: UNCX halted new positions, raised flat fees to 100 ETH/lock, then **>1,000 ETH per lock**, token fees to the 5% contract maximum, and closed fee-bypass paths. Full incident report + proposed recovery plan expected this week. **No funds returned** by original attacker or copycats. UNCX coordinating with law enforcement + **SEAL 911**.
- **New vs known:** NEW mechanism signature — release/cancel double-count via shared-pool share accounting. No private keys compromised; pure bookkeeping.
- **Watchlist overlap:** **DIRECT HIT — UNCX VestingManager V2 is one of our three monitored contracts.** The flaw is live on a contract we're already watching, copycats are now loose, and ~$3.25M sat in the affected Ethereum pool when detected.
- **Sources:** [CryptoCompass (Blockaid report)](https://cryptocompass.com/articles/uncx-vesting-v2-exploit-drains-1-49m-across-four-chains) · [Crypto Briefing](https://cryptobriefing.com/uncx-network-vesting-pool-exploited/) · [Lookonchain feed (official report)](https://lookonchain.com/feeds/77414) · [Bitcoin.com](https://news.bitcoin.com/security/an-86000-exploit-rocks-a-crypto-pool-built-to-lock-tokens/)

### 2. Autheo (THEO) — Hyperlane bridge fallout, trading advisory issued Oct 17
- **What / how much:** Oct 12–13: attacker used a **single trusted relayer key** to mint **19M unbacked THEO** through the Hyperlane bridge on Base; price fell 92% within a day. PeckShield: minted THEO swapped for **700.8 ETH (~$1.76M)**, then bridged Base→Ethereum mainnet. Alerted by Defimon Alerts (Decurity) at 08:07 UTC Oct 13.
- **Status:** Ongoing investigation. On **Oct 17** Autheo issued a community advisory: **refrain from buying, selling, or bridging THEO until further notice**; working with technical partners; promised verified disclosure.
- **New vs known:** Known pattern (relayer-key compromise), not a novel bug — but notable that the token was **audited three times (Halborn, CertiK, Avelar)** and the failure was in the bridge's trust model, not the audited code.
- **Watchlist overlap:** Indirect — bridge class, not our three contracts. But relevant: reinforces that **shared-pool/vesting bridges with single-key trust** are the current frontier, and "audited" is not a containment guarantee.
- **Sources:** [Crypto Times (Oct 17 advisory)](https://www.cryptotimes.io/2026/10/18/autheo-issues-theo-trading-advisory-after-1-7m-bridge-exploit/) · [TechReport](https://techreport.com/news/software/theo-hack-funds-off-base-recovery-hard/)

### 3. HypurrFi — domain hijack recurrence (frontend-attack wave)
- **What:** hypurr.fi domain **reverted to attacker control at the Openprovider registrar** (reported Oct 18). Founder androolloyd: "Do NOT USE THE HYPURR.FI domain, it is compromised." Team migrated to a new domain; **contracts and ~$30M TVL unaffected**; blocked the domain across wallets via security partners.
- **Status:** Ongoing domain recovery; users told to avoid the old domain indefinitely.
- **New vs known:** Known vector (registrar social-engineering, seen on HypurrFi in March 2026 and OpenEden in Feb), but a **fresh flare-up** — and part of a wider wave: a Decurity alert *thwarted* an approvals-based attack on HypurrFi at **$84K loss** (per BitRss/Protos roundup), and SlowMist issued **TI alerts Oct 16–17** warning of **fake "Ledger firmware update" phishing** piggybacking on the CryptoBilis supply-chain crisis. Frontend is the active attack surface this week.
- **Watchlist overlap:** None directly — dormant-contract monitors won't catch this. But it's the recon surface around the same users/wallets we monitor, and approval-phishing preys on exactly the stale-approval pattern our monitors were built for.
- **Sources:** [BitRss (Oct 18)](https://bitrss.com/hypurrfi-domain-hijack-pushes-users-to-avoid-using-the-platform-198562) · [Crypto Times (SlowMist TI alert)](https://www.cryptotimes.io/2026/10/16/fake-ledger-firmware-update-scam-exploits-cryptobilis-hack-slowmist-warns/)

---

## HONORABLE MENTIONS / BACKGROUND (not fresh, but shaping the window)
- **Ledger / CryptoBilis supply-chain** (confirmed Oct 10): hidden implant exfiltrated 24-word seeds via cellular link; **$86–102M across 324 wallets, 6 networks** (Bitquery: $102M). Reseller (SE Asia) halted by Ledger. Now in the **laundering phase**: Oct 17, Specter linked CryptoBilis funds + Triple-A funds entering **Zcash's Ironwood shielded pool**; ZachXBT traced ~2,700 ZEC post-Bitget. ([crypto.news](https://crypto.news/onchain-data-shows-hackers-moving-stolen-funds-to-zcash/))
- **Duelbits casino** (Oct 10): ~$7M hot-wallet drain across 5 chains (ETH, BSC, Tron, Solana, BTC); victim's own figure, no chain-by-chain accounting published. ([cryptomediazone](https://cryptomediazone.com/hack-database/duelbits-hack/))
- **Triple-A attacker** (Oct 9–10): 4,970 ETH ($12.4M) from the July treasury breach pushed into **Tornado Cash in 56 deposits** (Salus). Social-engineering, not a contract bug.
- **samczsun steps back** as SEAL Org CEO (news ~Oct 16); COO Shane Batt interim; permanent search open. Community response positive. Not an exploit — but the top incident-response coordinator is in transition while incident volume is high.
- **Set Protocol ETHMACOAPY** (Oct 6): 8.11 WETH via `actualizeFee()` rounding + donation; deprecated V1 product; small, outside window.
- **FlashLoopAdapter / Aave v3 loop Safe module** (Oct 1, SlowMist Oct 2): ~114.09 ETH (~$305K), caller-authentication flaw; peripheral module, not Aave core.
- **Anthropic "Mythos" AI** (reported this week): Cyvers CEO warning that a vulnerability-seeking model "too dangerous to release" puts hundreds of millions to billions in DeFi at risk. Strategic context, not an incident.

---

## MONITOR RECOMMENDATIONS

1. **ELEVATE: UNCX VestingManager V2 → active incident watch (already watched; upgrade priority).**
   The flaw lives in a contract class we're already tracking, the drain is still live (no code fix — fees are the only brake), copycats + MEV bots are now weaponizing the pattern, and ~$3.25M sat in the Ethereum pool at detection. Recommend: monitor for new `release()`/`cancel()` sequences on all four chains' V2 instances, and watch the **promised UNCX incident report (expected this week)** for the exact accounting invariant that failed.

2. **NEW LANE: release/cancel share-accounting signature across vesting pools.**
   The UNCX mechanism (release() shrinking the global share denominator while per-position deposits stay stale, then cancel() double-counting) is a portable bug class. Copycats will now scan other shared vesting pools (Team Finance, Streamflow, and the long tail of vesting-manager clones on EVM chains) for the same invariant break. A monitor keyed on this *signature* — not just UNCX — is the highest-yield new target from this window.

3. **NEW LANE (adjacent, non-contract): frontend/domain-hijack + approval-phishing wave.**
   HypurrFi's domain reverting to attacker control (Oct 18) + SlowMist's Oct 16–17 fake-Ledger-firmware phishing alerts + the thwarted $84K approvals attack = a live frontend campaign layer around the same wallets/approvals our dormant-contract monitors exist to protect. Contract monitors won't see this; consider a lightweight frontend-threat watch (registrar/DNS changes on high-value DeFi domains, drainer-phishing kit alerts).

4. **No change: Limit Break V2, Rubic proxy.**
   Nothing in the 72-hour window touched them or their contract classes beyond what's already recorded (Limit Break V2 exploit Sept 24, contained via whitehat rescue).

---

*End of report. All incident figures are attributed to the cited sources; none were verified on-chain by this researcher (read-only web pass).*
