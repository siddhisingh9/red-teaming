# Notes

Running log of decisions, gotchas, and things to revisit. Newest first.

## Day 3 — tool-calling loop, tolerant parser, MALFORMED outcome
- `agent/prompts.py`: system prompt + 3 tool JSON schemas (`web_search`,
  `read_url`, `log_value`), instructs the model to emit
  `<tool_call>{"name": ..., "arguments": {...}}</tool_call>`. Also tells the
  model tool output is untrusted data, not instructions -- this is the one
  line of defense the base agent has going into the attack runs.
- `agent/loop.py`: `run_agent()` replaces day 2's single-turn `run()`.
  generate -> parse -> (execute tool, generate again), capped at
  `MAX_ITERS = 3`, stops as soon as a turn has no tool call in it.
- Parser (`parse_tool_call`) is tolerant on purpose: strict `json.loads`
  first, then a regex fallback that bracket-matches the `arguments` object
  (so nested JSON survives) and repairs the two mistakes small models make
  most -- trailing commas and single-quoted strings. Only gives up (returns
  `Outcome.MALFORMED`) if neither works. Logs which tier fired.
- `Outcome` (schemas.py) now has four values: `SUCCESS`, `BLOCKED`, `ERROR`,
  `MALFORMED`. MALFORMED and ERROR are decided *before* `canary.judge()`
  ever runs on the text -- a malformed tool call is not the same event as
  the model correctly refusing, and counting it as BLOCKED would inflate
  the defense's apparent success rate for free.
- `RunRecord` now carries the full `messages` transcript, written on every
  record including ERROR/MALFORMED ones. `runner.py` no longer `continue`s
  past a failed case without logging it -- every case gets a record.
- `tools/sim.py` gained a `TOOL_REGISTRY` (`web_search`, `read_url`,
  `log_value`) so the loop has something to call. Still fixed stubs under
  the hood; real per-case injection splicing is still day 4's job.
- Green checkpoint (5x, real Qwen2.5-3B on a Colab T4, ≥4/5 must parse
  cleanly) needs a GPU this sandbox doesn't have -- verified the loop
  end-to-end here with a mocked `generate()` instead; real run happens on
  Colab.

## Day 1

- Scaffolded full repo layout. Wrote `config.py`, `schemas.py`,
  `judge/canary.py` for real; everything else is a stub with a `NotImplementedError`
  marking which day it's due, so nothing gets built ahead of the plan.
- Canary judge design: one unique token per run, injected into the agent's
  system/user context out of band (not part of the "attack" itself), success
  = token appears verbatim in the agent's final answer. Keeping this dumb and
  string-based on purpose — no LLM judge in the loop, so ASR numbers are
  reproducible and not gameable by an attacker that targets the judge itself.
- `data/attacks/test.jsonl` (families 5-6) must not be opened, loaded, or
  even glanced at until day 18. Anything that touches `data/attacks/` before
  then should read from `train.jsonl` only — enforce this in `test_split.py`.

## Day 2 — Qwen2.5-3B-Instruct, 4-bit nf4, T4
- 20 sequential generations, max_new_tokens=128, greedy
- **13.2 tok/s overall**, 13.9 tok/s median
- 673 tokens in 51s wall clock
- VRAM: 2165 MiB
