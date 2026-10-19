# WORMHOLE S5·T2 — Credit Card Fraud Parallels for On-Chain Test-Transaction Detection

**Shift:** WORMHOLE S5 (recon shift 5, thread 2) · **Date:** 2026-10-18
**Goal:** Learn from the credit card industry's ~35 years of fraud science — it deals with EXACTLY the graveyard-scanner problem: a tiny test authorization ($1) followed by the big fraud charge ($23.75M exploit).

---

## 1. The canonical "test then fraud" pattern in card literature

Card networks call it **card testing** (network term: **enumeration**). Attackers validate stolen card numbers by running a flood of tiny, low-risk transactions — typically **$0.99–$2.99**, often **sub-$1 or $0 authorizations** — before attempting larger fraudulent purchases. The test charge that clears tells the fraudster the card is live; the merchant that processed it becomes the proving ground for the fraud that follows ([wyllo.ai](https://wyllo.ai/glossary-term/card-testing-fraud/), [savingadvice.com](https://www.savingadvice.com/articles/2026/03/04/10724076_the-0-99-test-charge-why-a-tiny-transaction-could-signal-bigger-fraud.html)).

There are two flavors:

- **Enumeration / BIN attack:** bots take a valid BIN range (first 6–8 digits), brute-force remaining digits, then run thousands of tiny charges to discover which generated numbers are live. Tell-tales: sudden spike in declines, many attempts sharing one BIN range, mismatched geography, collapse in approval rate ([bincheck.io](https://bincheck.io/credit-card-fraud-investigation)).
- **Card-level test → monetize:** one known-good stolen card gets a handful of small charges ("burst of small charges, often $1–$5, at different merchants in quick succession"), then the big purchase ([legalclarity.org](https://legalclarity.org/how-do-credit-card-companies-detect-fraud-key-methods/)). Visa's official guidance: *"If the small purchase is successful, the fraudster starts making larger purchases to get as much as they can out of the card before the fraud is detected"* ([visa.ca](https://www.visa.ca/en_CA/run-your-business/small-business-tools/what-you-need-to-know-about-card-testing-fraud.html)).

**Escalation window — minutes, not hours.** The empirical detection rules all use tight windows:
- Reference real-time detection rule: ≥3 transactions averaging <$2.00 within a **2-minute** tumbling window (card testing clusters in seconds; legitimate micro-transactions spread out over time) ([risingwave.com](https://risingwave.com/blog/real-time-credit-card-fraud-detection-tutorial/)).
- Splunk's fraud rule: first amount <$20 followed by last amount >$3,000 within **1 minute**, ≥2 transactions ([lantern.splunk.com](https://lantern.splunk.com/Splunk_Platform/UCE/Financial_Services_and_Insurance/Detecting_credit_card_fraud?mt-language=JA)).
- A single bot can cycle through **thousands of card numbers in minutes**; validated cards are monetized or resold immediately ([legalclarity.org](https://legalclarity.org/what-is-card-testing-fraud-and-is-it-a-federal-crime/)).

**For graveyard-scanner:** the on-chain "test tx → drain tx" pattern is the same shape (probe → verify → exploit), and the card literature says the gap between test and monetization is on the order of **seconds to minutes**. Any detection pipeline whose alert loop is slower than ~minutes misses the window where intervention is possible. (On-chain has one advantage: finality means we *see* the test immediately on a public ledger; no reporting lag.)

---

## 2. How card systems catch the test: specific signals

### 2.1 Velocity checks (the workhorse)
Counts and sums over rolling windows per card/account: transactions in the last **1m / 5m / 1h / 24h**, total amount per window, ratio of current-window count to the account's 30-day average ([dev.to](https://dev.to/printo_tom/how-we-built-a-real-time-credit-card-fraud-detection-system-an-architects-perspective-4ib7), [dev.to](https://dev.to/nickparsons/feature-engineering-for-fraud-detection-5d8)). The cardinal rule: **a count threshold AND an amount threshold together** — e.g., ≥3 txs AND average <$2 — so legitimate micro-spending (parking, transit) doesn't fire ([risingwave.com](https://risingwave.com/blog/real-time-credit-card-fraud-detection-tutorial/)). Multiple rules firing on the same card is itself a stronger signal.

### 2.2 Behavioral profiling (the crown jewels)
FICO Falcon's key analytic weapons:
- **Profiles updated with each transaction, in real time.** Learned behavioral variables and profiles of cardholders and merchants adapt on every transaction to identify outliers ([dqindia.com](https://www.dqindia.com/fico-machine-learning-algorithms-improve-card-fraud-detection-by-30/)).
- **Behavior Sorted Lists ("B-lists"):** learn the account's frequent, repeated behaviors ("favorites"). Hits and misses on favorites let the model separate fraud vs. scam vs. normal. A transaction from a *favorite* device identifies 24× more scams than the base model ([businesswire.com](https://www.businesswire.com/news/home/20221208005058/en/)).
- Baseline profile features: typical spend sizes, merchant mix, transaction frequency, hours-of-day, days-of-week.

### 2.3 Device fingerprinting
Device ID, IP address, AVS mismatch signals are first-class features. A **new device + test charge** is the canonical fraud fingerprint ([spd.tech](https://spd.tech/machine-learning/credit-card-fraud-detection/)).

### 2.4 Geolocation / impossible travel
"Card used in Kansas at 2pm, then Dubai at 3pm, is physically impossible" — distance/time checks between successive transactions ([aieworks.substack.com](https://aieworks.substack.com/p/day-61-building-a-credit-card-fraud)).

### 2.5 Merchant-category (MCC) patterns
Pre-computed merchant risk scores by category. Fraud concentrates in cash-out categories (gift cards, crypto, money-transfer); a cardholder's first-ever visit to a high-risk MCC is scored ([aieworks.substack.com](https://aieworks.substack.com/p/day-61-building-a-credit-card-fraud), [dev.to](https://dev.to/printo_tom/how-we-built-a-real-time-credit-card-fraud-detection-system-an-architects-perspective-4ib7)).

### 2.6 Amount deviation
How far this transaction deviates from the cardholder's mean/median spend; dynamic decision thresholds keyed on amount — a $5,000 transaction is blocked at 60% fraud confidence, a $50 one needs 85% ([aieworks.substack.com](https://aieworks.substack.com/p/day-61-building-a-credit-card-fraud)).

---

## 3. The systems and the engineers who built them

| System | Facts |
|---|---|
| **FICO Falcon** (born 1992 at HNC Software; FICO acquired HNC 2002) | Protects 2.6B+ payment cards; consortium of **9,000+ banks contributing anonymized tx data** (~20B records/month, a petabyte per 5 years); sub-second scoring; 90+ AI/fraud patents. Born when fraud was ~1% of all transactions and threatened the industry ([predictiveanalyticsworld.com](https://www.predictiveanalyticsworld.com/machinelearningtimes/?p=13648), [dqindia.com](https://www.dqindia.com/fico-machine-learning-algorithms-improve-card-fraud-detection-by-30/)). |
| **Visa Advanced Authorization (VAA)** | Evaluates **100% of VisaNet transactions**, ~65k queries/sec peak; **500+ risk attributes in ~1 millisecond**; outputs a **1–99 risk score** to the issuer, which makes the approve/decline decision; credited with ~$25B/yr fraud prevention; fraud rate <0.1% ([investor.visa.com](https://investor.visa.com/news/news-details/2019/Visa-Prevents-Approximately-25-Billion-in-Fraud-Using-Artificial-Intelligence/default.aspx), [consultancycircle.com](https://consultancycircle.com/ai/ai-fraud-how-visa-tackles-evolving-scams-and-threats/)). |
| **Mastercard Decision Intelligence / DI Pro** | 143B transactions/yr; proprietary **RNN + transformer** models that learn *relationships between merchants* in a cardholder's history rather than textual analysis; full risk assessment in **<50ms**; +20% avg fraud-detection lift (up to 300% in cases) ([klover.ai](https://www.klover.ai/mastercard-ai-strategy-and-path-to-dominance-in-financial-intelligence/), [baypayforum.com](https://www.baypayforum.com/news/fraud-news/mastercard-joins-generative-ai-race-in-fraud-prevention)). |

**People to know:**
- **Dr. Scott Zoldi** — FICO chief analytics officer, inherited the Falcon consortium from HNC; the public voice of behavioral profiling, B-lists, and real-time profile updates ([businesswire.com](https://www.businesswire.com/news/home/20221208005058/en/)).
- **Tom Fawcett** — HNC Software researcher in the Falcon era; with Foster Provost wrote the foundational papers on cost-sensitive/adaptive fraud detection (see §6).
- **Salvatore Stolfo & Philip Chan** — Columbia; the JAM/cost-distribution papers that launched fraud detection as an ML research field.
- **Ajay Bhalla** — Mastercard president of enterprise risk and security; architect of DI Pro's merchant-relationship modeling ([losangelesfinancialtimes.com](https://losangelesfinancialtimes.com/mastercard-launches-gpt-like-ai-model-to-help-banks-detect-fraud/)).

---

## 4. False-positive economics: the precision/recall philosophy

Card issuers **live with, and budget for, false declines**. The numbers are brutal:

- Javelin (2015): only **1 in 5** fraud predictions is correct; errors cost banks **$118B** in lost revenue ([techxplore.com](https://techxplore.com/news/2018-09-false-positives-credit-card-fraud.html?deviceType=mobile)).
- Javelin (2014): US issuers falsely rejected **$118B** vs. **$9B** actual fraud — a **13:1 ratio** ([paymentsindustryintelligence.com](https://paymentsindustryintelligence.com/solving-card-not-present-false-decline-puzzle/)).
- **25–34% of all declined transactions were actually legitimate**; 51% of falsely declined cardholders used a secondary card (top-of-wallet churn); 39% abandon the card post-decline; 2/3 of false-decline victims never return to the merchant ([chargebackhelp.com](https://chargebackhelp.com/false-positives/), [paymentsindustryintelligence.com](https://paymentsindustryintelligence.com/solving-card-not-present-false-decline-puzzle/)).
- False positives cost merchants **5× more than chargebacks** in time, resources, and revenue ("long-tail damage") ([chargebackhelp.com](https://chargebackhelp.com/false-positives/)).
- Datos Insights: false declines to cost the industry **$297B by 2029** ([financialit.net](https://financialit.net/news/payments/banks-losing-160000-year-legacy-fraud-detection-systems-block-legitimate-card-payments)).

**The operating philosophy** (transferable in shape, with a big caveat below):

1. **Score ≠ action.** Visa/Mastercard return a 1–99 score; the *issuer* decides approve / decline / step-up-authenticate / flag-for-follow-up. Separation of scoring from action lets each issuer set its own risk appetite ([paymentsjournal.com](https://www.paymentsjournal.com/using-artificial-intelligence-visa-is-combatting-fraud-at-nearly-the-speed-of-light/)).
2. **Dynamic thresholds by stake.** A $5,000 transaction is blocked at 60% fraud confidence; a $50 one at 85% ([aieworks.substack.com](https://aieworks.substack.com/p/day-61-building-a-credit-card-fraud)). Thresholds also differ by review budget (0.5% transaction review rate is a common operating point — FICO's scam model targets that explicitly).
3. **Step-up, don't just decline.** Suspicious but sub-threshold → SMS verification, 3D Secure challenge, alert. The graded response ladder is how they keep recall high without nuking legitimate volume.
4. **Metrics are cost-weighted, not accuracy.** Practitioners evaluate on balanced error rate, G-mean, cost matrices — never raw accuracy ([fraud-detection-handbook.github.io](https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_4_PerformanceMetrics/ThresholdBased.html)).

**The caveat for us:** in card-land, the cost of a false negative is money an issuer can (partially) claw back, and the cost of a false positive is a customer annoyed for 30 seconds. On-chain, the false-negative cost is a **$23.75M irreversible drain** and there is no step-up authentication to insert. So the card industry's recall-tilted-but-careful philosophy applies *asymmetrically harder*: we should run at higher recall (more alerts) than a card issuer would, with tiered actions (log → alert → stage whitehat rescue) instead of decline/no-decline. False alerts are cheap compared to missed drains — but alert fatigue is the real analog of top-of-wallet churn, so tiering matters.

---

## 5. Models and real-time architecture (<100ms scoring)

**Model stack (evolution):** neural networks since the early 1990s (Visa pioneered NN fraud models; HNC/Falcon NNs 1992) → gradient boosting/random forests on engineered features → proprietary RNN/transformers (Mastercard DI Pro 2024, modeling merchant-relationship sequences) → layered ensembles: **supervised ML (known patterns) + unsupervised anomaly detection (emerging schemes)** — neither alone is considered production-sufficient ([spd.tech](https://spd.tech/machine-learning/credit-card-fraud-detection-case-study/), [consultancycircle.com](https://consultancycircle.com/ai/ai-fraud-how-visa-tackles-evolving-scams-and-threats/)).

**Architecture that hits the latency budget** (per a production-system writeup):
```
Tx request → API Gateway (rate limit, auth)
         → Feature Service: Redis + Flink, rolling profiles pre-materialized, feature assembly <20ms
         → Scoring Engine: rule layer + ML inference <50ms
         → Decision Engine: thresholds, risk bands, actions (approve / decline / step-up)
Total: <300ms synchronous; retraining/alerting/feedback all asynchronous.
```
The dominant lesson: **"the biggest performance gains did not come from switching models — they came from better features"** ([dev.to](https://dev.to/printo_tom/how-we-built-a-real-time-credit-card-fraud-detection-system-an-architects-perspective-4ib7)). Feature assembly is the expensive part; keep profiles in memory (Redis/Flink), materialize rolling counters continuously, and score is a cheap function call.

**Drift:** fraud patterns change constantly; "yesterday's model is today's liability" — retraining pipelines are scheduled and drift-monitored. FICO's consortium explicitly exists to validate new models against fresh fraud trends before release ([dqindia.com](https://www.dqindia.com/fico-machine-learning-algorithms-improve-card-fraud-detection-by-30/)).

**On-chain translation of the latency budget:** we don't have an authorization hook (the chain settles everything). Our equivalent constraint is *mempool-to-drain latency*: the test tx lands in a block; the drain follows seconds-to-minutes later. A per-block scoring loop (feature assembly from indexed state + cheap model inference) is the analog of Visa's <50ms path — eminently feasible given blocks are ~2–12s apart, not 50ms.

---

## 6. Visa's dual-speed defense (the most directly stealable architecture)

From Visa's Fall 2025 Biannual Threats Report ([visa.com.mx PDF](https://www.visa.com.mx/content/dam/VCOM/corporate/visa-perspectives/security-and-trust/documents/biannual-fall-2025-public-final.pdf)):

- **Slow phase (predictive mitigation, pre-monetization):** Visa Payment Threat Intelligence (dark-web monitoring), **Visa Account Attack Intelligence (identifies accounts compromised through card testing)** and the Breach Identification Tool. The point: find the *tested* accounts *before they're monetized* and get issuers to secure them proactively.
- **Fast phase (real-time blocking):** authorization systems, velocity controls, AI fraud models detect and block monetization attempts in milliseconds.

**This is the graveyard-scanner doctrine in card-industry language.** Slow phase = continuous off-chain watch for wallets exhibiting test-tx signatures (dust calls, failed calls, first-contact-with-vulnerable-contract patterns) — flag them, pre-stage rescue playbooks, alert whitehats. Fast phase = mempool/block-level detection of the drain-pattern forming, triggering the rescue race. Visa operates both speeds simultaneously because *the test and the monetization are detected by different systems at different times* — steal that directly.

---

## 7. Chargeback/dispute process: the recovery parallel (and why on-chain is harder)

The card chargeback lifecycle ([chargeflow.io](https://www.chargeflow.io/blog/chargeback-recovery-demonstrated-guide-ecommerce-merchants), [directpaynet.com](https://directpaynet.com/timeline-of-a-chargeback-the-merchants-guide-to-processing-chargebacks/), [netsuite.com](https://www.netsuite.com/portal/resource/articles/accounting/chargebacks.shtml)):

1. **Day 0:** cardholder disputes; issuer debits the merchant's acquirer, provisionally credits the cardholder.
2. **Days 1–5:** merchant notified with a reason code + response deadline.
3. **Representment (merchant response):** evidence package (receipts, delivery proof, IP/device logs, prior-transaction history) — Visa ~30 days (processors often compress to 9–18), Mastercard 45 days.
4. **Issuer review:** 30–75 days; funds returned on a win (fees usually not).
5. **Arbitration (optional):** network makes a binding ruling; additional weeks + fees.

Total: **30–90+ days**. Cardholders get up to **120 days** to file. The network is a **centralized arbiter with a clawback mechanism** — money moves back because the issuer can debit the acquirer.

**The whitehat-rescue parallel:**
- **What maps:** (a) the *evidence package* — representment requires timestamped logs, device/session evidence, transaction history; our rescue/post-mortem needs the same evidentiary discipline (trace bundles, mempool timestamps, funding graphs). (b) The *reason-code taxonomy* — networks classify disputes (fraud, processing error, consumer dispute); our finding taxonomy (pre-exploit, drain, post-exploit) serves the same triage function. (c) *Provisional credit* — the issuer credits the victim immediately, before investigation finishes; the closest on-chain analog is a whitehat front-run that parks funds — speed before certainty.
- **What doesn't map:** there is **no arbitration layer on-chain**. Once the drain settles, no network can debit the attacker. Chargebacks exist because the ledger is *reversible by policy*; ours is final by cryptography. Consequence: the card industry can afford to optimize for precision and handle misses with chargebacks; **we cannot.** Our error budget must be spent on recall (catch the test), because post-hoc recovery is a rescue race, not a dispute process.
- Recovery on-chain after the fact = the parts that *do* have centralized chokepoints: tracing → CEX deposit → freeze request with an evidence package. That flow *is* chargeback-shaped (reason code, evidence deadline, issuer/CEX review), just with a much lower win rate and no binding arbitration. Worth formalizing: a "representment-style" evidence template for CEX freeze requests would be a genuinely useful artifact.

---

## 8. Key papers (reading list)

1. **Chan, P.K. & Stolfo, S.J. — "Toward Scalable Learning with Non-Uniform Class and Cost Distributions: A Case Study in Credit Card Fraud Detection," KDD-98** (pp. 164–168). The founding paper: fraud as a cost-sensitive, massively imbalanced distributed-learning problem ([sigmod.org KDD-98 proceedings](https://sigmod.org/publications/dblp/db/conf/kdd/kdd98.html)).
2. **Fawcett, T. & Provost, F. — "Adaptive Fraud Detection," Data Mining and Knowledge Discovery 1(3), 1997.** Learning under adversarial drift — the reason models must retrain continuously; Fawcett built Falcon-era systems at HNC.
3. **Fawcett, T. & Provost, F. — "Activity Monitoring: Noticing interesting changes in behavior," KDD-99.** Formalizes profiling-based deviation detection (the ancestor of Falcon's behavioral profiles).
4. **Fawcett, T. — "An introduction to ROC analysis," Pattern Recognition Letters 27(8), 2006.** The metric bible for imbalanced fraud evaluation; why accuracy is meaningless here.
5. **Dal Pozzolo, A. et al. — "Credit Card Fraud Detection: A Realistic Modeling and a Novel Learning Strategy," IEEE TNNLS 29(8), 2018.** On realistic evaluation: time-ordered splits, concept drift, and alert-precision over time — directly relevant to backtesting our detectors.
6. **Dal Pozzolo, A. et al. — "Calibrating Probability with Undersampling for Unbalanced Classification," CIDM 2015.** Probability calibration under imbalance — needed if our scores feed tiered actions.
7. **The open "Fraud Detection Handbook"** ([fraud-detection-handbook.github.io](https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_4_PerformanceMetrics/ThresholdBased.html)) — practical guide to threshold-based metrics (BER, G-mean, cost matrices) for fraud; good reference for how we should evaluate the scanner.

---

## 9. On-chain analog map (concrete technique transfer)

| Card signal | On-chain analog | Transfer rating |
|---|---|---|
| Velocity: tx count / amount in 1m/5m/1h/24h per card | **tx count / value / new-contract interactions per wallet per N blocks**; rolling windows on (wallet × contract) pairs | **Steal wholesale** — the 2-minute card-testing rule (count≥N, avg<ε) ports nearly verbatim |
| Behavioral profile + B-lists ("favorites") | Per-wallet counterparty favorites: set of contracts/EOAs the wallet has interacted with ≥k times; **first-ever-interaction-with-contract-X is the highest-risk event** | **Steal wholesale** — the "miss on favorites" concept is exactly how to score a wallet touching a victim contract for the first time |
| Device fingerprinting | **Wallet clustering:** shared funder, shared relayer/paymaster, nonce-timing patterns, deployer graphs = "same device behind many wallets" | Adapt — on-chain identity is cheaper to rotate, so cluster-level velocity matters more than wallet-level |
| Geolocation / impossible travel | No spatial analog; temporal analog: **time-of-day / day-of-week deviation**, plus cross-chain bridge hop timing (funding appears on chain B minutes after chain A) | Partial — time features transfer; "impossible travel" becomes "impossible funding velocity" |
| MCC / merchant risk scores | **Protocol/category risk:** mixers, bridges, fresh token mints, unverified contracts, known-vulnerable contract versions (graveyard list itself) = high-risk "merchants" | **Steal wholesale** — precompute a risk score per contract/category exactly like MCC scoring |
| Amount deviation from cardholder mean | Value ramp: test txs are dust/zero-value or `staticcall`-style probes; **the amount jump between consecutive txs from the same wallet** is the feature | **Steal wholesale** — Splunk's "first<$20, then>$3000 in 1 min" rule is the drain signature |
| 1–99 score → issuer decides approve/decline/step-up | **1–99 risk score per (wallet, contract) pair → tiered actions:** log / alert / pre-stage rescue / whitehat front-run race | Steal wholesale — score/action separation is how we manage alert fatigue |
| Consortium data sharing (9,000 banks) | **We get this for free.** All chains' data is public; no coordination needed. Global "first seen by anyone" features (first wallet to touch a contract, first funding from a known bad cluster) are things card systems pay dearly for | **Superpower — exploit aggressively** |
| Dual-speed defense (slow predictive + fast real-time) | Slow: continuous profiling for test-tx signatures, pre-staged rescue playbooks. Fast: per-block/mempool scoring, trigger rescue race | **Steal wholesale** — this is the scanner's architecture |
| Step-up authentication | No on-chain equivalent mid-flow — BUT the analog is **delayed confirmation heuristics**: treat "test observed, drain not yet seen" as the step-up state (heightened watch, not a block) | Adapt |

**Steal wholesale (4):** velocity windows with dual count+amount thresholds; favorites/B-list first-contact scoring; contract-category risk scores (MCC analog); score/action separation with tiered thresholds by stake.
**Adapt (3):** device fingerprinting → wallet clustering; impossible travel → funding-velocity/timing anomalies; step-up auth → heightened-watch state between test and drain.
**Don't bother (1):** the chargeback clawback itself — no reversible ledger on-chain; replace with the rescue race, and use chargeback-shaped *evidence packages* only for the CEX-freeze path.

---

## 10. Bottom line for the recon paper

The card industry solved "detect the test before the fraud" under constraints *harsher* than ours in one dimension (50ms scoring budgets, adversaries who can change devices/IPs freely) and *easier* in another (they can reverse mistakes via chargebacks; we can't). Three things they know that we should internalize:

1. **The test is the detectable event; the drain is often unstoppable.** Their entire architecture (velocity rules on sub-$2 bursts, Account Attack Intelligence flagging tested accounts *pre-monetization*) assumes you catch the probe, not the theft. Our scanner's recall target should be measured on *test-tx detection*, not drain prediction.
2. **Features > models, profiles > features.** The winning move for 30 years has been per-entity behavioral profiles updated in real time (Falcon's B-lists, Visa's 500 attributes, Mastercard's merchant-relationship graphs), not cleverer classifiers. Build the per-wallet/per-contract profile store first; the model is the cheap part.
3. **You can't win the false-positive war, so tier it.** 13:1 false-decline-to-fraud ratios, $297B projected false-decline costs — the industry accepted that perfect precision is impossible and built *graded responses* (score → alert → step-up → decline). On-chain, our ladder is: log → alert → pre-stage rescue → front-run race. Each rung has a different precision requirement; don't hold the "race" rung to the same bar as the "log" rung.

---

*Sources: Visa investor/newsroom, Visa Fall 2025 Biannual Threats Report, Mastercard Decision Intelligence materials, FICO/Falcon consortium reporting, Javelin Strategy & Research (via techxplore/paymentsindustryintelligence), ChargebackHelp, chargeflow.io, directpaynet.com, RisingWave fraud-detection tutorial, dev.to production-architecture writeup, Splunk Lantern, Chan & Stolfo KDD-98, Fawcett & Provost (1997/1999/2006), fraud-detection-handbook.github.io. All URLs above.*
