# Responsible Disclosure & Redaction Policy

This repository is a **public, redacted** release of defensive DeFi work. It is
published to share detection tooling, whitehat rescue methodology, and the
research pattern of post-exploit copycat races — **without** handing anyone an
inventory of live, exploitable targets.

## The line we hold

Dormant-but-funded contracts are, by construction, often immutable and
unpausable: once one is identified as exploitable, there is frequently no
on-chain fix. For that class, **a public list of "here is value sitting behind a
callable, unfixable contract" is itself an attack accelerant.** So:

- **Live watchlists are withheld.** Every `monitors/*-targets.json` is published
  only as a `*-targets.example.json` schema with placeholder addresses. The real
  watchlists are handled privately.
- **Specific live addresses are redacted** inside all kept documents:
  `‹contract redacted›`, `‹wallet redacted›`, `‹tx redacted›`,
  `‹exposure redacted›`. The *mechanism*, the *pattern*, and the dollar
  *magnitude of already-public, resolved incidents* are kept — the identifying
  coordinates of anything still live are not.
- **No exploit code, no step-by-step against a live contract.** Research briefs
  that amounted to "here is a specific unexploited target and how" were dropped
  entirely rather than redacted.
- **Raw at-risk inventories** (wallet lists, deep-water scans, balance
  snapshots) are not published.

## What *is* kept, and why

- Monitor scripts, so defenders can run their own detection.
- Whitehat rescue playbooks (method, not targets).
- The recon pattern-book and research notes (mechanisms and findings).
- A small number of **public ABI event-signature hashes** and **canonical
  public token contracts** (e.g. USDC/USDT/DAI/WETH) remain in the scripts
  because they are shared public constants, not targets, and the tools need
  them to function. Historical, already-disclosed incident references are kept
  only where the incident is resolved/public.

## Handling live findings

Live, unresolved exposure discovered through this work is **not published here.**
It is handled privately through responsible-disclosure channels — direct contact
with the affected protocol, or coordination through SEAL-911-style emergency
response — never via a public target list.

## Reporting

If you believe something in this repo still exposes a live target, or you want to
coordinate a rescue, contact the maintainers privately rather than opening a
public issue with the details.
