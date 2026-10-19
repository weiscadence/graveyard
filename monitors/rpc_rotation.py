#!/usr/bin/env python3
"""Shared RPC rotation layer for graveyard-scanner monitors.

Problem: free public RPCs rate-limit, 403, or die at random. Every monitor
was hitting one endpoint and failing. This module provides per-chain fallback
chains: try each endpoint in order, roll to the next on failure.

No API keys. All endpoints are free public RPCs. For keyed access (Etherscan
V2, Alchemy), use transient interactive calls — never bake keys into files.

Usage:
    from rpc_rotation import rpc_call
    result = rpc_call("ethereum", "eth_blockNumber", [])
    # returns parsed JSON result, or None if all endpoints failed

    from rpc_rotation import CHAINS
    # CHAINS maps chain name -> list of RPC URLs in priority order
"""
import http.client
import json
import urllib.request

TIMEOUT = 20
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}

CHAINS = {
    "ethereum": [
        "https://eth.llamarpc.com",
        "https://rpc.ankr.com/eth",
        "https://ethereum.publicnode.com",
        "https://1rpc.io/eth",
        "https://eth.meowrpc.com",
    ],
    "polygon": [
        "https://polygon-bor.publicnode.com",
        "https://rpc.ankr.com/polygon",
        "https://polygon.llamarpc.com",
        "https://1rpc.io/matic",
    ],
    "base": [
        "https://base.llamarpc.com",
        "https://rpc.ankr.com/base",
        "https://base.publicnode.com",
        "https://1rpc.io/base",
    ],
    "bnb": [
        "https://bsc.publicnode.com",
        "https://rpc.ankr.com/bsc",
        "https://bsc-dataseed.binance.org",
        "https://1rpc.io/bnb",
    ],
    "arbitrum": [
        "https://arb1.arbitrum.io/rpc",
        "https://rpc.ankr.com/arbitrum",
        "https://arbitrum.publicnode.com",
    ],
    "avalanche": [
        "https://api.avax.network/ext/bc/C/rpc",
        "https://rpc.ankr.com/avalanche",
    ],
    "optimism": [
        "https://mainnet.optimism.io",
        "https://rpc.ankr.com/optimism",
        "https://optimism.publicnode.com",
    ],
}

# Etherscan V2 (keyed, transient use only) chain IDs for reference.
# Free tier covers: ethereum (1), polygon (137). NOT base (8453), bnb (56).
ETHERSCAN_V2_CHAINS = {
    "ethereum": 1,
    "polygon": 137,
    "base": 8453,      # paid plan required
    "bnb": 56,         # paid plan required
    "arbitrum": 42161,
    "optimism": 10,
}


def _post(url, method, params):
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params,
    }).encode()
    req = urllib.request.Request(url, data=body, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except (http.client.IncompleteRead, http.client.RemoteDisconnected) as e:
        # 2026-10-19: urllib truncates large JSON-RPC responses (>~16KB) on this
        # egress path (IncompleteRead at 16384 bytes, verified live against
        # ethereum.publicnode.com eth_getCode), while curl/requests fetch the
        # full body. Retry once via requests; on failure re-raise so the
        # rotation layer moves to the next endpoint.
        rq = None
        try:
            import requests as rq
        except ImportError:
            raise e
        r = rq.post(url, data=body,
                    headers={"Content-Type": "application/json",
                             "User-Agent": HEADERS["User-Agent"]},
                    timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()


def rpc_call(chain, method, params=None, _tried=None):
    """Call a JSON-RPC method on a chain, rotating through fallback endpoints.

    Returns the parsed 'result' field, or None if every endpoint failed.
    Never raises on transport errors — returns None instead.
    """
    params = params or []
    endpoints = CHAINS.get(chain, [])
    tried = _tried or []
    for url in endpoints:
        if url in tried:
            continue
        tried.append(url)
        try:
            resp = _post(url, method, params)
            if "result" in resp:
                return resp["result"]
            # Error response — try next endpoint
        except Exception:
            continue
    return None


def rpc_call_verbose(chain, method, params=None):
    """Same as rpc_call but returns (result, endpoint_used, failures)."""
    params = params or []
    failures = []
    for url in CHAINS.get(chain, []):
        try:
            resp = _post(url, method, params)
            if "result" in resp:
                return resp["result"], url, failures
            failures.append(f"{url}: rpc-error {str(resp.get('error'))[:60]}")
        except Exception as e:
            failures.append(f"{url}: {type(e).__name__} {str(e)[:60]}")
    return None, None, failures


# Blockscout v2 hosts known to index a given chain (established in workspace:
# uncx_watch.py uses eth.blockscout.com txlist for its ethereum leg).
# These serve read-only contract-presence checks when the JSON-RPC layer dies.
BLOCKSCOUT_V2 = {
    "ethereum": "https://eth.blockscout.com",
}


def blockscout_get_code(chain, address):
    """Read-only contract-presence check via Blockscout v2 REST.

    Returns (bytecode_bytes:int, sha256:str) or (None, None) on failure.
    Proved live 2026-10-18 for ethereum when all 10 JSON-RPC endpoints were
    unreachable: confirmed UNCX VestingManager V2 at 18,010 bytes, matching
    the earlier eth_getCode measurement. Use as the fallback when
    rpc_call(chain, 'eth_getCode', ...) returns None.
    """
    import hashlib
    host = BLOCKSCOUT_V2.get(chain)
    if not host:
        return None, None
    url = f"{host}/api/v2/smart-contracts/{address}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            r = json.load(resp)
    except Exception:
        return None, None
    code = r.get("deployed_bytecode") or ""
    if not (code.startswith("0x") and len(code) > 2):
        return None, None
    raw = bytes.fromhex(code[2:])
    return len(raw), hashlib.sha256(raw).hexdigest()


def health_check():
    """Return {chain: (ok_bool, latency_ms or error)} for all chains."""
    import time
    out = {}
    for chain, endpoints in CHAINS.items():
        url = endpoints[0]
        t0 = time.time()
        try:
            _post(url, "eth_blockNumber", [])
            out[chain] = (True, int((time.time() - t0) * 1000))
        except Exception as e:
            out[chain] = (False, f"{type(e).__name__}")
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        for chain, (ok, info) in health_check().items():
            print(f"{chain:12s} {'OK' if ok else 'FAIL'}  {info}")
    else:
        # Smoke test: block number on each chain
        for chain in CHAINS:
            r = rpc_call(chain, "eth_blockNumber", [])
            print(f"{chain:12s} block={int(r, 16) if r else 'FAILED'}")
