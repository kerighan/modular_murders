# Use --solo --phone-ui and a fresh --solo-save. Native touch events, not mouse clicks.
extends SceneTree

var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _touch(at: Vector2, pressed: bool, index: int = 0) -> void:
	var event := InputEventScreenTouch.new()
	event.index = index
	event.position = root.get_final_transform() * at
	event.pressed = pressed
	Input.parse_input_event(event)
	await process_frame

func _tap(button: Button) -> void:
	var at := button.get_global_rect().get_center()
	await _touch(at, true)
	await _touch(at, false)

func _swipe(at: Vector2, step: Vector2, count: int = 6) -> void:
	await _touch(at, true)
	for i in count:
		await create_timer(0.016).timeout
		at += step
		var event := InputEventScreenDrag.new()
		event.index = 0
		event.position = root.get_final_transform() * at
		event.relative = root.get_final_transform().basis_xform(step)
		Input.parse_input_event(event)
		await process_frame
	await _touch(at, false)

func _capture(name: String) -> void:
	await create_timer(0.15).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://art/captures/" + name + ".png")

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	for i in 180:
		await create_timer(0.05).timeout
		if client.setup_page != null:
			break
	if client.setup_page == null:
		_fail("Fresh setup required")
		return
	await create_timer(0.3).timeout
	var start: Vector2 = client.item_buttons["forensic_kit"].get_global_rect().get_center()
	await _swipe(start, Vector2(0, -18))
	var released: float = client.setup_scroll.get_v_scroll_bar().value
	print("Menu gesture: canvas ", root.get_final_transform(), " | start ", start, " | scroll ", released, " / ", client.setup_scroll.get_v_scroll_bar().max_value, " page ", client.setup_scroll.get_v_scroll_bar().page, " | mode ", client.touch_gestures.mode, " | velocity ", client.touch_gestures.velocity)
	await create_timer(0.15).timeout
	print("Menu after momentum: ", client.setup_scroll.get_v_scroll_bar().value)
	if released < 30 or client.setup_scroll.get_v_scroll_bar().value <= released + 3:
		_fail("Equipment-button swipe did not scroll with momentum")
		return
	if not client.chosen.is_empty():
		_fail("Dragging equipment accidentally selected an item")
		return
	client.touch_gestures.cancel_inertia()
	client.setup_scroll.scroll_vertical = 0
	await create_timer(0.15).timeout
	await _tap(client.item_buttons["forensic_kit"])
	await _tap(client.item_buttons["taxi"])
	if client.chosen.size() != 2:
		_fail("Real taps stopped working after a canceled button drag")
		return
	client.setup_scroll.ensure_control_visible(client.start_buttons["victim_street"])
	await create_timer(0.1).timeout
	await _tap(client.start_buttons["victim_street"])
	await _tap(client.start_btn)
	for i in 180:
		await create_timer(0.05).timeout
		if not client.view.has("setup"):
			break
	if client.view.has("setup"):
		_fail("Native touch setup failed to start")
		return
	await create_timer(0.7).timeout
	await _capture("zones-near-phone")
	var placard: Button
	for entry in client.navigation.entries:
		if entry.button.is_visible_in_tree() and not entry.button.disabled:
			placard = entry.button
			break
	if placard == null:
		_fail("No visible placard for drag arbitration test")
		return
	var before: Vector3 = client.cam_target
	var place: String = client.view["place"]
	var tick: int = client.view["tick"]
	await _swipe(placard.get_global_rect().get_center(), Vector2(14, 0))
	var on_release: Vector3 = client.cam_target
	await create_timer(0.15).timeout
	if before.distance_to(on_release) < 2 or on_release.distance_to(client.cam_target) < 0.2:
		_fail("Placard drag did not pan with inertia at phone DPI")
		return
	if client.view["place"] != place or client.view["tick"] != tick or client.interior.visible or client.navigation.sheet != null:
		_fail("Placard swipe accidentally fired its click")
		return
	await _touch(Vector2(500, 280), true)
	if client.touch_gestures.velocity.length() > 0.01:
		_fail("New finger press did not stop inertia")
		return
	await _touch(Vector2(500, 280), false)
	await create_timer(0.3).timeout
	if client.view["place"] != place or client.interior.visible:
		_fail("Stopping momentum accidentally clicked a destination")
		return
	# Pinch remains distinct from pan and never flings when a finger lifts.
	var size_before: float = client.cam.size
	await _touch(Vector2(350, 260), true)
	await _touch(Vector2(600, 260), true, 1)
	var pinch := InputEventScreenDrag.new()
	pinch.index = 1
	pinch.position = root.get_final_transform() * Vector2(680, 260)
	pinch.relative = root.get_final_transform().basis_xform(Vector2(80, 0))
	Input.parse_input_event(pinch)
	await process_frame
	await _touch(Vector2(680, 260), false, 1)
	await _touch(Vector2(350, 260), false)
	if client.cam.size >= size_before or client.touch_gestures.velocity.length() > 0.01:
		_fail("Pinch zoom failed or caused a camera fling")
		return
	client._stop_camera_focus()
	client.cam_target = Vector3(22, 2, 12)
	client.cam.size = 43
	await create_timer(0.3).timeout
	await _capture("zones-overview-phone")
	var toggle: MenuButton = client.notebook_menu
	if toggle == null:
		_fail("Missing reversible zone experiment toggle")
		return
	client.notebook_page.visible = true
	client.dialogue.hide()
	await create_timer(0.2).timeout # Hidden containers need a layout pass before tapping.
	await _capture("zones-notebook-phone")
	print("Zone toggle: ", toggle.get_global_rect(), " | pressed ", toggle.button_pressed, " | disabled ", toggle.disabled)
	await _tap(toggle)
	if not toggle.get_popup().visible:
		_fail("Notebook options did not open from a native tap")
		return
	# Popup windows route their own input on desktop; select the item by signal.
	toggle.get_popup().hide()
	toggle.get_popup().id_pressed.emit(0)
	print("Zone toggle result: enabled ", client.board_enabled)
	client.notebook_page.visible = false
	if client.board_zones.visible or client.board_enabled:
		_fail("Notebook toggle did not hide zone experiment")
		return
	await _capture("zones-off-phone")
	client.notebook_page.visible = true
	await create_timer(0.2).timeout
	await _tap(toggle)
	toggle.get_popup().hide()
	toggle.get_popup().id_pressed.emit(0)
	client.notebook_page.visible = false
	if not client.board_zones.visible or not client.board_enabled:
		_fail("Notebook toggle did not restore zone experiment")
		return
	for pair in client.board_zones.passages:
		if not pair[1] in client.view["adjacency"][pair[0]]:
			_fail("Visual frontier invented a movement edge")
			return
	for segment in client.board_zones.segments:
		if segment.owner == segment.other:
			_fail("Merged building parcel got an internal frontier")
			return
	for entry in client.navigation.entries:
		if "Trop loin" in entry.button.tooltip_text:
			_fail("Out-of-reach placard still exists")
			return
	await _tap(client.end_button)
	for i in 160:
		await create_timer(0.05).timeout
		if client.view["tick"] > tick:
			break
	if client.view["tick"] != tick + 1:
		_fail("Native touch end-turn button failed")
		return
	print("Touch smoke passed: menu momentum → taps → placard drag → camera momentum → stop without click → pinch → zones toggle/graph → native end-turn")
	quit(0)
