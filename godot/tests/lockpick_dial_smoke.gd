extends SceneTree

# Without the lockpick skill, a locked door brings up the timing dial; a hit in the arc opens it.
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
	await create_timer(0.3).timeout
	await RenderingServer.frame_post_draw
	if root.get_texture().get_image().save_png("res://art/captures/causal-" + name + "-" + suffix + ".png") != OK:
		_fail("Screenshot failed")

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
	if not client.view.has("setup"):
		_fail("Fresh causal setup required")
		return
	client.chosen = ["fingerprints", "search"]  # no lockpick: the dial decides
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue._finish_reveal()
	client.dialogue.hide()
	# Find a locked, empty apartment and walk to its street.
	var home := ""
	for i in 12:
		for place in client.view.places:
			var row: Dictionary = client.view.places[place]
			if row.get("street") != null and not row.get("custom", false) and client.view.presence.places[place].count == 0 and not str(place).begins_with("witness"):
				if client.view.place == row.street:
					for option in client.view.options:
						if option[0][0] == "unlock_home" and option[0][1] == place:
							home = place
				elif home.is_empty():
					var route: Dictionary = client.view.routes.get(row.street, {})
					if route.get("available", false):
						client._play_local(route.key.duplicate(true))
						await _settle()
			if not home.is_empty():
				break
		if not home.is_empty():
			break
		client._play_local(["end"])
		await _settle()
	if home.is_empty():
		_fail("No locked empty apartment reachable")
		return
	client._play_local(["unlock_home", home])
	for i in 200:
		await create_timer(0.025).timeout
		if client.qte_active:
			break
	if not client.qte_active or not client.qte.visible:
		_fail("Lockpicking without the skill must bring up the dial")
		return
	await _capture("lockpick-dial")
	# A miss keeps the door shut; the dial comes back on the next try.
	client.qte.angle = fposmod(client.qte.target + PI, TAU)
	client.qte.hit()
	await _settle()
	if client.view.place == home:
		_fail("A miss must not open the door")
		return
	client._play_local(["unlock_home", home])
	for i in 200:
		await create_timer(0.025).timeout
		if client.qte_active:
			break
	client.qte.angle = client.qte.target
	client.qte.hit()
	await _settle()
	await create_timer(0.8).timeout
	if client.view.place != home:
		_fail("A hit in the arc must open the door and walk in")
		return
	await _capture("lockpick-inside")
	# Stepping out is free and puts you back on the street, hallway button included.
	var street: String = client.view.places[home].street
	var ap: int = int(client.view.ap)
	client._leave_interior()
	await _settle()
	if client.view.place != street or int(client.view.ap) != ap:
		_fail("Leaving the picked flat must step out onto its street for free")
		return
	if client._door_choices(street).is_empty():
		_fail("Back on the street, the hallway doors must be offered again")
		return
	print("Lockpick dial smoke OK: miss kept the door shut, hit opened it, leaving steps out")
	quit(0)
