extends "res://tests/causal_guidance_smoke.gd"

func _run() -> void:
	suffix = "v18-poison-20x9"
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	for i in 500:
		if client.view.has("setup"):
			break
		await create_timer(0.025).timeout
	_check(client.view.has("setup"), "Fresh poison setup required")
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	_check(not client.view.scene_has_blood and not client.view.outdoors, "Poison must not invent blood or an outdoor attack")
	await _act(["investigate", "inspect_scene"])
	await _act(["investigate", "collect_drink"])
	await _act(["stop"])
	client.dialogue.hide()
	client.notebook_page.show()
	client._set_notebook_tab("leads")
	await _focus_lead("drink_analysis")
	await _capture("glass-trail")
	client.notebook_page.hide()
	await _act(["investigate", "request_exam"])
	await _go("lab")
	if client.view.ap == 0:
		await _act(["end"])
	client._open_interior(false)
	client.dialogue.hide()
	await _tap(client.lounge.staff_buttons["staff:lab"])
	var before_time: String = client.view.clock
	var before_ap: int = client.view.ap
	await _question(["ask", "service_status"])
	_check(client.view.clock == before_time and client.view.ap == before_ap, "Laboratory status is free; it cannot make time pass")
	await _act(["stop"])
	for i in 5:
		var ready := false
		for option in client.view.options:
			if option[0] == ["investigate", "analyze_drink"]:
				ready = true
		if ready:
			break
		await _act(["end"])
	client._open_interior(false)
	client.dialogue.hide()
	await _tap(client.lounge.staff_buttons["staff:lab"])
	await _question(["ask", "service_action", "analyze_drink"])
	_check(_lead("drink_analysis").complete, "Received glass analysis must close its trail")
	client.dialogue._finish_reveal()
	await _capture("glass-answer")
	await _act(["stop"])
	await _go("morgue")
	for i in 5:
		if client.view.crime_timing.state == "ready":
			break
		await _act(["end"])
	if client.view.ap == 0:
		await _act(["end"])
	client._open_interior(false)
	client.dialogue.hide()
	await _tap(client.lounge.staff_buttons["staff:medical"])
	await _question(["ask", "service_action", "read_medical"])
	_check(client.view.crime_timing.state == "known", "Poison medical period must be acquired")
	_check("administration" in client.view.crime_timing.text, "Poison must distinguish administration from later death")
	for note in client.view.journal:
		_check(note.category != "sample" or "sang" not in note.text, "Poison cannot invent a blood sample")
	client.dialogue._finish_reveal()
	await _capture("poison-medical")
	print("Causal poison smoke passed: acquired glass trail, physical lab/doctor, free status, delayed results, no blood, administration chronology")
	quit(0)
