"""Day 9: generation-0 baseline -- the number everything else is a delta
from. 40 goals (attackers/goals.py) x 3 splice positions x 1 attacker
generation seed per goal = 120 runs, vanilla attacker, undefended target.

Each goal already names one tool (it's written as "the target just called
{tool_name}..."), so unlike day 5's hand-written suite -- which is
tool-agnostic and gets swept across all 3 tools -- day 9 fixes tool_name to
the goal's own and sweeps position only: 40 x 3 x 1 = 120, not 40 x 3 x 3.
The same generated payload (one Gemini call per goal, cached by
attackers/vanilla.py) is tested spliced at all three positions, which is
itself a real question: does a payload written to read like "an opening
line" still land when spliced into the middle instead?

Resumable by construction: every planned run gets a stable run_id
("g0-van-0041", fixed by its position in the planned list) computed before
anything runs. On startup, existing run_ids already in the log are read
back and skipped; every completed record is appended and flushed
immediately, never batched -- a kill at any point loses at most the
in-flight record, never a completed one, and a restart producing the same
run_ids again is what makes "skip, don't duplicate" possible at all.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict

import config
import runner
from attackers.goals import GOALS
from attackers.vanilla import VanillaAttacker
from schemas import Outcome, Position, RunRecord

POSITIONS: tuple[Position, ...] = ("top", "middle", "bottom")


def build_plan() -> list[dict]:
    """The 120 planned runs, in a fixed order, each with a stable run_id.
    Built once and never reordered -- the run_id scheme depends on it."""
    plan = []
    i = 0
    for goal_idx, goal in enumerate(GOALS):
        for position in POSITIONS:
            i += 1
            plan.append(
                {
                    "run_id": f"g0-van-{i:04d}",
                    "goal": goal,
                    "goal_idx": goal_idx,
                    "position": position,
                }
            )
    return plan


def _load_done_ids(log_path) -> set[str]:
    if not log_path.exists():
        return set()
    done = set()
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            done.add(json.loads(line)["run_id"])
    return done


def run_sweep(log_path=config.GEN0_LOG_PATH, transport: str = "direct") -> list[RunRecord]:
    plan = build_plan()
    done_ids = _load_done_ids(log_path)
    if done_ids:
        print(f"resuming: {len(done_ids)}/{len(plan)} run_ids already in {log_path}")

    attacker = VanillaAttacker()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[RunRecord] = []

    # One AttackCase per goal (not per position) -- the seed ties every
    # position variant of a goal back to the same generated payload, and
    # VanillaAttacker's own disk cache makes re-generating on a resumed run
    # free instead of burning quota a second time.
    cases_by_goal_id: dict[str, object] = {}

    with open(log_path, "a", encoding="utf-8") as f:
        for n, item in enumerate(plan, 1):
            if item["run_id"] in done_ids:
                continue
            goal = item["goal"]
            seed = item["goal_idx"]
            case = cases_by_goal_id.get(goal["id"])
            if case is None:
                case = attacker.generate(goal["goal"], goal["tool_name"], seed=seed)
                cases_by_goal_id[goal["id"]] = case

            record = runner.run_one(
                case,
                goal["tool_name"],
                item["position"],
                control=False,
                transport=transport,
                attacker="vanilla",
                run_id=item["run_id"],
                generation=0,
                defender="base",
                seed=seed,
                attacker_model=attacker.model,
                attacker_temperature=attacker.temperature,
            )
            f.write(record.model_dump_json() + "\n")
            f.flush()
            records.append(record)
            print(
                f"[{n}/{len(plan)}] {item['run_id']} {goal['tool_name']} / "
                f"{item['position']} -> {record.outcome.value}"
            )

    return records


def load_all(log_path=config.GEN0_LOG_PATH) -> list[RunRecord]:
    records = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(RunRecord.model_validate_json(line))
    return records


def report(records: list[RunRecord]) -> None:
    counts = defaultdict(int)
    for r in records:
        counts[r.outcome] += 1
    success, blocked = counts[Outcome.SUCCESS], counts[Outcome.BLOCKED]
    asr = (success / (success + blocked) * 100) if (success + blocked) else 0.0
    print(
        f"\nGen-0 baseline ASR: {asr:.1f}% ({success}/{success + blocked}, "
        f"n={len(records)}, malformed={counts[Outcome.MALFORMED]}, error={counts[Outcome.ERROR]})"
    )
    runner._breakdown(records, "family", "family")
    runner._breakdown(records, "tool_name", "tool")
    runner._breakdown(records, "position", "position")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=["direct", "mcp"], default=config.TRANSPORT)
    parser.add_argument(
        "--report-only", action="store_true", help="skip the sweep, just report on the existing log"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

    if not args.report_only:
        run_sweep(transport=args.transport)
    # Always report on the full log, not just what this call completed --
    # run_sweep() only returns newly-completed records, and the baseline
    # table needs every run, old and new, resumed or not.
    report(load_all())


if __name__ == "__main__":
    main()
