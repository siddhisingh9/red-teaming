"""Central configuration: paths and env-derived settings. No secrets live here."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- paths -------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
CORPUS_PATH = DATA_DIR / "corpus" / "patterns.jsonl"
ATTACKS_HANDWRITTEN_PATH = DATA_DIR / "attacks" / "handwritten.jsonl"
ATTACKS_TRAIN_PATH = DATA_DIR / "attacks" / "train.jsonl"
ATTACKS_TEST_PATH = DATA_DIR / "attacks" / "test.jsonl"  # do not open before day 18
BENIGN_TASKS_PATH = DATA_DIR / "benign" / "tasks.jsonl"
SFT_TRAIN_PATH = DATA_DIR / "sft" / "train.jsonl"

LOGS_DIR = ROOT / "logs"
RUNS_LOG_PATH = LOGS_DIR / "runs.jsonl"
CONTROL_LOG_PATH = LOGS_DIR / "control_runs.jsonl"
MCP_LOG_PATH = LOGS_DIR / "mcp_runs.jsonl"

FIGURES_DIR = ROOT / "figures"
RESULTS_DIR = ROOT / "results"

FAISS_INDEX_PATH = ROOT / "attackers" / "index.faiss"
LORA_ADAPTER_DIR = ROOT / "defender" / "adapter"

# --- run-time flags ------------------------------------------------------

# Guards against accidentally loading the held-out test split before it's due.
ALLOW_TEST_SPLIT = os.environ.get("RT_ALLOW_TEST_SPLIT", "0") == "1"

# --- model settings ------------------------------------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

AGENT_MODEL = os.environ.get("RT_AGENT_MODEL", "llama-3.1-8b-instant")
ATTACKER_MODEL = os.environ.get("RT_ATTACKER_MODEL", "llama-3.3-70b-versatile")

# Tool transport: "direct" calls tools/sim.py in-process (fast, for
# day-to-day debugging); "mcp" round-trips through tools/mcp_client.py's
# real MCP stdio session (tools/mcp_server.py) -- the actual untrusted
# channel this project studies. Override with runner.py's --transport, or
# this env var. Keep "direct" the default forever; it's ~10x faster.
TRANSPORT = os.environ.get("RT_TRANSPORT", "direct")

DEFAULT_TEMPERATURE = 0.7
MAX_TURNS = 6

# --- corpus / eval sizes (fixed constants of the study design) ---------

NUM_INJECTION_PATTERNS = 60
NUM_INJECTION_FAMILIES = 6
NUM_BENIGN_TASKS = 30
BENIGN_MIX_FRACTION = 0.30  # fraction of benign examples folded into SFT set
