# Fresh --solo-save required. Exercises the real preparation controls and reset.
extends SceneTree

var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _tap(button: Button) -> void:
	var point := root.get_final_transform() * button.get_global_rect().get_center()
	var motion := InputEventMouseMotion.new()
	motion.position = point
	Input.parse_input_event(motion)
	await process_frame
	var press := InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.position = point
	press.pressed = true
	Input.parse_input_event(press)
	await process_frame
	press = press.duplicate()
	press.pressed = false
	Input.parse_input_event(press)
	await process_frame

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	for i in 160:
		await create_timer(0.05).timeout
		if client.setup_page != null:
			break
	if client.setup_page == null:
		_fail("Fresh solo setup did not open")
		return
	await create_timer(0.3).timeout
	var equipment := ["search", "rapport"] if client.item_buttons.has("search") else ["forensic_kit", "taxi"]
	for item in equipment:
		await _tap(client.item_buttons[item])
	if client.chosen.size() != 2:
		_fail("Preparation equipment buttons are not touchable")
		return
	var start_place: String = client.view.setup.get("default_start", "victim_street")
	client.setup_scroll.ensure_control_visible(client.start_buttons[start_place])
	await create_timer(0.2).timeout
	await _tap(client.start_buttons[start_place])
	if client.start_btn.disabled:
		_fail("Preparation start button remained disabled")
		return
	await _tap(client.start_btn)
	for i in 100:
		await create_timer(0.05).timeout
		if not client.view.has("setup"):
			break
	if client.view.has("setup") or client.view["place"] != start_place:
		_fail("Preparation did not start the solo game")
		return
	var seed: int = client.view["solo"]["seed"]
	client.dialogue.hide()
	client.notebook_page.visible = true
	await create_timer(0.2).timeout
	await _tap(client.notebook_menu)
	await create_timer(0.2).timeout
	if not client.notebook_menu.get_popup().visible:
		_fail("Compact notebook options did not open")
		return
	client.notebook_menu.get_popup().hide()
	client.notebook_menu.get_popup().id_pressed.emit(1)
	await create_timer(0.2).timeout
	if not client.restart_dialog.visible:
		_fail("New case confirmation did not open")
		return
	# Window input is separate on desktop; emit only this confirmation signal.
	client.restart_dialog.hide()
	client.restart_dialog.confirmed.emit()
	for i in 100:
		await create_timer(0.05).timeout
		if client.setup_page != null and client.view.get("solo", {}).get("seed", seed) != seed:
			break
	if client.setup_page == null or client.view["solo"]["seed"] == seed or client.chosen.size() != 0:
		_fail("New case failed to rebuild a clean preparation screen")
		return
	print("Solo setup smoke passed: equipment → scroll → start → notebook → confirmed new case")
	quit(0)
