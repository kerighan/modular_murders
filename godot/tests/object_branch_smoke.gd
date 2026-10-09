extends "res://tests/story_notes_smoke.gd"
## Visual fixtures use real engine options, never fabricated journal cards.

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	if not await _wait():
		_fail("Solo did not start")
		return
	if not await _act("move", "victim_house") or not await _act("search"):
		_fail("Victim papers unavailable")
		return
	client.dialogue.hide()
	var cache_fixture := false
	for arg in OS.get_cmdline_user_args():
		if arg == "--cache-fixture":
			cache_fixture = true
	if cache_fixture:
		# Seed 42: anonymous cache in a public place, unrelated to any home.
		if int(client.view.ap) == 0:
			if not await _act("end"):
				_fail("Cannot finish turn")
				return
			await create_timer(2.5).timeout
		if not await _act("move", "den"):
			_fail("Cache fixture destination unreachable")
			return
		if int(client.view.ap) == 0:
			if not await _act("end"):
				_fail("Cannot finish turn before searching cache")
				return
			await create_timer(2.5).timeout
		if not await _act("search") or client.view.story.object_status != "found":
			_fail("Anonymous cache did not update the notebook")
			return
	else:
		if client.view.story.object_status != "not_reported" or client.view.story.object != null:
			_fail("No-object case invents a disappeared item")
			return
	client.dialogue.hide()
	client.notebook_page.show()
	await create_timer(0.25).timeout
	await _tap(client.notebook_tabs.notes)
	await create_timer(0.3).timeout
	await _capture("object-cache-notes-phone" if cache_fixture else "object-none-notes-phone")
	if not cache_fixture:
		for card in client.notebook_notes.get_children():
			if not card.has_meta("journal_id"):
				continue
			var note: Dictionary = client.view.journal[int(card.get_meta("journal_id")) - 1]
			if note.title == "Qui connaissait le rendez-vous ?":
				client.notebook_scroll.scroll_vertical = int(card.position.y)
				await create_timer(0.25).timeout
				await _capture("object-none-invitation-phone")
				break
	print("Object branch smoke passed: real search, private notebook, " + ("anonymous cache" if cache_fixture else "no missing object"))
	quit(0)
