"""Real terminal playthrough, driven exclusively by the public engine view.

The mirror supplies menu keys, never murderer identity / story supports. The
culprit is calculated from the three sets printed in the detective's notes.
Run from the repository root, optionally with a seed. Isolated Loom per run.
"""
import os
import sys
import tempfile

import pexpect

sys.path.insert(0, os.getcwd())
from game import Game, ITEMS
from store import Store


def run(seed):
    directory = tempfile.mkdtemp(prefix=f"nexus-v9-cli-{seed}-")
    path = os.path.join(directory, "playtest.loom")
    child = pexpect.spawn(sys.executable, ["cli.py", str(seed), "--offline", "--perfect", "--compact"],
                          env={**os.environ, "NEXUS_SAVE": path, "NO_COLOR": "1"}, encoding="utf-8", timeout=30)
    child.logfile_read = sys.stdout
    mirror = Game(seed, challenge=lambda *_: 1.0)
    actions = 0

    def prompt():
        child.expect_exact("> ")

    prompt()
    for index, item in enumerate(("taxi", "crowbar")):
        child.sendline(str(list(ITEMS).index(item) + 1))
        if index == 0:
            prompt()
    prompt()
    starts = mirror.starts(["taxi", "crowbar"])
    child.sendline(str(starts.index("victim_street") + 1))
    mirror.equip(0, ["taxi", "crowbar"], "victim_street")
    mirror.start()
    prompt()

    def view():
        return mirror.view(mirror.player)

    def act(key):
        nonlocal actions
        options = dict(view()["options"])
        assert key in options, (key, options)
        taxi = {k: label for k, label in options.items() if label.startswith("Taxi")}
        if key in taxi:
            child.sendline("t")
            prompt()
            child.sendline(str(list(taxi).index(key) + 1))
        else:
            child.sendline(str([k for k in options if k not in taxi].index(key) + 1))
        mirror.play(key)
        actions += 1
        if view()["winner"]:
            child.expect(pexpect.EOF)
        else:
            prompt()

    def ready():
        if view()["ap"] == 0:
            act(("end",))

    def goto(place):
        ready()
        if view()["place"] == place:
            return
        for _ in range(20):
            if ("move", place) in dict(view()["options"]):
                act(("move", place))
                return
            street = view()["places"][place]["street"]
            if street and view()["place"] != street:
                goto(street)
            ready()
            consent = next((k for k in dict(view()["options"]) if k[0] == "confront"
                            and k[2] in ("access", "meeting")
                            and next(r for r in view()["notebook"] if r["id"] == k[1])["home"]["place"] == place), None)
            if consent:
                act(consent)
                ready()
            else:
                act(("end",))
        raise AssertionError(f"Unreachable destination {place}")

    def note(title):
        return next((n for n in view()["journal"] if n["title"] == title), None)

    def search(place):
        goto(place)
        ready()
        act(("search",))

    try:
        goto("police")
        ready()
        act(("authorize",))
        search("victim_house")
        loss = note("Un objet manque")
        opportunity = note("Qui connaissait le rendez-vous ?")
        if loss:
            assert not loss["people"]
            search(loss["leads"][0])
            opportunity = note("Qui pouvait ouvrir le coffre ?")
        assert opportunity and len(opportunity["people"]) >= 2
        for destination in opportunity["leads"]:
            if note("Une trace à replacer dans le temps"):
                break
            if destination.startswith("house_"):
                search(destination)
        motive = note("Une trace à replacer dans le temps")
        assert motive
        candidates = set(opportunity["people"]) & set(motive["people"])
        assert len(candidates) >= 2, "Opportunity and motive already identify someone!"
        print(f"\nPLAYTEST: deux axes, encore {len(candidates)} candidats : {sorted(candidates)}\n")
        search("crime_scene")
        goto("cctv")
        ready()
        act(next(k for k in dict(view()["options"]) if k[0] == "check_timeline"))
        camera = note("Un horaire recoupé")
        assert camera and len(camera["people"]) >= 2
        candidates &= set(camera["people"])
        assert len(candidates) == 1
        suspect = candidates.pop()
        print(f"\nPLAYTEST: trois axes indépendants convergent vers une personne, id {suspect}.\n")
        assert not note("L'objet retrouvé dans une cache"), "This route must not require finding an object"
        residence = next(r["home"] for r in view()["notebook"] if r["id"] == suspect)
        goto(residence["region"])
        for _ in range(20):
            ready()
            confrontation = next((k for k in dict(view()["options"]) if k[0] == "confront" and k[1] == suspect
                                  and str(k[2]).startswith("trace")), None)
            if confrontation:
                act(confrontation)
                break
            act(("end",))
        assert view()["story"]["resolved"]
        goto("police")
        ready()
        act(("accuse", suspect))
        child.close()
        assert child.exitstatus == 0
        store = Store(path)
        try:
            restored = store.load(str(seed))
            assert restored.view(restored.player)["journal"] == view()["journal"]
            assert restored.winner and restored.player.story_resolved
        finally:
            store.close()
        print(f"\nPLAYTEST PASS seed={seed} actions={actions} turns={view()['tick'] + 1} notes={len(view()['journal'])} db={path}")
    finally:
        if child.isalive():
            child.sendline("q")
            child.close(force=True)


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 42)
