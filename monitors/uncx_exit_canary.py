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

# is_exploit_sequence: an unreadable timestamp must not turn a full create+release+cancel into "clean"
tx = lambda m, ts: {"method": m, "timestamp": ts}
T0, T1, FAR = "2026-09-01T10:00:00Z", "2026-09-01T10:43:00Z", "2026-04-01T10:00:00Z"
SEQ = [
    ("full sequence in 43 min",            [tx("createPosition(x)", T0), tx("release", T1), tx("cancel", T1)], (True, True)),
    ("scattered over months",              [tx("createPosition", FAR), tx("release", T0), tx("cancel", T1)], (False, True)),
    ("only two method families",           [tx("createPosition", T0), tx("release", T1)], (False, True)),
    ("all timestamps unparseable -> hit",  [tx("createPosition", None), tx("release", ""), tx("cancel", "soon")], (True, False)),
    ("one unparseable among close -> hit", [tx("createPosition", T0), tx("release", "garbage"), tx("cancel", T1)], (True, False)),
    ("missing timestamp key -> hit",       [{"method": "createPosition"}, tx("release", T0), tx("cancel", T1)], (True, False)),
]
for name, txs, (want_hit, span_known) in SEQ:
    hit, span = u.is_exploit_sequence(txs)
    ok = hit == want_hit and (span is not None) == span_known
    fails += not ok
    print(("PASS" if ok else "FAIL"), name, "->", hit, span)
print(f"{len(CASES) + len(SEQ) - fails}/{len(CASES) + len(SEQ)} pass")
sys.exit(1 if fails else 0)
