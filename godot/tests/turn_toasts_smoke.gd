extends "res://tests/causal_guidance_smoke.gd"
# Turn-start headlines queue in the top-right card: the coroner's report, one after the other.

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
	_check(client.view.has("setup"), "Fresh setup required")
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	await _act(["investigate", "inspect_scene"])
	client.dialogue.hide()
	await _act(["investigate", "request_exam"])
	client.dialogue.hide()
	var shown := false
	for i in 4:
		await _act(["end"])
		_check(not client.case_toasts.card.visible, "The first note waits for the turn title")
		for j in 40:
			await create_timer(0.1).timeout
			if client.case_toasts.card.visible:
				break
		if client.case_toasts.card.visible and client.case_toasts.detail.text.begins_with("Le légiste a terminé"):
			shown = true
			await _capture("turn-toast")
			_check(client.case_toasts.card.modulate.a > 0.9, "The note must still be fully visible after a second")
			break
	_check(shown, "The coroner's report must be announced at turn start")
	_check(client.case_toasts.title.text.begins_with("Tour "), "Headline titled by turn")
	client.case_toasts.note("Tour 9", "Deuxième note")
	_check(client.case_toasts.queue.size() == 1, "A second note waits its turn instead of overwriting")
	print("Turn toasts smoke OK")
	quit(0)
