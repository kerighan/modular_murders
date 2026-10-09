# Full GUI round trip, with real native taps and an isolated fresh solo save.
extends SceneTree
var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _wait_for(place: String = "", stage: String = "") -> bool:
	for i in 200:
		await create_timer(0.05).timeout
		if client.qte_active:
			client._answer_qte(1.0)
		if not client.view.is_empty() and not client.view.has("setup") and not client.solo_busy:
			if (place.is_empty() or client.view.place == place) and (stage.is_empty() or (client.view.get("conversation") != null and client.view.conversation.stage == stage)):
				return true
	return false

func _tap(button: Button) -> void:
	var at := root.get_final_transform() * button.get_global_rect().get_center()
	var press := InputEventScreenTouch.new()
	press.position = at
	press.index = 0
	press.pressed = true
	Input.parse_input_event(press)
	await process_frame
	press = press.duplicate()
	press.pressed = false
	Input.parse_input_event(press)
	await process_frame

func _capture(name: String) -> void:
	await RenderingServer.frame_post_draw
	var suffix := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-suffix="):
			suffix = arg.trim_prefix("--capture-suffix=")
	root.get_texture().get_image().save_png("res://art/captures/" + name + suffix + ".png")

func _swipe_notebook() -> void:
	var at: Vector2 = client.notebook_scroll.get_global_rect().get_center() + Vector2(0, 60)
	var touch := InputEventScreenTouch.new()
	touch.position = root.get_final_transform() * at
	touch.index = 0
	touch.pressed = true
	Input.parse_input_event(touch)
	await process_frame
	for i in 5:
		await create_timer(0.016).timeout
		at.y -= 18
		var drag := InputEventScreenDrag.new()
		drag.position = root.get_final_transform() * at
		drag.relative = root.get_final_transform().basis_xform(Vector2(0, -18))
		drag.index = 0
		Input.parse_input_event(drag)
		await process_frame
	touch.position = root.get_final_transform() * at
	touch.pressed = false
	Input.parse_input_event(touch)
	await process_frame

func _choice(kind: String, argument: String = "") -> Button:
	for button in client.dialogue.choices.get_children():
		var key: Array = button.get_meta("key", [])
		if not key.is_empty() and key[0] == kind and (argument.is_empty() or str(key[1]) == argument):
			return button
	return null

func _read_all() -> void:
	if client.dialogue.reading:
		await _tap(client.dialogue.next_button)
	await create_timer(0.1).timeout

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	if not await _wait_for():
		_fail("Fresh solo game did not start")
		return
	var tick: int = client.view.tick
	# This test exercises district taps, not the closer default camera crop.
	client.cam.size = 27.0
	client._stop_camera_focus()
	await create_timer(1.0).timeout
	var district: Button
	for entry in client.navigation.entries:
		if entry.kind == "entrance" and entry.region != client.view.region:
			_fail("An entrance is visible outside the current district")
			return
		if entry.kind == "district" and entry.region == "bar":
			district = entry.button
			if not "Le Néon Bleu" in district.get_meta("locations") or entry.target != entry.button:
				_fail("District description is missing its places or created a remote ground target")
				return
	for marker in client.navigation_markers.get_children():
		if marker.get_meta("region") != client.view.region:
			_fail("Ground arrows must belong only to the current district")
			return
	await _capture("districts-overview-phone")
	if district == null or not district.is_visible_in_tree():
		_fail("The bar district must be touchable on the overview")
		return
	await _tap(district)
	if not await _wait_for("bar"):
		_fail("Travel to the bar failed")
		return
	if client.interior.visible or not client.region_transition.playing:
		_fail("Travel should show a region animation and leave the player outside")
		return
	await _capture("rpg-region-phone")
	await create_timer(1.6).timeout
	var entrance: Button
	for entry in client.navigation.entries:
		if entry.button.tooltip_text == "Entrer : Le Néon Bleu":
			entrance = entry.target
	if entrance == null:
		_fail("Missing explicit building entrance")
		return
	await _tap(entrance)
	await create_timer(0.3).timeout
	if not client.interior.visible or client.person_buttons.is_empty():
		_fail("Manual entry did not show selectable inhabitants")
		return
	await _capture("rpg-people-phone")
	await _tap(client.person_buttons.values()[0])
	if not await _wait_for("", "greeting"):
		_fail("One tap on the ground halo did not start the conversation")
		return
	if client.view.ap != 0 or client.view.tick != tick or not client.view.conversation.active:
		_fail("Last-PA conversation should stay on the same turn")
		return
	await create_timer(0.2).timeout
	await _capture("rpg-questions-phone")
	var present := JSON.stringify(client.view.present)
	for question in ["alibi", "link", "seen"]:
		var ask := _choice("ask", question)
		if ask == null:
			_fail("Missing unasked authorized question: " + question)
			return
		await _tap(ask)
		if not await _wait_for("", "reply"):
			_fail("NPC response did not arrive")
			return
		if client.dialogue.speech.text != client.view.conversation.text:
			_fail("RPG response differs from the actual engine speech")
			return
		if JSON.stringify(client.view.present) != present or client.view.tick != tick:
			_fail("Inhabitants moved during a dialogue")
			return
		await _read_all()
		if question == "alibi":
			await _capture("rpg-answer-phone")
		if question != "seen":
			await _tap(client.dialogue.next_button)
			await create_timer(0.15).timeout
	if client.view.pending != null or client.view.tick != tick or not client.dialogue.visible:
		_fail("Final answer vanished or advanced the turn automatically")
		return
	await _capture("rpg-final-answer-phone")
	await _tap(client.dialogue.next_button)
	await create_timer(0.3).timeout
	await _capture("rpg-exhausted-phone")
	await create_timer(1.4).timeout
	if client.interior.visible or client.dialogue.visible or client.view.tick != tick or client.end_button.disabled:
		_fail("0 PA should fade back to the city and wait for manual end")
		return
	await _tap(client.end_button)
	for i in 160:
		await create_timer(0.05).timeout
		if client.view.tick == tick + 1:
			break
	if client.view.tick != tick + 1 or client.view.ap != 3 or not client.turn_transition.playing:
		_fail("Manual end failed to announce the new turn")
		return
	await create_timer(0.5).timeout
	await _capture("rpg-city-phase-phone")
	await create_timer(1.0).timeout
	await _capture("rpg-new-turn-phone")
	await create_timer(1.3).timeout
	client.notebook_page.show()
	await create_timer(0.3).timeout
	await _capture("rpg-notebook-phone")
	if client.notebook_cards.size() != client.view.notebook.size():
		_fail("Notebook must include every known or unknown person")
		return
	for row in client.view.notebook:
		var portrait: Control = client.notebook_cards[int(row.id)].get_child(0).get_child(0).get_child(0)
		if portrait.unknown != (row.name == "?"):
			_fail("Unknown notebook portraits must not show a person's appearance")
			return
		var address: Button = client.notebook_cards[int(row.id)].get_meta("home_button") if client.notebook_cards[int(row.id)].has_meta("home_button") else null
		if row.name == "?" and (address != null or row.get("home") != null):
			_fail("An unknown person must not reveal an address")
			return
		if row.name != "?" and (address == null or JSON.stringify(address.get_meta("residence")) != JSON.stringify(row.home)):
			_fail("An identified person's card must show their actual residence")
			return
	await _swipe_notebook()
	await create_timer(0.15).timeout
	if client.notebook_scroll.scroll_vertical < 40 or not client.notebook_page.visible:
		_fail("Dragging notebook cards did not scroll naturally")
		return
	await _capture("rpg-notebook-scroll-phone")
	client.touch_gestures.cancel_inertia()
	client.notebook_scroll.scroll_vertical = 0
	await create_timer(0.2).timeout
	var noted_id := -1
	for row in client.view.notebook:
		if row.name != "?":
			noted_id = int(row.id)
			break
	if noted_id < 0:
		_fail("Expected an identified suspect for manual notebook notes")
		return
	var before := JSON.stringify(client.view)
	var note: Button = client.notebook_cards[noted_id].get_meta("note_button")
	await _tap(note)
	if not client.manual_exclusions.has(str(noted_id)) or client.notebook_cards[noted_id].modulate.a > 0.5 or JSON.stringify(client.view) != before or client.solo_busy:
		_fail("Manual exclusion must dim a card without sending a game action")
		return
	await _capture("notebook-manual-phone")
	client.manual_exclusions.clear()
	client.notes_case = ""
	client._load_case_notes()
	client._draw_notebook()
	if not client.manual_exclusions.has(str(noted_id)) or client.notebook_cards[noted_id].modulate.a > 0.5:
		_fail("Personal exclusions did not survive reloading notes")
		return
	await create_timer(0.2).timeout
	await _tap(client.notebook_cards[noted_id].get_meta("note_button"))
	if client.manual_exclusions.has(str(noted_id)) or client.notebook_cards[noted_id].modulate.a != 1.0:
		_fail("Reactivating a suspect must restore the card")
		return
	# The engine's deductions must never automatically strike off the UI card.
	var notebook_backup: Array = client.view.notebook.duplicate(true)
	for row in client.view.notebook:
		if int(row.id) == noted_id:
			row.out = true
	client._draw_notebook()
	if client.notebook_cards[noted_id].modulate.a != 1.0 or "ÉCARTÉ" in client.notebook_cards[noted_id].get_meta("status_label").text:
		_fail("The UI still rules out suspects automatically")
		return
	client.view.notebook = notebook_backup
	client._draw_notebook()
	# Notes are scoped to this investigation, not a new seed or another player.
	var old_seed = client.view.solo.seed
	client.view.solo.seed = int(old_seed) + 100000
	client._load_case_notes()
	if not client.manual_exclusions.is_empty():
		_fail("Personal notes leaked into another investigation")
		return
	client.view.solo.seed = old_seed
	client._load_case_notes()
	client.touch_gestures.cancel_inertia()
	client.notebook_scroll.scroll_vertical = 0
	await create_timer(0.3).timeout
	await _capture("residence-notebook-phone")
	var residence_button: Button = client.notebook_cards[noted_id].get_meta("home_button")
	var residence: Dictionary = residence_button.get_meta("residence")
	before = JSON.stringify(client.view)
	await _tap(residence_button)
	await create_timer(0.9).timeout
	if client.notebook_page.visible or client.focus != residence.region or client.solo_busy or JSON.stringify(client.view) != before:
		_fail("Locating a residence must focus the district without moving or spending AP")
		return
	await _capture("residence-located-phone")
	print("RPG smoke passed: districts/local entrances → dialogue/manual turn → personal notes → known-only addresses → native residence focus without PA")
	quit(0)
