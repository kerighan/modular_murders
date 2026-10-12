extends "res://tests/causal_guidance_smoke.gd"

# Runs the real seed-7 investigation from the guidance test, then checks the UI
# using native touches. No private scenario data or mocked notebook entries.
func _capture(name: String) -> void:
	await super._capture(name)
	if name == "named-position":
		for row in client.view.notebook:
			var card: Control = client.notebook_cards[int(row.id)]
			for node in card.find_children("*", "Control", true, false):
				if node.get_meta("notebook_portrait", false):
					_check(node.unknown == not row.profile_known, "Cited names must not reveal a physical portrait")
		return
	if name == "timeline":
		client.notebook_page.hide()
		await _go("police")
		for row in client.view.notebook:
			if row.profile_known:
				continue
			if client.view.ap == 0:
				await _act(["end"])
			await _act(["investigate", "record:p" + str(int(row.id))])
		client.dialogue.hide()
		client.notebook_page.show()
		client._set_notebook_tab("evidence")
		client.notebook_suspect_scroll.scroll_vertical = 0
		await super._capture("notebook-populated")
		_check(client.view.notebook.all(func(row): return row.profile_known), "Populated layout must use genuinely collected profiles")
		_check(client.notebook_suspect_scroll.get_v_scroll_bar().max_value > client.notebook_suspect_scroll.get_v_scroll_bar().page, "All seven suspects must remain reachable by scroll")
		return
	if name != "corroborated-card":
		return
	var public_view: String = JSON.stringify(client.view)
	var camera_position: Vector3 = client.cam_target
	var side: ScrollContainer = client.notebook_suspect_scroll
	var reading: ScrollContainer = client.notebook_scroll
	_check(side.get_global_rect().position.x > reading.get_global_rect().end.x, "Suspects must form an independent right column")
	_check(reading.size.y >= 350, "Notebook loses too much height to navigation")
	await _tap(client.notebook_cards[1].get_child(0))
	_check(client.notebook_selected == 1 and client.notebook_tab == "people", "Native portrait tap must select the dossier")
	await _tap(client.notebook_cards[1].get_meta("follow_button"))
	await create_timer(0.45).timeout
	_check(int(client.notebook_grid.get_child(0).get_meta("suspect_id")) == 1, "Following should animate the suspect to the top")
	await super._capture("notebook-followed")
	await _tap(client.notebook_cards[1].get_meta("note_button"))
	await create_timer(0.45).timeout
	_check(int(client.notebook_grid.get_child(-1).get_meta("suspect_id")) == 1, "Exclusion should move the suspect to the bottom")
	_check(client.manual_priorities.is_empty(), "Following/exclusion must remain exclusive")
	await super._capture("notebook-excluded")
	await _tap(client.notebook_cards[1].get_meta("note_button"))
	await _tap(client.notebook_tabs.evidence)
	_check(client.notebook_tab == "evidence" and side.visible, "Evidence must retain the suspects sidebar")
	await super._capture("notebook-evidence")
	# Open an earlier document through a real button and check its readable header.
	client.notebook_scroll.scroll_vertical = 0
	var card: Control = client.notebook_evidence.get_child(0)
	var heading: Button = card.get_child(0).get_child(0)
	var document_id: int = card.get_meta("evidence_id")
	await _tap(heading)
	_check(client.notebook_open_evidence == document_id, "Document heading should unfold the document")
	await super._capture("notebook-reading")
	client.touch_gestures.cancel_inertia()
	side.scroll_vertical = 0
	reading.scroll_vertical = 0
	await _swipe(side)
	_check(side.scroll_vertical > 0 and reading.scroll_vertical == 0, "Suspect drag should scroll only the right column")
	var side_offset: int = side.scroll_vertical
	await _swipe(reading)
	_check(reading.scroll_vertical > 0 and side.scroll_vertical == side_offset, "Evidence drag should scroll only the reading pane")
	_check(client.notebook_tab == "evidence", "Dragging across clickable cards must not select a suspect")
	_check(JSON.stringify(client.view) == public_view and client.cam_target == camera_position, "Notebook browsing and annotations must not mutate gameplay or camera")
	for tab in ["notes", "contacts", "leads"]:
		await _tap(client.notebook_tabs[tab])
		_check(client.notebook_tab == tab, "Native compact tab should switch the reading pane")
		await super._capture("notebook-" + tab)
	client.notebook_suspect_scroll.scroll_vertical = 0
	client._select_notebook_suspect(1)
	await super._capture("notebook-dossier")
	print("Notebook layout smoke passed: native tabs/portraits, independent momentum, readable height, manual sorting, unchanged gameplay")

func _swipe(container: ScrollContainer) -> void:
	await process_frame
	var at := container.get_global_rect().position + Vector2(container.size.x * 0.55, container.size.y * 0.70)
	var touch := InputEventScreenTouch.new()
	touch.pressed = true
	touch.position = at
	Input.parse_input_event(touch)
	await process_frame
	for step in 5:
		var motion := InputEventScreenDrag.new()
		motion.position = at - Vector2(0, (step + 1) * 22)
		motion.relative = Vector2(0, -22)
		Input.parse_input_event(motion)
		await create_timer(0.04).timeout
	touch = touch.duplicate()
	touch.position = at - Vector2(0, 110)
	touch.pressed = false
	Input.parse_input_event(touch)
	await create_timer(0.15).timeout
	client.touch_gestures.cancel_inertia()
