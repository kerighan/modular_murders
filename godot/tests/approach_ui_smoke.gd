extends "res://tests/summon_smoke.gd"
# Through the real buttons: ring a suspect, read the detective's look, "Lui parler (1 PA)",
# and the questions appear; the next button reads "Quitter" on the approach.

func _key_button(kind: String) -> Button:
	for button in client.dialogue.choices.get_children():
		var key: Array = button.get_meta("key", [])
		if not key.is_empty() and key[0] == kind:
			return button
	return null

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
	await _settle()
	client.dialogue.hide()
	await _act(["investigate", "inspect_scene"])
	client.dialogue.hide()
	var home := ""
	for place in client.view.places:
		if str(place).begins_with("home") and client.view.presence.places.get(place, {}).get("count", 0) > 0:
			home = str(place)
			break
	_check(not home.is_empty(), "A resident at home is needed")
	var street: String = client.view.places[home].street
	await _go(street)
	if client.view.ap == 0:
		await _act(["end"])
	await _act(["ring", home])
	_check(client.view.conversation.stage == "approach", "Ringing opens the approach")
	_check(client.dialogue.selecting and client.dialogue.speech.visible and _key_button("talk") != null, "The approach shows the look and 'Lui parler' together, no tap between")
	_check(client.dialogue.next_button.text == "Quitter", "The next button leaves on the approach")
	await _capture("approach-choice")
	var ap: int = client.view.ap
	await _tap(_key_button("talk"))
	_check(client.view.conversation.stage == "greeting" and client.view.ap == ap - 1, "'Lui parler' costs the point and opens the questions")
	_check(client.dialogue.selecting and _key_button("ask") != null, "Questions must be listed after 'Lui parler'")
	await _capture("approach-questions")
	print("Approach UI smoke OK")
	quit(0)
