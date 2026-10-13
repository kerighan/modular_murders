"""How repetitive is a case to solve? The blind guided bot plays each seed; its trajectory
(one token per step: the operation, or the place walked to) is compressed. A trajectory
that compresses well is a loop of the same gesture: a tour of venues, a row of records.
The worst seeds come first, so they can be looked at and fixed.

python scenario_entropy.py --seeds 0-59
"""
import argparse
import math
import random
import zlib
from collections import Counter

from scenario_play import PlaySession, sample_playable
from scenario_playtest import play


def tokens(steps):
    out = []
    for step in steps:
        if "go" in step:
            out.append("go")
        else:
            action = step["action"]
            out.append(action.split(":")[0].split(" ")[0])
    return out


def measure(seed, skills=("search", "rapport")):
    case = sample_playable(seed)
    session = PlaySession(case, skills, strict=False, difficulty="libre")
    result = play(session, guided=True)
    toks = tokens(result["steps"])
    text = " ".join(toks).encode()
    ratio = len(zlib.compress(text, 9)) / max(1, len(text))
    # Against the same tokens shuffled: below 1 means order itself repeats (loops of one gesture).
    shuffles = []
    for i in range(5):
        mixed = list(toks)
        random.Random(f"entropy-shuffle:{seed}:{i}").shuffle(mixed)
        shuffles.append(len(zlib.compress(" ".join(mixed).encode(), 9)))
    structure = round(len(zlib.compress(text, 9)) / max(1, sum(shuffles) / len(shuffles)), 3)
    counts = Counter(toks)
    entropy = -sum(n / len(toks) * math.log2(n / len(toks)) for n in counts.values()) if toks else 0.0
    return {"seed": seed, "case": str(case.seed), "motive": case.crime.kernel.premise.motive.value, "won": result["won"],
            "steps": len(toks), "ratio": round(ratio, 3), "structure": structure, "entropy": round(entropy, 2), "kinds": len(counts),
            "top": counts.most_common(3)}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="0-29", help="range a-b or a comma-separated list")
    parser.add_argument("--worst", type=int, default=10)
    args = parser.parse_args(argv)
    seeds = (range(int(args.seeds.split("-")[0]), int(args.seeds.split("-")[1]) + 1) if "-" in args.seeds
             else [int(s) for s in args.seeds.split(",")])
    rows = [measure(seed) for seed in seeds]
    rows.sort(key=lambda r: (r["structure"], r["ratio"]))
    print(f"{'seed':>5} {'case':>14} {'motive':>16} {'won':>4} {'steps':>5} {'struct':>6} {'ratio':>6} {'entr.':>5} {'kinds':>5}  most frequent gestures")
    for r in rows[:args.worst]:
        print(f"{r['seed']:>5} {r['case']:>14} {r['motive']:>16} {str(r['won']):>4} {r['steps']:>5} {r['structure']:>6} {r['ratio']:>6} {r['entropy']:>5} {r['kinds']:>5}  "
              + ", ".join(f"{k}×{n}" for k, n in r["top"]))
    structures = sorted(r["structure"] for r in rows)
    print(f"\n{len(rows)} cases · structure median {structures[len(structures) // 2]:.3f} · most varied {structures[-1]:.3f} · most repetitive {structures[0]:.3f}")


if __name__ == "__main__":
    main()
