"""Blind exploration using public action labels, notebook semantics and a map.

No culprit, hidden masks, private appearances or solver solutions are read.
This deliberately exhausts sources; it tests usability/reachability, not fun.
"""
import argparse
import json

from scenario_play import PlaySession, sample_playable


def play(session, max_steps=180, *, guided=False):
    steps, queries = [], set()
    for _ in range(max_steps):
        known = dict(session.state.known)
        if len(session.remaining()) == 1 and {"medical_window", "victim_diary"} <= known.keys():
            person, = session.remaining()
            success, text = session.accuse(person)
            return {"won": success, "minutes": session.at - (1440 + 480), "steps": steps, "ending": text}
        # Start medical processing early. Visit people before endlessly rummaging
        # through empty bins. No action's undiscovered output is inspected.
        priority = {"inspect_scene": 0, "request_exam": 1, "read_medical": 2,
                    "collect_drink": 3, "analyze_drink": 4, "read_diary": 6}
        if guided:
            priority["read_diary"] = 3
        choices = []
        for row in session.board():
            for action in row["actions"]:
                kind = action["operation"]
                score = priority.get(action["id"], {"interview": 5, "verify": 7, "read": 8,
                                                      "collect": 9, "analyze": 10, "search": 15}.get(kind, 12))
                if guided:
                    identifier = action["id"]
                    pid = action["actor"]
                    if pid in session.remaining() and identifier.startswith("meet:"):
                        score = 4
                    elif pid in session.case.plan.population and pid not in session.remaining():
                        # Do not exhaust every topic of an already-incompatible
                        # suspect unless another public trail points there.
                        continue
                    if identifier.startswith("verify:"):
                        person = identifier.split(":", 1)[1]
                        if "evening:" + person not in known:
                            continue
                        score = 4 if person in session.remaining() else 12
                    elif identifier.startswith("interview:witness:"):
                        score = 3
                    elif identifier.startswith("interview:p"):
                        score = 5
                    elif identifier.startswith("observe:p"):
                        score = 8
                    elif identifier.startswith("venue_guests:"):
                        score = 10
                # Prefer the current place within a priority; use only public IDs.
                choices.append((score, row["place"] != session.place, row["place"], action["id"]))
        # Once a public estimate is acquired, use it to select camera hours.
        window = next((session.case.claims[key]["window"] for key in known
                       if key in session.case.claims and "window" in session.case.claims[key]), None)
        if window:
            for row in session.board():
                if row["camera"]:
                    for hour in range(window[0] // 60, window[1] // 60 + 1):
                        if (row["place"], hour) not in queries:
                            choices.append((6 if guided else 11, row["place"] != session.place, row["place"], "camera " + str(hour)))
        if guided:
            context_done = {r["id"] for r in session.journal}
            for pid in sorted(session.remaining()):
                if "profile:" + pid not in known:
                    continue
                for topic in ("motive", "relation"):
                    if "context:" + pid + ":" + topic not in context_done:
                        choices.append((5, session.person_place(pid) != session.place,
                                        session.person_place(pid), "context " + pid + " " + topic))
            appointment = session.case.claims.get("victim_diary", {}).get("appointment") if "victim_diary" in known else None
            if appointment and "profile:" + appointment["host"] in known:
                pid = appointment["host"]
                if "context:" + pid + ":appointment" not in context_done:
                    choices.append((4, session.person_place(pid) != session.place,
                                    session.person_place(pid), "context " + pid + " appointment"))
        if not choices:
            # Waiting advances time rather than forcing actions through delays.
            if session.at >= 1440 + 20 * 60:
                break
            session.at += 15
            continue
        _, _, place, action = min(choices)
        if place != session.place:
            steps.append({"go": place, "text": session.go(place)})
        before = session.remaining()
        if action.startswith("context "):
            _, person, topic = action.split()
            text = session.ask_context(person, topic)
        elif action.startswith("camera "):
            hour = int(action.split()[1])
            queries.add((place, hour))
            text = session.camera(hour)
        else:
            # Movement may have caused a witness's window to close.
            if action not in {row["id"] for row in session.options()}:
                continue
            text = session.do(action)
        steps.append({"action": action, "text": text,
                      **({"candidates_before": len(before), "candidates_after": len(session.remaining())} if guided else {})})
    return {"won": False, "minutes": session.at - (1440 + 480), "steps": steps,
            "ending": "Exploration exhausted without a defensible accusation."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--transcript", action="store_true")
    parser.add_argument("--guided", action="store_true", help="Follow acquired trails and skip incompatible suspects; still no hidden truth")
    args = parser.parse_args(argv)
    results = []
    for seed in range(args.seed, args.seed + args.count):
        session = PlaySession(sample_playable(seed))
        report = play(session, guided=args.guided)
        results.append({"requested_seed": seed, "won": report["won"], "minutes": report["minutes"],
                        "actions": len([s for s in report["steps"] if "action" in s]),
                        **({"transcript": report["steps"], "ending": report["ending"]} if args.transcript else {})})
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
