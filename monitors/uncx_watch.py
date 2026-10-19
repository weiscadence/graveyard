#!/usr/bin/env python3
"""UNCX Network VestingManager V2 incident monitor (read-only).

Watches Vesting V2 contracts on Ethereum / Base / BNB Chain / Robinhood Chain
for new exploit-pattern activity after the Oct 14-15, 2026 accounting exploit
($86K -> $1.49M as copycats joined; Blockaid flagged "ongoing").

Exploit pattern: createPosition -> release() -> donate tokens -> cancel().
release() reduces global _totalTokenShares without removing shares from the
position's _depositedShares; cancel() then deducts the same shares twice,
leaving a tiny residual position that can claim other users' deposits.

Target addresses load from uncx-targets.example.json (ship your own watchlist). Chains with unresolved (null)
addresses are reported as PENDING and skipped. Never sends transactions.

State: uncx-state.json next to this script (last-seen tx hashes per chain).
Output: JSON report to stdout. Exit 2 with "ALERT" lines when new suspicious
activity is found. Exit 3 (INCOMPLETE) when there is no alert but the zero was not
earned: a chain errored, or no polled chain returned a single tx. Exit 0 only when
every polled chain answered and at least one tx was actually checked.
"""
import json, subprocess, sys, os, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "uncx-state.json")
TARGETS_FILE = os.path.join(HERE, "uncx-targets.example.json")  # public repo ships
# schema + example only; point this at your own watchlist (live lists not published,
# see RESPONSIBLE-DISCLOSURE.md)

# RPC rotation: shared fallback chains for free public endpoints.
# Imported lazily so the script still runs if the module is missing.
try:
    sys.path.insert(0, HERE)
    from rpc_rotation import rpc_call as _rotated_rpc
    _ROTATION = True
except ImportError:
    _ROTATION = False

# Exploit-relevant function name fragments (lowercased, parens stripped).
# Any successful state-changing call matching these from an unknown address alerts.
EXPLOIT_METHODS = {"createposition", "createvesting", "release", "cancel",
                   "cancelvesting", "donate", "withdraw", "claim", "topup"}

# Exploit sequence must concentrate in time: real ops complete in minutes
# (Sep 2026 attacker: 43 min). A wallet doing create/cancel/release scattered
# over months is normal vesting usage, not an attack.
SEQ_WINDOW_HOURS = 24


def ts_hours(ts):
    try:
        dt = datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp() / 3600
    except Exception:
        return None


def is_exploit_sequence(txs, window_hours=SEQ_WINDOW_HOURS):
    """True if txs contain create+release+cancel concentrated within window_hours.

    The wallet must touch all three method families AND compress them into the
    window. Returns (hit, span_hours). The 2026-10-18 pagination backfill
    showed why: a wallet doing create/cancel/release scattered over months
    (0x037287a8…, Apr+Sep 2026, pre-exploit normal usage) tripped the
    windowless version. A real exploit sequence runs in minutes to hours.
    """
    methods = " ".join(t["method"].split("(")[0].lower() for t in txs)
    if not ("create" in methods and "release" in methods and "cancel" in methods):
        return False, 0.0
    hs = [h for h in (ts_hours(t["timestamp"]) for t in txs) if h is not None]
    if not hs:
        return False, 0.0
    span = (max(hs) - min(hs)) if len(hs) > 1 else 0.0
    return span <= window_hours, span

# Pure reads — never alert on these.
READ_METHODS = {"name", "symbol", "decimals", "totalsupply", "balanceof",
                "getposition", "positions", "totalshares", "totaltokenshares",
                "owner", "fee", "paused", "version"}

# Per-chain tx-list sources. kind = "blockscout" (REST tx list, decoded methods)
# or kind = "rpc_logs" (eth_getLogs from a stored block cursor, selectors
# decoded via openchain with a local cache). "unavailable" = honestly reported
# coverage gap, not a dead poll.
# 2026-10-18 overnight hardening, run 2: bnb and base legs moved from DEGRADED
# to live via publicnode RPC. bsc-dataseed caps eth_getLogs (-32005), but
# bsc.publicnode.com serves 5000-block windows and base-rpc.publicnode.com
# serves 2000-block windows (verified live this run). Etherscan v2 API is
# key-gated for these chains (free tier: NOTOK), so RPC is the free path.
CHAIN_SOURCES = {
    "ethereum":  {"kind": "blockscout",
                  "url": lambda a: f"https://eth.blockscout.com/api/v2/addresses/{a}/transactions"},
    "base":      {"kind": "rpc_logs", "rpc": "https://base-rpc.publicnode.com",
                  "window": 2000,  # 2s blocks; 2000 ~ 66 min; walk from cursor each run
                  "note": "publicnode base-rpc is archive-gated beyond ~8k blocks; "
                          "cursor walking keeps us inside the live window at 4h cadence"},
    "bnb":       {"kind": "rpc_logs", "rpc": "https://bsc.publicnode.com",
                  "window": 5000,  # 3s blocks; 5000 ~ 4.2h
                  "note": "bsc-dataseed caps getLogs (-32005); bsc.publicnode.com serves 5000-block windows"},
    "robinhood": {"kind": "unavailable"},  # Arbitrum Orbit L2; no indexed free tx API in our stack
}


def fetch_tx_pages(base_url, seen, max_pages=10):
    """Walk Blockscout tx-list pages until we hit already-seen hashes.

    Burst-safety (added 2026-10-18): the old code only ever looked at page 1
    (50 txs). During an exploit wave more than 50 txs can land between polls
    and the overflow would be silently skipped — the exact scenario this
    monitor exists for. Blockscout v2 pagination is cursor-based
    (next_page_params), NOT ?page=N; a naive ?page= param returns an error.
    Walk the cursor until an overlap with `seen` or an empty page, bounded
    at max_pages (500 txs) to keep the poll bounded.
    """
    items = []
    url = base_url
    pages = 0
    for _ in range(max_pages):
        data = fetch(url)
        page_items = data.get("items", [])
        pages += 1
        if not page_items:
            break
        items.extend(page_items)
        if any((t.get("hash") or t.get("tx_hash")) in seen for t in page_items):
            break
        npp = data.get("next_page_params")
        if not npp:
            break
        q = "&".join(f"{k}={v}" for k, v in npp.items())
        url = base_url + "?" + q
    return items, pages


def fetch(url, timeout=40):
    p = subprocess.run(["curl", "-s", "-w", "\nHTTP_STATUS:%{http_code}", "--max-time", str(timeout), "-A", "Mozilla/5.0", url],
                       capture_output=True, text=True, timeout=timeout + 10)
    body, _, status = p.stdout.rpartition("\nHTTP_STATUS:")
    try:
        return json.loads(body)
    except Exception:
        raise RuntimeError(f"non-JSON response (http {status.strip()}; first 60 chars: {body[:60]!r})")


def rpc_call(rpc_url, method, params, timeout=45):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    p = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-A", "Mozilla/5.0",
                        "-H", "Content-Type: application/json",
                        "-d", body, rpc_url],
                       capture_output=True, text=True, timeout=timeout + 10)
    out = json.loads(p.stdout)
    if "error" in out:
        raise RuntimeError(f"rpc {method}: {out['error'].get('message', out['error'])!r}")
    return out.get("result")


def rpc_call_chain(chain, rpc_url, method, params, timeout=45):
    """Try the rotation layer first (free public fallback chain), then the
    configured URL. Raises only if every endpoint failed."""
    if _ROTATION:
        try:
            r = _rotated_rpc(chain, method, params)
            if r is not None:
                return r
        except Exception:
            pass
    return rpc_call(rpc_url, method, params, timeout)


def selector_name(selector, cache, timeout=20):
    """4-byte selector -> 'name(argtypes)' via openchain, cached in state."""
    if selector in cache:
        return cache[selector]
    try:
        p = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             f"https://api.openchain.xyz/signature-database/v1/lookup?function={selector}&filter=true"],
            capture_output=True, text=True, timeout=timeout + 10)
        res = json.loads(p.stdout).get("result", {}).get("function", {}).get(selector, [])
        name = res[0]["name"] if res else "unknown"
    except Exception:
        name = "unknown"
    cache[selector] = name
    return name


def ts_from_hex(h):
    try:
        return datetime.datetime.fromtimestamp(int(h, 16), datetime.timezone.utc).isoformat()[:16]
    except Exception:
        return "?"


def poll_rpc_chain(chain, addr, cfg, state):
    """Walk eth_getLogs from the stored block cursor -> latest on a public RPC.

    Returns (txs_newest_first, fresh, extra). Logs only exist for executed
    (non-reverted) txs, so status is reported "ok" honestly here. First run
    backfills one window; later runs walk from the previous latest.
    """
    cursor_key = chain + "_cursor"
    cache = state.setdefault("selector_cache", {})
    seen = set(state.get(chain, []))
    latest = int(rpc_call_chain(chain, cfg["rpc"], "eth_blockNumber", []), 16)
    frm = state.get(cursor_key)
    if frm is None:
        frm = max(0, latest - cfg["window"])
    touched = {}   # txhash -> blocknumber
    blk = frm
    while blk <= latest:
        to = min(blk + cfg["window"], latest)
        logs = rpc_call_chain(chain, cfg["rpc"], "eth_getLogs",
                        [{"address": addr, "fromBlock": hex(blk), "toBlock": hex(to)}])
        for l in logs or []:
            h = l.get("transactionHash")
            if h and h not in touched:
                touched[h] = int(l.get("blockNumber", "0x0"), 16)
        blk = to + 1
    fresh = []
    for h in [h for h in touched if h not in seen]:
        try:
            t = rpc_call_chain(chain, cfg["rpc"], "eth_getTransactionByHash", [h])
        except Exception:
            t = None
        if not t:
            continue
        inp = t.get("input") or "0x"
        sel = inp[:10] if len(inp) >= 10 else "0x"
        fresh.append({"hash": h,
                      "timestamp": ts_from_block(touched[h], cfg["rpc"]),
                      "method": selector_name(sel, cache),
                      "from": (t.get("from") or "")[:42],
                      "status": "ok",
                      "value": str(int(t.get("value", "0x0"), 16))})
    # newest first by block
    fresh.sort(key=lambda t: touched[t["hash"]], reverse=True)
    state[cursor_key] = latest + 1
    state[chain] = [t["hash"] for t in fresh] + list(state.get(chain, []))
    state[chain] = state[chain][:300]
    extra = {"checked": len(touched),
             "blocks_walked": f"{frm}..{latest}",
             "source": f"rpc eth_getLogs @ {cfg['rpc'].split('//')[1]}; selectors via openchain"}
    return fresh, fresh, extra


def ts_from_block(bnum, rpc_url):
    try:
        info = rpc_call(rpc_url, "eth_getBlockByNumber", [hex(bnum), False])
        ts = info.get("timestamp") if info else None
        return ts_from_hex(ts) if ts else "?"
    except Exception:
        return "?"


def norm_txs(items):
    out = []
    for t in items:
        h = t.get("hash") or t.get("tx_hash")
        frm = t.get("from")
        if isinstance(frm, dict):
            frm = frm.get("hash")
        method = t.get("method")
        if not method:
            di = t.get("decoded_input") or {}
            method = (di.get("method_call") or "?")[:40]
        ts = t.get("timestamp") or "?"
        out.append({"hash": h, "timestamp": str(ts)[:16], "method": str(method)[:40],
                    "from": (frm or "")[:42], "status": t.get("status") or "?",
                    "value": t.get("value") or "0"})
    return out


def is_exploit_method(method):
    m = (method or "").split("(")[0].lower().replace(" ", "").replace("_", "")
    return any(k in m for k in EXPLOIT_METHODS)


def is_read(method):
    m = (method or "").split("(")[0].lower().replace(" ", "").replace("_", "")
    return m in READ_METHODS


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    targets = json.load(open(TARGETS_FILE)) if os.path.exists(TARGETS_FILE) else {"targets": []}
    addr_by_chain = {t["chain"]: t.get("address") for t in targets.get("targets", [])}

    report = {"ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "incident": "UNCX VestingManager V2 accounting exploit (2026-10-14/15)",
              "chains": {}, "alerts": []}

    for chain, src in CHAIN_SOURCES.items():
        addr = addr_by_chain.get(chain)
        if not addr:
            report["chains"][chain] = {
                "pending": "target address resolved from project docs; no public RPC for this chain to verify or poll — configure in uncx-targets.example.json"}
            continue
        kind = src.get("kind")
        if kind == "unavailable":
            report["chains"][chain] = {
                "degraded": "no durable free tx API for Robinhood Chain in our stack"}
            continue
        try:
            if kind == "rpc_logs":
                txs, fresh, extra = poll_rpc_chain(chain, addr, src, state)
            else:
                seen = set(state.get(chain, []))
                items, pages = fetch_tx_pages(src["url"](addr), seen)
                txs = norm_txs(items)
                fresh = [t for t in txs if t["hash"] and t["hash"] not in seen]
                state[chain] = [t["hash"] for t in txs if t["hash"]][:500]
                extra = {"source": "blockscout v2 txlist API", "pages_fetched": pages}
        except Exception as e:
            report["chains"][chain] = {"error": str(e)[:120]}
            continue

        sus = []
        seq_alerts = []
        # Sequence check FIRST: same wallet doing create->release->cancel across fresh txs.
        # Single release()/cancel() calls are NORMAL user behavior (monthly vesting claims).
        # Only the full exploit sequence alerts, AND it must concentrate in time
        # (SEQ_WINDOW_HOURS): the 2026-10-18 backfill taught us that a wallet doing
        # create/cancel/release scattered over months (e.g. 0x037287a8…, Apr+Sep 2026,
        # pre-exploit normal usage) is not an attack. (Lesson 2026-10-18: naive per-call
        # alerting flagged a legitimate user with 38 routine releases as "suspicious.")
        by_wallet = {}
        for t in fresh:
            if t["status"] == "ok":
                by_wallet.setdefault((t["from"] or "").lower(), []).append(t)
        for w, wt in by_wallet.items():
            hit, span = is_exploit_sequence(wt)
            if hit:
                seq_alerts.append(
                    f"ALERT [{chain}] EXPLOIT-SEQUENCE: wallet {w[:14]} executed "
                    f"create->release->cancel pattern ({len(wt)} txs, {span:.1f}h span)")
                sus.extend(wt)
        # Single exploit-method calls are noted but do NOT alert alone.
        noted = 0
        for t in fresh:
            if t["status"] != "ok" or is_read(t["method"]):
                continue
            if is_exploit_method(t["method"]) and t not in sus:
                noted += 1
        report["alerts"].extend(seq_alerts)

        report["chains"][chain] = {
            "contract": addr[:14] + "...",
            "checked": len(txs), "new": len(fresh),
            "new_suspicious": len(sus),
            "latest": [f"{t['timestamp']} {t['method'][:28]} {t['status']}" for t in txs[:5]],
            **extra,
        }

    json.dump(state, open(STATE, "w"), indent=1)
    code, why = exit_code(report)
    report["verdict"] = {0: "CLEAN", 2: "ALERT", 3: "INCOMPLETE"}[code] + (": " + why if why else "")
    print(json.dumps(report, indent=1))
    if code == 3:
        print("INCOMPLETE: " + why + " (not a clean result)", file=sys.stderr)
    return code


def exit_code(report):
    """0 = clean, 2 = alert, 3 = incomplete. A zero is only clean if it was earned:
    every polled chain answered without error and at least one tx was checked."""
    if report.get("alerts"):
        return 2, ""
    chains = report.get("chains", {})
    errored = sorted(c for c, v in chains.items() if "error" in v)
    polled = {c: v for c, v in chains.items() if "checked" in v}
    if errored:
        return 3, "chain error on " + ", ".join(errored)
    if not polled:
        return 3, "no chain was polled"
    if sum(v["checked"] for v in polled.values()) == 0:
        return 3, "0 txs checked on " + ", ".join(sorted(polled))
    return 0, ""


if __name__ == "__main__":
    sys.exit(main())
