#!/usr/bin/env python3
"""Known-answer canary for uncx_watch.exit_code (offline, no network).
A zero only counts as CLEAN when it was earned. Run: python3 uncx_exit_canary.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uncx_watch as u

ok_chain = {"checked": 12, "new": 0, "new_suspicious": 0}
CASES = [
    ("alert wins",              {"alerts": ["ALERT x"], "chains": {"ethereum": {"error": "boom"}}}, 2),
    ("all polled, txs checked", {"alerts": [], "chains": {"ethereum": ok_chain, "bnb": {"pending": "-"}}}, 0),
    ("one chain errored",       {"alerts": [], "chains": {"ethereum": ok_chain, "base": {"error": "Invalid params"}}}, 3),
    ("polled but 0 txs",        {"alerts": [], "chains": {"ethereum": {"checked": 0, "new": 0}}}, 3),
    ("nothing polled",          {"alerts": [], "chains": {"bnb": {"pending": "-"}, "robinhood": {"degraded": "-"}}}, 3),
    ("empty report",            {"alerts": [], "chains": {}}, 3),
]
fails = 0
for name, rep, want in CASES:
    got, why = u.exit_code(rep)
    ok = got == want
    fails += not ok
    print(("PASS" if ok else "FAIL"), name, "->", got, why)
print(f"{len(CASES) - fails}/{len(CASES)} pass")
sys.exit(1 if fails else 0)
