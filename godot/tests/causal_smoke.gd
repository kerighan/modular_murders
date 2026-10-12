extends SceneTree

var client: Node
var suffix := "18x9"

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _settle() -> void:
	await create_timer(0.15).timeout
	for i in 400:
		if not client.solo_busy and not client.view.is_empty():
			return
		await create_timer(0.025).timeout
	_fail("Causal engine response timeout")

func _capture(name: String) -> void:
	await create_timer(0.65).timeout
	await RenderingServer.frame_post_draw
	if root.get_texture().get_image().save_png("res://art/captures/causal-" + name + "-" + suffix + ".png") != OK:
		_fail("Screenshot failed")

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
	await _settle()

func _run() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-suffix="):
			suffix = arg.trim_prefix("--capture-suffix=")
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	for i in 400:
		await create_timer(0.025).timeout
		if client.view.has("setup"):
			break
	if not client.view.has("setup") or not client.view.has("engine"):
		_fail("Fresh causal setup required")
		return
	await _capture("setup")
	client.chosen = ["fingerprints", "search"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue._finish_reveal()
	await _capture("briefing")
	client.dialogue.hide()
	await create_timer(1.6).timeout
	await _capture("city")
	client._open_interior()
	await _capture("scene")
	var fixture = null
	for row in client.view.fixtures:
		for action in row.actions:
			if action[0] == ["investigate", "inspect_scene"]:
				fixture = row
	if fixture == null or not client.lounge.fixture_buttons.has(fixture.id):
		_fail("Scene investigation has no physical fixture")
		return
	await _tap(client.lounge.fixture_buttons[fixture.id])
	if client.view.journal.is_empty():
		# Multi-action fixture opens a folder rather than choosing invisibly.
		client._play_local(["investigate", "inspect_scene"])
		await _settle()
	if client.view.journal.is_empty() or client.view.journal[0].category != "scene":
		_fail("Physical scene did not acquire its public observation")
		return
	client.dialogue._finish_reveal()
	await _capture("observation")
	client.dialogue.hide()
	var source: String = client.view.place
	var bin_id := ""
	for row in client.view.fixtures:
		if row.prop == "trash":
			bin_id = row.id
	await _tap(client.lounge.fixture_buttons[bin_id])
	await _settle()
	if client.lounge.fixture_buttons.has(bin_id):
		_fail("Searched bin retained its floor selector")
		return
	var bin_visible := false
	for mesh in client.lounge.props.get_children():
		if mesh.get_meta("fixture_id", "") == bin_id:
			bin_visible = true
	if not bin_visible:
		_fail("Searched bin disappeared from the 3D world")
		return
	client.dialogue.hide()
	await _capture("searched-bin")
	# Select a reachable real apartment, then tap its resident in the lounge.
	var home := ""
	for door in client.view.doors:
		if door.occupied and not door.actions.is_empty():
			home = str(door.place)
			break
	if home.is_empty():
		_fail("No reachable physical apartment door")
		return
	client._play_local(["move", home])
	await _settle()
	client._open_interior()
	await _capture("apartment")
	var person: Dictionary = client.view.present[0]
	await _tap(client.lounge.person_buttons[int(person.id)])
	if client.view.pending == null or client.view.conversation == null:
		_fail("One tap did not start the causal suspect conversation")
		return
	client.dialogue._finish_reveal()
	await _capture("dialogue")
	client.dialogue.advance()
	if client.dialogue.choices.get_child_count() != 6:
		_fail("Expected five uniform questions plus the people folder")
		return
	await _tap(client.dialogue.next_button)
	if client.view.pending != null or client.dialogue.waiting or client.dialogue.visible:
		_fail("Native closing button stuck on En attente")
		return
	client.notebook_page.show()
	await _capture("notebook")
	client._set_notebook_tab("notes")
	await _capture("notes")
	client._set_notebook_tab("leads")
	await _capture("leads")
	client.notebook_page.hide()
	client._play_local(["investigate", "search:" + home])
	await _settle()
	client.dialogue.hide()
	var print_key: Array = []
	for option in client.view.options:
		if option[0][0] == "fingerprint":
			print_key = option[0]
			break
	if print_key.is_empty() or not client.lounge.fixture_buttons.has("objects"):
		_fail("Found objects did not materialize fingerprint interactions")
		return
	await _tap(client.lounge.fixture_buttons.objects)
	client._play_local(print_key)
	await _settle()
	client.dialogue._finish_reveal()
	if client.view.journal[-1].category != "contact":
		_fail("Fingerprint action did not acquire its comparison note")
		return
	await _capture("fingerprints")
	client.dialogue.hide()
	client._play_local(["end"])
	await _settle()
	if int(client.view.tick) != 1 or int(client.view.ap) != 6:
		_fail("Manual end turn did not restore AP")
		return
	await create_timer(1.6).timeout
	client._play_local(["walk", "cctv"])
	await _settle()
	await create_timer(1.6).timeout
	client.dialogue.hide()
	client._open_interior()
	await _tap(client.lounge.fixture_buttons["camera"])
	client.dialogue._finish_reveal()
	client.dialogue.advance()
	client.dialogue._choose(["ask", "camera_district", source])
	await _settle()
	client.dialogue._finish_reveal()
	client.dialogue.advance()
	var windows := 0
	for button in client.dialogue.choices.get_children():
		if button.get_meta("key", [""])[0] == "ask" and button.get_meta("key")[1] == "camera_window":
			windows += 1
	if windows != 4:
		_fail("CCTV must offer exactly four direct recording windows")
		return
	await _capture("camera")
	client.dialogue._choose(["ask", "camera_window", 18])
	await _settle()
	client.dialogue._finish_reveal()
	await _capture("camera-result")
	client.dialogue.pages.clear()
	client.dialogue.advance()
	await _tap(client.dialogue.next_button)
	if client.view.pending != null or client.dialogue.waiting or client.dialogue.visible:
		_fail("CCTV closing button stuck on En attente")
		return
	client._play_local(["end"])
	await _settle()
	await create_timer(1.6).timeout
	client._play_local(["walk", "morgue"])
	await _settle()
	client.dialogue.hide()
	client._open_interior()
	var before_clock: String = client.view.clock
	var before_ap: int = client.view.ap
	await _tap(client.lounge.staff_buttons["staff:medical"])
	if client.dialogue.choices.get_child_count() != 1:
		_fail("Doctor must offer a status question even without an exam request")
		return
	for button in client.dialogue.choices.get_children():
		await _tap(button)
		break
	if client.view.clock != before_clock or client.view.ap != before_ap:
		_fail("Checking exam status advanced time or charged PA")
		return
	client.dialogue._finish_reveal()
	await _capture("medical-no-request")
	client.dialogue.advance()
	await _tap(client.dialogue.next_button)
	client._play_local(["end"])
	await _settle()
	await create_timer(1.6).timeout
	client._play_local(["walk", "restaurant"])
	await _settle()
	client.dialogue.hide()
	client._open_interior()
	var before_notes: int = client.view.journal.size()
	await _tap(client.lounge.staff_buttons["staff:restaurant"])
	if client.view.journal.size() != before_notes or client.dialogue.choices.get_child_count() < 2:
		_fail("Server must wait for a question rather than blurting inventory")
		return
	await _capture("server-questions")
	for button in client.dialogue.choices.get_children():
		var key: Array = button.get_meta("key", [])
		if key.size() > 2 and key[1] == "service_action":
			if "couteau" in button.text or "marteau" in button.text:
				_fail("Unasked question already leaked the missing object")
				return
			await _tap(button)
			break
	if client.view.journal.size() <= before_notes:
		_fail("Server question did not obtain its real inventory observation")
		return
	client.dialogue._finish_reveal()
	await _capture("server-answer")
	print("Causal v15 smoke passed: persistent bins, native suspect close, uniform questions, central CCTV/four windows, fingerprints, manual turns")
	quit(0)
