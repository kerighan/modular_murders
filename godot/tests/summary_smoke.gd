extends "res://tests/causal_guidance_smoke.gd"
# The Éléments tab opens on the case summary: who died, where, what we know.

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
	client.chosen = ["search", "rapport"]
	client.start_choice = client.view.setup.default_start
	client._start_game()
	await _settle()
	client.dialogue.hide()
	await _act(["investigate", "inspect_scene"])
	client.dialogue.hide()
	await _act(["investigate", "request_exam"])
	client.dialogue.hide()
	_check(client.view.summary.size() >= 3 and str(client.view.summary[0].title) == "L'affaire", "The summary opens with the affair")
	client.notebook_page.show()
	client._set_notebook_tab("evidence")
	await process_frame
	await process_frame
	var found := false
	for child in client.notebook_evidence.get_children():
		if child.get_meta("case_summary", false):
			found = true
	_check(found and client.notebook_evidence.get_child(0).get_meta("case_summary", false), "The summary card sits first in Éléments")
	await _capture("summary")
	print("Summary smoke OK")
	quit(0)
