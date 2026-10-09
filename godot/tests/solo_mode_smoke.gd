# Regression: an embedded APK plugin must select solo without a --solo CLI flag.
extends SceneTree

class EmbeddedPlugin:
	extends Object
	var opened := false
	func open_session(_seed: int, _name: String) -> void:
		opened = true
	func poll_messages() -> String:
		return "[]"
	func close_session() -> void:
		pass

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var plugin := EmbeddedPlugin.new()
	Engine.register_singleton("NexusSolo", plugin)
	var client: Node = load("res://main.tscn").instantiate()
	root.add_child(client)
	if not client.solo_mode or not plugin.opened or not client.end_button.disabled:
		push_error("Embedded APK started in server mode or enabled actions before receiving a view")
		quit(1)
		return
	if client.ws.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		push_error("Embedded APK attempted a WebSocket connection")
		quit(1)
		return
	client.queue_free()
	await process_frame
	Engine.unregister_singleton("NexusSolo")
	plugin.free()
	print("Solo mode smoke passed: embedded plugin → local session, no CLI flag, no WebSocket")
	quit(0)
