# red-teaming

Research project studying prompt-injection attacks against tool-calling LLM
agents, and whether LoRA fine-tuning on exploit transcripts makes a defender
model more robust — without wrecking its utility on benign tasks.

## Design

- **Agent under test** (`agent/`): a multi-turn tool-call loop around a
  chat model. Talks to simulated tools (`tools/sim.py`) or a real MCP server
  (`tools/mcp_server.py`).
- **Attackers** (`attackers/`): two arms —
  - `vanilla.py`: a Groq-backed model with no retrieval, improvising attacks.
  - `rag.py`: retrieves from a corpus of known injection patterns
    (`data/corpus/patterns.jsonl`, FAISS `IndexFlatIP`) and splices them into
    tool outputs before generation.
- **Judge** (`judge/canary.py`): the source of truth for whether an attack
  succeeded. Plants a unique canary token per run; a run is a *hit* iff the
  agent's final output leaks that token. Deliberately dumb and deterministic
  — no LLM-as-judge, no fuzzy matching, so results are reproducible and hard
  to game.
- **Defender** (`defender/`): takes exploit transcripts that scored as hits,
  turns them into corrected SFT pairs (agent should have refused / ignored
  the injected instruction), mixes in 30% benign tasks so the model doesn't
  learn to refuse everything, and LoRA-fine-tunes on top.
- **Split discipline**: `data/attacks/train.jsonl` (families 1-4) is the only
  thing either attacker or defender ever sees before day 18.
  `data/attacks/test.jsonl` (families 5-6) is held out to measure
  generalization to unseen attack families — **do not open it early**, that
  invalidates the eval.

## Layout

See the tree below; `← day N` comments mark when each file goes from stub to
real. `logs/runs.jsonl` is append-only — one JSON line per run, forever,
across the whole project, so later analysis can look at trends over time.

```
red-teaming/
├─ README.md RESULTS.md NOTES.md
├─ requirements.txt config.py schemas.py       ← day 1, written first
├─ runner.py analyze.py evaluate_all.py
├─ agent/
│  ├─ model.py                                  ← day 2  generate(messages) -> str
│  ├─ loop.py                                    ← day 3  multi-turn tool-call loop
│  └─ prompts.py                                 ← day 3  system prompt + tool schemas
├─ tools/
│  ├─ sim.py                                     ← day 4  3 tools, positional injection splicing
│  ├─ mcp_server.py                              ← day 6  FastMCP stdio server
│  └─ mcp_client.py                              ← day 6  same registry interface
├─ judge/
│  └─ canary.py                                  ← day 1  the only real component on day 1
├─ attackers/
│  ├─ base.py                                    ← day 8  ABC both arms implement
│  ├─ vanilla.py                                 ← day 8  Groq, no retrieval
│  ├─ build_index.py                             ← day 10 FAISS IndexFlatIP
│  └─ rag.py                                     ← day 11 retrieval into the generation step
├─ defender/
│  ├─ build_dataset.py                           ← day 15 exploits -> SFT pairs (+30% benign)
│  ├─ train_lora.py                              ← day 16 PEFT + TRL
│  └─ utility_eval.py                            ← day 17 30 benign tasks, deterministic checks
├─ data/
│  ├─ corpus/patterns.jsonl    60 payloads, 6 families
│  ├─ attacks/train.jsonl      families 1-4
│  ├─ attacks/test.jsonl       families 5-6   ← DO NOT OPEN UNTIL DAY 18
│  ├─ benign/tasks.jsonl       30 utility tasks
│  └─ sft/train.jsonl          defender training pairs
├─ tests/ test_split.py test_tools.py
├─ logs/runs.jsonl                               ← append-only, one line per run, forever
└─ figures/ results/
```

## Status

Day 1: repo scaffolded, split discipline documented, canary judge implemented.
