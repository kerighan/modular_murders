# Same JSON protocol, Android in-process or desktop development through pipes.
extends RefCounted

var plugin: Object
var process := {}
var buffer := PackedByteArray()
var failure := ""
var reported := false

func start(seed: int, name: String) -> void:
	if Engine.has_singleton("NexusSolo"):
		plugin = Engine.get_singleton("NexusSolo")
		plugin.open_session(seed, name)
	elif OS.has_feature("android"):
		failure = "Le moteur solo manque dans cet APK. Utilisez le build android-solo."
	else:
		var python := "python3"
		var engine := "legacy" if "--legacy-engine" in OS.get_cmdline_user_args() else "causal"
		var save := ProjectSettings.globalize_path("user://causal-solo.json" if engine == "causal" else "user://solo.json")
		for arg in OS.get_cmdline_user_args():
			if arg.begins_with("--python="):
				python = arg.trim_prefix("--python=")
			if arg.begins_with("--solo-save="):
				save = arg.trim_prefix("--solo-save=")
		var runtime := ProjectSettings.globalize_path("res://../solo_runtime.py")
		process = OS.execute_with_pipe(python, PackedStringArray(["-u", runtime, "--save", save, "--seed", str(seed), "--engine", engine]), false)
		if process.is_empty():
			failure = "Impossible de démarrer Python pour le test solo desktop."

func send(msg: Dictionary) -> void:
	var raw := JSON.stringify(msg)
	if plugin != null:
		plugin.send_message(raw)
	elif process.has("stdio"):
		process.stdio.store_buffer((raw + "\n").to_utf8_buffer())
		process.stdio.flush()

func poll() -> Array:
	if not failure.is_empty() and not reported:
		reported = true
		return [{"type": "error", "message": failure}]
	if plugin != null:
		var result = JSON.parse_string(plugin.poll_messages())
		return result if result is Array else []
	var messages := []
	if process.has("stdio"):
		buffer.append_array(process.stdio.get_buffer(65536))
		var newline := buffer.find(10)
		while newline >= 0:
			var msg = JSON.parse_string(buffer.slice(0, newline).get_string_from_utf8())
			if msg is Dictionary:
				messages.append(msg)
			buffer = buffer.slice(newline + 1)
			newline = buffer.find(10)
		if not OS.is_process_running(process.pid) and not reported:
			reported = true
			messages.append({"type": "error", "message": "Le moteur solo s'est arrêté. Vérifiez Python et networkx."})
	return messages

func close() -> void:
	if plugin != null:
		plugin.close_session()
	if process.has("stdio"):
		process.stdio.close()
	if process.has("pid") and OS.is_process_running(process.pid):
		OS.kill(process.pid)
