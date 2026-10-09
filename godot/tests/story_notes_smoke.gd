# Fresh solo save. Real engine actions, native Notes tab/scroll/pointer taps.
extends SceneTree
var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _wait() -> bool:
	for i in 200:
		await create_timer(0.04).timeout
		if client.qte_active:
			client._answer_qte(1.0)
		if not client.view.is_empty() and not client.view.has("setup") and not client.solo_busy:
			return true
	return false

func _act(kind: String, argument = null) -> bool:
	for option in client.view.options:
		var key: Array = option[0]
		if key[0] == kind and (argument == null or key.size() > 1 and key[1] == argument):
			client._play_local(key.duplicate())
			return await _wait()
	return false

func _tap(button: Button) -> void:
	var touch := InputEventScreenTouch.new()
	touch.position = root.get_final_transform() * button.get_global_rect().get_center()
	touch.index = 0
	touch.pressed = true
	Input.parse_input_event(touch)
	await process_frame
	touch = touch.duplicate()
	touch.pressed = false
	Input.parse_input_event(touch)
	await process_frame

func _capture(name: String) -> void:
	var suffix := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-suffix="):
			suffix = arg.trim_prefix("--capture-suffix=")
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://art/captures/" + name + suffix + ".png")

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	if not await _wait():
		_fail("Solo did not start")
		return
	await create_timer(0.8).timeout
	var person: int = int(client.view.present[0].id)
	if not await _act("interrogate", person):
		_fail("Interrogation unavailable")
		return
	for question in ["life", "grudge", "seen"]:
		if not await _act("ask", question):
			_fail("New life/rumour dialogue failed")
			return
	client.dialogue.hide()
	if not await _act("move", "victim_house") or not await _act("search"):
		_fail("Object-source investigation failed")
		return
	client.dialogue.hide()
	# Missing property no longer names an intermediary. The key register gives
	# a shared opportunity group, independently from any personal acquaintance.
	if not await _act("end"):
		_fail("Cannot finish turn before checking the key register")
		return
	await create_timer(2.5).timeout
	if not await _act("move", "bar") or not await _act("search"):
		_fail("Shared key register investigation failed")
		return
	client.dialogue.hide()
	await create_timer(1.0).timeout
	client.notebook_page.show()
	await create_timer(0.2).timeout
	await _tap(client.notebook_tabs.notes)
	await create_timer(0.3).timeout
	if client.notebook_tab != "notes" or not client.notebook_notes.is_visible_in_tree() or client.notebook_dossier.visible:
		_fail("Native Notes tab did not switch")
		return
	var count := 0
	for card in client.notebook_notes.get_children():
		if card.has_meta("journal_id"):
			count += 1
	if count != client.view.journal.size() or count < 6:
		_fail("Notes omitted previously recorded discoveries")
		return
	await _capture("story-notes-phone")
	await _tap(client.notebook_tabs.leads)
	await create_timer(0.2).timeout
	if client.notebook_tab != "leads" or not client.notebook_leads.is_visible_in_tree() or client.notebook_notes.visible:
		_fail("Native Pistes tab did not switch")
		return
	await _capture("story-leads-phone")
	await _tap(client.notebook_tabs.notes)
	await create_timer(0.2).timeout
	var note_card: Control
	for card in client.notebook_notes.get_children():
		if card.has_meta("journal_id") and not client.view.journal[int(card.get_meta("journal_id")) - 1].leads.is_empty():
			note_card = card
			break
	var lead: Button
	for widget in note_card.get_child(0).get_children():
		if widget is Button and widget.has_meta("note_place"):
			lead = widget
			break
	if lead == null:
		_fail("Missing touchable location in the document note")
		return
	client.notebook_scroll.ensure_control_visible(lead)
	await create_timer(0.3).timeout
	var before := JSON.stringify(client.view)
	await _tap(lead)
	await create_timer(0.8).timeout
	if client.notebook_page.visible or client.solo_busy or JSON.stringify(client.view) != before:
		_fail("Note pointer spent PA or changed the engine")
		return
	await _capture("story-note-pointer-phone")
	if not await _act("end"):
		_fail("Cannot return to a public conversation")
		return
	await create_timer(2.5).timeout
	if client.view.place != "bar" and not await _act("move", "bar"):
		_fail("Cannot return to a public conversation")
		return
	await create_timer(1.0).timeout
	if client.view.present.is_empty():
		_fail("No public person for targeted conversation")
		return
	var speaker: Dictionary = client.view.present[0]
	if speaker.name == null:
		if not await _act("interrogate", int(speaker.id)) or not await _act("stop"):
			_fail("Could not introduce public speaker")
			return
		for here in client.view.present:
			if int(here.id) == int(speaker.id):
				speaker = here
	client.interior.show()
	client._select_person(speaker)
	await create_timer(0.3).timeout
	var picker: Button
	for button in client.dialogue.choices.get_children():
		if button.has_meta("subject_picker"):
			picker = button
	if picker == null:
		_fail("Missing grouped relationship questions")
		return
	client.dialogue.choices_scroll.ensure_control_visible(picker)
	await create_timer(0.2).timeout
	await _tap(picker)
	await create_timer(0.2).timeout
	await _capture("story-people-questions-phone")
	var choice: Button = client.dialogue.choices.get_child(0)
	var before_count: int = client.view.journal.size()
	await _tap(choice)
	if not await _wait() or client.view.journal.size() != before_count + 1:
		_fail("Targeted question did not produce a saved testimony")
		return
	client.dialogue._finish_reveal()
	await create_timer(0.2).timeout
	await _capture("story-people-answer-phone")
	print("Story notes smoke passed: life/rumours → object → all notes → native tab → camera-only pointer → native targeted question")
	quit(0)
