#!/usr/bin/env python3
"""Blast L1 bridge balance snapshot — read-only pre-shutdown baseline.

Oct 26, 2026 the Blast L2 shuts down; its L1 bridge stack on Ethereum
becomes unmaintained-but-callable (the Aztec zombie pattern, whole-chain).
This takes a point-in-time snapshot of ERC-20 + ETH balances at every
canonical bridge address so any later watch can detect anomalous flows.

Usage:  python3 blast_snapshot.py [out.json]
Reads only: eth_call(balanceOf) + eth_getBalance. No transactions.
"""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpc_rotation import rpc_call

USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
DAI  = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
STETH= "0xae7ab96520DE3A18E5e111B5EaAB095312D7fE84"

TARGETS = {
    # address: [token contracts to read] (plus native ETH always)
    # Bridge/portal target addresses withheld from the public repo. Fill in the
    # canonical bridge-stack addresses for the chain you are baselining; the token
    # constants above (canonical public ERC-20s) are what gets balance-read at each.
    "0xL1_BLAST_BRIDGE_ADDRESS":        ("L1BlastBridge",         [USDC, WETH, USDT, DAI, STETH]),
    "0xL1_STANDARD_BRIDGE_ADDRESS":     ("L1StandardBridge",      [USDC, WETH, USDT, DAI]),
    "0xOPTIMISM_PORTAL_ADDRESS":        ("OptimismPortal",        []),
    "0xL1_CROSS_DOMAIN_MESSENGER_ADDR": ("L1CrossDomainMessenger",[]),
    "0xL2_OUTPUT_ORACLE_ADDRESS":       ("L2OutputOracle",        []),
    "0xOLD_GNOSIS_SAFE_DEPOSIT_ADDR":   ("OldGnosisSafeDeposit",  [USDC, USDT, DAI, WETH]),
}

def bal_of(token, holder):
    data = "0x70a08231" + holder[2:].lower().rjust(64, "0")
    r = rpc_call("ethereum", "eth_call", [{"to": token, "data": data}, "latest"])
    return int(r, 16) if r else None

def main():
    block = rpc_call("ethereum", "eth_blockNumber", [])
    snap = {"taken_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "block": block, "targets": {}}
    for addr, (name, tokens) in TARGETS.items():
        row = {"name": name}
        eth = rpc_call("ethereum", "eth_getBalance", [addr, "latest"])
        row["ETH_wei"] = int(eth, 16) if eth else None
        for t in tokens:
            row[t] = bal_of(t, addr)
        snap["targets"][name] = row
        time.sleep(0.3)
    out = sys.argv[1] if len(sys.argv) > 1 else "blast-balances-snapshot.json"
    json.dump(snap, open(out, "w"), indent=1)
    print(json.dumps(snap, indent=1))

if __name__ == "__main__":
    main()
