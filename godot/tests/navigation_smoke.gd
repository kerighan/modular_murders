# Run against an isolated review server; never against a user's live game.
extends SceneTree

var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _wait_for_place(place: String = "") -> bool:
	for i in 160:
		await create_timer(0.05).timeout
		if client.qte_active:
			client._answer_qte(1.0) # Apartment locks are a normal server challenge.
		if not client.view.is_empty() and not client.view.has("setup"):
			if place.is_empty() or client.view["place"] == place:
				return true
	return false

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _tap(button: Button) -> void:
	# Input events use physical pixels, Control rects use the scaled UI canvas.
	var at := root.get_final_transform() * button.get_global_rect().get_center()
	var motion := InputEventMouseMotion.new()
	motion.position = at
	Input.parse_input_event(motion)
	await process_frame
	print("Tap at ", at, " | expected ", button, " ", button.tooltip_text, " | visible ", button.is_visible_in_tree(), " | hovered ", root.gui_get_hovered_control())
	if root.gui_get_hovered_control() != null:
		print("Hovered tooltip: ", root.gui_get_hovered_control().tooltip_text)
	var press := InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.position = at
	press.pressed = true
	Input.parse_input_event(press)
	await process_frame
	var release := InputEventMouseButton.new()
	release.button_index = MOUSE_BUTTON_LEFT
	release.position = at
	release.pressed = false
	Input.parse_input_event(release)
	await process_frame

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	if not await _wait_for_place():
		_fail("Review server did not supply an equipped game view")
		return
	await create_timer(0.8).timeout # Let the focus transition and UI layout settle.
	var faded := false
	for form in client.visuals.building_forms.values():
		faded = faded or form.opacity < 0.95
	if not faded:
		_fail("Foreground buildings did not fade near the camera")
		return
	client.cam.size = 46.0
	await create_timer(1.2).timeout
	for form in client.visuals.building_forms.values():
		if form.opacity < 0.995:
			_fail("Buildings did not return to opaque when zooming out")
			return
		for mesh in form.meshes:
			if mesh.has_meta("opaque_material") and mesh.material_override != mesh.get_meta("opaque_material"):
				_fail("Transparent shader remained enabled after zooming out")
				return
	client.cam.size = 27.0
	await create_timer(0.8).timeout
	var grouped: Button
	for entry in client.navigation.entries:
		if entry.button.tooltip_text.begins_with("Entrées"):
			grouped = entry.target # Tap the ground chevron, not just its label.
	if grouped == null:
		_fail("Use a review seed with multiple accessible apartments")
		return
	await _tap(grouped)
	await process_frame
	if not is_instance_valid(client.navigation.sheet):
		_fail("Ground target did not open the destination list")
		return
	var choice_button: Button
	var expected := ""
	for button in client.navigation.sheet.find_children("*", "Button", true, false):
		for option in client.view["options"]:
			if option[0][0] == "move" and str(option[0][1]).begins_with("house_"):
				var label: String = client.view["places"][option[0][1]]["label"]
				if not button.disabled and button.tooltip_text.ends_with(" : " + label):
					choice_button = button
					expected = option[0][1]
					break
		if choice_button != null:
			break
	if choice_button == null:
		_fail("No server-authorized apartment in the destination list")
		return
	await _tap(choice_button)
	if not await _wait_for_place(expected):
		_fail("Destination button did not arrive at %s (current %s)" % [expected, client.view.get("place", "?")])
		return
	if client.navigation.sheet != null:
		_fail("Destination list did not close after choosing")
		return
	if client.navigation.actors.is_empty():
		_fail("Missing player avatar badge after moving")
		return
	await create_timer(0.7).timeout
	client.interior.visible = false
	client._mount_notifications(false)
	client.cam.size = 40.0
	client.cam_target = Vector3(18, 2, 12)
	await create_timer(0.2).timeout
	var walking_button: Button
	for entry in client.navigation.entries:
		if entry.kind == "district" and entry.region == "crime_scene" and not entry.button.disabled:
			walking_button = entry.button
	if walking_button == null or client.view["routes"]["crime_scene"]["cost"] != 2:
		_fail("Missing two-PA walking destination from the apartment")
		return
	var tick: int = client.view["tick"]
	await _tap(walking_button)
	if not await _wait_for_place("crime_scene") or client.view["tick"] != tick or client.view["ap"] != 0:
		_fail("The two-PA UI action did not consume the rest of the turn")
		return
	await create_timer(1.6).timeout
	await _tap(client.end_button)
	for i in 100:
		await create_timer(0.05).timeout
		if client.view["tick"] == tick + 1:
			break
	if client.view["tick"] != tick + 1:
		_fail("Manual end did not advance the turn")
		return
	print("Navigation smoke passed: camera fade/restore → ground target → apartment list → avatar → two-PA walk → manual next turn")
	quit(0)
