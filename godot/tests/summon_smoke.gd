extends "res://tests/causal_guidance_smoke.gd"

# Seed 0: the barman names his team, then "Faire appeler un employé…" calls Lina in; next turn
# she is at the bar and her home is empty.

func _button(meta: String) -> Button:
	for button in client.dialogue.choices.get_children():
		if button.has_meta(meta):
			return button
	return null

func _summon_button() -> Button:
	for button in client.dialogue.choices.get_children():
		var key: Array = button.get_meta("key", [])
		if not key.is_empty() and key[0] == "summon":
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
	_check(client.view.has("setup"), "Fresh summon setup required")
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	await _go("bar")
	if client.view.ap < 2:
		await _act(["end"])
	await _act(["service_menu", "staff:bar"])
	_check(_button("summon_picker") == null, "No call offered before the roster is known")
	await _act(["ask", "service_action", "venue_staff:bar"])
	client.dialogue._finish_reveal()
	for i in 6:  # real next-button touches, through a possible detective thought
		if client.dialogue.selecting:
			break
		await _tap(client.dialogue.next_button)
		if client.dialogue.reading:
			client.dialogue._finish_reveal()
	var picker := _button("summon_picker")
	_check(picker != null, "Roster known: the call folder must appear")
	await _tap(picker)
	var call := _summon_button()
	_check(call != null, "The folder lists an employee to call")
	await _capture("summon-folder")
	var id: int = int(call.get_meta("key")[1])
	var ap: int = client.view.ap
	await _tap(call)
	_check(client.view.ap == ap - 1, "Calling costs one point")
	var named := ""
	for row in client.view.notebook:
		if int(row.id) == id:
			named = str(row.name)
			_check(row.whereabouts.next.place == "bar" and row.whereabouts.next.activity == "appelé au travail", "Notebook must promise the bar next turn")
	_check(str(client.view.conversation.text).contains(named), "The barman confirms the call by name")
	await _capture("summon-reply")
	await _act(["stop"])
	client.dialogue.hide()
	await _act(["end"])
	var present := false
	for person in client.view.presence.places["bar"].people:
		if int(person.id) == id:
			present = true
	_check(present, "Next turn the employee is at the bar")
	for place in client.view.presence.places:  # named through the roster only: no address known, so nowhere else
		for person in client.view.presence.places[place].people:
			_check(place == "bar" or int(person.id) != id, "The called employee is nowhere but the bar")
	await _capture("summon-next-turn")
	print("Summon smoke OK: roster, folder, call, next-turn presence, empty home")
	quit(0)
