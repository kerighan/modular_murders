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

func _act(kind: String, argument = null) -> bool:
	for option in client.view.options:
		var key: Array = option[0]
		if key[0] == kind and (argument == null or key.size() > 1 and key[1] == argument):
			client._play_local(key.duplicate())
			return await _wait()
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
	if "--no-capture" in OS.get_cmdline_user_args():
		return
	var suffix := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-suffix="):
			suffix = arg.trim_prefix("--capture-suffix=")
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://art/captures/" + name + suffix + ".png")

func _choice(question: String) -> Button:
	for button in client.dialogue.choices.get_children():
		if button.get_meta("key", []) == ["ask", question]:
			return button
	return null

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	if not await _wait():
		_fail("Fresh solo did not start")
		return
	await create_timer(1.2).timeout
	client._open_interior()
	await create_timer(0.4).timeout
	if client.interior_box.get_child_count() != 0 or client.lounge.staff_buttons.is_empty() or client.lounge.fixture_buttons.is_empty():
		_fail("Local actions must be physically anchored to staff or objects")
		return
	await _capture("physical-bar-phone")
	await _tap(client.person_buttons.values()[0])
	if not await _wait() or client.view.get("conversation") == null:
		_fail("Native person tap failed")
		return
	await create_timer(0.3).timeout
	var scroll: ScrollBar = client.dialogue.choices_scroll.get_v_scroll_bar()
	if client.dialogue.choices.get_child_count() < 5 or scroll.max_value > scroll.page + 1:
		_fail("Five initial questions require scrolling")
		return
	for button in client.dialogue.choices.get_children():
		if not client.dialogue.choices_scroll.get_global_rect().encloses(button.get_global_rect()):
			_fail("A question is clipped outside the choices area")
			return
	await _capture("questions-full-phone")
	await _tap(_choice("grudge"))
	if not await _wait() or not client.view.conversation.has("thought"):
		_fail("Expected a private reflection after a grounded vague rumour (seed 42)")
		return
	client.dialogue._finish_reveal()
	await _capture("human-rumour-phone")
	await _tap(client.dialogue.next_button)
	client.dialogue._finish_reveal()
	if not client.dialogue.portrait.detective or client.dialogue.context.text != "Pensée" or client.dialogue.speech.get_parsed_text() != client.view.conversation.thought.text:
		print("Reflection diagnostic: ", client.dialogue.portrait.detective, " / ", client.dialogue.context.text, " / ", client.dialogue.speech.text, " / ", client.dialogue.speech.get_parsed_text())
		_fail("Reflection must use the detective portrait and a separate beat")
		return
	await _capture("detective-thought-phone")
	await _tap(client.dialogue.next_button)
	for question in ["alibi", "life"]:
		await _tap(_choice(question))
		if not await _wait():
			_fail("Conversation stopped unexpectedly")
			return
		client.dialogue._finish_reveal()
		await _tap(client.dialogue.next_button)
	client.dialogue.hide()
	client._open_interior()
	await create_timer(0.2).timeout
	var previous_ap: int = int(client.view.ap)
	await _tap(client.lounge.fixture_buttons.values()[0])
	if not await _wait() or int(client.view.ap) != previous_ap - 1 or client.view.journal.is_empty():
		_fail("Native object tap did not execute its legal engine action")
		return
	client.dialogue.hide()
	if not await _act("move", "cabaret"):
		_fail("Palace travel unavailable")
		return
	await create_timer(2.4).timeout
	if int(client.view.ap) != 0 or client.visuals.world_saturation > 0.01 or client.header.modulate.a != 1.0:
		_fail("0 AP must desaturate only the world")
		return
	await _capture("exhausted-monochrome-phone")
	if not await _act("end"):
		_fail("Manual end unavailable")
		return
	await create_timer(3.0).timeout
	if client.visuals.world_saturation < 0.99:
		_fail("New turn did not restore world colour")
		return
	client._open_interior()
	await create_timer(0.3).timeout
	if not client.lounge.staff_buttons.has("staff:cabaret"):
		_fail("The usher is missing from the Palace")
		return
	await _capture("palace-usher-phone")
	await _tap(client.lounge.staff_buttons["staff:cabaret"])
	await create_timer(0.2).timeout
	if not client.dialogue.visible or not client.dialogue.current_person.get("service", false):
		_fail("Native usher tap failed")
		return
	client.dialogue.hide()
	client._open_interior(true)
	await create_timer(0.4).timeout
	if client.lounge.door_buttons.size() != client.view.doors.size() or client.lounge.door_buttons.is_empty():
		_fail("Hallway doors do not match real apartments")
		return
	await _capture("apartment-hallway-phone")
	var empty_door := {}
	for door in client.view.doors:
		if not door.occupied and not door.actions.is_empty():
			empty_door = door
			break
	if not empty_door.is_empty():
		var door_ap: int = int(client.view.ap)
		await _tap(client.lounge.door_buttons[empty_door.place])
		if not await _wait() or client.view.place != empty_door.place or int(client.view.ap) != door_ap - 1 or not client.interior.visible:
			_fail("Native door tap must enter the real apartment, once, for its legal cost")
			return
		client.dialogue.hide()
		await create_timer(0.3).timeout
		await _capture("physical-apartment-phone")
	client.interior.hide()
	client.notebook_page.show()
	client._set_notebook_tab("people")
	await create_timer(0.3).timeout
	var rows: Array = client.view.notebook.filter(func(row): return row.name != "?")
	if rows.size() < 2:
		_fail("Not enough discovered people to test sorting")
		return
	var followed: int = int(rows[1].id)
	var excluded: int = int(rows[0].id)
	var before := JSON.stringify(client.view)
	client._select_notebook_suspect(followed)
	await process_frame
	client.notebook_scroll.ensure_control_visible(client.notebook_cards[followed].get_meta("follow_button"))
	await create_timer(0.2).timeout
	await _tap(client.notebook_cards[followed].get_meta("follow_button"))
	await create_timer(0.4).timeout
	if client.notebook_grid.get_child(0) != client.notebook_cards[followed] or not client.manual_priorities.has(str(followed)):
		_fail("Following must move the card to the top")
		return
	client._select_notebook_suspect(excluded)
	await process_frame
	client.notebook_scroll.ensure_control_visible(client.notebook_cards[excluded].get_meta("note_button"))
	await create_timer(0.2).timeout
	await _tap(client.notebook_cards[excluded].get_meta("note_button"))
	await create_timer(0.4).timeout
	if client.notebook_grid.get_child(-1) != client.notebook_cards[excluded] or client.notebook_cards[excluded].modulate.a > 0.5 or JSON.stringify(client.view) != before:
		_fail("Exclusion must move to the bottom without an engine action")
		return
	client.notebook_scroll.scroll_vertical = 0
	await create_timer(0.2).timeout
	await _capture("notebook-following-phone")
	client.notes_case = ""
	client._load_case_notes()
	client._draw_notebook()
	if not client.manual_priorities.has(str(followed)) or not client.manual_exclusions.has(str(excluded)):
		_fail("Both personal flags must survive reloading")
		return
	# Following an excluded person is the opposite choice, never a double flag.
	client._toggle_suspect_priority(excluded)
	await create_timer(0.4).timeout
	if client.manual_exclusions.has(str(excluded)) or not client.manual_priorities.has(str(excluded)) or client.notebook_cards[excluded].modulate.a != 1.0:
		_fail("Following an excluded person must reactivate and highlight them")
		return
	client._toggle_suspect_priority(excluded)
	await create_timer(0.4).timeout
	if client.manual_priorities.has(str(excluded)) or JSON.stringify(client.view) != before:
		_fail("Returning to neutral must not affect engine state")
		return
	client.notebook_page.hide()
	client._locate_note_place("victim_street")
	await create_timer(1.2).timeout
	var pinned: Button
	for entry in client.navigation.entries:
		if entry.get("region", "") == "victim_street":
			pinned = entry.button
	if pinned == null or not pinned.visible:
		_fail("Localiser must keep the selected district sign visible")
		return
	await _capture("located-district-phone")
	print("Presentation smoke passed: five unclipped questions, private thought, physical staff/objects/doors, manual sorted notes, world-only monochrome, pinned district")
	quit(0)
