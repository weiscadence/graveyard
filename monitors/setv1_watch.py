#!/usr/bin/env python3
"""Set Protocol V1 rebalancing-set incident monitor (read-only).

Watches the top-5 remaining Set V1 rebalancing sets on Ethereum for the
Oct 2026 actualizeFee() rounding exploit fingerprint after the protocol was
hit twice on 2026-10-06 (tx1 ~4.05 WETH on ETHMACOAPY/0xB647..., tx2 ~5.08
WETH on ETHEMAAPY/0x54e8... via Uniswap V4 flash accounting; a copycat
landed 2 blocks / ~24 s after the first hit).

Exploit sequence (SunWeb3Sec PoC, DeFiHackLabs src/test/2026-10/):
  core.issue(rSet, qty)            -> mint of rSet (Transfer 0x0 -> attacker)
  core.deposit + internalTransfer  -> DONATE base set into rSet's Vault backing
  rSet.actualizeFee()              -> permissionless, zero-fee, rounds unitShares UP
  core.redeem(rSet, qty)           -> burn of rSet (Transfer attacker -> 0x0)
All in ONE transaction. actualizeFee() emits NO event when fees are zero, so
detection is: Transfer mint/burn legs from eth_getLogs on the set token, plus
internal-call records (blockscout) for the actualizeFee leg, confirmed
per-tx via eth_getTransactionReceipt.

Target addresses load from setv1-targets.example.json (ship your own watchlist). Never sends transactions.

State: setv1-state.json next to this script (log cursor, seen tx hashes).
Output: JSON report to stdout; exit 0 normally, exit 2 with "ALERT" lines on
the fingerprint. --selftest replays the classifier on the two known Oct-6
attack txs (dead check with a known answer); exits 0 iff both are flagged.

MEMPOOL-SPEED ALERTING (why 30-minute polling cannot catch the copycat)
-----------------------------------------------------------------------
Observed: the copycat landed 2 blocks (~24 s) after the first hit. A cron
running every 30 minutes can only *record* an attack after the fact; it
cannot warn before the second hit lands.

What sub-24-second detection would actually require:
1. Pending-tx visibility. The Oct-6 txs show the hallmarks of private
   submission (single-block landing, no public-mempool trace in the
   writeups). Mempool sniffing alone MISSES private orderflow. You need
   BOTH:
     a. a mempool stream: newPendingTransactions over a low-latency RPC
        (local Erigon/Reth node, or a fiber feed like Chainbound /
        bloXroute), AND
     b. a private-orderflow view: block-builder/relay data (MevBoost
        relay feeds, mempool-dump services) or your own builder, because
        scanner-style attackers submit privately.
2. Pre-confirmation simulation. For every pending tx touching a target
   set, Core, or the Vault, run trace simulation (debug_traceCall) against
   the pending block and match the
   issue -> donate -> actualizeFee -> redeem call sequence BEFORE the tx
   is included. Budget ~200-800 ms per tx on local hardware; a remote RPC
   adds 100-300 ms RTT per call and will not keep up.
3. Latency budget inside one 12-second Ethereum block:
     propagation to your node ......... ~0.5-2 s
     trace + classify ................. ~0.5-1 s
     alert fan-out (page / wire post) . ~1-2 s
   Total ~2-5 s leaves ~7-10 s of headroom. The two-block (~24 s) copycat
   gap is beatable ONLY if the first attack's tx is visible
   pre-confirmation; a privately submitted first hit gives ZERO warning.
4. Response lever. NOTHING on-chain can stop it: V1 is immutable, no
   pause, no upgrade, no owner. The only sub-24s action is warning
   holders to redeem before the attacker's tx confirms (which itself
   needs private orderflow or priority fees to outrun the attacker).
   Realistic value of mempool alerting: forensic certainty plus
   copycat early-warning for the NEXT set on the ranked list — never
   prevention of the hit in flight.

Bottom line: THIS script is a forensic tripwire, not a shield. A real
shield needs a local node + pending-tx simulation + private-orderflow
access, and even then it can only warn, never block.
"""
import json, subprocess, sys, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "setv1-state.json")
TARGETS_FILE = os.path.join(HERE, "setv1-targets.example.json")  # schema + example
# only; point at your own watchlist (live lists not published)

RPC = "https://eth.drpc.org"
# Endpoint selection (verified 2026-10-18): eth.drpc.org serves BOTH
# eth_getLogs and eth_getTransactionReceipt. ethereum-rpc.publicnode.com
# returns NULL receipts; eth.meowrpc.com does not support eth_getLogs.
# If this endpoint degrades, re-verify the pair before swapping.
BLOCKSCOUT = "https://eth.blockscout.com/api/v2"

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO_TOPIC = "0x" + "0" * 64
LOG_WINDOW = 100  # getLogs chunk size; cursor-walked each run
# Verified 2026-10-18: eth.drpc.org free plan rejects ranges >~100 blocks
# despite its "10000 blocks" error text. 100 works; 120 fails.

# Known Oct-6 attack txs (selftest canaries — must classify ALERT).
CANARY_TX1 = "0xb54c77dae4c5ff8664779bacfb56d75242f39005b0b7778109d2f9033b9e8fc2"
CANARY_TX2 = "0xaca5f83ff3a206209f3d213c33d04e6febe345f6ad52ef476bd1c0ee1505ba65"


def fetch(url, timeout=40):
    p = subprocess.run(["curl", "-s", "-w", "\nHTTP_STATUS:%{http_code}", "--max-time", str(timeout), "-A", "Mozilla/5.0", url],
                       capture_output=True, text=True, timeout=timeout + 10)
    body, _, status = p.stdout.rpartition("\nHTTP_STATUS:")
    try:
        return json.loads(body)
    except Exception:
        raise RuntimeError(f"non-JSON response (http {status.strip()}; first 60 chars: {body[:60]!r})")


def rpc_call(method, params, timeout=45):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    p = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-A", "Mozilla/5.0",
                        "-H", "Content-Type: application/json",
                        "-d", body, RPC],
                       capture_output=True, text=True, timeout=timeout + 10)
    out = json.loads(p.stdout)
    if "error" in out:
        raise RuntimeError(f"rpc {method}: {out['error'].get('message', out['error'])!r}")
    return out.get("result")


def addr_topic(a):
    return "0x" + "0" * 24 + a.lower().replace("0x", "")


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(state):
    state["seen_tx"] = state.get("seen_tx", [])[:600]
    state["seen_itx"] = state.get("seen_itx", [])[:600]
    json.dump(state, open(STATE, "w"), indent=1)


def walk_logs(targets, state):
    """eth_getLogs Transfer events on all target set tokens from cursor."""
    latest = int(rpc_call("eth_blockNumber", []), 16)
    frm = state.get("logs_cursor")
    first_run = frm is None
    if first_run:
        frm = max(0, latest - LOG_WINDOW)
    addrs = [t["address"] for t in targets]
    hits = []  # (txhash, target_addr, log)
    blk = frm
    while blk <= latest:
        to = min(blk + LOG_WINDOW, latest)
        logs = rpc_call("eth_getLogs", [{
            "address": addrs, "topics": [TRANSFER_TOPIC],
            "fromBlock": hex(blk), "toBlock": hex(to)}]) or []
        for l in logs:
            h = l.get("transactionHash")
            if h:
                hits.append((h, (l.get("address") or "").lower(), l))
        blk = to + 1
    state["logs_cursor"] = latest + 1
    return hits, latest, first_run


def poll_internal_txs(targets, state):
    """Newest-first internal txs per target via blockscout; dedup by tx+index."""
    seen = set(state.get("seen_itx", []))
    fresh = []  # (txhash, target_addr, item)
    for t in targets:
        a = t["address"]
        try:
            items = fetch(f"{BLOCKSCOUT}/addresses/{a}/internal-transactions").get("items", [])
        except Exception:
            continue
        for it in items:
            key = f"{it.get('transaction_hash')}:{it.get('index')}"
            if key not in seen:
                seen.add(key)
                fresh.append((it.get("transaction_hash"), a.lower(), it))
    state["seen_itx"] = sorted(seen)
    return fresh


def poll_direct_calls(targets, state):
    """Top-level txs TO each target (rare; decoded method via blockscout)."""
    fresh = []
    seen_tx = set(state.get("seen_tx", []))
    for t in targets:
        a = t["address"]
        try:
            items = fetch(f"{BLOCKSCOUT}/addresses/{a}/transactions?filter=to").get("items", [])
        except Exception:
            continue
        for it in items:
            h = it.get("hash")
            key = "direct:" + (h or "")
            if h and key not in seen_tx:
                seen_tx.add(key)  # mark here; main dedups the tx itself via h
                fresh.append((h, a.lower(), it))
    state["seen_tx"] = sorted(seen_tx)
    return fresh


def internal_txs_for_tx(txhash):
    try:
        return fetch(f"{BLOCKSCOUT}/transactions/{txhash}/internal-transactions").get("items", [])
    except Exception:
        return []


def classify_tx(txhash, target_addrs, vault, benign, itx_hint=None):
    """Replay the fingerprint classifier on one tx. Returns legs dict."""
    legs = {"issue": False, "redeem": False, "donate": False,
            "direct_call": False, "wallets": set(), "target": None,
            "mint_recipient": None}
    try:
        r = rpc_call("eth_getTransactionReceipt", [txhash])
    except Exception as e:
        legs["error"] = str(e)[:100]
        return legs
    if not r:
        legs["error"] = "no receipt"
        return legs
    tx_from = (r.get("from") or "").lower()
    if tx_from:
        legs["wallets"].add(tx_from)
    logs = r.get("logs") or []
    for l in logs:
        if (l.get("topics") or [None])[0] != TRANSFER_TOPIC or len(l.get("topics") or []) < 3:
            continue
        la = (l.get("address") or "").lower()
        frm_t, to_t = l["topics"][1], l["topics"][2]
        if la in target_addrs:
            legs["target"] = la
            if frm_t == ZERO_TOPIC:
                legs["issue"] = True
                legs["mint_recipient"] = "0x" + to_t[-40:]
                legs["wallets"].add(("0x" + to_t[-40:]).lower())
            if to_t == ZERO_TOPIC:
                legs["redeem"] = True
                legs["wallets"].add(("0x" + frm_t[-40:]).lower())
        if to_t == addr_topic(vault) and frm_t != ZERO_TOPIC:
            frm = ("0x" + frm_t[-40:]).lower()
            if frm in legs["wallets"] or frm == tx_from:
                legs["donate"] = True
    # actualizeFee leg: actualizeFee() emits NO event when fees are zero, and
    # free-tier trace metadata carries no input selectors, so the method
    # cannot be confirmed directly. Heuristic: a state-changing internal
    # "call" into the target from a non-protocol address (or the token
    # itself — the Oct-6 tx1 trace shows the target self-calling at one
    # point) is an actualizeFee PROBE CANDIDATE. Never the sole ALERT basis;
    # it upgrades issue->ISSUE+ACTUALIZEFEE and is noted alone.
    itxs = itx_hint if itx_hint is not None else internal_txs_for_tx(txhash)
    for it in itxs or []:
        to = it.get("to")
        to_h = (to.get("hash") if isinstance(to, dict) else to or "").lower()
        frm = it.get("from")
        frm_h = (frm.get("hash") if isinstance(frm, dict) else frm or "").lower()
        if to_h in target_addrs and (it.get("type") or "").lower() == "call" and frm_h not in benign:
            legs["direct_call"] = True
            legs["target"] = legs["target"] or to_h
            if frm_h:
                legs["wallets"].add(frm_h)
    legs["wallets"] = sorted(legs["wallets"])
    return legs


def verdict(legs):
    """(alert_label or None, note)."""
    if legs.get("issue") and legs.get("redeem"):
        extra = []
        if legs.get("donate"):
            extra.append("donate")
        if legs.get("direct_call"):
            extra.append("actualizeFee-call")
        return ("EXPLOIT-SEQUENCE", "issue+redeem same tx" + (" [" + "+".join(extra) + " seen]" if extra else ""))
    if legs.get("issue") and legs.get("direct_call"):
        return ("ISSUE+ACTUALIZEFEE", "mint + direct set-token call same tx (redeem may follow)")
    if legs.get("direct_call"):
        return (None, "lone direct call into set token (actualizeFee probe candidate)")
    if legs.get("issue") or legs.get("redeem"):
        return (None, "lone issue/redeem leg (user exit or partial sequence)")
    return (None, "no fingerprint legs")


def selftest(targets, vault, benign):
    """Dead check with a known answer: both Oct-6 attack txs must ALERT."""
    taddrs = {t["address"].lower() for t in targets}
    ok = True
    for name, h in (("tx1/ETHMACOAPY", CANARY_TX1), ("tx2/ETHEMAAPY", CANARY_TX2)):
        itxs = internal_txs_for_tx(h)
        legs = classify_tx(h, taddrs, vault, benign, itx_hint=itxs)
        label, note = verdict(legs)
        flagged = label is not None
        print(f"{'PASS' if flagged else 'FAIL'} {name} {h[:14]}... -> "
              f"{label or 'no-alert'} ({note}) "
              f"[issue={legs['issue']} redeem={legs['redeem']} donate={legs['donate']} direct={legs['direct_call']}]")
        ok = ok and flagged
    print("SELFTEST " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        tg = json.load(open(TARGETS_FILE))
        targets = tg["targets"]
        vault = tg["infrastructure"]["vault"]["address"].lower()
        infra = tg["infrastructure"]
        benign = {infra["core"]["address"].lower(), vault,
                  infra["transfer_proxy"]["address"].lower()}
        return selftest(targets, vault, benign)

    state = load_state()
    tg = json.load(open(TARGETS_FILE)) if os.path.exists(TARGETS_FILE) else {"targets": []}
    targets = [t for t in tg.get("targets", []) if t.get("address")]
    infra = tg.get("infrastructure", {})
    vault = infra.get("vault", {}).get("address", "").lower()
    benign = {infra.get("core", {}).get("address", "").lower(), vault,
              infra.get("transfer_proxy", {}).get("address", "").lower()} - {""}
    taddrs = {t["address"].lower() for t in targets}
    ticker_of = {t["address"].lower(): t.get("ticker", "?") for t in targets}

    report = {"ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "incident": "Set Protocol V1 actualizeFee() rounding exploit (2026-10-06)",
              "targets": {}, "alerts": [], "suspicious": []}

    try:
        log_hits, latest, first_run = walk_logs(targets, state)
    except Exception as e:
        print(json.dumps({"error": f"eth_getLogs walk failed: {str(e)[:120]}"}, indent=1))
        return 1

    itx_fresh = poll_internal_txs(targets, state)
    direct_fresh = poll_direct_calls(targets, state)

    # tx hashes worth classifying: any Transfer touch + any fresh internal/direct call
    seen_tx = set(state.get("seen_tx", []))
    candidates = {}
    for h, ta, _l in log_hits:
        candidates.setdefault(h, {"target": ta, "via": set()})["via"].add("logs")
    for h, ta, it in itx_fresh:
        if h:
            c = candidates.setdefault(h, {"target": ta, "via": set()})
            c["via"].add("internal-tx")
            c["itx"] = c.get("itx", []) + [it]
    for h, ta, it in direct_fresh:
        if h:
            c = candidates.setdefault(h, {"target": ta, "via": set()})
            c["via"].add("direct-call")
            m = (it.get("method") or "").lower()
            if "actualizefee" in m:
                c["direct_actualizefee"] = True

    if first_run:
        # Baseline: record everything seen, alert on nothing (history is in the paper).
        for h in candidates:
            seen_tx.add(h)
        state["seen_tx"] = sorted(seen_tx)
        save_state(state)
        report["targets"]["baseline"] = (f"first run: baselined {len(candidates)} txs, "
                                        f"cursor at block {latest}; future runs alert on new activity only")
        print(json.dumps(report, indent=1))
        return 0

    wallet_seqs = {}  # wallet -> set of legs seen this run
    alerted_wallets = set()  # wallets already covered by a same-tx ALERT
    for h, c in candidates.items():
        if h in seen_tx:
            continue
        seen_tx.add(h)
        # Merge per-address poll hits with the tx's own internal-tx page so
        # the direct_call heuristic isn't limited to the address window.
        itx_hint = (c.get("itx") or []) + internal_txs_for_tx(h)
        legs = classify_tx(h, taddrs, vault, benign, itx_hint=itx_hint)
        if c.get("direct_actualizefee"):
            legs["direct_call"] = True
        label, note = verdict(legs)
        tick = ticker_of.get(legs["target"] or c["target"], "?")
        wallets = ",".join(w[:14] for w in legs["wallets"][:2]) or "?"
        entry = {"tx": h, "ticker": tick, "legs": {k: v for k, v in legs.items()
                                                  if k in ("issue", "redeem", "donate", "direct_call")},
                 "wallets": legs["wallets"], "note": note, "via": sorted(c["via"])}
        if label:
            report["alerts"].append(f"ALERT [ethereum] {label}: tx {h} on {tick} — {note} (wallet {wallets})")
            alerted_wallets.update(legs["wallets"])
        elif legs["direct_call"] or legs["issue"] or legs["redeem"]:
            report["suspicious"].append(entry)
        for w in legs["wallets"]:
            s = wallet_seqs.setdefault(w, set())
            for leg in ("issue", "redeem", "donate", "direct_call"):
                if legs.get(leg):
                    s.add(leg)

    # Cross-tx "one wallet" form: same wallet showing issue+redeem(+donate)
    # across txs inside this run's window (not already same-tx alerted).
    for w, s in wallet_seqs.items():
        if {"issue", "redeem"} <= s and w not in alerted_wallets:
            report["alerts"].append(
                f"ALERT [ethereum] WALLET-SEQUENCE: wallet {w[:14]} showed "
                f"{'+'.join(sorted(s))} across txs this window")

    for t in targets:
        report["targets"][t["ticker"]] = {"address": t["address"][:14] + "...",
                                          "hit_status": t.get("hit_status", "")[:60]}
    report["summary"] = {"blocks": f"cursor->{latest}", "txs_classified": len(candidates),
                         "alerts": len(report["alerts"]),
                         "suspicious": len(report["suspicious"])}
    state["seen_tx"] = sorted(seen_tx)
    save_state(state)
    print(json.dumps(report, indent=1))
    return 2 if report["alerts"] else 0


if __name__ == "__main__":
    sys.exit(main())
