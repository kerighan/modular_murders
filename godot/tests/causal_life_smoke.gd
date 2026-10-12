extends SceneTree

var client: Node
var suffix := "v16-life-20x9"

func _initialize() -> void:
	_run.call_deferred()

func _check(ok: bool, message: String) -> void:
	if not ok:
		push_error(message)
		quit(1)

func _act(key: Array) -> void:
	client._play_local(key)
	await create_timer(0.15).timeout
	for i in 500:
		if not client.solo_busy and not client.turn_transition.playing:
			return
		await create_timer(0.025).timeout
	_check(false, "Life response timeout")

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

func _capture(name: String) -> void:
	await create_timer(0.5).timeout
	await RenderingServer.frame_post_draw
	_check(root.get_texture().get_image().save_png("res://art/captures/life-" + name + "-" + suffix + ".png") == OK, "Life screenshot failed")

func _focus_thread() -> void:
	await process_frame
	await process_frame
	for card in client.notebook_leads.get_children():
		if card.get_meta("lead_id", "") == "thread:p1":
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
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await create_timer(0.5).timeout
	while client.solo_busy:
		await create_timer(0.025).timeout
	await _act(["investigate", "inspect_scene"])
	await _act(["investigate", "request_exam"])
	await _go("police")
	for pid in [0, 1, 2, 4, 5]:
		if client.view.ap == 0:
			await _act(["end"])
		await _act(["investigate", "record:p" + str(pid)])
	client.dialogue.hide()
	# Seed 7, Tess: real loan grievance and independent continuous alibi.
	var place := ""
	for note in client.view.notebook:
		if note.id == 1:
			place = note.whereabouts.current.place
	await _go(place if client.view.places[place].street == null else str(client.view.places[place].street))
	if client.view.ap == 0:
		await _act(["end"])
	# Read again: the trip may have crossed a turn boundary.
	for note in client.view.notebook:
		if note.id == 1:
			place = note.whereabouts.current.place
	if client.view.places[place].street != null:
		await _go(str(client.view.places[place].street))
		await _act(["ring", place])
	else:
		await _go(place)
		await _act(["interrogate", 1])
	await _act(["ask", "motive"])
	await _act(["ask", "evening"])
	await _act(["stop"])
	client.dialogue.hide()
	client.notebook_page.show()
	client._set_notebook_tab("people")
	await _capture("positions-notebook")
	client._set_notebook_tab("leads")
	await _focus_thread()
	await _capture("open-thread")
	client.notebook_page.hide()
	var destination := ""
	for lead in client.view.leads:
		if lead.id == "evening:p1":
			destination = lead.destinations[0].place
	_check(not destination.is_empty(), "Named evening witness must open a locatable trail")
	await _go(destination)
	if client.view.ap == 0:
		await _act(["end"])
	await _act(["investigate", "verify:p1"])
	await _go("morgue")
	for i in 8:
		if client.view.options.any(func(option): return option[0] == ["investigate", "read_medical"]):
			break
		await _act(["end"])
	await _act(["investigate", "read_medical"])
	var refuted := false
	for lead in client.view.leads:
		if lead.id == "thread:p1":
			refuted = lead.state == "refuted" and lead.complete
	_check(refuted, "Loan hypothesis must close only after independent alibi and crime time")
	client.dialogue.hide()
	client.notebook_page.show()
	client._set_notebook_tab("leads")
	await _focus_thread()
	await _capture("refuted-thread")
	client.notebook_page.hide()
	# Exercise ordinary lunchtime life via actual manual turns, not clock writes.
	var lunch := ""
	for i in 40:
		for note in client.view.notebook:
			if note.whereabouts.current.activity == "déjeune":
				lunch = note.whereabouts.current.place
		if not lunch.is_empty():
			break
		await _act(["end"])
	_check(not lunch.is_empty(), "At least one known suspect must go out for lunch")
	await _go(lunch)
	client._open_interior(false)
	client.dialogue.hide()
	_check(not client.lounge.person_buttons.is_empty(), "Lunch must be physically populated")
	await _capture("public-lunch")
	print("Causal life smoke passed: whereabouts, public lunch, refutable false trail")
	quit(0)
