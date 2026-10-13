extends SceneTree

var client: Node
var suffix := "v17-20x9"

func _initialize() -> void:
	_run.call_deferred()

func _check(ok: bool, message: String) -> void:
	if not ok:
		push_error(message)
		quit(1)

func _settle() -> void:
	await create_timer(0.15).timeout
	for i in 500:
		if not client.solo_busy and not client.turn_transition.playing:
			return
		await create_timer(0.025).timeout
	_check(false, "Contacts response timeout")

func _act(key: Array) -> void:
	client._play_local(key)
	await _settle()

func _go(place: String) -> void:
	var parent = client.view.places[place].street
	if parent != null and client.view.place != parent:
		await _go(str(parent))
	if client.view.place == place:
		return
	while client.view.ap < client.view.routes[place].cost:
		await _act(["end"])
	await _act(client.view.routes[place].key)
	client.dialogue.hide()

func _card(id: int) -> Dictionary:
	for row in client.view.notebook:
		if row.id == id:
			return row
	return {}

func _contact(id: String) -> Dictionary:
	for row in client.view.contacts:
		if row.id == id:
			return row
	return {}

func _capture(name: String) -> void:
	await create_timer(0.65).timeout
	await RenderingServer.frame_post_draw
	_check(root.get_texture().get_image().save_png("res://art/captures/contacts-" + name + "-" + suffix + ".png") == OK, "Contact screenshot failed")

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

func _approach(id: int) -> void:
	for i in 8:
		var destination: String = _card(id).whereabouts.current.place
		var parent = client.view.places[destination].street
		await _go(destination if parent == null else str(parent))
		if client.view.ap == 0:
			await _act(["end"])
		if _card(id).whereabouts.current.place != destination:
			continue
		await _act(["interrogate", id] if parent == null else ["ring", destination])
		await _act(["talk"])  # the detective's look first, then the point is spent
		return
	_check(false, "Could not approach known suspect")

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
	_check(client.view.has("setup"), "Fresh seed 7 setup required")
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	await _act(["investigate", "inspect_scene"])
	await _go("police")
	if client.view.ap == 0:
		await _act(["end"])
	await _act(["investigate", "record:p1"])
	await _approach(1)
	await _act(["talk_about", 1, 0])
	_check(_card(0).name != "?" and not _card(0).profile_known, "Mention must identify name, not physical profile")
	_check(_card(0).appearance.is_empty() and _card(0).home == null, "Mention leaked physical appearance or home")
	client.dialogue.hide()
	client.notebook_page.show()
	client._set_notebook_tab("people")
	await process_frame
	client.notebook_scroll.ensure_control_visible(client.notebook_cards[0])
	await _capture("name-only")
	client.notebook_page.hide()
	if client.view.ap == 0:
		await _act(["stop"])
		await _act(["end"])
		await _approach(1)
	await _act(["ask", "evening"])
	_check(_contact("observer:p1").role == "Témoin" and _contact("observer:p1").name == "Camille", "Camille must be a witness contact")
	await _act(["stop"])
	await _go(str(_contact("observer:p1").place))
	if client.view.ap == 0:
		await _act(["end"])
	client._open_interior(false)
	client.dialogue.hide()
	await _tap(client.lounge.staff_buttons["observer:p1"])
	_check(client.view.conversation.person.role == "Témoin", "Native witness tap lost its status")
	_check(client.dialogue.context.text.begins_with("Témoin"), "Witness role missing from dialogue")
	await _capture("witness-dialogue")
	await _act(["ask", "service_action", "verify:p1"])
	await _act(["stop"])
	client.dialogue.hide()
	client.notebook_page.show()
	client._set_notebook_tab("contacts")
	await process_frame
	await process_frame
	for card in client.notebook_contacts.get_children():
		if card.get_meta("contact_id", "") == "observer:p1":
			client.notebook_scroll.ensure_control_visible(card)
	await _capture("notebook")
	_check(client.view.notebook.size() == 5 and not _contact("observer:p1").statements.is_empty(), "Contacts must not expand suspect roster")
	client.notebook_page.hide()
	# Ordinary lunch: actual manual turns, without moving actors or the clock.
	await _go("bar")
	var populated := false
	for i in 60:
		if not client.view.present.is_empty():
			populated = true
			break
		await _act(["end"])
	_check(populated, "Bar never receives a client")
	client._open_interior(false)
	client.dialogue.hide()
	var behind_bar := false
	for actor in client.lounge.figures.get_children():
		if actor.get_meta("contact_id", "") == "staff:bar":
			behind_bar = actor.position.z < -2.0
	_check(behind_bar, "Barman must stand behind counter, not among clients")
	_check(not client.lounge.person_buttons.is_empty(), "Suspects must remain in client lane")
	await _capture("bar-lanes")
	await _tap(client.lounge.staff_buttons["staff:bar"])
	_check(client.dialogue.context.text.begins_with("Personnel"), "Barman status missing from dialogue")
	await _capture("staff-dialogue")
	await _act(["stop"])
	var identity: String = client.notes_case
	client._toggle_suspect_note(0)
	client._toggle_suspect_priority(1)
	_check(client.manual_exclusions.has("0") and client.manual_priorities.has("1"), "Manual annotations not created")
	client._send({"type": "restart"})
	await _settle()
	_check(client.view.has("setup"), "Restart must return to setup")
	_check(client.manual_exclusions.is_empty() and client.manual_priorities.is_empty(), "Previous case annotations leaked on restart")
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	_check(client.notes_case != identity, "Notebook namespace must change with investigation")
	_check(client.manual_exclusions.is_empty() and client.manual_priorities.is_empty(), "Prior annotations returned after equipping new case")
	print("Causal contacts smoke passed: named silhouettes, witness/staff roles, separate lanes, isolated case annotations")
	quit(0)
