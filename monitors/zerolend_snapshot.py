#!/usr/bin/env python3
"""ZeroLend withdrawal-only pools — one-shot read-only snapshot.

ZeroLend (Aave V3 fork) shut down 2026-02-16/17: markets set to 0% LTV,
withdrawal-only, oracles pulled from dead chains (Manta, Zircuit, XLayer).
This script measures CURRENT on-chain state: which Pool proxies are still
live contracts, what reserves are listed, LTV config (0 = frozen), aToken
supply (outstanding supplier claims), debt-token supply (outstanding
borrows), and actual underlying ERC-20 custody held by the aToken contracts.

Read-only: eth_getCode + eth_call only. No state changes, no keys.

Outputs: work/incident-monitor/zerolend-snapshot-20261019.json
Usage: python3 zerolend_snapshot.py
"""
import json
import os
import sys
import time
import urllib.request

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}
TIMEOUT = 20

# Chain -> public RPC endpoints (script-local; rotation layer lacks these
# chains; no keyed endpoints used).
ENDPOINTS = {
    "linea": [
        "https://linea-rpc.publicnode.com",
        "https://rpc.linea.build",
        "https://rpc.ankr.com/linea",
        "https://1rpc.io/linea",
    ],
    "base": [
        "https://base-rpc.publicnode.com",
        "https://base.llamarpc.com",
        "https://rpc.ankr.com/base",
    ],
    "manta": [
        "https://pacific-rpc.publicnode.com",
        "https://1rpc.io/manta",
        "https://rpc.ankr.com/manta_pacific",
    ],
    "xlayer": [
        "https://xlayerrpc.okx.com",
        "https://rpc.ankr.com/xlayer",
    ],
}

# Pool proxies + PoolAddressesProviders are listed in the protocol's official
# deployed-addresses docs. Public repo ships placeholders; supply your own.
POOLS = {
    # Pool proxy + PoolAddressesProvider addresses are published in the protocol's
    # own deployed-addresses docs; they are withheld here so the public repo does not
    # ship a ready-made at-risk-market inventory. Fill from the official docs for the
    # chain you are snapshotting.
    "linea":  {"pool": "0xPOOL_PROXY_ADDRESS", "provider": "0xADDRESSES_PROVIDER", "chain_id": 59144},
    "base":   {"pool": "0xPOOL_PROXY_ADDRESS", "provider": "0xADDRESSES_PROVIDER", "chain_id": 8453},
    "manta":  {"pool": "0xPOOL_PROXY_ADDRESS", "provider": "0xADDRESSES_PROVIDER", "chain_id": 169},
    "xlayer": {"pool": "0xPOOL_PROXY_ADDRESS", "provider": "0xADDRESSES_PROVIDER", "chain_id": 196},
}

# Aave V3 Pool selectors
SEL_GET_RESERVES_LIST = "0xd1946dbc"
SEL_GET_RESERVE_DATA = "0x35ea6a75"
SEL_TOTAL_SUPPLY = "0x18160ddd"
SEL_BALANCE_OF = "0x70a08231"


def _post(url, method, params):
    """POST via curl (python's urllib hits IncompleteRead on publicnode's
    chunked keep-alive responses; curl handles them fine)."""
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    )
    import subprocess

    p = subprocess.run(
        [
            "curl", "-m", str(TIMEOUT), "-s", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-H", "User-Agent: " + HEADERS["User-Agent"],
            "--data-binary", body,
        ],
        capture_output=True, text=True, timeout=TIMEOUT + 5,
    )
    return json.loads(p.stdout)


def rpc(chain, method, params):
    """Rotate endpoints; return (result, url) or (None, None)."""
    for url in ENDPOINTS[chain]:
        try:
            r = _post(url, method, params)
            if "result" in r:
                return r["result"], url
        except Exception:
            continue
    return None, None


def get_code(chain, addr):
    res, _ = rpc(chain, "eth_getCode", [addr, "latest"])
    if res and res != "0x":
        return (len(res) - 2) // 2
    return 0


def eth_call(chain, to_addr, data):
    res, _ = rpc(chain, "eth_call", [{"to": to_addr, "data": data}, "latest"])
    return res


def enc_addr(a):
    return "0x" + a[2:].lower().rjust(64, "0")


def words(hexstr):
    h = hexstr[2:]
    return [h[i : i + 64] for i in range(0, len(h), 64)]


def parse_reserve_list(hexstr):
    """getReservesList returns address[]: offset, length, then entries."""
    if not hexstr or len(hexstr) < 130:
        return []
    ws = words(hexstr)
    n = int(ws[1], 16)
    return ["0x" + ws[2 + i][-40:] for i in range(n) if 2 + i < len(ws)]


def snapshot_chain(chain):
    cfg = POOLS[chain]
    out = {"chain": chain, "chain_id": cfg["chain_id"], "pool": cfg["pool"]}
    pool_code = get_code(chain, cfg["pool"])
    out["pool_bytecode_bytes"] = pool_code
    if pool_code == 0:
        out["error"] = "pool proxy has no code or RPC unreachable"
        return out
    prov_code = get_code(chain, cfg["provider"])
    out["provider_bytecode_bytes"] = prov_code

    res = eth_call(chain, cfg["pool"], SEL_GET_RESERVES_LIST)
    reserves = parse_reserve_list(res)
    out["reserves"] = reserves
    out["reserve_count"] = len(reserves)
    details = []
    for asset in reserves:
        d = {"asset": asset}
        rd = eth_call(chain, cfg["pool"], SEL_GET_RESERVE_DATA + enc_addr(asset)[2:])
        if rd and len(rd) > 2 + 64 * 11:
            ws = words(rd)
            # ZeroLend's Pool.getReserveData returns an EXTENDED ReserveData
            # (15 words, empirically decoded on Linea 2026-10-19): the stock
            # Aave V3 fields are shifted +4 words by 4 extra struct fields
            # (w4..w7, purpose unknown — recorded raw). Verified: w11 ==
            # docs' ReserveStrategy-rateStrategyStableOne address.
            d["ltv_bps"] = int(ws[0], 16) & 0xFFFF
            d["reserve_extra_w4"] = ws[4]
            d["reserve_extra_w5"] = ws[5]
            d["reserve_extra_w6"] = ws[6]
            d["reserve_extra_w7"] = ws[7]
            atoken = "0x" + ws[8][-40:]
            vardebt = "0x" + ws[10][-40:]
            d["aToken"] = atoken
            d["stableDebtToken"] = "0x" + ws[9][-40:]
            d["variableDebtToken"] = vardebt
            d["interestRateStrategy"] = "0x" + ws[11][-40:]
            d["accruedToTreasury"] = int(ws[12], 16)
            if atoken != "0x0000000000000000000000000000000000000000":
                ts = eth_call(chain, atoken, SEL_TOTAL_SUPPLY)
                d["aToken_totalSupply"] = int(ts, 16) if ts and len(ts) > 2 else None
                # actual underlying custody: balanceOf(aToken) on the asset
                bal = eth_call(chain, asset, SEL_BALANCE_OF + enc_addr(atoken)[2:])
                d["underlying_held_by_aToken"] = (
                    int(bal, 16) if bal and len(bal) > 2 else None
                )
            if vardebt != "0x0000000000000000000000000000000000000000":
                ds = eth_call(chain, vardebt, SEL_TOTAL_SUPPLY)
                d["variableDebt_totalSupply"] = (
                    int(ds, 16) if ds and len(ds) > 2 else None
                )
        details.append(d)
        time.sleep(0.3)  # be gentle on free RPCs
    out["reserve_details"] = details
    return out


def main():
    result = {
        "snapshot_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chains": {},
    }
    for chain in POOLS:
        print(f"--- {chain} ---", flush=True)
        try:
            snap = snapshot_chain(chain)
        except Exception as e:
            snap = {"chain": chain, "error": f"{type(e).__name__}: {e}"}
        result["chains"][chain] = snap
        if snap.get("pool_bytecode_bytes"):
            print(
                f"  pool code: {snap['pool_bytecode_bytes']} bytes, "
                f"reserves: {snap.get('reserve_count')}"
            )
        else:
            print(f"  FAILED: {snap.get('error')}")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "inventory", "zerolend-snapshot-20261019.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=1)
    print("wrote", path)


if __name__ == "__main__":
    main()
