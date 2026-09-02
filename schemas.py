"""Pydantic schemas shared across the pipeline. Kept in one place so every
component reading/writing a jsonl file agrees on its shape."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

Position = Literal["top", "middle", "bottom"]


class Outcome(str, Enum):
    """judge/canary.py's verdict on a single run.

    SUCCESS and BLOCKED come from canary.judge() scanning a well-formed final
    answer. ERROR and MALFORMED are assigned upstream, before canary.judge()
    ever runs -- MALFORMED means the agent's tool-call JSON couldn't be
    parsed (agent/loop.py's parse_tool_call), ERROR means something raised
    while driving the loop. Neither is a "the defense held" data point, so
    neither may be counted as BLOCKED.
    """

    BLOCKED = "BLOCKED"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    MALFORMED = "MALFORMED"


class AttackCase(BaseModel):
    """One attack scenario to run through the pipeline."""

    name: str  # short id, e.g. "direct_override_1" -- used as the log key
    family: str  # attack family, e.g. "direct_override" -- for grouped ASR
    technique: str  # human-readable description of what this case tries
    injected_text: str  # the injection payload for this case


class CorpusPattern(BaseModel):
    """One row of data/corpus/patterns.jsonl -- the raw 60-pattern retrieval
    corpus attackers/rag.py (day 10+) embeds and searches over FAISS
    IndexFlatIP. Distinct from AttackCase: data/attacks/{train,test}.jsonl
    are this same corpus, family-split and reshaped into AttackCase so
    runner.py-style sweeps can drive them."""

    id: str  # e.g. "F2-007" -- family index + sequence, unique across the corpus
    family: str  # matches AttackCase.family for the derived train/test split
    text: str  # the raw injection payload
    source: str  # where this pattern came from -- a paper, OWASP category, or "own variant"
    notes: str = ""  # short phrase on why/how the technique works


class ToolCall(BaseModel):
    """A tool invocation the agent requests mid-turn."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    """What a tool hands back to the agent -- this is where injected text
    hides. `position` records where in the content the injection was
    spliced (or requested, if `injection` was None and nothing got spliced
    in) -- it's a real experimental variable, not incidental metadata."""

    tool_name: str
    content: str
    was_poisoned: bool = False
    injection_id: str | None = None
    position: Position | None = None


class AgentTurn(BaseModel):
    """One turn of agent output."""

    role: str
    content: str
    tool_call: ToolCall | None = None


class RunRecord(BaseModel):
    """One line of logs/runs.jsonl. Append-only, never rewritten.

    `messages` is the full transcript (system/user/assistant/tool turns) for
    this run, stored on every record regardless of outcome -- including
    ERROR and MALFORMED ones. It's the only thing that lets a week-3 "how did
    this ASR number happen" question get answered after the fact.

    Day 9: `run_id` is stable across a resumed sweep (the same planned run
    always gets the same id), so a killed-and-restarted run can tell which
    records already landed and skip them instead of duplicating. `git_sha`,
    `generation`, `attacker`, `defender`, `agent_model`, and `latency_s` are
    populated for every record from here on; retrofitting them onto records
    logged before day 9 isn't attempted -- old logs stay old-shaped.
    """

    run_id: str  # stable per planned (attacker, case, tool, position) run -- the resume key
    git_sha: str  # short commit hash of the code that produced this record
    generation: int = 0  # 0 = undefended target; increments once the defender loop (day 15+) exists
    attacker: str  # "handwritten" | "vanilla" | "rag" -- which arm produced injected_text
    defender: str = "base"  # "base" until day 17's LoRA-defended model exists
    seed: int | None = None  # the attacker LLM's generation seed, if injected_text came from one
    agent_model: str  # the target model actually driving this run
    attacker_model: str | None = None  # the attacker LLM's model id, if applicable
    attacker_temperature: float | None = None
    latency_s: float  # wall-clock seconds for the agent loop itself (excludes attacker generation)

    case_name: str
    family: str
    tool_name: str
    transport: str  # "direct" or "mcp" -- see config.TRANSPORT
    injected_text: str
    tool_response: str
    final_output: str
    outcome: Outcome
    position: Position
    messages: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
