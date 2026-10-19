#!/usr/bin/env python3
"""Limit Break Payment Processor incident monitor (read-only).

Watches V2 (Ethereum/Polygon/Base) and V3 (ApeChain) for new on-chain activity
after the Sept 25, 2026 exploit. Flags new successful state-changing calls from
unknown addresses. Settlement-function calls are classified TESTING vs
TARGETING per the playbook rule (known 2026-10-17 probe operators = TESTING;
new wallets = possible TARGETING, escalate). Never sends transactions.

State: state.json next to this script (last-seen tx hashes per chain).
Output: JSON report to stdout; exit 0 normally, exit 2 with "ALERT" lines when
new suspicious activity is found.
"""
import json, subprocess, sys, os, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state.json")

V2 = "0xLIMITBREAK_V2_CONTRACT"  # live protocol target withheld; configure your own
V3 = "0xLIMITBREAK_V3_CONTRACT"  # live protocol target withheld; configure your own
RESCUE_WALLET = "0xRESCUE_WALLET_ADDRESS"  # whitehat rescue wallet withheld

# addresses whose activity is expected (team / whitehats); everything else is "unknown"
KNOWN = {RESCUE_WALLET.lower()}

# Test-vs-Targeting rule (RESCUE-PLAYBOOK.md, added 2026-10-18; ground truth
# RECON-20261017-03). A settlement-function call from an address in this set =
# TESTING phase (watch only, do not escalate). The same settlement call from a
# NEW wallet = possible TARGETING phase (escalate to the operator immediately).
# These are the confirmed 2026-10-17 Limit Break V2 probing operators:
#  (synthetic fixtures below stand in for the real 2026-10-17 probe operators;
#   the real operator wallets are withheld from the public repo)
OPERATOR_TEST = {
    "0x00000000000000000000000000000000000000d1",
    "0x00000000000000000000000000000000000000d2",
    "0x00000000000000000000000000000000000000d3",
    "0x00000000000000000000000000000000000000d4",
}

# Settlement-path functions: exploit developers validate the attack path
# against contracts they control (mock collections) before aiming at real
# victims. These method names are the classifier input for TESTING vs TARGETING.
SETTLEMENT_METHODS = {"buylisting", "buylistingadvanced", "bulkbuylistingsadvanced",
                      "acceptoffer", "filllisting", "fillorder", "buyoutlisting"}


def is_settlement(method):
    m = (method or "").split("(")[0].lower().replace(" ", "").replace("_", "")
    return m in SETTLEMENT_METHODS or m.startswith("buylisting") or "acceptoffer" in m

# Mock-vs-real collection classifier (RESCUE-PLAYBOOK.md "Test vs Targeting",
# ground truth RECON-20261017-03, encoded 2026-10-18). Event ABI from
# limitbreakinc/payment-processor src/interfaces/IPaymentProcessorEvents.sol
# (public repo): all four settlement events share the topic layout
#   topics[1] = first party, topics[2] = seller, topics[3] = tokenAddress
# (the NFT collection). Topic hashes computed with keccak over the canonical
# signatures (BuListingERC721 hash 0xffb29e9c... matches the selector in the
# Polygon rescue playbook, confirming the strings).
SETTLEMENT_TOPICS = {
    # BuyListingERC721(address,address,address,address,address,uint256,uint256)
    "0xffb29e9cf48456d56b6d414855b66a7ec060ce2054dcb124a1876310e1b7355c",
    # BuyListingERC1155(address,address,address,address,address,uint256,uint256,uint256)
    "0x1217006325a98bdcc6afc9c44965bb66ac7460a44dc57c2ac47622561d25c45a",
    # AcceptOfferERC721(address,address,address,address,address,uint256,uint256)
    "0x8b87c0b049fe52718fe6ff466b514c5a93c405fb0de8fbd761a23483f9f9e198",
    # AcceptOfferERC1155(address,address,address,address,address,uint256,uint256,uint256)
    "0x6f4c56c4b9a9d2479f963d802b19d17b02293ce1225461ac0cb846c482ee3c3e",
}

# Known operator-owned mock collections from the 2026-10-17 probes
# (RECON-20261017-03). Real operator-owned mock collections withheld; the
# synthetic fixtures below preserve the classifier's set-membership logic.
# The evening fill was a self-deal (seller == operator intermediary) -> TESTING.
MOCK_COLLECTIONS = {
    "0x00000000000000000000000000000000000000d2",
    "0x00000000000000000000000000000000000000d4",
    "0x00000000000000000000000000000000000000d5",
}
# keccak256(runtime bytecode) of the same two mock collections, measured
# 2026-10-18 via eth_getCode on Polygon (read-only). Catches mock CLONES:
# exploit devs redeploy the same mock contract for the next probe.
MOCK_CODEHASHES = {
    "49b91deff3f1c0742b51dbe7c3cd0db0041ef666d5be6a0a2270dc0067c0e95b",
    "01b84260f5025f58dc586ae7e1cd13cb5540777bc3e8da887a9050a1d0b718ad",
    # evening mock collection 0x8a65977d... runtime bytecode keccak,
    # measured 2026-10-18 via eth_getCode on Polygon (read-only)
    "7d767595dfb14b55d3f77b3ba8a78235ebf95b780d4af2e2983df08c59542b45",
}


def parse_settlement_event(logs, pp_addr):
    """Scan receipt logs for a settlement event from the payment processor.
    Returns (seller, collection) address strings, or (None, None)."""
    if not logs:
        return None, None
    for lg in logs:
        topics = lg.get("topics") or []
        if len(topics) < 4:
            continue
        if (lg.get("address") or "").lower() != pp_addr.lower():
            continue
        if (topics[0] or "").lower() not in SETTLEMENT_TOPICS:
            continue
        def addr(t):
            # Lowercase: topic hex may arrive checksummed (Blockscout/Caldera
            # REST) and every downstream set (MOCK_COLLECTIONS, OPERATOR_TEST,
            # self-deal ==) is lowercase. Without this, a checksummed known
            # mock misses the set and a checksummed self-deal seller !=
            # lowercased sender -> false TARGETING escalation (2026-10-18 fix).
            return ("0x" + t[-40:]).lower() if t else None
        return addr(topics[2]), addr(topics[3])
    return None, None


def classify_settlement(chain_rpc, sender, seller, collection):
    """Test-vs-Targeting verdict for a settlement call with a parsed event.
    Returns (verdict, reason). verdict in {"TESTING","TARGETING","UNCLEAR"}.
    Read-only: at most two eth_getCode calls for unknown contracts."""
    # Normalize: membership sets and the self-deal comparison are lowercase.
    # Callers must not rely on the event parser having done this (2026-10-18).
    sender = (sender or "").lower() or None
    seller = (seller or "").lower() or None
    collection = (collection or "").lower() or None
    if not seller or not collection:
        return "UNCLEAR", "settlement event missing from receipt logs; seller-based classification only"
    if collection in MOCK_COLLECTIONS:
        return "TESTING", f"collection {collection[:12]} is a known 2026-10-17 mock (RECON-20261017-03)"
    if sender and seller == sender:
        return "TESTING", "seller == tx sender (self-deal: both sides controlled)"
    if seller in OPERATOR_TEST:
        return "TESTING", f"seller {seller[:12]} is a known 2026-10-17 probe operator contract"
    # clone check: same mock bytecode under a new address
    try:
        code = rpc_call(chain_rpc, "eth_getCode", [collection, "latest"]) or "0x"
    except Exception:
        code = "0x"
    if code != "0x":
        import hashlib
        try:
            from Crypto.Hash import keccak as _keccak
            kh = _keccak.new(digest_bits=256, data=bytes.fromhex(code[2:])).hexdigest()
        except ImportError:
            kh = hashlib.sha3_256(bytes.fromhex(code[2:])).hexdigest()  # NOT keccak; best-effort only
            kh = None
        if kh and kh in MOCK_CODEHASHES:
            return "TESTING", f"collection {collection[:12]} bytecode hash matches a known mock (clone redeploy)"
    # third-party seller EOA = the playbook's flip-to-targeting fingerprint
    try:
        seller_code = rpc_call(chain_rpc, "eth_getCode", [seller, "latest"]) or "0x"
    except Exception:
        seller_code = "0x"
    if seller_code == "0x" and (not sender or seller != sender):
        return "TARGETING", (f"seller {seller[:12]} is a third-party EOA and collection "
                             f"{collection[:12]} is not a known mock — real-collection "
                             "targeting fingerprint; escalate")
    return "UNCLEAR", (f"seller {seller[:12]} / collection {collection[:12]} not classifiable "
                       "from on-chain shape alone; human review")

CHAINS = [
    {"name": "ethereum", "pp": V2, "txlist": f"https://eth.blockscout.com/api/v2/addresses/{V2}/transactions"},
    # polygon: Blockscout API is Cloudflare-challenged (HTTP 403) as of 2026-10-08.
    # Keyless fallback: public RPC eth_getLogs over the V2 address. Only txs that emit
    # events are visible (an event-less state change would be missed) — documented in
    # the per-run report note.
    {"name": "polygon",  "pp": V2, "txlist": "RPC"},
    # base: no free tx API (basescan V1 deprecated, etherscan V2 paywalled for Base,
    # base.blockscout.com unreachable) -> monitored as degraded; V2 is same bytecode as Ethereum
    {"name": "base",     "pp": V2, "txlist": "DEGRADED"},
    {"name": "apechain", "pp": V3, "txlist": f"https://apechain.calderaexplorer.xyz/api/v2/addresses/{V3}/transactions"},
]

POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"
# Provider (publicnode) hard-caps eth_getLogs at 10,000 blocks per call
# (error -32701). Requests MUST be chunked at <= 10000 blocks (2026-10-15 fix:
# the single-call POLYGON_MAX_RANGE window went fully blind from 2026-10-08).
POLYGON_CHUNK = 10000
# Max backfill per run in blocks (~11.6 days at ~2s/block). Chunked calls make
# this cheap; V2 is quiet post-exploit, so per-tx lookups stay small.
POLYGON_MAX_RANGE = 1000000

READ_METHODS = {"getfloorprice", "remainingfillablequantity", "royaltyinfo", "getroyalty", "name",
                "symbol", "decimals", "totalSupply", "owner", "paused", "getpaymenttoken"}

def fetch(url, timeout=40):
    p = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-A", "Mozilla/5.0", url],
                       capture_output=True, text=True, timeout=timeout + 10)
    return json.loads(p.stdout)

def norm_txs(chain, items):
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
        ts = t.get("timestamp") or (datetime.datetime.fromtimestamp(int(t["time"]), datetime.timezone.utc).isoformat() if t.get("time") else "?")
        out.append({"hash": h, "timestamp": str(ts)[:16], "method": str(method)[:40],
                    "from": (frm or "")[:42], "status": t.get("status") or "?",
                    "value": t.get("value") or "0"})
    return out

def rpc_batch(rpc, calls, timeout=40, retries=1):
    """Send a JSON-RPC batch; returns list of results (raises on transport/JSON error)."""
    payload = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p}
               for i, (m, p) in enumerate(calls)]
    last_err = None
    for attempt in range(retries + 1):
        try:
            p = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-A", "Mozilla/5.0",
                                "-H", "Content-Type: application/json",
                                "-d", json.dumps(payload), rpc],
                               capture_output=True, text=True, timeout=timeout + 10)
            if not p.stdout.strip():
                raise RuntimeError("empty RPC response")
            resp = json.loads(p.stdout)
            break
        except Exception as e:
            last_err = e
            time.sleep(2)
    else:
        raise RuntimeError(f"rpc transport failed after {retries + 1} tries: {last_err}")
    if isinstance(resp, dict) and resp.get("error"):
        raise RuntimeError(f"rpc error: {resp['error']}")
    out = {}
    items = resp if isinstance(resp, list) else [resp]
    for r in items:
        if r.get("error"):
            raise RuntimeError(f"rpc batch item error: {r['error']}")
        out[r["id"]] = r.get("result")
    return [out[i] for i in range(len(calls))]

def rpc_call(rpc, method, params, timeout=40):
    return rpc_batch(rpc, [(method, params)], timeout=timeout)[0]

def decode_selector(state, selector):
    """4-byte selector -> 'name(args)' via openchain.xyz (keyless); cached in state."""
    cache = state.setdefault("polygon_selectors", {})
    if selector in cache:
        return cache[selector]
    name = selector
    try:
        p = subprocess.run(["curl", "-s", "--max-time", "15", "-A", "Mozilla/5.0",
                            f"https://api.openchain.xyz/signature-database/v1/lookup"
                            f"?function={selector}&filter=true"],
                           capture_output=True, text=True, timeout=25)
        d = json.loads(p.stdout)
        fn = (d.get("result") or {}).get("function", {}).get(selector)
        if fn:
            name = fn[0]["name"]
    except Exception:
        pass
    cache[selector] = name
    return name

def _persist(state):
    """Write state to disk immediately. The Polygon backfill spans many chunks;
    a transient RPC failure mid-backfill must not discard completed chunks."""
    json.dump(state, open(STATE, "w"), indent=1)


# Non-settlement state-changing calls: the playbook's operator-wallet rule still
# applies — a known 2026-10-17 testing operator probing new functions stays
# TESTING (watch only, do not escalate). A new wallet's state-changing call
# stays a raw ALERT (possible escalation path into TARGETING).
def label_non_settlement(name, t, frm):
    if frm in OPERATOR_TEST:
        return (f"TESTING [{name}] non-settlement state-changing call {t['method']} "
                f"from {t['from'][:12]} value={t['value']} at {t['timestamp']} tx {t['hash'][:14]} — "
                "known 2026-10-17 testing operator; watch, do not escalate")
    return (f"ALERT [{name}] new successful state-changing call: {t['method']} "
            f"from {t['from'][:12]} value={t['value']} at {t['timestamp']} tx {t['hash'][:14]}")


def poll_polygon_rpc(state):
    """Keyless Polygon poll via public RPC eth_getLogs. Returns list of tx records
    in the same shape as norm_txs(). Advances state['polygon_last_block']
    incrementally per completed chunk, persisted immediately, so a failed run
    resumes where it left off instead of restarting the backfill."""
    latest = int(rpc_call(POLYGON_RPC, "eth_blockNumber", []), 16)
    last = state.get("polygon_last_block")
    if last is None:
        # first run after the Blockscout->RPC switch: seed at head, no backfill
        state["polygon_last_block"] = latest
        _persist(state)
        return []
    frm = last + 1
    if frm > latest:
        return []
    if latest - frm > POLYGON_MAX_RANGE:
        frm = latest - POLYGON_MAX_RANGE
    out = []
    start = frm
    while start <= latest:
        end = min(start + POLYGON_CHUNK - 1, latest)
        # chunked getLogs: provider rejects any single call over 10k blocks
        # (-32701) and occasionally times out (-32002); retry transient failures
        logs = rpc_batch(
            POLYGON_RPC,
            [("eth_getLogs", [{
                "address": V2,
                "fromBlock": hex(start),
                "toBlock": hex(end),
            }])],
            timeout=40, retries=2)[0] or []
        tx_hashes = []
        seen_h = set()
        for lg in logs:
            h = lg.get("transactionHash")
            if h and h not in seen_h:
                seen_h.add(h)
                tx_hashes.append(h)
        if tx_hashes:
            txs = rpc_batch(POLYGON_RPC,
                            [("eth_getTransactionByHash", [h]) for h in tx_hashes],
                            retries=2)
            rcts = rpc_batch(POLYGON_RPC,
                             [("eth_getTransactionReceipt", [h]) for h in tx_hashes],
                             retries=2)
            # one batched block lookup per unique block for timestamps
            blk_nums = sorted({t.get("blockNumber") for t in txs if t and t.get("blockNumber")})
            blk_ts = {}
            if blk_nums:
                blks = rpc_batch(POLYGON_RPC,
                                 [("eth_getBlockByNumber", [b, False]) for b in blk_nums],
                                 retries=2)
                for b, bh in zip(blk_nums, blks):
                    if bh and bh.get("timestamp"):
                        blk_ts[b] = datetime.datetime.fromtimestamp(
                            int(bh["timestamp"], 16), datetime.timezone.utc
                        ).strftime("%Y-%m-%dT%H:%M")
            for h, tx, rc in zip(tx_hashes, txs, rcts):
                if not tx:
                    continue
                sel = (tx.get("input") or "")[:10]
                method = decode_selector(state, sel) if len(sel) == 10 else (tx.get("input") or "?")[:40]
                status = "ok" if rc and rc.get("status") == "0x1" else "?"
                ts = blk_ts.get(tx.get("blockNumber"), "?")
                seller, collection = parse_settlement_event(rc.get("logs") if rc else None, V2)
                rec = {"hash": h, "timestamp": ts, "method": str(method)[:40],
                       "from": (tx.get("from") or "")[:42], "status": status,
                       "value": tx.get("value") or "0"}
                if seller:
                    rec["seller"] = seller
                    rec["collection"] = collection
                out.append(rec)
        # watermark advances per completed chunk, persisted now
        state["polygon_last_block"] = end
        _persist(state)
        time.sleep(0.5)  # be polite to the free RPC
        start = end + 1
    return out

def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    report = {"ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "apechain_v3_sunset": "2026-11-30",
              "days_to_sunset": (datetime.date(2026, 11, 30) - datetime.date.today()).days,
              "chains": {}, "alerts": []}
    for c in CHAINS:
        name = c["name"]
        if c["txlist"] == "DEGRADED":
            report["chains"][name] = {"degraded": (
                "no durable free tx API for Base; same V2 bytecode as Ethereum. "
                "Measured 2026-10-15: publicnode base-rpc serves eth_getLogs only for "
                "the most recent ~8k blocks (~4.4h, archive-gated beyond; keyed access "
                "needs the operator's approval), too fragile for the 4h cadence - one missed run "
                "breaks continuity and the existing gap can't backfill.")}
            continue
        try:
            if c["txlist"] == "RPC":
                txs = poll_polygon_rpc(state)
                src_note = "rpc eth_getLogs (event-emitting txs only)"
            else:
                items = fetch(c["txlist"]).get("items", [])
                txs = norm_txs(name, items)
                src_note = None
        except Exception as e:
            report["chains"][name] = {"error": str(e)[:120]}
            continue
        seen = set(state.get(name, []))
        fresh = [t for t in txs if t["hash"] and t["hash"] not in seen]
        state[name] = [t["hash"] for t in txs[:50] if t["hash"]]
        sus = []
        for t in fresh:
            m = (t["method"] or "").split("(")[0].lower().replace(" ", "")
            is_read = m in READ_METHODS
            frm = (t["from"] or "").lower()
            if not is_read and t["status"] == "ok" and frm not in KNOWN:
                sus.append(t)
                if is_settlement(t["method"]):
                    # Test-vs-Targeting classifier (RESCUE-PLAYBOOK.md): the
                    # settlement event's collection address separates TESTING
                    # (operator-owned mock) from TARGETING (third-party /
                    # established collection). Polygon receipts are already
                    # fetched above; ethereum/apechain receipts are pulled
                    # best-effort (settlement txs are rare, so the extra calls
                    # stay cheap). Any failure falls back to the tx-sender rule.
                    chain_rpc = {"polygon": POLYGON_RPC,
                                 "ethereum": "https://ethereum-rpc.publicnode.com",
                                 "apechain": "https://apechain.caldera.xyz/http"}.get(name)
                    seller, collection = t.get("seller"), t.get("collection")
                    if (seller is None or collection is None) and chain_rpc:
                        try:
                            rc = rpc_call(chain_rpc, "eth_getTransactionReceipt", [t["hash"]])
                            seller, collection = parse_settlement_event(rc.get("logs") if rc else None, c["pp"])
                        except Exception:
                            seller, collection = None, None
                    verdict, reason = ("UNCLEAR", "receipt unavailable"), ""
                    if chain_rpc and seller:
                        verdict, reason = classify_settlement(chain_rpc, frm, seller, collection)
                        # Known operator sender + unclassifiable receipt must not
                        # sit as UNCLEAR (human-review noise): the playbook's
                        # operator-wallet rule pins it to TESTING regardless.
                        if verdict == "UNCLEAR" and frm in OPERATOR_TEST:
                            verdict, reason = ("TESTING",
                                               "known 2026-10-17 testing operator (receipt unclassifiable)")
                    elif frm in OPERATOR_TEST:
                        verdict, reason = "TESTING", "known 2026-10-17 testing operator"
                    if verdict == "TESTING":
                        report["alerts"].append(
                            f"TESTING [{name}] settlement call {t['method']} from {t['from'][:12]} "
                            f"value={t['value']} at {t['timestamp']} tx {t['hash'][:14]} — {reason}; "
                            "watch, do not escalate")
                    elif verdict == "TARGETING":
                        report["alerts"].append(
                            f"TARGETING [{name}] settlement call {t['method']} from {t['from'][:12]} "
                            f"value={t['value']} at {t['timestamp']} tx {t['hash'][:14]} — {reason}; "
                            "BRIEF JIGGY (rescue window may be opening)")
                    else:
                        report["alerts"].append(
                            f"UNCLEAR [{name}] settlement call {t['method']} from {t['from'][:12]} "
                            f"value={t['value']} at {t['timestamp']} tx {t['hash'][:14]} — {reason}; "
                            "human review, do not escalate alone")
                else:
                    report["alerts"].append(label_non_settlement(name, t, frm))
        report["chains"][name] = {
            "checked": len(txs), "new": len(fresh),
            "new_suspicious": len(sus),
            "latest": [f"{t['timestamp']} {t['method'][:28]} {t['status']}" for t in txs[:5]],
        }
        if src_note:
            report["chains"][name]["source"] = src_note
    json.dump(state, open(STATE, "w"), indent=1)
    print(json.dumps(report, indent=1))
    return 2 if report["alerts"] else 0

if __name__ == "__main__":
    sys.exit(main())
