extends SceneTree
var client: Node

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	client = load("res://main.tscn").instantiate()
	root.add_child(client)
	for i in 250:
		await create_timer(0.05).timeout
		if not client.view.is_empty() and not client.view.has("setup") and not client.solo_busy:
			break
	if client.view.is_empty() or client.view.has("setup"):
		push_error("Fresh solo did not start")
		quit(1)
		return
	client._open_interior()
	await create_timer(1.5).timeout
	if client.lounge.get_world_3d() != client.get_world_3d() or client.lounge.find_children("*", "SubViewport", true, false).size() != 0:
		push_error("Interior must use the global world, not an isolated render or a modal")
		quit(1)
		return
	if client.cam_target.distance_to(client.lounge.global_position) > 10 or client.lounge.scale.x < 1.5:
		push_error("Camera did not teleport to the enlarged interior")
		quit(1)
		return
	await RenderingServer.frame_post_draw
	var suffix := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-suffix="):
			suffix = arg.trim_prefix("--capture-suffix=")
	root.get_texture().get_image().save_png("res://art/captures/lounge-phone" + suffix + ".png")
	# A drag in the global room moves the camera, never the detective or AP.
	var before: Vector3 = client.cam_target
	var ap: int = int(client.view.ap)
	var drag_at := Vector2(root.size.x * 0.78, root.size.y * 0.57)
	var finger := InputEventScreenTouch.new()
	finger.index = 0
	finger.pressed = true
	finger.position = drag_at
	Input.parse_input_event(finger)
	await process_frame
	for step in 5:
		var motion := InputEventScreenDrag.new()
		motion.index = 0
		motion.position = drag_at + Vector2((step + 1) * 15, -step * 3)
		motion.relative = Vector2(15, -3)
		motion.velocity = Vector2(300, -60)
		Input.parse_input_event(motion)
		await create_timer(0.04).timeout
	finger = finger.duplicate()
	finger.pressed = false
	finger.position = drag_at + Vector2(75, -12)
	Input.parse_input_event(finger)
	await create_timer(0.15).timeout
	if client.cam_target.distance_to(before) < 0.5 or int(client.view.ap) != ap:
		push_error("Interior camera drag failed or spent an action")
		quit(1)
		return
	client.touch_gestures.cancel_inertia()
	client.cam_target = before
	client._update_camera()
	await create_timer(0.2).timeout
	await RenderingServer.frame_post_draw
	if client.person_buttons.is_empty():
		push_error("No ground target for the inhabitants")
		quit(1)
		return
	var button: Button = client.person_buttons.values()[0]
	var at: Vector2 = root.get_final_transform() * button.get_global_rect().get_center()
	var event := InputEventScreenTouch.new()
	event.index = 0
	event.pressed = true
	event.position = at
	Input.parse_input_event(event)
	await process_frame
	event = event.duplicate()
	event.pressed = false
	Input.parse_input_event(event)
	for i in 150:
		await create_timer(0.05).timeout
		if client.qte_active:
			client._answer_qte(1.0)
		if not client.solo_busy and client.view.get("conversation") != null:
			break
	if client.view.get("conversation") == null or client.view.conversation.stage != "greeting":
		push_error("Native ground tap did not start the conversation directly")
		quit(1)
		return
	client.dialogue.hide()
	client.interior.hide()
	await process_frame
	if client.lounge.visible or client.cam_target.distance_to(client.lounge.global_position) < 100:
		push_error("Leaving the room did not return the same camera to the city")
		quit(1)
		return
	print("Lounge smoke passed: global 3D world, enlarged room, camera teleport/return, native drag without AP, one-tap conversation")
	quit(0)
