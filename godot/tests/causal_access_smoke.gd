extends SceneTree

var client: Node
var suffix := "v16-20x9"

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
	_fail("Access response timeout")

func _act(key: Array) -> void:
	client._play_local(key)
	await _settle()
	for i in 200:
		if not client.turn_transition.playing:
			break
		await create_timer(0.025).timeout

func _go(place: String) -> void:
	var parent = client.view.places[place].street
	if parent != null and client.view.place != parent:
		await _go(str(parent))
	if client.view.place == place:
		return
	if client.view.routes[place].cost > client.view.ap:
		await _act(["end"])
	await _act(client.view.routes[place].key)
	client.dialogue.hide()

func _tap(button: Button) -> void:
	await process_frame
	await process_frame
	var event := InputEventScreenTouch.new()
	event.pressed = true
	event.position = root.get_final_transform() * button.get_global_rect().get_center()
	Input.parse_input_event(event)
	await process_frame
	event = event.duplicate()
	event.pressed = false
	Input.parse_input_event(event)
	await _settle()

func _question(key: Array) -> void:
	await process_frame
	await process_frame
	var before: int = client.view.conversation.id if client.view.conversation != null else -1
	var place: String = client.view.place
	for button in client.dialogue.choices.get_children():
		if button.get_meta("key", []) == key:
			await _tap(button)
			for i in 400:
				if client.view.place != place or client.view.conversation != null and client.view.conversation.id != before:
					return
				await create_timer(0.025).timeout
			_fail("Native question did not reach the engine: " + str(key))
			return
	for button in client.dialogue.choices.get_children():
		if button.get_meta("background_picker", false) and key[1] in ["relation", "work", "habits"]:
			await _tap(button)
			await _question(key)
			return
	_fail("Missing physical question: " + str(key))

func _capture(name: String) -> void:
	await create_timer(0.7).timeout
	await RenderingServer.frame_post_draw
	if root.get_texture().get_image().save_png("res://art/captures/access-" + name + "-" + suffix + ".png") != OK:
		_fail("Access screenshot failed")

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
	if not client.view.has("setup") or not client.view.setup.items.has("lockpick"):
		_fail("Fresh access engine and lockpicking skill required")
		return
	client.chosen = ["fingerprints", "lockpick"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	if "Seed 7" not in client.header.text:
		_fail("Requested seed must be visible in the upper-left HUD")
		return
	var home := ""
	for place in client.view.places:
		if client.view.places[place].street != null and not client.view.places[place].get("custom", false) and client.view.presence.places[place].count > 0:
			home = place
			break
	if home.is_empty():
		_fail("Seed 7 must have a resident at home")
		return
	await _go(str(client.view.places[home].street))
	await _capture("city-entrances")
	client._open_interior(true)
	if not client.lounge.corridor.visible or client.lounge.geometry.visible or not client.lounge.person_buttons.is_empty() or not client.lounge.fixture_buttons.is_empty():
		_fail("Hallway must contain only doors, no duplicated residents/objects")
		return
	await _capture("closed-doors")
	var street: String = client.view.place
	await _tap(client.lounge.door_buttons[home])
	if client.view.place != street or client.view.doorstep != home or client.view.conversation.stage != "greeting" or not str(client.view.conversation.text).is_empty():
		_fail("Ringing must open questions on the doorstep, not enter or auto-answer")
		return
	if client.dialogue.choices.get_child_count() != 5 or client.lounge.person_buttons.size() != 1:
		_fail("One resident must appear only on the doorstep, with uniform questions")
		return
	await _capture("doorstep-questions")
	client.dialogue.hide()
	await _capture("resident-on-threshold")
	client.dialogue.show_cue(client.view.conversation, client.view.options)
	await _question(["ask", "relation"])
	client.dialogue._finish_reveal()
	await _capture("requested-answer")
	client.dialogue.advance()
	await _question(["ask", "evening"])
	if "Je n'ai rien" in str(client.view.conversation.text) or "chez moi" not in str(client.view.conversation.text):
		_fail("Every suspect must give a sourced personal evening account")
		return
	client.dialogue._finish_reveal()
	await _capture("evening-account")
	client.dialogue.advance()
	await _tap(client.dialogue.next_button)
	if client.view.pending != null or client.dialogue.visible or not client.lounge.person_buttons.is_empty():
		_fail("Closing must release conversation and return resident inside")
		return
	# Seed 7: another resident of this corridor has a corroborable visitor.
	var other_home := ""
	for door in client.view.doors:
		if door.place != home and door.occupied:
			other_home = door.place
			break
	await _tap(client.lounge.door_buttons[other_home])
	await _question(["ask", "evening"])
	if not "on s'est retrouvés chez moi" in str(client.view.conversation.text):
		_fail("Seed 7 second resident must provide a real visitor, not an empty answer")
		return
	client.dialogue._finish_reveal()
	await _capture("visitor-account")
	var visitor_lead = null
	for lead in client.view.leads:
		if str(lead.id).begins_with("evening:"):
			visitor_lead = lead
	if visitor_lead == null or visitor_lead.complete or client.view.places[visitor_lead.destinations[0].place].street != null:
		_fail("Personal alibi must open an unconfirmed lead towards a public witness")
		return
	client.notebook_page.show()
	client.dialogue.hide()
	client._set_notebook_tab("leads")
	await _capture("visitor-lead")
	client.notebook_page.hide()
	client.dialogue.show()
	client.dialogue.advance()
	await _tap(client.dialogue.next_button)
	var empty_home := ""
	var victim_home := ""
	for lead in client.view.leads:
		if lead.id == "victim_home":
			victim_home = lead.destinations[0].place
	for place in client.view.places:
		if client.view.places[place].street != null and not client.view.places[place].get("custom", false) and client.view.presence.places[place].count == 0:
			# A private apartment, not the police-open victim home.
			for note in client.view.notebook:
				if note.home != null and note.home.place == place:
					empty_home = place
	# Unknown empty homes are equally valid; find a real unlock key after arriving.
	if empty_home.is_empty():
		for place in client.view.places:
			if place != victim_home and client.view.places[place].street != null and not client.view.places[place].get("custom", false) and client.view.presence.places[place].count == 0:
				empty_home = place
				break
	await _go(str(client.view.places[empty_home].street))
	if client.view.ap < 3:
		await _act(["end"])
	client._open_interior(true)
	var before: int = client.view.ap
	await _tap(client.lounge.door_buttons[empty_home])
	await _question(["unlock_home", empty_home])
	if client.view.ap != before - 1 or client.view.place == empty_home:
		_fail("Crochetage must open an empty door, not teleport inside")
		return
	client.dialogue._finish_reveal()
	client.dialogue.advance()
	await _tap(client.lounge.door_buttons[empty_home])
	await _question(["move", empty_home])
	if client.view.place != empty_home or not client.interior.visible or not client.view.present.is_empty() or client.lounge.corridor.visible:
		_fail("Entering an unlocked empty apartment must show its objects, no resident")
		return
	await _capture("empty-apartment")
	await _go("hospital")
	if client.view.places.morgue.street != "hospital" or client.nodes.has("morgue"):
		_fail("Morgue must be an entrance of hospital, not a separate Palace-side building")
		return
	await _capture("hospital-entrances")
	var morgue_entry = null
	for entry in client.navigation.entries:
		if entry.get("place", "") == "morgue":
			morgue_entry = entry
	if morgue_entry == null or morgue_entry.color != Color("63e1ec"):
		_fail("Missing cyan secondary hospital entrance")
		return
	await _tap(morgue_entry.target)
	if client.view.place != "morgue" or client.view.region != "hospital" or not client.interior.visible:
		_fail("Hospital secondary entrance did not enter the real morgue")
		return
	await _capture("morgue")
	await _go("cabaret")
	await create_timer(0.8).timeout
	var expected: Vector3 = client._world("cabaret") + Vector3(-1.55, 0, 0.05)
	if client.detectives[0].position.distance_to(expected) > 0.01:
		_fail("Palace detective is not standing at its actual entrance")
		return
	await _capture("palace-arrival")
	print("Access v16 smoke passed: door-only corridor, question-first doorstep, lockpick empty home, cyan/violet entrances, hospital morgue, Palace arrival")
	quit(0)
