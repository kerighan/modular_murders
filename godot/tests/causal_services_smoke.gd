extends SceneTree

var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

func _settle() -> void:
	await create_timer(0.1).timeout
	for i in 400:
		if not client.solo_busy and not client.view.is_empty():
			return
		await create_timer(0.025).timeout
	_fail("Service response timeout")

func _act(key: Array) -> void:
	if key[0] in ["walk", "move"] and client.view.routes[key[1]].cost > client.view.ap:
		await _act(["end"])
	client._play_local(key)
	await _settle()
	for i in 200:
		if not client.turn_transition.playing:
			break
		await create_timer(0.025).timeout
	client.dialogue.hide()

func _has(key: Array) -> bool:
	for option in client.view.options:
		if option[0] == key:
			return true
	return false

func _capture(name: String) -> void:
	await create_timer(0.8).timeout
	await RenderingServer.frame_post_draw
	if root.get_texture().get_image().save_png("res://art/captures/causal-" + name + "-v16-20x9.png") != OK:
		_fail("Service screenshot failed")

func _tap(button: Button, expect_reply: bool = true) -> void:
	await process_frame
	await process_frame
	var before: int = client.view.conversation.id if client.view.conversation != null else -1
	var event := InputEventScreenTouch.new()
	event.pressed = true
	event.position = root.get_final_transform() * button.get_global_rect().get_center()
	Input.parse_input_event(event)
	await process_frame
	event = event.duplicate()
	event.pressed = false
	Input.parse_input_event(event)
	await _settle()
	if not expect_reply:
		return
	for i in 400:
		if client.view.conversation != null and client.view.conversation.id != before:
			return
		await create_timer(0.025).timeout
	_fail("Native service tap did not open a conversation")

func _question(key: Array) -> void:
	for button in client.dialogue.choices.get_children():
		if button.get_meta("key", []) == key:
			await _tap(button)
			return
	for button in client.dialogue.choices.get_children():
		if button.get_meta("police_records_picker", false) and key.size() > 2 and str(key[2]).begins_with("record:"):
			await _tap(button, false)
			await _question(key)
			return
	_fail("Missing native service question: " + str(key))

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	for i in 400:
		await create_timer(0.025).timeout
		if client.view.has("setup"):
			break
	if not client.view.has("engine") or not client.view.has("setup"):
		_fail("Fresh causal service setup required")
		return
	client.chosen = ["fingerprints", "search"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	client._open_interior()
	if client.view.scene_has_blood or client.lounge.blood.visible or client.view.outdoors:
		_fail("Seed 0 poison must be indoors and have no blood")
		return
	await _capture("poison-scene")
	await _act(["investigate", "inspect_scene"])
	await _act(["investigate", "collect_drink"])
	await _act(["investigate", "request_exam"])
	await _act(["walk", "lab"])
	if int(client.view.ap) == 0:
		await _act(["end"])
	client._open_interior()
	var before_time: String = client.view.clock
	var before_pa: int = client.view.ap
	await _tap(client.lounge.staff_buttons["staff:lab"])
	await _question(["ask", "service_status"])
	if client.view.clock != before_time or client.view.ap != before_pa:
		_fail("Analysis status must not advance time or spend PA")
		return
	client.dialogue._finish_reveal()
	await _capture("pending-analysis")
	client.dialogue.advance()
	client.dialogue._choose(["stop"])
	await _settle()
	for i in 8:
		if _has(["investigate", "analyze_drink"]):
			break
		await _act(["end"])
	if not _has(["investigate", "analyze_drink"]):
		_fail("Analysis did not become available after its processing delay")
		return
	if not client.lounge.staff_buttons.has("staff:lab"):
		_fail("Laboratory technician missing from global 3D interior")
		return
	await _capture("laboratory")
	var before: int = client.view.journal.size()
	await _tap(client.lounge.staff_buttons["staff:lab"])
	if client.view.journal.size() != before or client.dialogue.choices.get_child_count() < 2:
		_fail("Technician answered before a question / empty service greeting")
		return
	await _capture("laboratory-questions")
	await _question(["ask", "service_action", "analyze_drink"])
	if client.view.journal[-1].category != "laboratory" or not client.view.conversation.person.get("service", false):
		_fail("Native laboratory tap failed to analyze the actual acquired glass")
		return
	client.dialogue._finish_reveal()
	await _capture("poison-analysis")
	client.dialogue.advance()
	client.dialogue._choose(["stop"])
	await _settle()
	if client.dialogue.visible or client.dialogue.waiting:
		_fail("Service conversation did not close")
		return
	await _act(["end"])
	await _act(["walk", "hospital"])
	await _act(["move", "morgue"])
	client._open_interior()
	for i in 8:
		if _has(["investigate", "read_medical"]):
			break
		await _act(["end"])
	if not client.lounge.staff_buttons.has("staff:medical"):
		_fail("Medical examiner missing from global 3D interior")
		return
	await _capture("morgue")
	await _tap(client.lounge.staff_buttons["staff:medical"])
	await _capture("medical-questions")
	await _question(["ask", "service_action", "read_medical"])
	client.dialogue._finish_reveal()
	if client.view.conversation == null or not client.view.conversation.person.get("service", false):
		_fail("Medical response must belong to the physical doctor")
		return
	for note in client.view.journal:
		if "blood" in str(note.source):
			_fail("Poison flow invented a blood sample")
			return
	await _capture("medical-report")
	await _act(["stop"])
	await _act(["walk", "bar"])
	if client.view.ap == 0:
		await _act(["end"])
	client._open_interior()
	if not client.lounge.staff_buttons.has("staff:bar"):
		_fail("Permanent barman missing")
		return
	await _tap(client.lounge.staff_buttons["staff:bar"])
	await _question(["ask", "service_action", "venue_guests:bar"])
	client.dialogue._finish_reveal()
	await _capture("bar-guests")
	await _act(["stop"])
	await _act(["walk", "restaurant"])
	if client.view.ap == 0:
		await _act(["end"])
	client._open_interior()
	if not client.lounge.staff_buttons.has("staff:restaurant"):
		_fail("Permanent restaurant server missing")
		return
	await _tap(client.lounge.staff_buttons["staff:restaurant"])
	await _capture("restaurant-server-questions")
	await _act(["stop"])
	await _act(["walk", "police"])
	if client.view.ap == 0:
		await _act(["end"])
	client._open_interior()
	if not client.lounge.staff_buttons.has("staff:police"):
		_fail("Commissioner must be a physical interlocutor")
		return
	await _tap(client.lounge.staff_buttons["staff:police"])
	await _capture("police-questions")
	var record_key: Array = []
	for option in client.view.options:
		if option[0].size() > 2 and option[0][1] == "service_action" and str(option[0][2]).begins_with("record:"):
			record_key = option[0]
			break
	await _question(record_key)
	client.dialogue._finish_reveal()
	if "Cheveux" not in str(client.view.conversation.text):
		_fail("Police record must restore physical descriptors including hair")
		return
	await _capture("police-record")
	await _act(["stop"])
	client.notebook_page.show()
	client._set_notebook_tab("people")
	await _capture("police-portrait")
	print("Causal v16 service smoke passed: poison/lab/morgue, permanent bar/restaurant staff, police record folder, real hair portraits")
	quit(0)
