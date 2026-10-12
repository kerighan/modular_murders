extends "res://tests/causal_guidance_smoke.gd"

func _primary_questions() -> void:
	var expected := ["relation", "evening", "observations", "motive"]
	var buttons: Array = client.dialogue.choices.get_children()
	_check(buttons.size() >= 4 and buttons.size() <= 7, "Main questions should remain compact")
	for i in expected.size():
		_check(buttons[i].get_meta("key", []) == ["ask", expected[i]], "Primary question order must be relation/alibi/witness/tensions")
		_check(buttons[i].is_visible_in_tree(), "Primary question must be visible immediately")
		_check(client.dialogue.choices_scroll.get_global_rect().encloses(buttons[i].get_global_rect()), "Primary question should not require scrolling")
	for button in buttons:
		_check("Vous et la victime" not in button.text, "Relationship must not be inside a biography folder")
		_check(button.get_meta("key", []) != ["ask", "service_status"], "Suspects must not offer an empty status question")

func _return_to_questions() -> void:
	client.dialogue._finish_reveal()
	# Use actual next-button touches, including a possible detective thought.
	for i in 6:
		if client.dialogue.selecting:
			return
		await _tap(client.dialogue.next_button)
		if client.dialogue.reading:
			client.dialogue._finish_reveal()
	_check(false, "Dialogue did not return to its questions")

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
	_check(client.view.has("setup"), "Fresh dialogue setup required")
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	await _act(["investigate", "inspect_scene"])
	await _go("bar")
	if client.view.ap == 0:
		await _act(["end"])
	client.dialogue.hide()
	client._open_interior(false)
	client.dialogue.hide()
	await create_timer(1.5).timeout
	await _tap(client.lounge.staff_buttons["staff:bar"])
	_check(client.dialogue.choices.get_child_count() > 0, "Barman should open concrete questions")
	for button in client.dialogue.choices.get_children():
		_check(button.get_meta("key", []) != ["ask", "service_status"], "Barman must not offer the useless add-something question")
		_check("quelque chose à ajouter" not in button.text, "Generic relaunch remains visible")
	await _capture("dialogue-barman")
	await _act(["stop"])
	# Learn a real profile, then approach its actual location using public info.
	await _go("police")
	if client.view.ap == 0:
		await _act(["end"])
	await _act(["investigate", "record:p1"])
	await _approach(1)
	await process_frame
	_primary_questions()
	await _capture("dialogue-primary")
	await _question(["ask", "relation"])
	_check(client.view.conversation.question.begins_with("Votre relation avec la victime ?"), "One tap must ask relationship directly")
	client.dialogue._finish_reveal()
	await _capture("dialogue-relation-answer")
	await _return_to_questions()
	_primary_questions()
	if client.view.ap == 0:
		var state: String = JSON.stringify(client.view.journal)
		var time: String = client.view.clock
		var blocked: Button = client.dialogue.choices.get_child(1)
		_check(blocked.disabled, "Unasked alibi must be grey at zero PA")
		await _tap(blocked)
		_check(client.dialogue.selecting and client.view.ap == 0 and client.view.clock == time and JSON.stringify(client.view.journal) == state, "Disabled question should do nothing, not display a PA error")
		await _capture("dialogue-zero-pa")
		await _question(["ask", "relation"])
		_check(client.view.ap == 0 and client.view.clock == time and JSON.stringify(client.view.journal) == state, "Already asked relation must be freely repeatable at zero PA")
		await _return_to_questions()
		await _tap(client.dialogue.next_button)
		_check(client.view.pending == null and not client.dialogue.visible, "Exit must close the exhausted conversation")
		await _act(["end"])
		await _approach(1)
		_primary_questions()
	await _question(["ask", "evening"])
	_check("Alibi" in client.view.conversation.question, "Alibi must execute directly without a folder")
	await _return_to_questions()
	_primary_questions()
	var profile_folder: Button
	for button in client.dialogue.choices.get_children():
		if button.get_meta("background_picker", false):
			profile_folder = button
	_check(profile_folder != null, "Secondary biography should remain available")
	var pa_before: int = client.view.ap
	var time_before: String = client.view.clock
	await _tap(profile_folder)
	var keys := []
	for button in client.dialogue.choices.get_children():
		keys.append(button.get_meta("key", []))
	_check(keys == [["ask", "work"], ["ask", "circle"]], "Biography folder should only contain work and the victim's circle")
	_check(client.view.ap == pa_before and client.view.clock == time_before, "Opening a folder must not spend PA/time")
	await _question(["ask", "work"])
	await _return_to_questions()
	for button in client.dialogue.choices.get_children():
		if button.get_meta("background_picker", false):
			await _tap(button)
			break
	await _question(["ask", "circle"])
	await _return_to_questions()
	_check(client.view.ap == 0, "Four fresh informative questions should exhaust this real seed-7 route")
	var state: String = JSON.stringify(client.view.journal)
	var time: String = client.view.clock
	var blocked: Button = client.dialogue.choices.get_child(2)
	_check(blocked.disabled, "Unasked witness question must be grey at zero PA")
	await _tap(blocked)
	_check(client.dialogue.selecting and client.view.ap == 0 and client.view.clock == time and JSON.stringify(client.view.journal) == state, "Disabled question should do nothing, not display a PA error")
	await _capture("dialogue-zero-pa")
	await _question(["ask", "relation"])
	_check(client.view.ap == 0 and client.view.clock == time and JSON.stringify(client.view.journal) == state, "Already asked relation must be freely repeatable at zero PA")
	await _return_to_questions()
	_primary_questions()
	await _capture("dialogue-return")
	await _tap(client.dialogue.next_button)
	_check(client.view.pending == null and not client.dialogue.visible, "Exit must close the exhausted conversation")
	print("Dialogue menu smoke passed: no empty relaunch, relation first, direct alibi/witness/tensions, native questions/return, secondary biography only")
	quit(0)
