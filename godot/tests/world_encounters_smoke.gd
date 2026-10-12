extends SceneTree
var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _wait() -> bool:
	for i in 250:
		await create_timer(0.04).timeout
		if client.qte_active:
			client._answer_qte(1.0)
		if not client.view.is_empty() and not client.view.has("setup") and not client.solo_busy:
			return true
	return false

func _tap(button: Button) -> void:
	var event := InputEventScreenTouch.new()
	event.index = 0
	event.pressed = true
	event.position = root.get_final_transform() * button.get_global_rect().get_center()
	Input.parse_input_event(event)
	await process_frame
	event = event.duplicate()
	event.pressed = false
	Input.parse_input_event(event)
	await process_frame

func _capture(name: String) -> void:
	var suffix := "-v11"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-suffix="):
			suffix = arg.trim_prefix("--capture-suffix=")
	await create_timer(0.2).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://art/captures/" + name + suffix + ".png")

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	if not await _wait():
		_fail("Fresh solo did not start")
		return
	await create_timer(1.2).timeout
	if not client.interior.visible:
		client._open_interior()
	if not await _wait():
		_fail("Automatic arrival scene did not complete its free engine action")
		return
	var cue = client.view.get("conversation")
	if cue == null or cue.stage != "scene" or cue.beats.size() != 2 or client.view.ap != 3:
		_fail("Two-speaker arrival exchange should start automatically without spending PA")
		return
	if client.dialogue.current_person.id != cue.beats[0].person.id or not client.dialogue.visible:
		_fail("First speaker not materialized in dialogue")
		return
	client.dialogue._finish_reveal()
	await _capture("arrival-exchange-first-phone")
	await _tap(client.dialogue.next_button)
	if client.dialogue.current_person.id != cue.beats[1].person.id or client.dialogue.full_text != cue.beats[1].text:
		_fail("Native tap failed to switch speaker and portrait")
		return
	client.dialogue._finish_reveal()
	await _capture("arrival-exchange-second-phone")
	await _tap(client.dialogue.next_button)
	if client.dialogue.visible:
		_fail("Native tap failed to close completed scene")
		return
	var consumed_cue := int(client.last_cue_id)
	client._open_interior()
	await create_timer(0.25).timeout
	if client.dialogue.visible or client.view.get("arrival_scene") != null or client.last_cue_id != consumed_cue:
		_fail("One-shot exchange repeated on re-entry")
		return
	var total := 0
	for presence in client.view.presence.places.values():
		total += int(presence.count)
	if total != client.view.notebook.size():
		_fail("Presence totals double-count or miss a suspect")
		return
	client.interior.hide()
	client._draw_actions(str(client.view.region))
	var shown := 0
	for entry in client.navigation.entries:
		if entry.button.has_meta("presence_count"):
			shown += 1
	if shown < 2:
		_fail("Missing district/place presence indicators")
		return
	await create_timer(0.5).timeout
	await _capture("presence-world-phone")
	client.navigation.show_choices("Quartiers · personnes présentes", client.district_choices)
	await _capture("presence-district-list-phone")
	client.navigation.close_sheet()
	var destination := ""
	for place in client.view.places:
		if client.view.places[place].get("street") == null and client.view.routes[place].get("available", false):
			for home in client.view.places:
				if client.view.places[home].get("street") == place:
					destination = str(place)
					break
		if not destination.is_empty():
			break
	if destination.is_empty():
		_fail("No reachable district with real apartment doors")
		return
	client._play_local(client.view.routes[destination].key.duplicate(true))
	if not await _wait():
		_fail("Travel to actual apartment district failed")
		return
	# A second, different encounter may have fired on this room's arrival.
	for i in 8:
		if not client.dialogue.visible:
			break
		await _tap(client.dialogue.next_button)
	client._open_interior(true)
	await create_timer(1.8).timeout
	if client.lounge.door_buttons.is_empty():
		_fail("Apartment presence capture needs real doors, not an empty corridor")
		return
	await _capture("presence-apartment-doors-phone")
	print("World encounters smoke passed: native two-speaker exchange, no PA, no repeat, district/place/door presence")
	quit(0)
