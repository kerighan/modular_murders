# Game client. The separate city_visuals.gd owns the procedural voxel art.
extends Node3D

const URL := "ws://127.0.0.1:8000/ws/%d/%s"
const SEED := 42
const NAME := "Ada"
const BLOCK := 12.0  # 7.6-wide pavements + 4.4-wide two-lane streets
const CAM_OFFSET := Vector3(23, 32, 27)
const CityVisuals := preload("res://city_visuals.gd")
const CityNavigation := preload("res://city_navigation.gd")
const VoxelAvatar := preload("res://voxel_avatar.gd")
const SoloTransport := preload("res://solo_transport.gd")
const TouchMomentum := preload("res://touch_momentum.gd")
const RPGDialogue := preload("res://rpg_dialogue.gd")
const CaseToasts := preload("res://case_toasts.gd")
const RegionTransition := preload("res://region_transition.gd")
const TurnTransition := preload("res://turn_transition.gd")
var turn_transition: Control
var exhausted_tick := -1
var dialogue: Control
var case_toasts: Control
var region_transition: Control
var room_backdrop: Control
var lounge: Node3D
var inside_scene := false
var exterior_far := 4000.0
var selected_person := {}
var pending_events := []
var last_cue_id := -1
var enter_requested := ""
var action_context := ""
var last_region := ""
var person_buttons := {}
var end_key_pending: Array = []
var last_world_tick := -1
const BoardZones := preload("res://board_zones.gd")
var board_zones: MeshInstance3D
var board_enabled := true
var touch_gestures: Node
var focus_tween: Tween
var solo_mode := false
var solo: RefCounted
var solo_busy := false
var new_case_button: Button
var restart_dialog: ConfirmationDialog
var qte_button: Button
var visuals: Node3D
var navigation: Control
var navigation_markers: Node3D
var taxi_choices: Array = []
var district_choices: Array = []
var district_button: Button
var end_button: Button
var navigation_hint: Label
var art_preview := false
var phone_ui := false
var server_url := URL % [SEED, NAME]
var interface_theme: Theme
const DETECTIVE_COLORS := [Color(0.3, 0.9, 1.0), Color(1.0, 0.5, 0.2), Color(0.6, 1.0, 0.4), Color(1.0, 0.3, 0.6)]
var dragging := false
var cam_target := Vector3(15, 0, 10)
var detectives := []  # transient markers
var dressed := false

# one colour per family of action, until real icons exist
const STYLE := {
	"move": [Color(0.25, 0.55, 0.95), "»"], "search": [Color(0.95, 0.75, 0.2), "¤"],
	"talk": [Color(0.85, 0.35, 0.75), "«»"], "office": [Color(0.55, 0.55, 0.65), "§"],
	"accuse": [Color(0.9, 0.25, 0.25), "!"], "end": [Color(0.3, 0.3, 0.35), "·"],
}
const FAMILY := {
	"investigate": "search", "confront": "talk", "talk_about": "talk", "check_timeline": "office",
	"move": "move", "walk": "move", "search": "search", "unlock": "search", "try_code": "search", "lab": "search",
	"interrogate": "talk", "ring": "talk", "observe": "talk", "ask": "talk", "stop": "talk", "verify": "talk",
	"authorize": "office", "record": "office", "file": "office", "victim_file": "office",
	"accuse": "accuse", "end": "end",
}

var ws := WebSocketPeer.new()
var view := {}
var nodes := {}  # place id -> Node3D
var people := []  # transient voxel figures
var buttons := []  # transient action buttons
var cam: Camera3D
var hud: CanvasLayer
var header: Label
var cards: VBoxContainer  # the events of the moment, as small boxes
var anchors := {}  # button -> [world position, 2D offset], so buttons follow the camera
var focus := ""  # place the camera is zoomed on
var setup_page: PanelContainer
var setup_scroll: ScrollContainer
var chosen := []  # items picked on the setup page
var start_choice := ""
var item_buttons := {}
var start_buttons := {}
var start_btn: Button
var interior: Control  # lightweight HUD for the interior, not a scene modal
var interior_box: HBoxContainer
var interior_title: Label
var interior_column: VBoxContainer
var notification_scroll: ScrollContainer
var notification_layer: CanvasLayer
var last_place := ""
var reconnect_t := 0.0
var notebook_page: PanelContainer
var notebook_scroll: ScrollContainer
var notebook_grid: GridContainer
var notebook_summary: Label
var notebook_evidence: VBoxContainer
var notebook_dossier: VBoxContainer
var notebook_notes: VBoxContainer
var notebook_leads: VBoxContainer
var notebook_tabs := {}
var notebook_tab := "people"
var notebook_cards := {}
var manual_exclusions := {}
var notes_case := ""
const NOTES_PATH := "user://case-notes.cfg"
var notes_path := NOTES_PATH
const DISTRICT_NAMES := {
	"victim_street": "Quartier Verlaine", "alley": "Quartier des Traverses",
	"bar": "Quartier du Néon", "crime_scene": "Quartier du Canal",
	"cctv": "Quartier des Ondes", "cabaret": "Quartier du Palace",
	"den": "Quartier des Jeux", "hospital": "Quartier Saint-Vital",
	"police": "Quartier Central", "victim_house": "Résidence Verlaine",
}
var qte: ProgressBar
var qte_active := false
var qte_t := 0.0
var equipped := false
var entered := false
var taxi_mode := false
var taxi_btn: Button
var houses := {}  # house id -> Node3D

func _ready() -> void:
	art_preview = "--art-preview" in OS.get_cmdline_user_args()
	phone_ui = OS.has_feature("mobile") or "--phone-ui" in OS.get_cmdline_user_args()
	if phone_ui:
		get_tree().root.content_scale_size = Vector2i(960, 540)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--notes-path="):
			notes_path = arg.trim_prefix("--notes-path=")
		if arg.begins_with("--server-url="):
			server_url = arg.trim_prefix("--server-url=")
	# Godot feature tags are lowercase. The embedded plugin is also authoritative:
	# an APK must never silently fall back to the desktop WebSocket connection.
	solo_mode = Engine.has_singleton("NexusSolo") or OS.has_feature("android") or "--solo" in OS.get_cmdline_user_args()
	cam = Camera3D.new()
	add_child(cam)
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL if "--ortho" in OS.get_cmdline_user_args() else Camera3D.PROJECTION_PERSPECTIVE
	cam.fov = 38.0
	cam.far = 250.0
	cam.size = 22.7
	_update_camera()
	visuals = CityVisuals.new()
	add_child(visuals)
	visuals.dress_world()
	if art_preview:
		_art_preview()
		return
	board_enabled = "--no-board-zones" not in OS.get_cmdline_user_args()
	board_zones = BoardZones.new()
	add_child(board_zones)
	_build_hud()
	touch_gestures = TouchMomentum.new()
	touch_gestures.host = self
	add_child(touch_gestures)
	if solo_mode:
		header.text = "NEXUS CITY · SOLO\nChargement de l'enquête hors ligne…"
		solo = SoloTransport.new()
		var initial_seed := randi_range(1, 2147483647) if Engine.has_singleton("NexusSolo") or OS.has_feature("android") else SEED
		for arg in OS.get_cmdline_user_args():
			if arg.begins_with("--seed="):
				initial_seed = int(arg.trim_prefix("--seed="))
		solo.start(initial_seed, NAME)
	else:
		header.text = "NEXUS CITY\nConnexion au serveur…"
		ws.connect_to_url(server_url)
	if "--shot" in OS.get_cmdline_user_args():  # screenshot for headless review, then quit
		get_tree().create_timer(4.0).timeout.connect(_shot)

func _shot() -> void:
	if "--carnet" in OS.get_cmdline_user_args() and notebook_page != null:
		notebook_page.visible = true
	if "--destinations" in OS.get_cmdline_user_args() and navigation != null:
		for entry in navigation.entries:
			if entry.button.tooltip_text.begins_with("Entrées"):
				entry.button.pressed.emit()
				break
	if "--taxi-list" in OS.get_cmdline_user_args() and navigation != null:
		navigation.show_choices("Taxi · destinations", taxi_choices)
	await RenderingServer.frame_post_draw
	var path := "user://city-shot.png"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shot-path="):
			path = arg.trim_prefix("--shot-path=")
	var error := get_viewport().get_texture().get_image().save_png(path)
	if error != OK:
		push_error("Could not save screenshot: %s (%d)" % [path, error])
		get_tree().quit(1)
		return
	print("Screenshot: ", path, " (", error, ")")
	print("Art meshes: ", visuals.mesh_count, " | triangles: ", visuals.triangle_count,
		" | draw calls: ", Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		" | frame ms: ", Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0)
	get_tree().quit()

func _art_preview() -> void:
	# Art review only: this fixture never feeds options or changes the server view.
	var grid := [["alley", "crime_scene", "victim_street", null, "victim_house"],
		["cctv", "bar", "police", null, null], ["cabaret", "den", "hospital", null, null],
		[null, null, null, null, null]]
	visuals.build(grid)
	for r in grid.size():
		for c in grid[r].size():
			if grid[r][c] != null:
				visuals.make_place(grid[r][c], Vector3(c * BLOCK, 0, r * BLOCK))
	visuals.finish()
	cam_target = Vector3(BLOCK * 1.8, 2.8, BLOCK * 1.2)
	cam.size = 46.0
	if "--detail" in OS.get_cmdline_user_args():
		cam_target = Vector3(BLOCK, 2.2, BLOCK)
		cam.size = 24.0
	if "--wide" in OS.get_cmdline_user_args():
		cam.size = 68.0
	if "--hero" in OS.get_cmdline_user_args():
		cam_target = Vector3(BLOCK * 2.0, 4.2, 0)
		cam.size = 16.0
	if "--bridge" in OS.get_cmdline_user_args():
		cam_target = Vector3(BLOCK * 3.0, 3.8, -0.4)
		cam.size = 26.0
	if "--campus" in OS.get_cmdline_user_args():
		cam_target = Vector3(BLOCK * 2.5, 2.4, BLOCK * 2.0)
		cam.size = 25.0
	if "--courtyard" in OS.get_cmdline_user_args():
		cam_target = Vector3(0, 2.4, BLOCK * 2.5)
		cam.size = 26.0
	_update_camera()
	_art_overlay()
	if "--shot" in OS.get_cmdline_user_args():
		get_tree().create_timer(3.0).timeout.connect(_shot)

func _art_overlay() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 1
	add_child(layer)
	var title := Label.new()
	title.position = Vector2(28, 23)
	title.text = "N E X U S   C I T Y"
	title.add_theme_color_override("font_color", Color("65d9ec"))
	title.add_theme_font_size_override("font_size", 24)
	layer.add_child(title)
	var subtitle := Label.new()
	subtitle.position = Vector2(30, 58)
	subtitle.text = "SECTOR 07  /  PLUIE NÉON\n2084.11.03    21:47"
	subtitle.add_theme_color_override("font_color", Color("6b95a9"))
	subtitle.add_theme_font_size_override("font_size", 12)
	layer.add_child(subtitle)

func _process(delta: float) -> void:
	_update_camera()
	if art_preview:
		return
	var protected := focus
	if not nodes.has(protected) and view.has("places") and view["places"].has(protected):
		protected = view["places"][protected]["street"]
	visuals.update_camera_fade(cam, cam_target, protected, delta)
	if solo_mode:
		for message in solo.poll():
			_on_message(message)
	else:
		_poll_server(delta)
	if new_case_button != null:
		new_case_button.disabled = solo_busy or qte_active
	for btn in anchors:
		btn.position = cam.unproject_position(anchors[btn][0]) + anchors[btn][1]
	if notification_scroll != null:
		notification_scroll.visible = false # Spoken lines use the RPG box, not a log stack.
	for label in get_tree().get_nodes_in_group("labels"):  # constant size on screen whatever the zoom
		label.pixel_size = label.get_meta("base") * cam.size / 28.0
	if qte_active:
		qte_t += delta
		qte.value = max(0.0, 100.0 - qte_t * 50.0)
		if qte_t > 2.0:
			_answer_qte(0.0)

func _poll_server(delta: float) -> void:
	ws.poll()
	if ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		while ws.get_available_packet_count() > 0:
			_on_message(JSON.parse_string(ws.get_packet().get_string_from_utf8()))
	elif ws.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		reconnect_t += delta
		if reconnect_t > 2.0:  # the server went away: keep knocking
			reconnect_t = 0.0
			ws = WebSocketPeer.new()
			ws.connect_to_url(server_url)

func _exit_tree() -> void:
	if solo != null:
		solo.close()

func _input(event: InputEvent) -> void:
	# Track releases even when a Control consumes them, so camera gestures cannot stick.
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and not event.pressed:
		dragging = false

func _unhandled_input(event: InputEvent) -> void:
	if qte_active and event.is_action_pressed("ui_accept"):
		_answer_qte(1.0 if qte_t < 0.7 else 0.6 if qte_t < 1.4 else 0.25)
	# look around: drag with the mouse or a finger, zoom with the wheel
	if (event is InputEventMouseButton or event is InputEventMouseMotion) and event.device == InputEvent.DEVICE_ID_EMULATION:
		return  # screen-drag handles the finger; avoid panning twice
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			dragging = event.pressed
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP:
			cam.size = clamp(cam.size * 0.9, 8.0, 68.0)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			cam.size = clamp(cam.size * 1.1, 8.0, 68.0)
	elif event is InputEventMouseMotion and dragging:
		_pan(event.relative)
	elif event is InputEventMagnifyGesture:
		if event.factor > 0.0:
			cam.size = clampf(cam.size / event.factor, 8.0, 68.0)

func _pan(pixels: Vector2) -> void:
	# Touch events use the logical canvas, not the high-DPI render target pixels.
	var height: float = navigation.get_viewport_rect().size.y if navigation != null else get_viewport().get_visible_rect().size.y
	var k: float = cam.size / maxf(height, 1.0) * 1.35
	var right := Vector3(cam.global_basis.x.x, 0, cam.global_basis.x.z).normalized()
	var forward := Vector3(cam.global_basis.z.x, 0, cam.global_basis.z.z).normalized()
	cam_target += -right * pixels.x * k - forward * pixels.y * k / 0.65
	_update_camera()

func _map_gestures_allowed() -> bool:
	return not qte_active and not (is_instance_valid(setup_page) and setup_page.visible) \
		and not notebook_page.visible \
		and not (dialogue != null and dialogue.visible) \
		and not (turn_transition != null and turn_transition.playing) \
		and not is_instance_valid(navigation.sheet) \
		and not (is_instance_valid(restart_dialog) and restart_dialog.visible)

func _stop_camera_focus() -> void:
	if is_instance_valid(focus_tween):
		focus_tween.kill()

func _update_camera() -> void:
	if cam == null:
		return
	var distance := cam.size / (2.0 * tan(deg_to_rad(cam.fov * 0.5)))
	cam.position = cam_target + CAM_OFFSET.normalized() * distance
	cam.look_at(cam_target)

func _answer_qte(score: float) -> void:
	if not qte_active:
		return
	qte_active = false
	qte.visible = false
	qte_button.visible = false
	_send({"type": "score", "score": score})

func _send(msg: Dictionary) -> void:
	if msg.get("type") == "play":
		action_context = str(msg.get("key", [""])[0])
	if solo_mode:
		if msg.get("type") != "score":
			if solo_busy:
				return
			solo_busy = true
		solo.send(msg)
		return
	if ws.get_ready_state() != WebSocketPeer.STATE_OPEN:
		turn_transition.abort()
		_show_cards(["Connexion perdue avec le serveur. Nouvelle tentative…"], Color(0.5, 0.1, 0.1))
		return
	ws.send_text(JSON.stringify(msg))

func _on_message(msg: Dictionary) -> void:
	if "--shot" in OS.get_cmdline_user_args():
		print("<< ", msg.get("type"), " ", msg.get("events", msg.get("message", msg.get("kind", ""))))
	match msg.get("type"):
		"reset":
			_reset_solo_city()
		"view":
			solo_busy = false
			var previous := view
			view = msg
			if not view.has("setup"):
				equipped = true
			if view.has("setup") and not equipped:
				var args := OS.get_cmdline_user_args()
				if "--enter" in args or "--carnet" in args or "--city" in args or "--inside" in args:
					equipped = true  # review modes skip the setup
					_send({"type": "equip", "items": ["taxi", "forensic_kit"], "start": "bar" if "--inside" in args else "victim_street"})
				else:
					_show_setup()
			elif "--enter" in OS.get_cmdline_user_args() and not entered:  # review mode: walk into an apartment
				for opt in view["options"]:
					if opt[0][0] == "move" and str(opt[0][1]).begins_with("house_"):
						entered = true
						_send({"type": "play", "key": opt[0]})
						break
			_draw()
			if not view.has("setup"):
				_present_feedback(previous)
		"events":
			pending_events.append_array(msg["events"])
		"challenge":
			qte_t = 0.0
			qte_active = true
			qte.visible = true
			qte_button.visible = true
			qte_button.text = "%s · Appuyez vite !" % str(msg["kind"]).capitalize()
			dialogue.set_busy_hint("Approchez votre interlocuteur · touchez le bouton de persuasion.")
			if "--shot" in OS.get_cmdline_user_args():  # review mode: a perfect reflex
				_answer_qte(1.0)
		"error":
			solo_busy = false
			end_key_pending.clear()
			turn_transition.abort()
			enter_requested = ""
			dialogue.recover()
			_show_cards([msg["message"]], Color(0.5, 0.1, 0.1))

func _reset_solo_city() -> void:
	# Keep the transport, rebuild only the seed-dependent scene/UI.
	view = {}
	manual_exclusions.clear()
	notes_case = ""
	dialogue.hide()
	case_toasts.clear()
	pending_events.clear()
	selected_person.clear()
	last_cue_id = -1
	last_region = ""
	exhausted_tick = -1
	last_world_tick = -1
	end_key_pending.clear()
	turn_transition.abort()
	enter_requested = ""
	equipped = false
	chosen.clear()
	start_choice = ""
	item_buttons.clear()
	start_buttons.clear()
	if is_instance_valid(setup_page):
		setup_page.queue_free()
		setup_page = null
	interior.visible = false
	inside_scene = false
	cam.far = exterior_far
	_mount_notifications(false)
	notebook_page.visible = false
	navigation.clear()
	for actor in people + detectives:
		actor.queue_free()
	people.clear()
	detectives.clear()
	nodes.clear()
	houses.clear()
	board_zones.mesh = null
	visuals.queue_free()
	visuals = CityVisuals.new()
	add_child(visuals)
	visuals.dress_world()
	dressed = false
	focus = ""
	last_place = ""

func _show_cards(lines: Array, color: Color) -> void:
	if not lines.is_empty():
		case_toasts.note("Attention" if color.r > color.b else "Information", str(lines[0]))

func _present_feedback(previous: Dictionary) -> void:
	var cue = view.get("conversation")
	var notebook_changed := not previous.is_empty() and not previous.has("setup") and JSON.stringify(previous.get("notebook", [])) != JSON.stringify(view.get("notebook", []))
	if cue != null and int(cue.id) != last_cue_id:
		last_cue_id = int(cue.id)
		selected_person = cue.person.duplicate(true)
		dialogue.show_cue(cue, view["options"])
		if notebook_changed:
			var detail: String = str(cue.notes[0]) if not cue.get("notes", []).is_empty() and cue.stage == "reply" else "Informations sur " + str(cue.person.name)
			case_toasts.note("Carnet mis à jour", detail)
	elif not pending_events.is_empty():
		if action_context in ["move", "walk", "end", "", "equip"]:
			for line in pending_events:
				if str(line).begins_with("🔔") or str(line).begins_with("📰") or "porte résiste" in str(line):
					case_toasts.note("Information", str(line))
		else:
			dialogue.show_result(pending_events, view["player"])
			if notebook_changed or previous.get("facts", []) != view.get("facts", []):
				case_toasts.note("Carnet mis à jour", "Vos nouvelles informations sont dans le carnet.")
	var new_turn: bool = not previous.is_empty() and not previous.has("setup") and (view["tick"] != previous.get("tick", view["tick"]) or view.get("active_player") != previous.get("active_player"))
	if new_turn:
		var title := "T O U R   %d" % (int(view["tick"]) + 1)
		var caption := "À vous de jouer · %d PA" % view["ap"] if view.get("active_player", view["player"]) == view["player"] else "Au tour de " + str(view["active_player"])
		if turn_transition.phase_waiting:
			turn_transition.finish_turn(title, caption)
		else:
			turn_transition.play(title, caption)
	elif not dialogue.visible:
		_check_exhausted()
	pending_events.clear()
	action_context = ""

# ---------------------------------------------------------------- the city

func _draw() -> void:
	var grid: Array = view["grid"]
	var places: Dictionary = view["places"]
	var here: String = view["place"]
	if not dressed:
		dressed = true
		_lay_city(grid)
	var street = places[here]["street"] if places[here]["street"] != null else here
	_load_case_notes()
	var changed_place := here != last_place and not last_place.is_empty()
	var changed_region: bool = street != last_region and not last_region.is_empty()
	if changed_place:
		interior.hide()
		dialogue.hide()
		_mount_notifications(false)
	for r in grid.size():
		for c in grid[r].size():
			var id = grid[r][c]
			if id == null:
				continue
			if not nodes.has(id):
				nodes[id] = _make_place(id, Vector3(c * BLOCK, 0, r * BLOCK))
			var box: MeshInstance3D = nodes[id].get_node("Box")
			var mat := box.get_surface_override_material(0) as StandardMaterial3D
			mat.emission_enabled = id == here
			mat.emission = Color(0.9, 0.3, 0.6)
			mat.emission_energy_multiplier = 0.6
			var label: Label3D = nodes[id].get_node("Label")
			label.text = places[id]["label"] + ("  ✓" if places[id]["searched"] else "")
			label.visible = false # Ground destinations replace duplicate roof labels.
	visuals.finish()
	board_zones.update_view(view, visuals.occupied_cells)
	board_zones.visible = board_enabled
	var per_street := {}
	for id in places:
		var st = places[id]["street"]
		if st == null:
			continue
		var i: int = per_street.get(st, 0)
		per_street[st] = i + 1
		if not houses.has(id):
			houses[id] = _make_house(nodes[st].position + Vector3(-2.6 + (i % 6) * 1.0, 0.16, 2.82 + (i / 6) * 0.5))
		var hmat := (houses[id].get_node("Box") as MeshInstance3D).get_surface_override_material(0) as StandardMaterial3D
		hmat.albedo_color = Color(0.9, 0.3, 0.6) if id == here else Color(0.95, 0.8, 0.35) if places[id]["lit"] else Color(0.14, 0.13, 0.2)
		hmat.emission_enabled = places[id]["lit"] or id == here
		hmat.emission = Color(0.9, 0.3, 0.6) if id == here else Color(0.9, 0.6, 0.1)
		(houses[id].get_node("Label") as Label3D).text = places[id]["label"].replace("Appart. ", "") + (" ✓" if places[id]["searched"] else "")
		(houses[id].get_node("Label") as Label3D).visible = false
	for p in people:
		p.queue_free()
	people.clear()
	for id in view["glance"]:
		for i in view["glance"][id][0]:
			var cap: Node3D = visuals.figure(nodes[id].position + Vector3(-2.0 + i * 0.6, 0.2, 3.0), Color("59626f"), i)
			add_child(cap)
			people.append(cap)
			if last_world_tick >= 0 and int(view["tick"]) != last_world_tick:
				var arrival := cap.position
				cap.position += Vector3(1.4, 0, 0)
				cap.create_tween().tween_property(cap, "position", arrival, 1.2).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	last_world_tick = int(view["tick"])
	for d in detectives:
		d.queue_free()
	detectives.clear()
	for i in view["detectives"].size():
		var det: Dictionary = view["detectives"][i]
		var place: String = det["place"]
		var base: Node3D = houses[place] if houses.has(place) else nodes[place]
		var marker := Node3D.new()
		marker.position = (base.position + Vector3(0, 0.15, 1.0)) if houses.has(place) else _world(place)
		marker.position += Vector3(-1.55 + i * 0.7, 0, 0.05)
		var color: Color = Color("ffd386") if det["you"] else DETECTIVE_COLORS[i % DETECTIVE_COLORS.size()]
		marker.set_meta("name", det["name"])
		marker.set_meta("you", det["you"])
		marker.set_meta("color", color)
		var cap: Node3D = visuals.detective_figure(Vector3.ZERO, color, det["you"])
		marker.add_child(cap)
		add_child(marker)
		if det["you"] and changed_region:
			var arrival := marker.position
			marker.position += Vector3(1.5, 0, 0.15)
			marker.create_tween().tween_property(marker, "position", arrival, 0.65).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		detectives.append(marker)
	var pr: Dictionary = view["progress"]
	header.text = "NEXUS CITY  /  %s\n%s · Tour %d · %d PA · %d preuves · %d documents" % [
		_district_title(street), view["player"], view["tick"] + 1, view["ap"], pr["preuves"], pr.get("documents", 0)]
	if solo_mode:
		header.text += " · SOLO hors ligne"
	if view["pending"] != null:
		header.text += "   — en conversation avec %s" % view["pending"]
	_draw_actions(street)
	_draw_notebook()
	if not interior.visible:
		_focus(here)
	if changed_region:
		region_transition.arrive(_district_title(street))
	if here == enter_requested or "--inside" in OS.get_cmdline_user_args():
		_open_interior()
	enter_requested = ""
	last_place = here
	last_region = street
	if interior.visible:
		_draw_interior()

func _focus(here: String) -> void:
	# inside an apartment, the camera glides onto it; back on the street, it shows the whole city
	if here == focus:
		return
	focus = here
	var target: Vector3 = (houses[here] if houses.has(here) else nodes[here]).position
	var size := 17.0 if houses.has(here) else 18.0
	if "--close-camera" in OS.get_cmdline_user_args() and not houses.has(here):
		size = 20.0
	if "--route-overview" in OS.get_cmdline_user_args() and not houses.has(here):
		size = 40.0
		target += Vector3(-6.0, 0, 12.0)
	_stop_camera_focus()
	if touch_gestures != null:
		touch_gestures.cancel_inertia()
	focus_tween = create_tween().set_parallel().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	focus_tween.tween_property(self, "cam_target", target + Vector3(0, 1.5, 0), 0.8)
	focus_tween.tween_property(cam, "size", size, 0.8)

func _make_house(at: Vector3) -> Node3D:
	return visuals.make_house(at)

func _make_place(id: String, at: Vector3) -> Node3D:
	return visuals.make_place(id, at)

func _lay_city(grid: Array) -> void:
	visuals.build(grid)

# ---------------------------------------------------------------- actions on the map

func _draw_actions(street: String) -> void:
	for b in buttons:
		b.queue_free()
	buttons.clear()
	anchors.clear()
	navigation.clear()
	for child in navigation_markers.get_children():
		child.queue_free()
	taxi_choices.clear()
	district_choices.clear()
	var end_key: Array = []
	for opt in view["options"]:
		var key: Array = opt[0]
		var text: String = opt[1]
		if key[0] == "end":
			end_key = key
			continue
		if key[0] == "move" and text.begins_with("Taxi") and view["places"][key[1]]["street"] == null:
			taxi_choices.append({"label": view["places"][key[1]]["label"], "hint": "Taxi · zone (1 PA)", "callback": _play_option.bind(key.duplicate(true))})
	var current: String = view["place"]
	var spot: Vector3 = houses[current].position + Vector3(0, 0.15, 1.0) if houses.has(current) else _world(street)
	var outdoor := current in ["victim_street", "alley"]
	var has_local_action: bool = not view["present"].is_empty()
	for option in view["options"]:
		if not option[0][0] in ["move", "walk", "end"]:
			has_local_action = true
	var local_marker: Node3D
	if not outdoor or has_local_action:
		navigation.add_destination(spot, "Explorer" if outdoor else "Entrer", view["places"][current]["label"], _open_interior, true)
		navigation.entries[-1]["region"] = street
		local_marker = visuals.navigation_marker(spot, true)
		local_marker.set_meta("region", street)
		navigation_markers.add_child(local_marker)
	var doors := _door_choices(street)
	if not doors.is_empty():
		var at := _world(street) + Vector3(2.0, 0, 0.3)
		navigation.add_destination(at, "Entrées", "Appartements du quartier", navigation.show_choices.bind("Entrées · " + str(view["places"][street]["label"]), doors))
		navigation.entries[-1]["region"] = street
		local_marker = visuals.navigation_marker(at)
		local_marker.set_meta("region", street)
		navigation_markers.add_child(local_marker)
	if view.has("routes"):
		for dest in view["routes"]:
			var route: Dictionary = view["routes"][dest]
			if route["cost"] == 0 or dest == street or view["places"][dest]["street"] != null:
				continue
			var cost: int = route["cost"]
			var available: bool = route["available"]
			var reason: String = route["reason"]
			if reason == "too_far" or cost > int(view["ap"]):
				continue
			if not available:
				continue
			var callback := _play_option.bind(route["key"].duplicate(true))
			var locations := _district_locations(dest)
			navigation.add_district(nodes[dest].position + Vector3(0, 1.8, 0), _district_title(dest), locations, cost, callback, dest)
			district_choices.append({"label": _district_title(dest), "hint": "%d PA · %s" % [cost, view["places"][dest]["label"]], "callback": callback})
	end_button.disabled = end_key.is_empty()
	end_button.set_meta("key", end_key)
	var end_style: StyleBoxFlat = interface_theme.get_stylebox("normal", "Button").duplicate()
	if int(view["ap"]) == 0 and not end_key.is_empty():
		end_style.border_color = Color("ffd386")
		end_style.set_border_width_all(2)
	end_button.add_theme_stylebox_override("normal", end_style)
	taxi_btn.visible = not taxi_choices.is_empty()
	district_button.disabled = district_choices.is_empty()
	navigation_hint.visible = board_enabled or not phone_ui
	navigation_hint.text = "Glissez · Zoomez · Touchez un halo pour parler" if interior.visible else "Quartiers · Entrées sur place · Glissez pour explorer"
	for actor in detectives:
		var avatar := VoxelAvatar.new()
		avatar.detective = true
		avatar.accent = actor.get_meta("color")
		navigation.add_actor(actor.position + Vector3(0, 1.8, 0), actor.get_meta("name"), avatar, actor.get_meta("you"), actor)

func _district_title(region: String) -> String:
	if region == "crime_scene" and view.has("crime_site"):
		return view.crime_site.get("district", "Quartier du Canal")
	return DISTRICT_NAMES.get(region, "Quartier · " + str(view["places"][region]["label"]))

func _district_locations(region: String) -> Array:
	var locations := [view["places"][region]["label"]]
	for place in view["places"]:
		if view["places"][place]["street"] == region:
			locations.append(view["places"][place]["label"])
	return locations

func _door_choices(region: String) -> Array:
	var choices := []
	if view["place"] != region:
		var route: Dictionary = view.get("routes", {}).get(region, {})
		if route.get("available", false):
			choices.append({"label": "Sortir dans le quartier", "hint": "(%d PA)" % route.cost, "callback": _play_option.bind(route.key.duplicate(true))})
	for place in view["places"]:
		if view["places"][place]["street"] != region:
			continue
		if place == view["place"]:
			choices.append({"label": view["places"][place]["label"], "hint": "Entrer", "callback": _open_interior})
			continue
		var route: Dictionary = view.get("routes", {}).get(place, {})
		var available: bool = route.get("available", false)
		var callback := _enter_place.bind(place, route.key.duplicate(true)) if available else Callable()
		var hint := "Entrer (%d PA)" % route.get("cost", 1) if available else "Indisponible"
		for option in view["options"]:
			if option[0][0] == "ring" and "house_" + str(int(option[0][1])) == place:
				available = true
				hint = "Sonner (1 PA)"
				callback = _play_local.bind(option[0].duplicate(true))
		choices.append({"label": view["places"][place]["label"], "hint": hint, "available": available, "callback": callback})
	return choices

func _enter_place(place: String, key: Array) -> void:
	enter_requested = place
	_send({"type": "play", "key": key})

func _play_option(key: Array) -> void:
	enter_requested = ""
	interior.hide()
	dialogue.hide()
	touch_gestures.cancel_inertia()
	_send({"type": "play", "key": key})

func _play_local(key: Array) -> void:
	if key[0] in ["interrogate", "ring"] and not dialogue.visible:
		var person := {"id": int(key[1]), "name": null, "look": ""}
		for candidate in view["present"]:
			if int(candidate.id) == int(key[1]):
				person = candidate
		dialogue.preview(person, [])
		dialogue.waiting = true
		dialogue.choices_scroll.hide()
		dialogue.next_button.disabled = true
		dialogue.set_busy_hint("Approchez votre interlocuteur…")
	_send({"type": "play", "key": key})

func _world(place: String) -> Vector3:
	return nodes[place].position + nodes[place].get_meta("entrance", Vector3(0, 0.25, 3.35))

func _anchor(place: String) -> Vector2:
	return cam.unproject_position(_world(place))

func _house_of(sid) -> String:
	# apartments are keyed by their owner's id in the engine: house_<id>
	var h := "house_%d" % int(sid)
	return h if houses.has(h) else ""

func _add_button(text: String, color: Color, at: Vector2, key: Array, pulse: bool, anchor: Array = []) -> Button:
	var btn := Button.new()
	btn.theme = interface_theme
	btn.text = text
	btn.position = at
	if anchor:
		anchors[btn] = anchor
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("0c1b2a").lerp(color, 0.14)
	sb.border_color = color
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(3)
	sb.content_margin_left = 8
	sb.content_margin_right = 8
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	btn.add_theme_stylebox_override("normal", sb)
	var hover := sb.duplicate()
	hover.bg_color = Color("0c1b2a").lerp(color, 0.4)
	btn.add_theme_stylebox_override("hover", hover)
	btn.pressed.connect(func(): if key.size(): _play_local(key))
	hud.add_child(btn)
	buttons.append(btn)
	if pulse:  # a slow breathing to say "you can do this"
		var tween := btn.create_tween().set_loops()  # bound to the button: dies with it
		tween.tween_property(btn, "modulate:a", 0.55, 0.7).set_trans(Tween.TRANS_SINE)
		tween.tween_property(btn, "modulate:a", 1.0, 0.7).set_trans(Tween.TRANS_SINE)
	return btn

# ---------------------------------------------------------------- hud and notebook page

# ---------------------------------------------------------------- setup page

func _show_setup() -> void:
	if setup_page != null:
		return
	var setup: Dictionary = view["setup"]
	setup_page = _page("Préparez votre enquête")
	var column: VBoxContainer = setup_page.get_child(0)
	setup_scroll = ScrollContainer.new()
	setup_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	setup_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	column.add_child(setup_scroll)
	var body := VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 12)
	setup_scroll.add_child(body)
	var items_title := Label.new()
	items_title.text = "Choisissez %d objets ou compétences" % setup["slots"]
	body.add_child(items_title)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 8)
	body.add_child(grid)
	for id in setup["items"]:
		var btn := Button.new()
		btn.custom_minimum_size = Vector2(220, 96 if phone_ui else 80)
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		btn.tooltip_text = setup["items"][id]
		btn.toggle_mode = true
		var caption := Label.new()
		caption.text = setup["items"][id]
		caption.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		caption.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		caption.mouse_filter = Control.MOUSE_FILTER_IGNORE
		caption.add_theme_font_size_override("font_size", 16 if phone_ui else 14)
		btn.add_child(caption)
		caption.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		caption.offset_left = 14
		caption.offset_right = -14
		caption.offset_top = 8
		caption.offset_bottom = -8
		btn.toggled.connect(func(on: bool): _pick_item(id, on))
		grid.add_child(btn)
		item_buttons[id] = btn
	var starts_title := Label.new()
	starts_title.text = "\nPoint de départ"
	body.add_child(starts_title)
	var row := GridContainer.new()
	row.columns = 4
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(row)
	var all_starts: Array = setup["free_starts"].duplicate()
	all_starts.append_array(setup["paid_starts"].keys())
	for place in all_starts:
		var btn := Button.new()
		btn.text = view["places"][place]["label"]
		btn.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		btn.custom_minimum_size = Vector2(160, 72 if phone_ui else 56)
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		btn.toggle_mode = true
		btn.toggled.connect(func(on: bool): _pick_start(place, on))
		row.add_child(btn)
		start_buttons[place] = btn
	start_btn = Button.new()
	start_btn.text = "Commencer"
	start_btn.custom_minimum_size.y = 72 if phone_ui else 56
	start_btn.disabled = true
	start_btn.pressed.connect(_start_game)
	column.add_child(start_btn)
	_refresh_setup()

func _pick_item(id: String, on: bool) -> void:
	if on:
		chosen.append(id)
	else:
		chosen.erase(id)
	_refresh_setup()

func _pick_start(place: String, on: bool) -> void:
	start_choice = place if on else ""
	for other in start_buttons:
		if other != place:
			start_buttons[other].set_pressed_no_signal(false)
	_refresh_setup()

func _refresh_setup() -> void:
	var setup: Dictionary = view["setup"]
	var full: bool = chosen.size() >= int(setup["slots"])
	for id in item_buttons:
		item_buttons[id].disabled = full and id not in chosen
	for place in start_buttons:
		var allowed: bool = place in setup["free_starts"] or chosen.has(setup["paid_starts"].get(place, ""))
		start_buttons[place].disabled = not allowed
		if not allowed and start_choice == place:
			start_choice = ""
			start_buttons[place].set_pressed_no_signal(false)
	start_btn.disabled = not (full and start_choice != "")

func _start_game() -> void:
	equipped = true
	_send({"type": "equip", "items": chosen, "start": start_choice})
	setup_page.queue_free()
	setup_page = null

func _page(title_text: String) -> PanelContainer:
	# a full page over everything, opaque, with a column inside
	var page := PanelContainer.new()
	page.theme = interface_theme
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("0c1726")
	sb.border_color = Color("397c90")
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(24)
	page.add_theme_stylebox_override("panel", sb)
	page.anchor_right = 1.0
	page.anchor_bottom = 1.0
	page.offset_left = 16
	page.offset_top = 16
	page.offset_right = -16
	page.offset_bottom = -16
	var top := CanvasLayer.new()
	top.layer = 3
	add_child(top)
	top.add_child(page)
	var column := VBoxContainer.new()
	page.add_child(column)
	var title := Label.new()
	title.text = title_text
	title.add_theme_font_size_override("font_size", 28)
	column.add_child(title)
	return page

func _build_hud() -> void:
	var theme := Theme.new()
	theme.default_font_size = 18 if phone_ui else 16
	theme.set_color("font_color", "Label", Color("d1e6ec"))
	theme.set_color("font_color", "Button", Color("d1e6ec"))
	for state in ["normal", "hover", "pressed", "disabled", "focus"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color("122638") if state == "normal" else Color("214357")
		if state == "disabled":
			style.bg_color = Color("101b27")
		style.border_color = Color("427689")
		style.set_border_width_all(1)
		style.set_corner_radius_all(3)
		style.set_content_margin_all(12)
		theme.set_stylebox(state, "Button", style)
	interface_theme = theme
	hud = CanvasLayer.new()
	hud.layer = 1
	add_child(hud)
	navigation = CityNavigation.new()
	navigation.camera = cam
	navigation.phone_ui = phone_ui
	navigation.theme = interface_theme
	hud.add_child(navigation)
	navigation_markers = Node3D.new()
	add_child(navigation_markers)
	header = Label.new()
	header.theme = interface_theme
	header.add_theme_font_size_override("font_size", 18 if phone_ui else 16)
	header.position = Vector2(22, 16)
	header.add_theme_color_override("font_color", Color("8cc6d7"))
	hud.add_child(header)
	qte = ProgressBar.new()
	qte.visible = false
	var challenge_layer := CanvasLayer.new()
	challenge_layer.layer = 8 # Also above the city phase if an owner returns home.
	add_child(challenge_layer)
	challenge_layer.add_child(qte)
	qte.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	qte.offset_left = -200
	qte.offset_right = 200
	qte.offset_top = -136
	qte.offset_bottom = -108
	qte_button = Button.new()
	qte_button.theme = interface_theme
	qte_button.visible = false
	challenge_layer.add_child(qte_button)
	qte_button.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	qte_button.offset_left = -200
	qte_button.offset_right = 200
	qte_button.offset_top = -100
	qte_button.offset_bottom = -24
	qte_button.pressed.connect(func(): _answer_qte(1.0 if qte_t < 0.7 else 0.6 if qte_t < 1.4 else 0.25))
	cards = VBoxContainer.new()
	cards.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	cards.add_theme_constant_override("separation", 8)
	notification_layer = CanvasLayer.new()
	notification_layer.layer = 5
	add_child(notification_layer)
	notification_scroll = ScrollContainer.new()
	notification_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	notification_scroll.mouse_filter = Control.MOUSE_FILTER_PASS
	notification_layer.add_child(notification_scroll)
	notification_scroll.add_child(cards)
	_mount_notifications(false)
	_build_interior()
	taxi_btn = Button.new()
	taxi_btn.theme = interface_theme
	var dock := HBoxContainer.new()
	dock.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	dock.offset_left = -578
	dock.offset_top = -92 if phone_ui else -76
	dock.offset_right = -24
	dock.offset_bottom = -20
	dock.add_theme_constant_override("separation", 10)
	dock.alignment = BoxContainer.ALIGNMENT_END
	hud.add_child(dock)
	taxi_btn.text = "Taxi"
	taxi_btn.custom_minimum_size = Vector2(100, 72 if phone_ui else 56)
	taxi_btn.pressed.connect(func(): navigation.show_choices("Taxi · destinations", taxi_choices))
	dock.add_child(taxi_btn)
	district_button = Button.new()
	district_button.theme = interface_theme
	district_button.text = "Quartiers"
	district_button.custom_minimum_size = Vector2(110, 72 if phone_ui else 56)
	district_button.pressed.connect(func(): navigation.show_choices("Quartiers accessibles", district_choices))
	dock.add_child(district_button)
	var carnet := Button.new()
	carnet.theme = interface_theme
	carnet.text = "Carnet"
	carnet.custom_minimum_size = Vector2(110, 72 if phone_ui else 56)
	carnet.pressed.connect(func(): notebook_page.visible = not notebook_page.visible)
	dock.add_child(carnet)
	end_button = Button.new()
	end_button.theme = interface_theme
	end_button.text = "Terminer le tour"
	end_button.disabled = true # No action until the engine supplies a legal key.
	end_button.custom_minimum_size = Vector2(204, 72 if phone_ui else 56)
	end_button.pressed.connect(_finish_turn)
	dock.add_child(end_button)
	navigation_hint = Label.new()
	navigation_hint.visible = board_enabled or not phone_ui
	navigation_hint.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	navigation_hint.offset_left = 24
	navigation_hint.offset_top = -36 if phone_ui else -62
	navigation_hint.add_theme_color_override("font_color", Color("92b4c3"))
	navigation_hint.add_theme_font_size_override("font_size", 11 if phone_ui else 13)
	hud.add_child(navigation_hint)
	# the notebook: a page over everything, opened by the button
	notebook_page = PanelContainer.new()
	notebook_page.theme = interface_theme
	notebook_page.visible = false
	var page := StyleBoxFlat.new()  # an opaque page: the city stays behind
	page.bg_color = Color("0c1726")
	page.border_color = Color("397c90")
	page.set_border_width_all(2)
	page.set_corner_radius_all(8)
	page.set_content_margin_all(24)
	notebook_page.add_theme_stylebox_override("panel", page)
	notebook_page.anchor_right = 1.0
	notebook_page.anchor_bottom = 1.0
	notebook_page.offset_left = 16
	notebook_page.offset_top = 16
	notebook_page.offset_right = -16
	notebook_page.offset_bottom = -16
	var top := CanvasLayer.new()  # above the action buttons and the interior, and it swallows clicks
	top.layer = 4
	add_child(top)
	top.add_child(notebook_page)
	var column := VBoxContainer.new()
	notebook_page.add_child(column)
	var title := Label.new()
	title.text = "Carnet"
	title.add_theme_font_size_override("font_size", 28)
	var notebook_heading := HBoxContainer.new()
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	notebook_heading.add_child(title)
	var zone_toggle := CheckButton.new()
	zone_toggle.text = "Frontières · essai"
	zone_toggle.custom_minimum_size.y = 48
	zone_toggle.button_pressed = board_enabled
	zone_toggle.toggled.connect(func(enabled):
		board_enabled = enabled
		board_zones.visible = enabled
		if not view.is_empty() and not view.has("setup"):
			var here: String = view["place"]
			var street = view["places"][here]["street"]
			_draw_actions(here if street == null else street))
	notebook_heading.add_child(zone_toggle)
	column.add_child(notebook_heading)
	notebook_summary = Label.new()
	notebook_summary.add_theme_font_size_override("font_size", 14)
	notebook_summary.add_theme_color_override("font_color", Color("89b5c5"))
	column.add_child(notebook_summary)
	var tabs := HBoxContainer.new()
	tabs.add_theme_constant_override("separation", 10)
	column.add_child(tabs)
	for id in ["people", "leads", "notes"]:
		var tab := Button.new()
		tab.toggle_mode = true
		tab.add_theme_color_override("font_pressed_color", Color("a5e8e2"))
		tab.text = {"people": "Personnes", "leads": "Pistes", "notes": "Notes"}[id]
		tab.custom_minimum_size.y = 44
		tab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		tab.pressed.connect(_set_notebook_tab.bind(id))
		notebook_tabs[id] = tab
		tabs.add_child(tab)
	notebook_scroll = ScrollContainer.new()
	notebook_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	notebook_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	column.add_child(notebook_scroll)
	var dossier := VBoxContainer.new()
	dossier.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dossier.add_theme_constant_override("separation", 14)
	notebook_scroll.add_child(dossier)
	notebook_dossier = VBoxContainer.new()
	notebook_dossier.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	notebook_dossier.add_theme_constant_override("separation", 14)
	dossier.add_child(notebook_dossier)
	notebook_notes = VBoxContainer.new()
	notebook_notes.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	notebook_notes.add_theme_constant_override("separation", 12)
	dossier.add_child(notebook_notes)
	notebook_leads = VBoxContainer.new()
	notebook_leads.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	notebook_leads.add_theme_constant_override("separation", 14)
	dossier.add_child(notebook_leads)
	_set_notebook_tab("people")
	notebook_evidence = VBoxContainer.new()
	notebook_dossier.add_child(notebook_evidence)
	notebook_grid = GridContainer.new()
	notebook_grid.columns = 2
	notebook_grid.add_theme_constant_override("h_separation", 12)
	notebook_grid.add_theme_constant_override("v_separation", 12)
	notebook_dossier.add_child(notebook_grid)
	var footer := HBoxContainer.new()
	column.add_child(footer)
	var close := Button.new()
	close.text = "Fermer"
	close.custom_minimum_size.y = 56 if phone_ui else 48
	close.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	close.pressed.connect(func(): notebook_page.visible = false)
	footer.add_child(close)
	if solo_mode:
		new_case_button = Button.new()
		new_case_button.text = "Nouvelle enquête · solo"
		new_case_button.custom_minimum_size.y = 56
		new_case_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		footer.add_child(new_case_button)
		restart_dialog = ConfirmationDialog.new()
		restart_dialog.theme = interface_theme
		restart_dialog.title = "Nouvelle enquête"
		restart_dialog.dialog_text = "Remplacer la partie solo sauvegardée par une nouvelle enquête ?"
		restart_dialog.ok_button_text = "Nouvelle enquête"
		restart_dialog.cancel_button_text = "Garder ma partie"
		restart_dialog.get_ok_button().custom_minimum_size.y = 72 if phone_ui else 56
		restart_dialog.get_cancel_button().custom_minimum_size.y = 72 if phone_ui else 56
		add_child(restart_dialog)
		new_case_button.pressed.connect(func(): restart_dialog.popup_centered(Vector2i(640, 260)))
		restart_dialog.confirmed.connect(func(): _send({"type": "restart"}))
	var conversation_layer := CanvasLayer.new()
	conversation_layer.layer = 4
	add_child(conversation_layer)
	dialogue = RPGDialogue.new()
	dialogue.phone_ui = phone_ui
	dialogue.ui_theme = interface_theme
	conversation_layer.add_child(dialogue)
	dialogue.action_selected.connect(_play_local)
	dialogue.closed.connect(_on_dialogue_closed)
	case_toasts = CaseToasts.new()
	notification_layer.add_child(case_toasts)
	var travel_layer := CanvasLayer.new()
	travel_layer.layer = 2
	add_child(travel_layer)
	region_transition = RegionTransition.new()
	travel_layer.add_child(region_transition)
	var turn_layer := CanvasLayer.new()
	turn_layer.layer = 7
	add_child(turn_layer)
	turn_transition = TurnTransition.new()
	turn_layer.add_child(turn_transition)
	turn_transition.midpoint.connect(func():
		interior.hide()
		dialogue.hide()
		touch_gestures.cancel_inertia()
		_mount_notifications(false)
		if not end_key_pending.is_empty():
			var key := end_key_pending.duplicate()
			end_key_pending.clear()
			_send({"type": "play", "key": key}))

# ---------------------------------------------------------------- inside a place

func _build_interior() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 1
	add_child(layer)
	interior = Control.new()
	interior.theme = interface_theme
	interior.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	interior.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(interior)
	interior.hide()
	interior_title = Label.new()
	interior_title.position = Vector2(24, 76)
	interior_title.add_theme_font_size_override("font_size", 20)
	interior_title.modulate = Color("ffc17c")
	interior_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	interior.add_child(interior_title)
	interior_box = HBoxContainer.new()
	interior_box.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	interior_box.offset_left = 24
	interior_box.offset_right = 250
	interior_box.offset_top = -150
	interior_box.offset_bottom = -98
	interior.add_child(interior_box)
	lounge = preload("res://interior_lounge.gd").new()
	lounge.camera = cam
	lounge.overlay = interior
	lounge.position = Vector3(2048, 0, 2048)
	lounge.scale = Vector3.ONE * 1.5
	lounge.hide()
	add_child(lounge)
	lounge.person_selected.connect(_select_person)
	var leave := Button.new()
	leave.text = "Sortir  ›"
	leave.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	leave.offset_left = -184
	leave.offset_right = -24
	leave.offset_top = 24
	leave.offset_bottom = 80
	leave.custom_minimum_size = Vector2(160, 56)
	leave.pressed.connect(func(): interior.visible = false; dialogue.hide(); _mount_notifications(false))
	interior.add_child(leave)
	interior.visibility_changed.connect(_sync_interior_scene)

func _sync_interior_scene() -> void:
	if lounge == null:
		return
	lounge.visible = interior.visible
	navigation.visible = not interior.visible
	if view.is_empty() or view.has("setup"):
		return
	_stop_camera_focus()
	if touch_gestures != null:
		touch_gestures.cancel_inertia()
	if interior.visible:
		exterior_far = cam.far
		inside_scene = true
		cam.far = 160.0
		cam_target = lounge.global_position + Vector3(0, 2.25, 0)
		cam.size = 27.0
	elif inside_scene:
		inside_scene = false
		cam.far = exterior_far
		var here: String = view.place
		var target: Node3D = houses[here] if houses.has(here) else nodes[here]
		cam_target = target.position + Vector3(0, 1.5, 0)
		cam.size = 17.0 if houses.has(here) else 18.0
	_update_camera()
	navigation_hint.text = "Glissez · Zoomez · Touchez un halo pour parler" if interior.visible else "Quartiers · Entrées sur place · Glissez pour explorer"

func _open_interior() -> void:
	interior.visible = true
	_mount_notifications(false)
	_draw_interior()

func _mount_notifications(inside: bool) -> void:
	if not inside:
		if notification_scroll.get_parent() != notification_layer:
			notification_scroll.reparent(notification_layer)
		notification_scroll.custom_minimum_size = Vector2.ZERO
		notification_scroll.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
		notification_scroll.offset_left = -384
		notification_scroll.offset_right = -24
		notification_scroll.offset_top = 20
		notification_scroll.offset_bottom = 180

func _draw_interior() -> void:
	var here: String = view["place"]
	interior_title.text = view["places"][here]["label"]
	person_buttons.clear()
	for c in interior_box.get_children():
		interior_box.remove_child(c)
		c.queue_free()
	lounge.populate(view)
	person_buttons = lounge.person_buttons
	var options: Array = view["options"]
	var taken := {}  # option index -> shown under a person
	for person in view["present"]:
		for i in options.size():
			var key: Array = options[i][0]
			if key.size() > 1 and key[0] in ["interrogate", "confront", "talk_about", "observe"] and int(key[1]) == int(person["id"]):
				taken[i] = true
	var local_actions := []
	for i in options.size():
		var key: Array = options[i][0]
		if taken.has(i) or key[0] in ["move", "walk", "end", "ask", "stop"]:
			continue
		local_actions.append(options[i])
	if local_actions.size() == 1:
		interior_box.add_child(_action_button(local_actions[0], false))
	elif not local_actions.is_empty():
		var actions_button := Button.new()
		actions_button.text = "Actions du lieu…"
		actions_button.custom_minimum_size = Vector2(226, 52)
		actions_button.pressed.connect(_open_action_folder.bind("Actions du lieu", local_actions))
		interior_box.add_child(actions_button)

func _open_action_folder(title: String, actions: Array) -> void:
	dialogue.preview({"name": title, "look": "", "id": 0, "detective": true}, actions)

func _select_person(person: Dictionary) -> void:
	selected_person = person.duplicate(true)
	if view.get("pending") != null:
		var cue = view.get("conversation")
		if cue != null and int(cue.person.id) == int(person.id):
			dialogue.show_cue(cue, view.options)
		return
	var actions := []
	for option in view["options"]:
		var key: Array = option[0]
		if key.size() > 1 and key[0] in ["interrogate", "confront", "talk_about", "observe", "verify", "accuse", "file", "record"] and int(key[1]) == int(person.id):
			if key[0] == "interrogate":
				_play_local(key.duplicate(true))
				return
			var label := "Parler (1 PA)" if key[0] == "interrogate" else str(option[1])
			actions.append([key.duplicate(true), label])
	dialogue.preview(person, actions)

func _on_dialogue_closed() -> void:
	selected_person.clear()
	if interior.visible:
		_draw_interior()
	_check_exhausted()

func _check_exhausted() -> void:
	if view.is_empty() or view.has("setup") or view.get("pending") != null or view.get("winner") != null:
		return
	if int(view["ap"]) == 0 and not end_button.disabled and int(view["tick"]) != exhausted_tick:
		exhausted_tick = int(view["tick"])
		turn_transition.play("ACTIONS ÉPUISÉES", "Appuyez sur « Terminer le tour » quand vous êtes prêt.")

func _action_button(opt: Array, pulse: bool) -> Button:
	var key: Array = opt[0]
	var family: String = FAMILY.get(key[0], "office")
	var text: String = opt[1]
	if key[0] == "interrogate":
		text = "Interroger"
	elif key[0] == "observe":
		text = "Observer de plus près"
	var btn := _add_button(STYLE[family][1] + " " + text, STYLE[family][0], Vector2.ZERO, key, pulse)
	hud.remove_child(btn)
	buttons.erase(btn)
	btn.custom_minimum_size = Vector2(0, 72 if phone_ui else 56)
	btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	btn.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	btn.add_theme_font_size_override("font_size", 14)
	return btn

func _figure(person: Dictionary) -> Control:
	var avatar := VoxelAvatar.new()
	avatar.look = person["look"]
	avatar.identity = int(person["id"])
	return avatar

func _draw_notebook() -> void:
	for container in [notebook_grid, notebook_evidence]:
		for child in container.get_children():
			container.remove_child(child)
			child.queue_free()
	notebook_cards.clear()
	_draw_notebook_notes()
	_draw_notebook_leads()
	var rows: Array = view["notebook"].duplicate(true)
	for i in rows.size():
		rows[i]["display_order"] = i
	var known := 0
	for row in rows:
		if row.name != "?":
			known += 1
	notebook_summary.text = "%d / %d personnes identifiées   ·   %d preuves établies" % [known, rows.size(), view["facts"].size()]
	var evidence_toggle := Button.new()
	evidence_toggle.text = "PREUVES & SOURCES FIABLES   ▾"
	evidence_toggle.custom_minimum_size.y = 48
	notebook_evidence.add_child(evidence_toggle)
	var evidence_body := VBoxContainer.new()
	evidence_body.visible = false
	notebook_evidence.add_child(evidence_body)
	evidence_toggle.pressed.connect(func(): evidence_body.visible = not evidence_body.visible)
	_notebook_text(evidence_body, "PREUVES ÉTABLIES", ", ".join(view["facts"]) if not view["facts"].is_empty() else "Aucune preuve recueillie pour le moment.", Color("8fd6d1"))
	if not view["trusted"].is_empty():
		_notebook_text(evidence_body, "TÉMOIGNAGES FIABLES", ", ".join(view["trusted"]), Color("8fd6d1"))
	rows.sort_custom(func(a, b):
		if (a.name == "?") != (b.name == "?"):
			return a.name != "?"
		return int(a.display_order) < int(b.display_order))
	for row in rows:
		var identified: bool = row.name != "?"
		var card := PanelContainer.new()
		card.custom_minimum_size.x = 380 if phone_ui else 440
		card.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var style := StyleBoxFlat.new()
		style.bg_color = Color("122536") if identified else Color("0d1e2d")
		style.border_color = Color("b69366") if identified else Color("294353")
		style.border_width_left = 3
		style.set_corner_radius_all(6)
		style.set_content_margin_all(14)
		card.add_theme_stylebox_override("panel", style)
		notebook_grid.add_child(card)
		notebook_cards[int(row.id)] = card
		var body := VBoxContainer.new()
		body.add_theme_constant_override("separation", 10)
		card.add_child(body)
		var top := HBoxContainer.new()
		top.add_theme_constant_override("separation", 14)
		body.add_child(top)
		var avatar := VoxelAvatar.new()
		avatar.identity = int(row.id)
		avatar.unknown = not identified
		avatar.look = " ".join(row.traits.values())
		avatar.custom_minimum_size = Vector2(64, 76)
		avatar.set_meta("notebook_portrait", true)
		top.add_child(avatar)
		var identity_box := VBoxContainer.new()
		identity_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		top.add_child(identity_box)
		var name_label := Label.new()
		name_label.text = row.name if identified else "Individu non identifié"
		name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		name_label.add_theme_font_size_override("font_size", 19 if identified else 16)
		name_label.add_theme_color_override("font_color", Color("edd2a7") if identified else Color("79929e"))
		identity_box.add_child(name_label)
		var status := Label.new()
		status.text = "ALIBI CONFIRMÉ" if row.alibi == "confirmé" else "ALIBI À VÉRIFIER" if row.alibi == "à vérifier" else "PISTE OUVERTE" if identified else "À IDENTIFIER"
		status.add_theme_font_size_override("font_size", 11)
		status.add_theme_color_override("font_color", Color("d9aa73") if identified else Color("647e8c"))
		identity_box.add_child(status)
		var exclude := Button.new()
		exclude.custom_minimum_size = Vector2(96, 48)
		exclude.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		exclude.add_theme_font_size_override("font_size", 13)
		exclude.set_meta("suspect_note", int(row.id))
		exclude.pressed.connect(_toggle_suspect_note.bind(int(row.id)))
		top.add_child(exclude)
		card.set_meta("note_button", exclude)
		card.set_meta("status_label", status)
		card.set_meta("original_status", status.text)
		_update_suspect_card(int(row.id))
		if not identified:
			continue
		var home = row.get("home")
		if home is Dictionary and view["places"].has(home.get("region", "")):
			var address_heading := Label.new()
			address_heading.text = "DOMICILE · TOUCHER POUR REPÉRER"
			address_heading.add_theme_font_size_override("font_size", 11)
			address_heading.add_theme_color_override("font_color", Color("89b5c5"))
			body.add_child(address_heading)
			var address := Button.new()
			address.text = "%s\n%s" % [_district_title(home.region), home.label]
			address.custom_minimum_size.y = 56
			address.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			address.add_theme_font_size_override("font_size", 14)
			address.add_theme_color_override("font_color", Color("a5dadd"))
			address.tooltip_text = "Repérer le quartier sur la carte · sans déplacement ni PA"
			address.set_meta("residence", home.duplicate(true))
			address.pressed.connect(_locate_residence.bind(home.duplicate(true)))
			body.add_child(address)
			card.set_meta("home_button", address)
		var traits := []
		for trait_key in row.traits:
			traits.append("%s : %s" % [trait_key.capitalize(), row.traits[trait_key]])
		if not traits.is_empty():
			_notebook_text(body, "PORTRAIT", "  ·  ".join(traits), Color("b1c4ce"))
		var life = row.get("life")
		if life is Dictionary:
			_notebook_text(body, "PROJET & PRESSION · À RECOUPER", "Projet : %s\nPression : %s" % [life.goal, life.pressure], Color("d9aa73"))
		var relationship = row.get("relationship")
		if relationship is Dictionary:
			var link_text := "Sa déclaration : %s" % (relationship.claim if relationship.claim != null else "pas encore demandé")
			if not relationship.witnesses.is_empty():
				link_text += "\nSelon %s : %s" % [", ".join(relationship.witnesses), relationship.reported]
			_notebook_text(body, "LIEN CONTESTÉ · À CONFRONTER" if relationship.contradiction else "LIEN AVEC LA VICTIME · SOURCES", link_text, Color("e4b27b"))
		if row.claim != null:
			_notebook_text(body, "ALIBI · " + str(row.alibi).to_upper(), str(row.claim).capitalize() + (" avec " + ", ".join(row["with"]) if not row["with"].is_empty() else ""), Color("b1c4ce"))
		if not row.said.is_empty():
			_notebook_text(body, "DÉCLARATIONS · NON PROUVÉES", "\n".join(row.said), Color("d9aa73"))
	_update_notebook_summary()

func _set_notebook_tab(id: String) -> void:
	notebook_tab = id
	notebook_dossier.visible = id == "people"
	notebook_notes.visible = id == "notes"
	notebook_leads.visible = id == "leads"
	for key in notebook_tabs:
		notebook_tabs[key].set_pressed_no_signal(key == id)
	if notebook_scroll != null:
		notebook_scroll.scroll_vertical = 0

func _draw_notebook_notes() -> void:
	for child in notebook_notes.get_children():
		notebook_notes.remove_child(child)
		child.queue_free()
	var journal: Array = view.get("journal", [])
	notebook_tabs.notes.text = "Notes · %d" % journal.size()
	var story: Dictionary = view.get("story", {})
	var object_label: String = str(story.object) if story.get("object") != null else "à découvrir"
	if story.get("object_status") == "not_reported":
		object_label = "aucune disparition signalée"
	elif story.get("object_status") == "found":
		object_label += " · retrouvé"
	elif story.get("object_status") == "unidentified":
		object_label += " · propriétaire à identifier"
	elif story.get("object_status") == "unrecovered":
		object_label += " · non récupérable"
	var overview := "Crime : %s · Objet : %s\nMobile : %s" % [story.get("window") if story.get("window") != null else "heure à établir", object_label, story.get("motive") if story.get("motive") != null else "à reconstituer — un soupçon ne suffit pas"]
	_notebook_text(notebook_notes, "REPRENDRE L'AFFAIRE", overview, Color("8fd6d1"))
	if journal.is_empty():
		_notebook_text(notebook_notes, "NOTES", "Vos découvertes et vos échanges apparaîtront ici.", Color("89b5c5"))
	for i in range(journal.size() - 1, -1, -1):
		var note: Dictionary = journal[i]
		var card := PanelContainer.new()
		card.set_meta("journal_id", note.id)
		var style := StyleBoxFlat.new()
		style.bg_color = Color("122536")
		style.border_color = Color("d5a56c") if note.kind in ["soupçon", "déclaration", "témoignage"] else Color("55b7c9")
		style.border_width_left = 3
		style.set_corner_radius_all(6)
		style.set_content_margin_all(14)
		card.add_theme_stylebox_override("panel", style)
		notebook_notes.add_child(card)
		var body := VBoxContainer.new()
		body.add_theme_constant_override("separation", 8)
		card.add_child(body)
		var source := Label.new()
		source.text = "TOUR %d · %s · %s" % [note.turn, str(note.kind).to_upper(), note.source]
		source.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		source.add_theme_font_size_override("font_size", 11)
		source.modulate = Color("89b5c5")
		body.add_child(source)
		_notebook_text(body, str(note.title).to_upper(), str(note.text), Color("edd2a7"))
		for place in note.get("leads", []):
			if not view.places.has(place):
				continue
			var lead := Button.new()
			lead.text = "Repérer · " + str(view.places[place].label)
			lead.custom_minimum_size.y = 44
			lead.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			lead.add_theme_font_size_override("font_size", 13)
			lead.tooltip_text = "Repérer une piste · caméra seulement, aucun PA"
			lead.set_meta("note_place", place)
			lead.pressed.connect(_locate_note_place.bind(str(place)))
			body.add_child(lead)

func _locate_note_place(place: String) -> void:
	var street = view.places[place].street
	_locate_residence({"region": place if street == null else street, "label": view.places[place].label})

func _draw_notebook_leads() -> void:
	for child in notebook_leads.get_children():
		notebook_leads.remove_child(child)
		child.queue_free()
	var leads: Array = view.get("leads", [])
	notebook_tabs.leads.text = "Pistes · %d" % leads.size()
	_notebook_text(notebook_leads, "VOTRE ENQUÊTE, VOS CHOIX", "Des chemins possibles, pas des ordres. Vous pouvez les suivre ou explorer librement. Un soupçon seul ne suffit jamais.", Color("8fd9d5"))
	if leads.is_empty():
		_notebook_text(notebook_leads, "PAR OÙ COMMENCER ?", "Relever le constat sur la scène extérieure, visiter le domicile de la victime ou rencontrer les habitants.", Color("d5ac77"))
	for item in leads:
		var card := PanelContainer.new()
		card.set_meta("lead_id", item.id)
		var style := StyleBoxFlat.new()
		style.bg_color = Color("122536")
		style.border_color = Color("59aaa9") if item.complete else Color("d9a269")
		style.border_width_left = 3
		style.set_corner_radius_all(8)
		style.set_content_margin_all(16)
		card.add_theme_stylebox_override("panel", style)
		notebook_leads.add_child(card)
		var body := VBoxContainer.new()
		body.add_theme_constant_override("separation", 8)
		card.add_child(body)
		_notebook_text(body, ("SOURCE RECUEILLIE · " if item.complete else "À EXPLORER · ") + str(item.title).to_upper(), str(item.reason) + "\n\n" + str(item.objective), Color("8fd9d5") if item.complete else Color("ebbe88"))
		var destinations := GridContainer.new()
		destinations.columns = 2
		destinations.add_theme_constant_override("h_separation", 8)
		destinations.add_theme_constant_override("v_separation", 8)
		body.add_child(destinations)
		for destination in item.destinations:
			var button := Button.new()
			button.text = "Repérer · " + str(destination.label)
			button.custom_minimum_size.y = 48
			button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			button.add_theme_font_size_override("font_size", 13)
			button.set_meta("lead_place", destination.place)
			button.pressed.connect(_locate_note_place.bind(str(destination.place)))
			destinations.add_child(button)

func _locate_residence(home: Dictionary) -> void:
	# This is a camera shortcut, not a move or a free apartment entrance.
	var region: String = home.get("region", "")
	if not nodes.has(region):
		return
	notebook_page.hide()
	interior.hide()
	navigation.close_sheet()
	_focus(region)
	case_toasts.note("Domicile repéré", "%s · %s" % [_district_title(region), home.label])

func _load_case_notes() -> void:
	var case_id := "solo:%s:%s" % [view.get("solo", {}).get("seed", SEED), view.get("player", NAME)] if solo_mode else "server:%s:%s" % [server_url, view.get("player", NAME)]
	if case_id == notes_case:
		return
	notes_case = case_id
	manual_exclusions.clear()
	var config := ConfigFile.new()
	if config.load(notes_path) == OK:
		var saved = config.get_value("suspects", notes_case, {})
		if saved is Dictionary:
			for id in saved:
				if saved[id] == true:
					manual_exclusions[str(id)] = true

func _toggle_suspect_note(id: int) -> void:
	var key := str(id)
	if manual_exclusions.has(key):
		manual_exclusions.erase(key)
	else:
		manual_exclusions[key] = true
	_update_suspect_card(id)
	_update_notebook_summary()
	var config := ConfigFile.new()
	var load_error := config.load(notes_path)
	if load_error != OK and load_error != ERR_FILE_NOT_FOUND:
		case_toasts.note("Notes personnelles illisibles", "Fichier conservé. Votre choix reste visible pour cette session.")
		return
	config.set_value("suspects", notes_case, manual_exclusions)
	if config.save(notes_path) != OK:
		case_toasts.note("Note non sauvegardée", "Votre choix reste visible pour cette session.")

func _update_suspect_card(id: int) -> void:
	if not notebook_cards.has(id):
		return
	var card: Control = notebook_cards[id]
	var excluded := manual_exclusions.has(str(id))
	card.modulate.a = 0.42 if excluded else 1.0
	card.get_meta("note_button").text = "Réactiver" if excluded else "Écarter"
	card.get_meta("note_button").tooltip_text = "Note personnelle uniquement · aucun effet sur les règles"
	card.get_meta("status_label").text = "ÉCARTÉ PAR VOUS" if excluded else card.get_meta("original_status")

func _update_notebook_summary() -> void:
	var identified := 0
	for row in view["notebook"]:
		if row.name != "?":
			identified += 1
	var notes_count := manual_exclusions.size()
	notebook_summary.text = "%d / %d identifiés · %d preuves · %d documents\n%d %s par vous" % [identified, view["notebook"].size(), view["facts"].size(), view.get("progress", {}).get("documents", 0), notes_count, "piste écartée" if notes_count == 1 else "pistes écartées"]

func _notebook_text(parent: Control, label: String, content: String, color: Color) -> void:
	var heading := Label.new()
	heading.text = label
	heading.add_theme_font_size_override("font_size", 11)
	heading.add_theme_color_override("font_color", color)
	parent.add_child(heading)
	var text := Label.new()
	text.text = content
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	text.add_theme_font_size_override("font_size", 14)
	text.add_theme_color_override("font_color", Color("c0d0d8"))
	parent.add_child(text)

func _finish_turn() -> void:
	if solo_busy or turn_transition.playing or qte_active or view.get("pending") != null:
		return
	var key: Array = end_button.get_meta("key", [])
	if key.is_empty():
		return
	end_key_pending = key.duplicate()
	turn_transition.phase()
