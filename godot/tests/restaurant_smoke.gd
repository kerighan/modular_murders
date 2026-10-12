extends SceneTree
var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _capture(name: String) -> void:
	var suffix := "-v12-18x9"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-suffix="):
			suffix = arg.trim_prefix("--capture-suffix=")
	await RenderingServer.frame_post_draw
	var error := root.get_texture().get_image().save_png("res://art/captures/" + name + suffix + ".png")
	if error != OK:
		_fail("Restaurant capture failed")

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	for i in 250:
		await create_timer(0.04).timeout
		if client.view.has("setup") and not client.solo_busy:
			break
	if not client.view.has("setup"):
		_fail("Restaurant test requires fresh isolated solo setup")
		return
	client.chosen = ["taxi", "forensic_kit"]
	client.start_choice = "restaurant"
	client._start_game()
	for i in 250:
		await create_timer(0.04).timeout
		if not client.view.has("setup") and not client.solo_busy:
			break
	if client.view.get("place") != "restaurant" or not client.nodes.has("restaurant"):
		_fail("Restaurant missing from live game or 3D world")
		return
	client._focus("restaurant")
	await create_timer(1.8).timeout
	await _capture("restaurant-world-phone")
	client._open_interior()
	await create_timer(1.8).timeout
	if client.lounge.get_world_3d() != client.get_world_3d() or not client.lounge.staff_buttons.has("staff:restaurant"):
		_fail("Restaurant must have a physical server in the global world")
		return
	# Finish an optional automatic arrival exchange before inspecting the room.
	for i in 8:
		if not client.dialogue.visible:
			break
		client.dialogue.advance()
		await create_timer(0.15).timeout
	await _capture("restaurant-room-phone")
	var button: Button = client.lounge.staff_buttons["staff:restaurant"]
	var event := InputEventScreenTouch.new()
	event.index = 0
	event.pressed = true
	event.position = root.get_final_transform() * button.get_global_rect().get_center()
	Input.parse_input_event(event)
	await process_frame
	event = event.duplicate()
	event.pressed = false
	Input.parse_input_event(event)
	await create_timer(0.25).timeout
	if not client.dialogue.visible:
		_fail("Native tap on restaurant server did not open service dialogue")
		return
	await _capture("restaurant-server-phone")
	for arg in OS.get_cmdline_user_args():
		if not arg.begins_with("--partner-id="):
			continue
		var person_id := int(arg.trim_prefix("--partner-id="))
		client.dialogue.hide()
		client._play_local(["interrogate", person_id])
		for i in 250:
			await create_timer(0.04).timeout
			if client.qte_active:
				client._answer_qte(1.0)
			if not client.solo_busy and client.view.get("conversation") != null:
				break
		client._play_local(["ask", "link"])
		for i in 250:
			await create_timer(0.04).timeout
			if not client.solo_busy:
				break
		client.dialogue._finish_reveal()
		if not "On était ensemble" in client.dialogue.full_text:
			_fail("Partner relationship was not presented in its own dialogue")
			return
		await _capture("current-partner-phone")
	print("Restaurant smoke passed: real map location, global interior, physical server, native one-tap actions")
	quit(0)
