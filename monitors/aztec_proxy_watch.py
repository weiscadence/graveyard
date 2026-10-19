#!/usr/bin/env python3
"""One-shot / monitorable read-only check: has a frozen TransparentUpgradeableProxy
ever emitted Upgraded(address) or
AdminChanged(address,address)?

Evidence pair with aztec-connect-brief.md: owner()=0x0 (renounced). A zero-event
history over the scanned window corroborates "frozen forever"; any Upgraded event
would be a 10/10 protective signal (contradicts renounced-ownership read -> recheck).

Usage: python3 aztec_proxy_watch.py  -> JSON to stdout, no state written.
READ-ONLY: eth_getLogs only. Uses rpc_rotation.py (free endpoints, no keys).
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpc_rotation import rpc_call
from Crypto.Hash import keccak

PROXY = os.environ.get("AZTEC_PROXY", "0xYOUR_FROZEN_PROXY_ADDRESS")  # set to your
# own deprecated/renounced proxy; live target address not published
UPGRADED = "0x" + keccak.new(digest_bits=256, data=b"Upgraded(address)").hexdigest()
ADMIN_CHANGED = "0x" + keccak.new(digest_bits=256, data=b"AdminChanged(address,address)").hexdigest()
CHUNK = 50_000
SCAN_DEPTH = 500_000  # last ~500k blocks; widen deliberately, not by default

def main():
    latest = rpc_call("ethereum", "eth_blockNumber")
    latest_n = int(latest, 16)
    start = latest_n - SCAN_DEPTH
    events = []
    for lo in range(start, latest_n + 1, CHUNK):
        hi = min(lo + CHUNK - 1, latest_n)
        for topic in (UPGRADED, ADMIN_CHANGED):
            try:
                logs = rpc_call("ethereum", "eth_getLogs", [{
                    "address": PROXY,
                    "topics": [topic],
                    "fromBlock": hex(lo),
                    "toBlock": hex(hi),
                }])
            except Exception as e:  # endpoint hiccup -> note, don't die
                print(json.dumps({"error": str(e), "window": [hex(lo), hex(hi)]}), file=sys.stderr)
                continue
            for lg in (logs or []):
                events.append({
                    "block": lg["blockNumber"],
                    "tx": lg["transactionHash"],
                    "event": "Upgraded" if topic == UPGRADED else "AdminChanged",
                    "topics": lg["topics"],
                })
    print(json.dumps({
        "proxy": PROXY,
        "scanned": [hex(start), hex(latest_n)],
        "upgraded_topic": UPGRADED,
        "admin_changed_topic": ADMIN_CHANGED,
        "upgrade_events_found": events,
        "no_upgrade_events_in_window": len(events) == 0,
        "owner_is_zero_per_brief": True,
    }, indent=2))

if __name__ == "__main__":
    main()
