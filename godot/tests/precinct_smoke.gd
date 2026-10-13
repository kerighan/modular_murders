extends "res://tests/causal_guidance_smoke.gd"
# The police station has its own room: the reception counter faces the commissaire's halo.

func _run() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-suffix="):
			suffix = arg.trim_prefix("--capture-suffix=")
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	for i in 500:
		if client.view.has("setup"):
			break
		await create_timer(0.025).timeout
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	await _go("police")
	client._open_interior(false)
	await create_timer(1.5).timeout
	_check(client.lounge.precinct.visible and not client.lounge.geometry.visible and not client.lounge.bar_room.visible, "Police opens the precinct room")
	_check(client.lounge.staff_buttons.has("staff:police"), "The commissaire is reachable")
	await _capture("precinct")
	await _tap(client.lounge.staff_buttons["staff:police"])
	_check(client.view.get("conversation") != null, "Tapping the commissaire opens the talk")
	await _capture("precinct-talk")
	print("Precinct smoke OK")
	quit(0)
