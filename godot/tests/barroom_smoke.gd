extends "res://tests/causal_guidance_smoke.gd"

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
	_check(client.view.has("setup"), "Fresh barroom setup required")
	client.chosen = ["search", "rapport"]
	client.start_choice = "bar"
	client._start_game()
	await _settle()
	# Use actual routines to wait for clients, never decorative phantom suspects.
	for i in 10:
		if not client.view.present.is_empty():
			break
		await _act(["end"])
	client.dialogue.hide()
	client._open_interior(false)
	await _settle()
	client.dialogue.hide()
	_check(client.lounge.bar_room.visible and not client.lounge.geometry.visible, "Bar must have its own decor")
	_check(client.lounge.get_world_3d() == client.get_world_3d(), "Bar must remain in the global 3D world")
	_check(client.lounge.bar_room.find_children("*", "SubViewport", true, false).is_empty(), "Bar must not add another viewport")
	_check(client.lounge.staff_buttons.has("staff:bar"), "Barman must have a real interaction target")
	var meshes: Array = client.lounge.bar_room.find_children("*", "MeshInstance3D", true, false)
	_check(meshes.size() <= 4, "Bar geometry should remain material-batched for Android")
	for light in client.lounge.bar_room.find_children("*", "OmniLight3D", true, false):
		_check(not light.shadow_enabled, "Bar must not add shadow costs")
	await create_timer(2.0).timeout
	await _capture("barroom")
	await _tap(client.lounge.staff_buttons["staff:bar"])
	_check(client.dialogue.visible and client.dialogue.choices.get_child_count() > 0, "One-tap barman must open questions without inventing an answer")
	await _capture("barroom-barman")
	await _act(["stop"])
	await _go("restaurant")
	client.dialogue.hide()
	client._open_interior(false)
	await _settle()
	_check(not client.lounge.bar_room.visible and client.lounge.geometry.visible, "Other venues should retain the shared lounge")
	await _capture("barroom-restaurant-unchanged")
	print("Barroom smoke passed: real routines, distinct global room, bounded meshes/lights, native barman tap, other interiors unchanged")
	quit(0)
