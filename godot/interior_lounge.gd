extends Node3D
## Shared, low-poly lounge. World truth comes only from the public view.
## Same 3D world and camera as the city; no modal or additional viewport.
signal person_selected(person: Dictionary)

const Geometry := preload("res://city_visuals.gd")
const CYAN := Color("63e1ec")
const PINK := Color("ee4985")
const GOLD := Color("ffc17c")
var camera: Camera3D
var overlay: Control
var stage: Node3D
var geometry: Node3D
var figures: Node3D
var exterior: Node3D
var blood: Node3D
var targets := []
var person_buttons := {}
var entries := []
var place := ""

func _ready() -> void:
	stage = self
	geometry = Geometry.new()
	stage.add_child(geometry)
	_build_room()
	_build_exterior()
	figures = Node3D.new()
	stage.add_child(figures)

func _build_exterior() -> void:
	exterior = Node3D.new()
	stage.add_child(exterior)
	geometry._begin()
	geometry._box(Vector3(0, -0.15, 0), Vector3(17, 0.3, 13), Color("21333e"))
	for x in range(-8, 9):
		for z in range(-6, 7):
			geometry._box(Vector3(x, 0.005, z), Vector3(0.97, 0.035, 0.97), Color("2c404b") if (x + z) % 2 else Color("293844"))
	geometry._box(Vector3(0, 1.2, -6.4), Vector3(17, 2.4, 0.3), Color("29333f"))
	for x in [-7, 7]:
		geometry._box(Vector3(x, 1.7, -4.0), Vector3(0.15, 3.4, 0.15), Color("626067"))
		geometry._box(Vector3(x, 3.3, -3.7), Vector3(0.3, 0.17, 0.6), GOLD, "light")
	geometry._box(Vector3(0, 1.65, -6.2), Vector3(4, 0.05, 0.1), CYAN, "light")
	geometry._flush(exterior, "OutdoorCourtyard")
	blood = Node3D.new()
	exterior.add_child(blood)
	geometry._begin()
	for drop in [[Vector3(-1.4, 0.04, 1.7), 0.3], [Vector3(-1.0, 0.04, 1.4), 0.17], [Vector3(-0.65, 0.04, 1.05), 0.12], [Vector3(-1.75, 0.04, 1.4), 0.16]]:
		geometry._box(drop[0], Vector3(drop[1], 0.012, drop[1] * 0.7), Color("a72a3e"))
	geometry._flush(blood, "BloodDrops")
	exterior.hide()

func _build_room() -> void:
	geometry._begin()
	geometry._box(Vector3(0, -0.22, 0), Vector3(17, 0.4, 13), Color("171726"))
	# Tile joints, dark cutaway walls, timber panelling and warm sconces.
	for x in range(-8, 9):
		for z in range(-6, 7):
			var tint := Color("292437") if (x + z) % 2 == 0 else Color("252232")
			var bar_glow := maxf(0.0, 1.0 - Vector2(x + 4.8, z + 1.8).length() / 3.7)
			var stage_glow := maxf(0.0, 1.0 - Vector2(x - 4.5, z + 2.0).length() / 3.8)
			tint = tint.lerp(Color("8b3052"), maxf(bar_glow, stage_glow) * 0.55)
			geometry._box(Vector3(x, 0.005, z), Vector3(0.97, 0.04, 0.97), tint)
	geometry._box(Vector3(0, 2.1, -6.4), Vector3(17, 4.2, 0.35), Color("2c2030"))
	geometry._box(Vector3(-8.3, 2.1, 0), Vector3(0.35, 4.2, 13), Color("2c2230"))
	for x in [-7.4, -3.0, 1.3, 7.5]:
		geometry._box(Vector3(x, 2.1, -6.15), Vector3(0.32, 4.2, 0.28), Color("67473e"))
		geometry._box(Vector3(x, 2.4, -5.92), Vector3(0.16, 0.44, 0.18), GOLD, "light")
		geometry._box(Vector3(x, 2.15, -5.98), Vector3(0.25, 0.10, 0.25), Color("896046"))
	for x in range(-8, 9):
		geometry._box(Vector3(x, 0.6, -6.12), Vector3(0.035, 1.1, 0.08), Color("684538"))
	geometry._box(Vector3(0, 1.25, -6.10), Vector3(16.5, 0.08, 0.08), Color("80583e"))
	# A few warm lanterns and voxel plants frame the cutaway without blocking it.
	for at in [Vector3(-7.6, 0, 4.8), Vector3(7.5, 0, -5.4)]:
		geometry._box(at + Vector3(0, 0.35, 0), Vector3(0.65, 0.7, 0.65), Color("493236"))
		geometry._box(at + Vector3(0, 1.15, 0), Vector3(0.12, 1.0, 0.12), Color("665442"))
		for branch in [Vector3(-0.3, 1.15, 0), Vector3(0.3, 1.55, 0.1), Vector3(0, 1.9, -0.15)]:
			geometry._box(at + branch, Vector3(0.6, 0.35, 0.5), Color("4c6650"))
	# Back bar: bottles, brass edge, narrow pink neon, four stools.
	geometry._box(Vector3(-5.0, 1.2, -3.9), Vector3(5.5, 2.4, 0.75), Color("211c30"))
	for shelf in [0.65, 1.55, 2.45]:
		geometry._box(Vector3(-5.0, shelf, -3.48), Vector3(5.5, 0.12, 0.7), Color("655047"))
		for i in 15:
			var tint: Color = [Color("a96349"), Color("397d6c"), Color("82805c"), Color("695584")][i % 4]
			geometry._box(Vector3(-7.4 + i * 0.35, shelf + 0.25, -3.6), Vector3(0.17, 0.38 + (i % 3) * 0.04, 0.17), tint)
	geometry._box(Vector3(-4.8, 0.73, -1.8), Vector3(5.7, 1.45, 0.85), Color("432534"))
	geometry._box(Vector3(-4.8, 1.5, -1.8), Vector3(6.1, 0.13, 1.15), Color("776053"))
	geometry._box(Vector3(-4.8, 1.29, -1.2), Vector3(5.8, 0.06, 0.08), PINK, "light")
	for x in [-6.8, -5.4, -4.0, -2.6]:
		geometry._box(Vector3(x, 0.48, -0.45), Vector3(0.13, 0.9, 0.13), Color("786653"))
		geometry._box(Vector3(x, 0.95, -0.45), Vector3(0.55, 0.13, 0.55), Color("632834"))
	# Raised stage and folded curtains: common room, not a full cabaret yet.
	geometry._box(Vector3(4.5, 0.25, -4.0), Vector3(6.3, 0.5, 3.8), Color("4b2939"))
	geometry._box(Vector3(4.5, 0.09, -1.87), Vector3(5.0, 0.18, 0.45), Color("4c3242"))
	geometry._box(Vector3(4.5, 0.52, -2.08), Vector3(6.3, 0.035, 0.09), GOLD, "light")
	for i in 24:
		geometry._box(Vector3(1.4 + i * 0.27, 2.1, -5.7 + (i % 2) * 0.13), Vector3(0.26, 3.2, 0.22), Color("702438") if i % 2 else Color("922c4c"))
	geometry._box(Vector3(4.5, 3.9, -5.45), Vector3(6.5, 0.18, 0.25), Color("9d593f"))
	for x in [1.4, 7.6]:
		geometry._box(Vector3(x, 2.15, -5.35), Vector3(0.035, 3.25, 0.06), PINK, "light")
	# Seating at the near-left, outside the suspect interaction lane.
	for at in [Vector3(-6.3, 0, 2.7), Vector3(-2.7, 0, 4.5)]:
		geometry._box(at + Vector3(0, 0.42, 0), Vector3(0.2, 0.84, 0.2), Color("5c4542"))
		geometry._box(at + Vector3(0, 0.9, 0), Vector3(1.65, 0.12, 1.15), Color("695042"))
		geometry._box(at + Vector3(0, 1.15, 0), Vector3(0.11, 0.4, 0.11), GOLD, "light")
		for offset in [-0.85, 0.85]:
			geometry._box(at + Vector3(offset, 0.45, 1.0), Vector3(0.7, 0.85, 0.55), Color("622a38"))
			geometry._box(at + Vector3(offset, 1.0, 1.22), Vector3(0.7, 0.7, 0.12), Color("752e43"))
	for x in [-6.8, -1.0, 6.8]:
		geometry._box(Vector3(x, 0.7, 6.0), Vector3(0.13, 1.4, 0.13), Color("6e5042"))
		geometry._box(Vector3(x, 1.52, 6.0), Vector3(0.20, 0.36, 0.20), GOLD, "light")
		geometry._box(Vector3(x, 1.75, 6.0), Vector3(0.32, 0.08, 0.32), Color("936244"))
	geometry._flush(geometry, "LoungeStatic")
	# Local lights without shadows. Draw-call cost is bounded, even on Android.
	for spec in [[Vector3(-4.5, 2.6, -1.4), PINK], [Vector3(4.5, 2.5, -3.8), PINK], [Vector3(-4.5, 2.6, 3.7), GOLD]]:
		var light := OmniLight3D.new()
		light.position = spec[0]
		light.light_color = spec[1]
		light.light_energy = 1.15
		light.omni_range = 7
		light.shadow_enabled = false
		stage.add_child(light)

func _actor(at: Vector3, look: String, id: int, detective: bool = false) -> Node3D:
	var root := Node3D.new()
	root.position = at
	figures.add_child(root)
	geometry._begin()
	var coat: Color = Color("32465a") if detective else [Color("685368"), Color("526662"), Color("77634d"), Color("596174")][absi(id) % 4]
	var hair := Color("3b3031") if "noirs" in look else Color("ab683e") if "roux" in look else Color("c2a272") if "blonds" in look else Color("644535")
	for x in [-0.17, 0.17]:
		geometry._box(Vector3(x, 0.32, 0), Vector3(0.24, 0.6, 0.27), Color("1c2331"))
		geometry._box(Vector3(x, 0.08, 0.10), Vector3(0.27, 0.16, 0.4), Color("17202b"))
	geometry._box(Vector3(0, 0.9, 0), Vector3(0.65, 0.65, 0.35), coat)
	for x in [-0.4, 0.4]:
		geometry._box(Vector3(x, 0.88, 0), Vector3(0.16, 0.58, 0.23), coat.darkened(0.12))
		geometry._box(Vector3(x, 0.60, 0), Vector3(0.14, 0.14, 0.22), Color("c2997e"))
	geometry._box(Vector3(0, 1.47, 0), Vector3(0.43, 0.45, 0.4), Color("c8a08a"))
	geometry._box(Vector3(0, 1.73, -0.015), Vector3(0.45, 0.15, 0.43), hair)
	if detective:
		geometry._box(Vector3(0, 1.77, 0), Vector3(0.56, 0.13, 0.5), Color("374252"))
		geometry._box(Vector3(0, 1.89, 0), Vector3(0.40, 0.2, 0.38), Color("354251"))
		geometry._box(Vector3(0, 1.82, 0.21), Vector3(0.42, 0.035, 0.03), CYAN, "light")
		geometry._box(Vector3(0, 0.7, 0), Vector3(0.7, 0.35, 0.36), coat)
	var tint: Color = CYAN if detective else GOLD
	for side in [-1, 1]:
		geometry._box(Vector3(side * 0.65, 0.06, 0), Vector3(0.08, 0.02, 1.1), tint, "guide")
		geometry._box(Vector3(0, 0.06, side * 0.55), Vector3(1.35, 0.02, 0.08), tint, "guide")
	geometry._flush(root, "Actor")
	return root

func populate(view: Dictionary) -> void:
	for child in figures.get_children():
		figures.remove_child(child)
		child.queue_free()
	for target in targets:
		target.button.queue_free()
	targets.clear()
	entries.clear()
	person_buttons.clear()
	place = view.place
	var outside := place in ["crime_scene", "alley", "victim_street"]
	geometry.visible = not outside
	exterior.visible = outside
	blood.visible = place == "crime_scene"
	var detective_index := 0
	for detective in view.get("detectives", []):
		if detective.place != view.place:
			continue
		var at := Vector3(-4.2 + detective_index * 1.5, 0, 2.4)
		_actor(at, "", detective_index, true)
		_add_target(at, "VOUS" if detective.you else str(detective.name), {}, false)
		detective_index += 1
	for i in view.present.size():
		var person: Dictionary = view.present[i]
		var at := Vector3(-0.4 + (i % 4) * 2.1, 0, -0.3 + (i / 4) * 2.25)
		_actor(at, str(person.look), int(person.id))
		_add_target(at, str(person.name) if person.name != null else "Inconnu", person, true)

func _add_target(at: Vector3, title: String, person: Dictionary, clickable: bool) -> void:
	var button := preload("res://entrance_target.gd").new()
	button.navigation = self
	button.size = Vector2(88, 90)
	button.tooltip_text = "Parler à " + title if clickable else "Votre détective"
	button.disabled = not clickable
	button.mouse_filter = Control.MOUSE_FILTER_STOP if clickable else Control.MOUSE_FILTER_IGNORE
	for state in ["normal", "hover", "pressed", "focus", "disabled"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color(0.15, 0.35, 0.45, 0.16) if state in ["hover", "pressed", "focus"] else Color.TRANSPARENT
		style.set_corner_radius_all(20)
		button.add_theme_stylebox_override(state, style)
	var label := Label.new()
	label.text = title
	label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	label.offset_top = -20
	label.offset_bottom = 0
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 13)
	label.add_theme_color_override("font_color", GOLD if clickable else CYAN)
	label.add_theme_color_override("font_shadow_color", Color.BLACK)
	label.add_theme_constant_override("shadow_outline_size", 3)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	button.add_child(label)
	if clickable:
		button.pressed.connect(func(): person_selected.emit(person.duplicate(true)))
		person_buttons[int(person.id)] = button
	overlay.add_child(button)
	targets.append({"at": at, "button": button})
	entries.append({"kind": "entrance", "target": button})

func _process(_delta: float) -> void:
	if camera == null or not is_visible_in_tree():
		return
	for target in targets:
		var point: Vector3 = to_global(target.at)
		var foot: Vector2 = camera.unproject_position(point)
		var screen: Vector2 = overlay.get_viewport_rect().size
		target.button.visible = not camera.is_position_behind(point) and Rect2(28, 100, screen.x - 56, screen.y - 195).has_point(foot)
		target.button.position = foot - Vector2(44, 76)
