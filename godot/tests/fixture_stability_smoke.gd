extends "res://tests/causal_guidance_smoke.gd"

# Compare actual rendered vertices, colours and positions, not just API labels.
# Halos are intentionally excluded: they describe remaining interactions.
func _physical_meshes() -> Dictionary:
	var result := {}
	for node in client.lounge.props.get_children():
		if not node.has_meta("fixture_id"):
			continue
		var id: String = str(node.get_meta("fixture_id"))
		if not result.has(id):
			result[id] = []
		var surfaces := []
		for surface in node.mesh.get_surface_count():
			surfaces.append(node.mesh.surface_get_arrays(surface))
		result[id].append([node.get_meta("fixture_at"), hash(surfaces), node.transform])
	return result

func _ensure_fixture_visible(id: String) -> void:
	await process_frame
	var button: Button = client.lounge.fixture_buttons[id]
	if button.is_visible_in_tree():
		return
	# Front-row props can be outside the initial phone framing. Bring them in
	# through the same native drag used by a player, not a synthetic action.
	var at := Vector2(320, 320)
	var touch := InputEventScreenTouch.new()
	touch.pressed = true
	touch.position = root.get_final_transform() * at
	Input.parse_input_event(touch)
	await process_frame
	for step in 6:
		var motion := InputEventScreenDrag.new()
		motion.position = root.get_final_transform() * (at - Vector2(0, (step + 1) * 18))
		motion.relative = root.get_final_transform().basis_xform(Vector2(0, -18))
		Input.parse_input_event(motion)
		await create_timer(0.025).timeout
	touch = touch.duplicate()
	touch.position = root.get_final_transform() * (at - Vector2(0, 108))
	touch.pressed = false
	Input.parse_input_event(touch)
	await create_timer(0.1).timeout
	client.touch_gestures.cancel_inertia()
	_check(button.is_visible_in_tree(), "Native drag could not reveal fixture " + id)

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
	_check(client.view.has("setup"), "Fresh fixture setup required")
	client.chosen = ["search", "fingerprints"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	client._open_interior(false)
	await create_timer(2.0).timeout
	client.dialogue.hide()
	var scene: String = client.view.place
	var original_framing: Vector3 = client.cam_target
	var before := _physical_meshes()
	_check(before.has("fixture:crime_scene"), "Body must exist before inspection")
	_check(before.has("objects"), "Portable kit must exist from equipment selection")
	await _capture("fixtures-before")
	await _tap(client.lounge.fixture_buttons["fixture:crime_scene"])
	_check(_physical_meshes() == before, "Inspecting body changed physical meshes")
	client.dialogue.hide()
	await _capture("fixtures-inspected")
	# Merely tapping the examined body must not silently request its transport.
	var pa: int = client.view.ap
	var clock_before: String = client.view.clock
	await _tap(client.lounge.fixture_buttons["fixture:crime_scene"])
	_check(client.dialogue.visible and client.view.ap == pa and client.view.clock == clock_before, "Body tap must open a deliberate examination choice")
	_check(_physical_meshes() == before, "Opening body choices must leave scene unchanged")
	client.dialogue.hide()
	# All available collection/search actions preserve their real object meshes.
	var rows: Array = client.view.fixtures.duplicate(true)
	for fixture in rows:
		if fixture.prop not in ["blood", "drink", "evidence", "trash"]:
			continue
		if fixture.actions.is_empty():
			continue
		var before_collection: int = client.view.ap
		await _ensure_fixture_visible(str(fixture.id))
		await _tap(client.lounge.fixture_buttons[fixture.id])
		_check(client.view.ap == before_collection - 1, "Native collection/search did not execute " + str(fixture.id))
		_check(_physical_meshes() == before, "Collecting/searching moved or removed " + str(fixture.id))
		client.dialogue.hide()
	client.cam_target = original_framing
	client._update_camera()
	await process_frame
	await _capture("fixtures-collected")
	if client.view.ap == 0:
		await _act(["end"])
		client._open_interior(false)
		client.dialogue.hide()
	await _tap(client.lounge.fixture_buttons["fixture:crime_scene"])
	await _question(["investigate", "request_exam"])
	_check(client.view.body_location == "morgue", "Requested examination must transport body")
	var explained := false
	for note in client.view.journal:
		if "transféré à la morgue" in note.text:
			explained = true
	_check(explained, "Transport must be explained in the requested answer")
	client.dialogue.hide()
	var survivors := before.duplicate(true)
	survivors.erase("fixture:crime_scene")
	_check(_physical_meshes() == survivors, "Only transported body may disappear; remaining slots/meshes must be unchanged")
	await _capture("fixtures-transferred")
	await _go("morgue")
	client._open_interior(false)
	client.dialogue.hide()
	await create_timer(1.5).timeout
	var occupied := false
	for fixture in client.view.fixtures:
		if fixture.id == "fixture:exam_table":
			occupied = fixture.body_present
	_check(occupied and _physical_meshes().has("fixture:exam_table"), "Transported body must be on morgue table")
	await _capture("fixtures-morgue")
	await _go(scene)
	client._open_interior(false)
	client.dialogue.hide()
	_check(_physical_meshes() == survivors, "Revisiting scene recreated body or moved remaining props")
	print("Fixture stability smoke passed: native touches, rendered geometry unchanged on inspection/collection, deliberate transport, stable slots, body at morgue, revisit")
	quit(0)
