extends SceneTree
var client: Node
var suffix := "v18-20x9"

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
	_check(false, "Guidance response timeout")

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

func _lead(id: String) -> Dictionary:
	for row in client.view.leads:
		if row.id == id:
			return row
	return {}

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
		return
	_check(false, "Known suspect could not be approached")

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
	for button in client.dialogue.choices.get_children():
		if button.get_meta("key", []) == key:
			await _tap(button)
			return
	for button in client.dialogue.choices.get_children():
		if button.get_meta("verification_picker", false) and key.size() > 2 and str(key[2]).begins_with("verify:"):
			await _tap(button)
			await _question(key)
			return
	_check(false, "Missing dialogue action " + str(key))

func _capture(name: String) -> void:
	await create_timer(0.65).timeout
	await RenderingServer.frame_post_draw
	_check(root.get_texture().get_image().save_png("res://art/captures/guidance-" + name + "-" + suffix + ".png") == OK, "Guidance screenshot failed")

func _focus_lead(id: String) -> void:
	await process_frame
	await process_frame
	for card in client.notebook_leads.get_children():
		if card.get_meta("lead_id", "") == id:
			client.notebook_scroll.ensure_control_visible(card)
			return

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
	client.dialogue.hide()
	_check(client.view.notebook.size() == 7, "Expected seven suspects")
	client._pin_district(str(client.view.crime_site.region))
	await _capture("crime-marker")
	await _act(["investigate", "inspect_scene"])
	await _go("police")
	if client.view.ap == 0:
		await _act(["end"])
	await _act(["investigate", "record:p1"])
	await _approach(1)
	var target := -1
	for row in client.view.notebook:
		if row.name == "?":
			target = int(row.id)
			break
	await _act(["talk_about", 1, target])
	_check(not _card(target).profile_known and _card(target).whereabouts != null, "Cited names need positions but no physical profile")
	client.dialogue.hide()
	client.notebook_page.show()
	client._select_notebook_suspect(target)
	await process_frame
	client.notebook_suspect_scroll.ensure_control_visible(client.notebook_cards[target])
	await _capture("named-position")
	client.notebook_page.hide()
	if client.view.ap == 0:
		await _act(["stop"])
		await _act(["end"])
		await _approach(1)
	await _act(["ask", "evening"])
	await _act(["stop"])
	_check(not _lead("evening:p1").complete, "Self-report cannot corroborate itself")
	client.dialogue.hide()
	client.notebook_page.show()
	client._set_notebook_tab("leads")
	await _focus_lead("evening:p1")
	await _capture("open-trail")
	client.notebook_page.hide()
	var destination: String = _lead("evening:p1").destinations[0].place
	await _go(destination)
	if client.view.ap == 0:
		await _act(["end"])
	client._open_interior(false)
	client.dialogue.hide()
	var keeper := "staff:restaurant" if destination == "restaurant" else "staff:bar"
	_check(client.lounge.staff_buttons.has(keeper), "The cited service contact must exist at the destination")
	await _capture("service-open")
	await _tap(client.lounge.staff_buttons[keeper])
	_check(client.dialogue.choices.get_child_count() <= 6, "Role menu requires folding verifications")
	await _question(["ask", "service_action", "verify:p1"])
	await _act(["stop"])
	client.dialogue.hide()
	_check(_card(1).alibi == "corroboré", "Collected testimony must be marked before medical timing")
	_check(_lead("evening:p1").complete, "Verification lead must visibly close")
	await _capture("service-verified")
	client.notebook_page.show()
	client._select_notebook_suspect(1)
	await process_frame
	client.notebook_suspect_scroll.ensure_control_visible(client.notebook_cards[1])
	await _capture("corroborated-card")
	client.notebook_page.hide()
	await _go("morgue")
	if client.view.ap == 0:
		await _act(["end"])
	client._open_interior(false)
	await _tap(client.lounge.staff_buttons["staff:medical"])
	await _question(["ask", "service_action", "request_exam_morgue"])
	await _act(["stop"])
	for i in 5:
		if client.view.crime_timing.state == "ready":
			break
		await _act(["end"])
	_check(client.view.crime_timing.state == "ready", "Medical report should become available within four turns")
	client._open_interior(false)
	client.dialogue.hide()
	await _tap(client.lounge.staff_buttons["staff:medical"])
	await _question(["ask", "service_action", "read_medical"])
	_check(_card(1).alibi == "confirmé", "Independent testimony plus medical period should confirm alibi")
	client.dialogue._finish_reveal()
	await _capture("medical-answer")
	var before_pa: int = client.view.ap
	var before_time: String = client.view.clock
	await _act(["ask", "service_status"])
	_check(client.view.ap == before_pa and client.view.clock == before_time, "Medical estimate recall must be free and repeatable")
	await _act(["stop"])
	await _go("cctv")
	if client.view.ap == 0:
		await _act(["end"])
	await _act(["camera_menu"])
	await _act(["ask", "camera_district", client.view.crime_site.place])
	var hour: int = int(client.view.crime_timing.start) / 60
	var window := 22 if hour >= 22 else 20 if hour >= 20 else 18 if hour >= 18 else 0
	await _act(["ask", "camera_window", window])
	await _act(["stop"])
	client.dialogue.hide()
	client.notebook_page.show()
	client._set_notebook_tab("timeline")
	await _capture("timeline")
	client.notebook_page.hide()
	var identity: String = client.notes_case
	client._toggle_suspect_note(1)
	client._send({"type": "restart"})
	await _settle()
	_check(client.view.has("setup") and int(client.view.solo.seed) <= 1000 and int(client.view.solo.seed) >= 0, "Restart seed must be human readable")
	_check(client.manual_exclusions.is_empty() and client.manual_priorities.is_empty(), "Prior annotations leaked")
	print("Causal guidance smoke passed: role-based trail, seven suspects, learned positions, verified glow, repeatable medical period, acquired timeline, short seed")
	quit(0)
