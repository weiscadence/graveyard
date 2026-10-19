# Wormhole Shift 5 — Thread 5: PREDATOR-PREY / IMMUNE SYSTEM
## Kill-switch review for the graveyard-scanner recon paper

**Date:** 2026-10-18. **Mode:** read-only research (web search + page fetches). No contact with anyone.
**Rule applied:** an idea survives only if it yields something we can BUILD or MEASURE that we couldn't before. If it merely reframes what we already know, it dies. Verdicts recorded below, plainly.

---

## 1. Self vs non-self: negative selection (DEAD)

**The biology/computation.** T-cell maturation in the thymus destroys lymphocytes that react to self antigens; surviving detectors are released to recognize non-self. Forrest et al. turned this into the Negative Selection Algorithm (NSA): randomly generate detectors, discard any that match a sample of "self" data, deploy the survivors as anomaly detectors — formally a one-class classification method trained on normal data only (V-detector / Ji & Dasgupta).

**The mapping attempt.** Our problem: distinguish legitimate user transactions (mock collections, routine releases) from attacker probes. A negative-selection system would need (a) a feature encoding of transactions, (b) a representative "self" set of legitimate traffic, (c) detectors covering the non-self space. In principle: train on a protocol's normal tx distribution, flag txs that match no self-pattern.

**Why it dies.** Three independent kills:

1. **Wrong problem shape.** Our scanner is a structural, protocol-level filter (deprecated + immutable + stranded value + permissionless mutation) — a signature/diff-rule system on *code and state*, not a tx-classifier. Negative selection detects anomalous *instances against a normal baseline*; it cannot generate our structural rules. It solves a problem we don't currently have, and for the problem we do have (scanning programs for structural exploitability), it's the wrong tool.
2. **Known scaling failure.** The literature is explicit: direct implementations need a detector count that grows exponentially with self-set size, with "holes" in non-self coverage that are undetectable in principle (analysis summarized at johannes-textor.name/negativeselection.html; see also the review in arxiv.org/pdf/0906.3461). Even with improvements (V-detectors), the field never converged on a version that beats plain one-class baselines.
3. **It adds nothing over existing ML.** "Train on normal, flag the rest" is one-class SVM / isolation forest with extra steps and worse scaling. The immune framing contributes no mechanism a textbook anomaly detector lacks.

**Verdict: KILL.** If the team ever wants tx-level anomaly detection on a per-protocol basis, plain one-class methods (isolation forest on tx feature vectors) do the job; negative selection would be poetry, not engineering.

**Sources:**
- Algorithm reference + scaling disadvantages: https://algorithmafternoon.com/immune/negative_selection_algorithm/
- Efficiency problems (exponential detector generation, holes): https://johannes-textor.name/negativeselection.html and https://tbb.bio.uu.nl/textor/negativeselection.html
- V-detector coverage analysis (Forrest et al. lineage, Ji & Dasgupta): http://www.sciencedirect.com/science/article/pii/S0020025508005434
- Critique summary: https://arxiv.org/pdf/0906.3461

---

## 2. Danger theory (Matzinger) / Dendritic Cell Algorithm (DEAD — barely)

**The biology/computation.** Matzinger's danger theory (2002): the immune system responds not to foreignness but to *damage* — danger signals from cells dying unnatural deaths. The Dendritic Cell Algorithm (DCA, Greensmith 2007) operationalizes this: dendritic cells fuse multiple input signals (PAMP, danger, safe) over a time window and correlate the fused signal with a secondary "antigen" stream — multi-sensor data fusion with context. It was applied to port-scan and botnet detection, reportedly with fewer false alarms than self-organizing maps.

**The mapping attempt.** Don't classify txs as attacker-vs-legit by appearance; watch for value-extraction "tissue damage" (large outflows, LP drain patterns) and correlate with preceding tx features. The DCA's genuine novelty vs negative selection: *damage-first signal fusion* and *co-stimulation* (no response without a second confirming signal).

**Why it dies.** It reframes what the scanner already does. Our filter is already damage-first: the "stranded value" criterion IS a danger signal, and our multi-factor filter (deprecated ∧ immutable ∧ stranded ∧ permissionless) IS co-stimulation — we already require multiple independent signals before alerting. The DCA's concrete algorithm is weighted multi-signal correlation with time windows; that is implementable but contributes no mechanism our existing scoring lacks. The one real lesson — "weight damage signals over identity signals" — is already our design.

**Verdict: KILL.** Genuine literature, but for this team's pipeline it's a reframing of existing architecture. (Note for the record: if a future tx-monitoring layer is ever built, the DCA papers are a legitimate reference for multi-signal alert correlation — but that future doesn't justify keeping the thread.)

**Sources:**
- DCA background, danger theory, applications: https://arxiv.org/pdf/1305.7416
- DCA for anomaly/port-scan detection: https://arxiv.org/pdf/1001.2411
- AIS-in-IDS survey (danger theory, libtissue, DCA vs TLR vs negative selection): https://pmc.ncbi.nlm.nih.gov/articles/PMC3981469/

---

## 3. Optimal foraging theory (WEAK SURVIVE)

**The biology.** OFT (Stephens & Krebs 1986): predators rank prey by profitability = E/h (energy per handling time), and the optimal-diet rule says a prey type is either always taken or always rejected on encounter — with a counter-intuitive twist: *the decision on prey B depends on the abundance of superior prey A, not on B's own abundance.* The Marginal Value Theorem extends this to patch-leaving: leave a patch when its marginal return drops to the environment average. Prediction: when high-profit prey become scarce, diet broadens to previously-rejected lower-ranked prey.

**The mapping attempt.** Our scanner's filter (deprecated + immutable + stranded value + permissionless mutation) is implicitly a profitability ranking — attackers maximize extractable value per reverse-engineering/probing effort. OFT's concrete content beyond "attackers are rational":

1. **Ranked watchlist:** score unexploited targets by expected_extractable_value / (search_time + handling_time), where handling ≈ exploit-development effort for that bug class. Rank, don't just threshold.
2. **The diet rule (non-obvious):** whether copycats bother with a target class depends on the availability of *higher-ranked* targets, not on how many targets of that class exist. Predictable consequence: a mid-value class gets hit only after the top classes are drained or patched.
3. **Diet-breadth expansion after waves:** the actionable forecast rule — after an exploit wave drains/patches the top-N ranked classes, the next wave's most likely target class is the (N+1)-ranked class. This is a concrete reprioritization algorithm: re-rank and reprioritize the watchlist after every wave, rather than rescanning everything at equal priority.

**Why it survives (weakly).** Items 2–3 give something buildable and measurable: a profitability-ranked queue plus a post-wave reprioritization rule, with a testable prediction against historical wave data (did copycats hit top-ranked remaining targets first? did diets broaden after top-rank drains?). We would not have written down the all-or-nothing diet rule or the depletion-driven broadening from rational-choice economics alone.

**Caveats.** This is the thinnest survivor. Much of it is rational-agent economics wearing a biology costume. OFT also assumes sequential encounters and stable prey handling times — in DeFi, "search time" is dominated by information (who knows the bug class), not geometry, so the MVT patch-leaving math doesn't transfer cleanly. Keep it as a ranking/reprioritization heuristic, not a law.

**Sources:**
- Profitability model E/(h+s), diet-breadth rule, all-or-nothing inclusion: https://www.bohrium.com/sciencepedia/optimal%20foraging%20theory/185390
- Optimal Diet Model details: https://scales.arabpsychology.com/trm/optimal-foraging-theory/

---

## 4. Red Queen / predator-prey arms race (DEAD)

**The biology.** Van Valen 1973: species must keep evolving just to hold relative fitness — co-evolutionary arms races; in cyber, mapped as attacker-vs-defender capability escalation.

**The mapping attempt.** Does the DeFi exploit/defense cycle match Red Queen dynamics? Descriptively, yes — weaponization windows compress, defenses adapt, attackers re-tool. The one quasi-actionable reading (from the geopolitical-cyber piece): a constant-rate defense program *loses ground* at the threat's advance rate, so budget/effort must grow just to hold position.

**Why it dies.** It gives the scanner nothing to build or measure. "Threats advance; keep running" is true and unactionable for a recon pipeline — it doesn't tell us which targets to scan, how to score them, or how to detect anything. The one measurable implication (track threat-advance rate vs our scan coverage rate) is a management metric, not a detection mechanism. The "Restrained Red Queen" variant (collect intel from attacks instead of retaliating) is nation-state strategy, out of scope.

**Verdict: KILL.** Correct description, zero mechanism. Do not cite in the recon paper except as an acknowledged-and-discarded framing.

**Sources:**
- Red Queen in cyber strategy (constant-effort defense loses ground; weaponization-window compression): https://geopoliticalcyber.johnellis.com.au/p/running-to-stand-still-the-illusion
- Cyber Defense Review "restrained Red Queen" (nation-state scope): https://cyberdefensereview.army.mil/CDR-Content/Articles/Article-View/Article/1590213/bring-on-the-cyber-attacks-the-increased-predatory-power-of-the-restrained-red/

---

## 5. Epidemiology: SIR for copycat waves (SIR DEAD; self-exciting cascades SURVIVE)

**The question.** We measured a ~15h copycat window. Can epidemic modeling predict wave size from R0-like parameters?

**SIR itself dies.** The classic SIR model (Kermack–McKendrick) assumes homogeneous mixing, target-to-target transmission, and recovery-with-immunity. Copycat exploit waves violate all three: targets don't infect each other (the *technique* spreads between attackers via information, not contact), and "recovered" means drained/patched, not immune — and a drained target can never be re-infected, so the susceptible pool is a fixed finite set of vulnerable protocols, not a mixing population. Fitting SIR to copycat data would be curve-fitting theater.

**What survives: the R0 analog in branching-process / self-exciting (Hawkes) form.** The correct formalism is the one seismology uses for aftershocks and cyber literature already uses for attack cascades:

- Each exploit *triggers* copycat exploits at a rate decaying with time since the original (the triggering kernel g(t)).
- The **branching ratio η** = expected number of direct offspring copycats per exploit — this is the true R0 analog.
- **Expected total wave size = 1/(1−η)** for η<1 (geometric series of generations); if η≥1 the process doesn't self-terminate.
- **Stochastic die-out:** even with η near 1, a large fraction of "introductions" produce zero copycats by chance (network-epidemic literature: with R0≈1.33, ~2/3 of seeds die out — the aicassindra worked example). This explains why most exploits produce no copycats even when the exploit is "contagious" — a prediction SIR-ODE models can't make.
- **The 15h window is the kernel timescale:** fit g(t) and the ~15h copycat window becomes the measured decay constant, not a magic number.

**Concrete buildable spec:**
1. Log exploit events + subsequent copycat events (same bug class, different attacker/protocol) — the team already tracks the ~15h window; extend to full timestamps and per-exploit features (PoC published? media/tweet coverage? TVL size? bug-class novelty?).
2. Fit a marked Hawkes / branching process per feature stratum (cyber literature does exactly this: Hawkes with external excitation for vulnerability-driven attack cascades, calibrated on Hackmageddon + NVD data — arXiv 2311.15701 and the HAL follow-up).
3. Extract η per exploit feature → at the next first-exploit, predict **expected copycat count = η/(1−η)** and the kernel decay time → drive scanner reprioritization (point the watchlist at the predicted target class for the predicted duration).

**Why it survives.** It converts the observed 15h window into a fitted parameter, predicts "how many copycats" from first-exploit characteristics, and explains zero-copycat exploits without hand-waving. This is measurable with data the team can collect and produces a number (expected wave size + duration) no other method gives.

**Honesty note:** this is seismology/point-process statistics, not biology. The SIR/epidemiology *framing* dies; the self-exciting-cascade *mechanism* survives. Credit accordingly.

**Sources:**
- Hawkes with external excitation for cyber-attack frequency (vulnerability-driven cascades, Hackmageddon + NVD calibration): https://arxiv.org/pdf/2311.15701
- Cyber risk frequency modeling using Hawkes, estimation methods compared: https://hal.science/hal-05305048v1
- Network epidemic threshold, R0, stochastic die-out, final-size math (Pastor-Satorras & Vespignani): https://www.aicassindra.com/blogs/algorithms/epidemic_models_networks.html
- SIR for malware (baseline we're rejecting for this use): https://api.intechopen.com/chapter/pdf-download/85267.pdf
- Hawkes definition (self-exciting intensity, stationarity condition ∫g<1): http://www.stat.ucla.edu/~frederic/papers/Hawkes3.pdf

---

## Summary verdict table

| Idea | Verdict | Reason in one line |
|---|---|---|
| Negative selection (self/non-self) | **DEAD** | Wrong problem (tx anomaly vs structural rules); exponential scaling failure; isolation forest with extra steps |
| Danger theory / DCA | **DEAD** | Reframes our existing damage-first multi-signal filter; adds no mechanism |
| Optimal foraging theory | **WEAK SURVIVE** | Profitability-ranked watchlist + post-wave diet-broadening reprioritization rule; testable against wave history |
| Red Queen arms race | **DEAD** | Descriptive only; no buildable mechanism for the scanner |
| SIR epidemiology | **DEAD** | Wrong transmission model (no target-to-target contact, no recovery-immunity) |
| Self-exciting cascades (branching ratio η as R0) | **SURVIVE** | Fit η per exploit features → predict wave size = η/(1−η), kernel from the 15h window; explains zero-copycat exploits; drives watchlist reprioritization |

**Recommended recon-paper treatment:** kill 1, 2, 4 explicitly (state they were tested and rejected, with reasons — this is the honest-calibration posture the user wants). Fold the two survivors into the wave-prediction section: OFT ranking as the *target-selection* model, Hawkes/branching as the *wave-size/duration* model. The combination is coherent: OFT says *which class* the copycats hit next; Hawkes says *how many* and *for how long*.

**Next measurable step (for the paper):** back-test both on historical exploit waves — (a) did copycats strike the highest-profitability remaining class (OFT)? (b) does η fitted on early copycats predict total wave size (Hawkes)? A spreadsheet of 10–20 historical waves with features is all that's needed; no new infrastructure.
