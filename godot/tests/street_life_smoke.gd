extends SceneTree

# Street life: cars cruise the free lanes and the skyrail train crosses the viaduct.
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
	if not client.view.has("setup"):
		_fail("Fresh causal setup required")
		return
	client.chosen = ["fingerprints", "search"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue._finish_reveal()
	client.dialogue.hide()
	await create_timer(1.0).timeout
	var visuals = client.visuals
	if visuals.traffic.is_empty() or visuals.train == null:
		_fail("No traffic or no train in the city")
		return
	for car in visuals.traffic:
		var lane: float = car.node.position.x if car.vertical else car.node.position.z
		var offset: float = absf(lane - car.axis)
		if absf(offset - 0.95) > 0.01:
			_fail("A car is off its lane: offset %.2f" % offset)
			return
	visuals.train_clock = 0.0  # a train right now, for the capture
	var before := []
	for car in visuals.traffic:
		before.append(car.node.position)
	await _capture("street-life-a")
	await create_timer(3.0).timeout
	await _capture("street-life-b")
	var moved := 0
	for i in visuals.traffic.size():
		if visuals.traffic[i].node.position.distance_to(before[i]) > 2.0:
			moved += 1
	if moved < visuals.traffic.size() - 1:
		_fail("Cars did not cruise: %d moved" % moved)
		return
	if not visuals.train_running or absf(visuals.train.position.x) >= visuals.train_span:
		_fail("Train did not cross the viaduct")
		return
	# A wide view of the whole city, to see the traffic and the viaduct at once.
	client._stop_camera_focus()
	client.cam_target = visuals.city_center + Vector3(0, 1.5, 6.0)
	client.cam.size = 50.0
	await create_timer(1.0).timeout
	await _capture("street-life-wide-a")
	await create_timer(4.0).timeout
	await _capture("street-life-wide-b")
	print("Street life smoke OK: %d cars cruising, train at x=%.1f" % [moved, visuals.train.position.x])
	quit(0)
