extends SceneTree

# Free mode in the client: difficulty at setup, countdown, the Fils tab,
# the accusation confirmation and the closing card.
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
	await create_timer(0.65).timeout
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
	if not client.view.has("setup") or not client.view.has("engine"):
		_fail("Fresh causal setup required")
		return
	if not client.difficulty_buttons.has("difficile") or client.difficulty_choice != "normal":
		_fail("Setup page lacks the difficulty row with its default level")
		return
	client.difficulty_buttons.difficile.button_pressed = true
	if client.difficulty_choice != "difficile":
		_fail("Difficulty toggle did not register")
		return
	client.chosen = ["fingerprints", "search"]
	client.start_choice = client.view.setup.default_start
	await _capture("setup-difficulty")
	client._start_game()
	await _settle()
	client.dialogue._finish_reveal()
	client.dialogue.hide()
	await create_timer(1.2).timeout
	if str(client.view.get("difficulty", "")) != "difficile" or client.view.get("time_left") == null:
		_fail("Engine did not start the free mode with the chosen difficulty")
		return
	if not client.header.text.contains("avant l'échéance"):
		_fail("Header lacks the countdown")
		return
	await _capture("countdown")
	client.notebook_page.show()
	client._set_notebook_tab("threads")
	await create_timer(0.2).timeout
	if client.notebook_threads.get_child_count() < 4:
		_fail("Fils tab is missing the status and three thread cards")
		return
	var next_steps := 0
	for card in client.notebook_threads.get_children():
		if card is PanelContainer:
			for line in card.get_child(0).get_children():
				if line is Label and str(line.text).begins_with("▶"):
					next_steps += 1
	if next_steps == 0:
		_fail("No next step highlighted in the threads")
		return
	await _capture("threads")
	client.notebook_page.hide()
	# Filing a case asks for confirmation before anything is sent.
	var sent_before: int = client.view.get("tick", 0)
	client._play_local(["accuse", 0])
	await create_timer(0.3).timeout
	if client.accuse_dialog == null or not client.accuse_dialog.visible or client.accuse_key.is_empty():
		_fail("Accusation went out without a confirmation")
		return
	await _capture("accuse-confirm")
	client.accuse_dialog.canceled.emit()
	await create_timer(0.2).timeout
	if not client.accuse_key.is_empty() or client.solo_busy or int(client.view.get("tick", 0)) != sent_before:
		_fail("Cancelled accusation left a pending key or reached the engine")
		return
	# The closing card renders from the view alone.
	client.view["ended"] = {"won": false, "title": "Affaire classée", "mistakes": 1,
		"text": "L'échéance est passée : le dossier est classé sans suite.\nLe coupable ne sera jamais inquiété."}
	client._show_ending()
	await create_timer(0.2).timeout
	if client.end_page == null:
		_fail("Closing card did not open")
		return
	await _capture("ending")
	print("causal threads smoke OK")
	quit(0)
