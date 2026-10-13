extends SceneTree

# The Réseau tab: an ego graph around the victim from what was actually heard.
var client: Node
var suffix := "16x9"

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

func _act(key: Array) -> void:
	client._play_local(key)
	await _settle()

func _capture(name: String) -> void:
	await create_timer(0.4).timeout
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
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue._finish_reveal()
	client.dialogue.hide()
	if client.view.network.nodes.size() != 1 or not client.view.network.edges.is_empty():
		_fail("Before any conversation the graph holds the victim alone")
		return
	# Meet two residents, ask their relation and their job, ask each about the other.
	var met := []
	for i in 10:
		if met.size() >= 2:
			break
		for place in client.view.places:
			var row: Dictionary = client.view.places[place]
			if row.get("street") == null or row.get("custom", false) or str(place).begins_with("witness"):
				continue
			if client.view.presence.places[place].count == 0:
				continue
			if client.view.place != row.street:
				var route: Dictionary = client.view.routes.get(row.street, {})
				if not route.get("available", false):
					continue
				await _act(route.key.duplicate(true))
			await _act(["ring", place])
			if client.view.pending == null:
				continue
			var pid: int = int(client.view.conversation.person.id)
			if pid in met:
				await _act(["stop"])
				continue
			await _act(["ask", "relation"])
			await _act(["ask", "work"])
			for other in met:
				await _act(["talk_about", pid, other])
			await _act(["stop"])
			met.append(pid)
			if met.size() >= 2:
				break
		if client.view.ap == 0 and met.size() < 2:
			await _act(["end"])
	client.dialogue.hide()
	if client.view.network.edges.is_empty():
		_fail("Two relation answers must draw at least one tie")
		return
	client.notebook_page.show()
	client._set_notebook_tab("network")
	await create_timer(0.3).timeout
	await _capture("network")
	print("Network smoke OK: %d ties, %d people" % [client.view.network.edges.size(), client.view.network.nodes.size()])
	quit(0)
