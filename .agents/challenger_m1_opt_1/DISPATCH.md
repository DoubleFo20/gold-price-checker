# Task Assignment: Challenger 1 for Milestone 1

## Mission
Empirically stress-test and challenge Milestone 1 implementation: Forecast Engine Restoration & Horizons (F1..F6).

## Working Directory
`d:\xampp\htdocs\gold-price-checker\.agents\challenger_m1_opt_1`

## Mandatory Reference Files (MUST READ FIRST)
- `d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md`
- `d:\xampp\htdocs\gold-price-checker\.agents\PROJECT.md`
- `d:\xampp\htdocs\gold-price-checker\.agents\worker_m1_opt_2\changes.md`
- `d:\xampp\htdocs\gold-price-checker\.agents\worker_m1_opt_2\handoff.md`

## Challenge Scope & Stress Testing Targets
1. Write and execute stress tests on `/api/forecast` across periods 1, 7, 30, and 90.
2. Test extreme scenarios: empty database, database with only 1 row, database with non-consecutive dates, invalid period inputs (`period=0`, `period=14`, `period=-1`, `period=abc`).
3. Verify that predictions strictly obey guardrail constraints (1d: 2.5%, 7d: 7%, 30d: 12%, 90d: 18%) under high volatility synthetic inputs.
4. Verify that `lower_bound <= forecast <= upper_bound` strictly holds for every single step from $t=1$ to $t=90$.
5. Issue clear verdict: **APPROVE** or **CHALLENGE_FAILED / REQUEST_CHANGES**.

## Deliverable
Write your findings to `d:\xampp\htdocs\gold-price-checker\.agents\challenger_m1_opt_1\challenge.md` and complete `handoff.md`. Send a message when complete.

## 2026-09-10T08:36:20Z
Read your task assignment in d:\xampp\htdocs\gold-price-checker\.agents\challenger_m1_opt_1\DISPATCH.md.
Also read d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md.
Perform empirical stress-testing and challenge on Milestone 1. Issue clear verdict APPROVE or CHALLENGE_FAILED in handoff.md. Send a message when complete.

