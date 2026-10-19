#!/usr/bin/env python3
"""Canary test for limitbreak_watch.classify_settlement (read-only, no network).
Exercises every branch against 2026-10-17 ground truth. Fails loudly on regression."""
import sys, importlib.util, os
_HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("lw", os.path.join(_HERE, "limitbreak_watch.py"))
lw = importlib.util.module_from_spec(spec); spec.loader.exec_module(lw)

FAKE_EOA = "0x" + "00"
code_map = {}

def fake_rpc_call(rpc, method, params):
    assert method == "eth_getCode", method
    return code_map.get(params[0].lower(), "0x")

lw.rpc_call = fake_rpc_call
fails = []
def check(name, args, want):
    v, why = lw.classify_settlement("https://unused", *args)
    ok = (v == want)
    print(("PASS" if ok else "FAIL"), name, "->", v, "|", why[:100])
    if not ok: fails.append(name)

AFTERNOON_SENDER = "0x00000000000000000000000000000000000000d1"
AFTERNOON_MOCK = "0x00000000000000000000000000000000000000d2"
EVENING_SENDER = "0x00000000000000000000000000000000000000d3"
EVENING_CONTRACT = "0x00000000000000000000000000000000000000d4"
NEW_WALLET = "0x1111111111111111111111111111111111111111"
REAL_COLLECTION = "0x2222222222222222222222222222222222222222"  # EOA-shaped, unrecognized
REAL_SELLER = "0x3333333333333333333333333333333333333333"     # third-party EOA

# 1. afternoon probe: known mock collection -> TESTING (no network needed)
check("afternoon probe known mock", (AFTERNOON_SENDER, AFTERNOON_SENDER, AFTERNOON_MOCK), "TESTING")
# 2. evening probe: known operator contract -> TESTING (no network needed)
check("evening probe operator contract", (EVENING_SENDER, EVENING_CONTRACT, REAL_COLLECTION), "TESTING")
# 3. self-deal: sender == seller -> TESTING (no network needed)
check("self-deal", (NEW_WALLET, NEW_WALLET, REAL_COLLECTION), "TESTING")
# 4. new wallet vs real collection, third-party EOA seller -> TARGETING
check("new-wallet targeting", (NEW_WALLET, REAL_SELLER, REAL_COLLECTION), "TARGETING")
# 5. mock clone: unknown address, bytecode == known mock -> TESTING via codehash
from Crypto.Hash import keccak
fake_code = "0x60806040deadbeef"
kh = keccak.new(digest_bits=256, data=bytes.fromhex(fake_code[2:])).hexdigest()
lw.MOCK_CODEHASHES.add(kh)  # canary mock codehash
CLONE = "0x4444444444444444444444444444444444444444"
code_map[CLONE.lower()] = fake_code
check("mock clone redeploy", (NEW_WALLET, NEW_WALLET, CLONE), "TESTING") if False else None
# note: sender==seller short-circuits; use a contract seller for the clone path
code_map[EVENING_CONTRACT.lower()] = "0x6001"
v, why = lw.classify_settlement("https://unused", EVENING_CONTRACT, EVENING_CONTRACT, CLONE)
# 5b. clone with non-self-deal seller (operator contract is in OPERATOR_TEST -> TESTING anyway), use fresh seller
code_map["0x5555555555555555555555555555555555555555"] = "0x6001"  # contract seller, not operator
check("mock clone via codehash", (NEW_WALLET, "0x5555555555555555555555555555555555555555", CLONE), "TESTING")
lw.MOCK_CODEHASHES.discard(kh)
# 6. contract seller, unknown collection, code not a mock -> UNCLEAR
check("contract seller unclear", (NEW_WALLET, "0x5555555555555555555555555555555555555555", REAL_COLLECTION), "UNCLEAR")
# 7. missing event fields -> UNCLEAR
check("missing fields", (NEW_WALLET, None, REAL_COLLECTION), "UNCLEAR")

if fails:
    print("CANARY FAILED:", fails); sys.exit(1)
print("ALL CANARIES PASS")
