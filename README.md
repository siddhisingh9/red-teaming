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

## Status

Day 1: repo scaffolded, split discipline documented, canary judge implemented.
Days 2-7: real target model + tool-calling loop, tool simulator with a
position knob, MCP transport, 12 hand-written attacks (19.4% ASR on
Qwen2.5-3B), 60-payload corpus with a frozen train/test split by family.
Day 8: `attackers/vanilla.py` -- Groq-backed vanilla attacker (caching,
429 backoff), `attackers/goals.py`'s 40-triple goal list. Pending a real
`GROQ_API_KEY` to run the actual generation checkpoint.
