from fastapi.testclient import TestClient

import server
from game import AP


def test_two_detectives_over_websockets(tmp_path):
    server.store.close()
    server.store = server.Store(str(tmp_path / "s.loom"))
    server.tables.clear()
    with TestClient(server.app) as client:
        with client.websocket_connect("/ws/5/Ada?players=Ada,Bob") as ada, client.websocket_connect("/ws/5/Bob") as bob:
            assert ada.receive_json()["type"] == "view"  # on joining
            assert bob.receive_json()["type"] == "view"
            assert ada.receive_json()["type"] == "view"  # refreshed when Bob sat down
            ada.send_json({"type": "equip", "items": ["taxi"], "start": "bar"})
            assert ada.receive_json()["type"] == "view"
            bob.receive_json()
            bob.send_json({"type": "equip", "items": ["crowbar"], "start": "alley"})
            msgs = [ada.receive_json(), ada.receive_json()]  # start events for Ada, then the view
            assert {m["type"] for m in msgs} == {"events", "view"}
            view = next(m for m in msgs if m["type"] == "view")
            assert view["place"] == "bar" and view["ap"] == AP and view["options"]
            bob.receive_json()

            bob.send_json({"type": "play", "key": ["end"]})
            assert bob.receive_json()["type"] == "error"  # not Bob's turn

            move = next(k for k, _ in view["options"] if k[0] == "move" and k[1] == "crime_scene")
            ada.send_json({"type": "play", "key": ["interrogate", 3.0]})  # a float id, as JSON clients send it
            assert ada.receive_json()["message"].startswith("not an option")  # refused cleanly, not a crash
            ada.send_json({"type": "play", "key": move})
            events = ada.receive_json()
            assert events["type"] == "events" and events["events"][0].startswith("Vous êtes")
            assert ada.receive_json()["place"] == "crime_scene"
            assert bob.receive_json()["type"] == "view"

            # a search under the tape: the server asks Ada for a score, she answers, the search proceeds
            ada.send_json({"type": "play", "key": ["search"]})
            msg = ada.receive_json()
            assert msg["type"] == "challenge" and msg["kind"] == "discrétion"
            ada.send_json({"type": "score", "score": 1})
            events = ada.receive_json()
            assert events["type"] == "events" and not events["events"][0].startswith("Un agent")
