"""Run the reminder eval set and write evals/results.md.

    python evals/run_evals.py              # uses Gemini if GEMINI_API_KEY is set, else the fallback lines
    python evals/run_evals.py --offline    # fallback lines only (no network)
    python evals/run_evals.py --repeat 3   # sample each case several times (Gemini output varies)

Each case is run at every humor level. The checks are the same ones the
backend applies at runtime (app.reminders), so a rejected Gemini wrapper
shows up here as source=fallback.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from app import config, reminders  # noqa: E402
from app.reminders import ReminderContext  # noqa: E402

MEDS = ["Moxifloxacin", "Prednisolone", "Ketorolac"]
CHECKS = {
    "instruction_preserved": "Instruction preserved exactly",
    "tone_matches_flag": "Tone matches flag",
    "no_medical_advice": "No medical advice",
    "length_ok": "Acceptable length",
    "humor_level_ok": "Requested humor level",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    use_gemini = bool(config.GEMINI_API_KEY) and not args.offline

    cases = json.loads((ROOT / "cases.json").read_text())
    passed, total, sources = Counter(), 0, Counter()
    failures, samples = [], []

    for case in cases:
        fields = {k: v for k, v in case.items() if k != "id"}
        ctx = ReminderContext(**fields, all_medications=MEDS)
        for humor in reminders.HUMOR_LEVELS:
            for _ in range(args.repeat):
                rem = reminders.build_reminder(ctx, humor, use_gemini=use_gemini)
                checks = reminders.script_checks(rem, ctx, humor)
                total += 1
                sources[rem.source] += 1
                passed.update(name for name, ok in checks.items() if ok)
                bad = [name for name, ok in checks.items() if not ok]
                if bad:
                    failures.append((case["id"], humor, bad, rem.script))
                if humor == "full" and len(samples) < 6:
                    samples.append((case["id"], rem.source, rem.script))

    mode = f"live Gemini ({config.GEMINI_TEXT_MODEL})" if use_gemini else "offline (fallback lines)"
    lines = [
        "# Reminder eval results",
        "",
        f"Run: {datetime.now():%Y-%m-%d %H:%M} · mode: {mode} · "
        f"{len(cases)} cases × {len(reminders.HUMOR_LEVELS)} humor levels × {args.repeat} = {total} reminders",
        "",
        f"Wrapper source: " + ", ".join(f"{k} {v}" for k, v in sources.most_common()),
        "",
        "| Check | Pass rate |",
        "| --- | --- |",
    ]
    lines += [f"| {label} | {100 * passed[name] / total:.0f}% ({passed[name]}/{total}) |" for name, label in CHECKS.items()]
    lines += ["", "## Sample scripts (humor: full)", ""]
    lines += [f"- **{cid}** ({src}): {script}" for cid, src, script in samples]
    lines += ["", "## Failures", ""]
    lines += [f"- {cid} / {humor}: {', '.join(bad)} — {script}" for cid, humor, bad, script in failures] or ["None."]

    report = "\n".join(lines) + "\n"
    (ROOT / "results.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
