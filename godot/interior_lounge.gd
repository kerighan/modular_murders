extends Node3D
## Shared, low-poly lounge. World truth comes only from the public view.
## Same 3D world and camera as the city; no modal or additional viewport.
signal person_selected(person: Dictionary)

const Geometry := preload("res://city_visuals.gd")
const CYAN := Color("63e1ec")
const PINK := Color("ee4985")
const GOLD := Color("ffc17c")
const HOME := Color("b896ff")
var camera: Camera3D
var overlay: Control
var stage: Node3D
var geometry: Node3D
var bar_room: Node3D
var precinct: Node3D
var figures: Node3D
var exterior: Node3D
var corridor: Node3D
var blood: Node3D
var targets := []
var person_buttons := {}
var staff_buttons := {}
var fixture_buttons := {}
var door_buttons := {}
var door_meshes := {}  # place -> the door's own meshes, so a tap can swing it open
var props: Node3D
var entries := []
var place := ""

func _ready() -> void:
	stage = self
	geometry = Geometry.new()
	stage.add_child(geometry)
	_build_room()
	_build_bar()
	_build_precinct()
	_build_exterior()
	_build_corridor()
	figures = Node3D.new()
	stage.add_child(figures)
	props = Node3D.new()
	stage.add_child(props)

func _build_precinct() -> void:
	# Neon-noir precinct, after the reference sheet: slate floor, reception counter under the
	# badge and flags, a holding cell in red, desks lit by their screens, the evidence board.
	precinct = Node3D.new()
	precinct.name = "Precinct"
	stage.add_child(precinct)
	var g := geometry
	g._begin()
	g._box(Vector3(0, -0.22, 0), Vector3(17, 0.4, 13), Color("151a22"))
	for ix in 34:
		for iz in 26:
			var x := -8.25 + ix * 0.5
			var z := -6.25 + iz * 0.5
			var tint: Color = [Color("2a2f3a"), Color("262a33"), Color("30343f"), Color("23272f")][(ix * 5 + iz * 3) % 4]
			var amber := maxf(0, 1.0 - Vector2(x + 4.8, z + 1.6).length() / 4.2)
			var cyan := maxf(0, 1.0 - Vector2(x - 3.2, z - 0.8).length() / 4.6)
			var red := maxf(0, 1.0 - Vector2(x - 6.6, z + 4.6).length() / 3.2)
			tint = tint.lerp(Color("b07a3a"), amber * 0.45).lerp(Color("3fa6b3"), cyan * 0.40).lerp(Color("b33a4a"), red * 0.5)
			g._box(Vector3(x, 0.005, z), Vector3(0.485, 0.035, 0.485), tint)
	# Concrete walls in panels, a skirting rail, two cold tubes.
	g._box(Vector3(0, 2.1, -6.4), Vector3(17, 4.2, 0.3), Color("262a33"))
	g._box(Vector3(-8.3, 2.1, 0), Vector3(0.3, 4.2, 13), Color("282c35"))
	for i in 9:
		g._box(Vector3(-8.0 + i * 2.1, 2.1, -6.2), Vector3(0.06, 4.2, 0.06), Color("1b1f26"))
	for i in 7:
		g._box(Vector3(-8.1, 2.1, -6.0 + i * 2.1), Vector3(0.06, 4.2, 0.06), Color("1b1f26"))
	g._box(Vector3(0, 0.35, -6.2), Vector3(17, 0.14, 0.06), Color("3a3f4a"))
	g._box(Vector3(-8.1, 0.35, 0), Vector3(0.06, 0.14, 13), Color("3a3f4a"))
	g._box(Vector3(0, 4.14, -6.1), Vector3(17, 0.18, 0.5), Color("171b22"))
	g._box(Vector3(-8.1, 4.14, 0), Vector3(0.5, 0.18, 13), Color("171b22"))
	for x in [-4.8, 2.0]:
		g._box(Vector3(x, 3.75, -6.1), Vector3(1.6, 0.06, 0.06), CYAN, "light")
	# Reception: the commissaire's counter, the badge and the flags above it.
	g._box(Vector3(-4.8, 0.53, -1.8), Vector3(6.3, 1.06, 0.9), Color("3a2a22"))
	g._box(Vector3(-4.8, 1.13, -1.8), Vector3(6.65, 0.15, 1.15), Color("5b4231"))
	g._box(Vector3(-4.8, 0.62, -1.33), Vector3(6.3, 0.045, 0.05), GOLD, "light")
	g._box(Vector3(-6.4, 1.6, -1.9), Vector3(0.12, 0.8, 0.12), Color("4a4035"))
	g._box(Vector3(-6.4, 2.02, -1.9), Vector3(0.5, 0.22, 0.5), Color("7a5a2e"))
	g._box(Vector3(-6.4, 1.9, -1.9), Vector3(0.3, 0.06, 0.3), GOLD, "light")
	g._box(Vector3(-3.4, 1.5, -2.0), Vector3(0.62, 0.5, 0.08), Color("1b2129"))
	g._box(Vector3(-3.4, 1.5, -1.95), Vector3(0.52, 0.4, 0.03), Color("63c7d6"), "light")
	for i in 3:
		g._box(Vector3(-5.5 + i * 0.5, 1.25, -1.75), Vector3(0.36, 0.08 + (i % 2) * 0.05, 0.3), Color("c9c2b0"))
	g._box(Vector3(-4.8, 2.55, -6.15), Vector3(1.3, 1.5, 0.08), Color("1c2230"))
	g._box(Vector3(-4.8, 2.55, -6.10), Vector3(1.1, 1.3, 0.04), Color("b8882f"))
	g._box(Vector3(-4.8, 2.55, -6.06), Vector3(0.8, 0.95, 0.03), Color("1c2230"))
	g._box(Vector3(-4.8, 2.55, -6.02), Vector3(0.3, 0.3, 0.03), GOLD, "light")
	for x in [-6.3, -3.3]:
		g._box(Vector3(x, 1.9, -5.95), Vector3(0.07, 3.8, 0.07), Color("8a7756"))
		g._box(Vector3(x, 3.82, -5.95), Vector3(0.14, 0.14, 0.14), GOLD)
		for i in 7:
			var stripe := Color("b8303d") if i % 2 == 0 else Color("d9d3c7")
			g._box(Vector3(x + 0.25, 3.5 - i * 0.16, -5.95), Vector3(0.42, 0.15, 0.06), stripe)
		g._box(Vector3(x + 0.14, 3.42, -5.93), Vector3(0.2, 0.3, 0.05), Color("2b3b7a"))
	# Holding cell: bars, a cot, a red tube that bleeds on the floor.
	for i in 9:
		g._box(Vector3(4.6 + i * 0.45, 1.5, -3.3), Vector3(0.06, 3.0, 0.06), Color("6c7380"))
	for i in 7:
		g._box(Vector3(4.6, 1.5, -6.2 + i * 0.47), Vector3(0.06, 3.0, 0.06), Color("6c7380"))
	g._box(Vector3(6.5, 3.0, -3.3), Vector3(3.9, 0.1, 0.1), Color("7c838f"))
	g._box(Vector3(4.6, 3.0, -4.75), Vector3(0.1, 0.1, 3.0), Color("7c838f"))
	g._box(Vector3(6.6, 0.25, -5.4), Vector3(2.4, 0.5, 1.0), Color("39404a"))
	g._box(Vector3(6.6, 0.56, -5.4), Vector3(2.3, 0.14, 0.9), Color("4a5160"))
	g._box(Vector3(6.6, 3.55, -6.1), Vector3(2.2, 0.06, 0.06), Color("ff3a4f"), "light")
	g._box(Vector3(4.9, 1.1, -3.3), Vector3(0.5, 2.2, 0.08), Color("4a505c"))
	g._box(Vector3(5.05, 1.1, -3.22), Vector3(0.08, 0.2, 0.06), GOLD)
	# Lockers, a water cooler, posters.
	for i in 4:
		g._box(Vector3(1.2 + i * 0.62, 1.1, -5.95), Vector3(0.58, 2.2, 0.6), Color("3b434f") if i % 2 == 0 else Color("343c47"))
		g._box(Vector3(1.2 + i * 0.62, 1.6, -5.63), Vector3(0.2, 0.05, 0.03), CYAN, "light")
	g._box(Vector3(-7.6, 0.5, 5.4), Vector3(0.5, 1.0, 0.5), Color("3b434f"))
	g._box(Vector3(-7.6, 1.35, 5.4), Vector3(0.42, 0.7, 0.42), Color("4fb9d9"), "light")
	for z in [1.2, 3.4]:
		g._box(Vector3(-8.08, 2.2, z), Vector3(0.05, 1.0, 0.72), Color("c9c2b0"))
		g._box(Vector3(-8.03, 2.35, z), Vector3(0.025, 0.5, 0.42), Color("5b5a63"))
	# Evidence board: photos, pins, red string.
	g._box(Vector3(0.9, 2.45, -6.15), Vector3(2.9, 1.8, 0.08), Color("5a4531"))
	for i in 6:
		g._box(Vector3(-0.3 + (i % 3) * 1.1, 2.9 - (i / 3) * 0.9, -6.09), Vector3(0.36, 0.42, 0.03), [Color("c9c2b0"), Color("9ba6b1"), Color("b9ad99")][i % 3])
		g._box(Vector3(-0.3 + (i % 3) * 1.1, 3.1 - (i / 3) * 0.9, -6.06), Vector3(0.06, 0.06, 0.03), Color("ff3a4f"))
	g._box(Vector3(0.25, 2.9, -6.04), Vector3(1.1, 0.025, 0.02), Color("ff3a4f"), "light")
	g._box(Vector3(0.8, 2.45, -6.04), Vector3(0.025, 0.9, 0.02), Color("ff3a4f"), "light")
	g._box(Vector3(1.35, 2.0, -6.04), Vector3(1.1, 0.025, 0.02), Color("ff3a4f"), "light")
	# Detectives' desks: the screens light the room more than the ceiling does.
	for desk in [Vector3(1.4, 0, 0.6), Vector3(5.6, 0, 1.6), Vector3(3.6, 0, 4.4)]:
		for x in [-0.95, 0.95]:
			g._box(desk + Vector3(x, 0.42, 0), Vector3(0.12, 0.84, 0.9), Color("3a3129"))
		g._box(desk + Vector3(0, 0.9, 0), Vector3(2.2, 0.12, 1.1), Color("5b4231"))
		g._box(desk + Vector3(-0.35, 1.25, -0.2), Vector3(0.7, 0.5, 0.08), Color("1b2129"))
		g._box(desk + Vector3(-0.35, 1.25, -0.15), Vector3(0.6, 0.4, 0.03), Color("63c7d6"), "light")
		g._box(desk + Vector3(-0.35, 1.0, 0.25), Vector3(0.5, 0.05, 0.2), Color("2a3039"))
		g._box(desk + Vector3(0.6, 1.02, 0.1), Vector3(0.4, 0.12, 0.3), Color("c9c2b0"))
		g._box(desk + Vector3(0.75, 1.3, -0.3), Vector3(0.1, 0.5, 0.1), Color("4a4035"))
		g._box(desk + Vector3(0.75, 1.58, -0.3), Vector3(0.36, 0.14, 0.36), Color("7a5a2e"))
		g._box(desk + Vector3(0.75, 1.5, -0.3), Vector3(0.22, 0.05, 0.22), GOLD, "light")
		g._box(desk + Vector3(0, 0.3, 1.0), Vector3(0.55, 0.6, 0.55), Color("2b3140"))
		g._box(desk + Vector3(0, 0.95, 1.22), Vector3(0.55, 0.7, 0.12), Color("353c4d"))
	# Two square pillars, each with its own small lamp.
	for at in [Vector3(-1.2, 0, -3.6), Vector3(7.2, 0, -0.6)]:
		g._box(at + Vector3(0, 2.1, 0), Vector3(0.7, 4.2, 0.7), Color("2e323c"))
		g._box(at + Vector3(0, 2.3, 0.42), Vector3(0.2, 0.3, 0.12), Color("1b1f26"))
		g._box(at + Vector3(0, 2.3, 0.49), Vector3(0.14, 0.2, 0.03), GOLD, "light")
	g._flush(precinct, "PrecinctStatic")
	for spec in [[Vector3(-4.8, 2.0, -1.4), GOLD, 6.5], [Vector3(3.4, 2.0, 1.4), Color("5fd0dc"), 7.5], [Vector3(6.6, 2.0, -4.8), Color("ff3a4f"), 4.0]]:
		var light := OmniLight3D.new()
		light.position = spec[0]
		light.light_color = spec[1]
		light.light_energy = 1.25
		light.omni_range = spec[2] * 1.5
		light.shadow_enabled = false
		precinct.add_child(light)
	precinct.hide()

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

func _build_corridor() -> void:
	corridor = Node3D.new()
	stage.add_child(corridor)
	geometry._begin()
	geometry._box(Vector3(0, -0.15, 0), Vector3(17, 0.3, 13), Color("222131"))
	geometry._box(Vector3(0, 1.5, -6.1), Vector3(17, 3, 0.2), Color("383044"))
	geometry._box(Vector3(-8.3, 1.1, 0), Vector3(0.2, 2.2, 13), Color("342d40"))
	for x in [-7, 0, 7]:
		geometry._box(Vector3(x, 2.85, -5.8), Vector3(1.4, 0.08, 0.1), HOME, "light")
	for z in [-4, 0, 4]:
		geometry._box(Vector3(0, 0.015, z), Vector3(16, 0.025, 0.035), Color("635669"))
	geometry._flush(corridor, "ResidentialCorridor")
	corridor.hide()

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
	# Waist-height counter: the staff's face stays visible behind it.
	geometry._box(Vector3(-4.8, 0.55, -1.8), Vector3(5.7, 1.1, 0.85), Color("432534"))
	geometry._box(Vector3(-4.8, 1.15, -1.8), Vector3(6.1, 0.13, 1.15), Color("776053"))
	geometry._box(Vector3(-4.8, 0.94, -1.2), Vector3(5.8, 0.06, 0.08), PINK, "light")
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
		geometry.add_child(light)

func _build_bar() -> void:
	# A distinct, batched cutaway; no textures, viewport or shadow-casting lights.
	bar_room = Node3D.new()
	bar_room.name = "NeonBarroom"
	stage.add_child(bar_room)
	geometry._begin()
	geometry._box(Vector3(0, -0.22, 0), Vector3(17, 0.4, 13), Color("171b23"))
	for ix in 34:
		for iz in 26:
			var x := -8.25 + ix * 0.5
			var z := -6.25 + iz * 0.5
			var tint: Color = [Color("30292b"), Color("28262b"), Color("3b2f2b"), Color("24252c")][(ix * 7 + iz * 3) % 4]
			var red := maxf(0, 1.0 - Vector2(x + 4.8, z + 2.4).length() / 5.0)
			var amber := maxf(0, 1.0 - Vector2(x - 4.6, z + 3.4).length() / 3.8)
			tint = tint.lerp(Color("bd3c4d"), red * 0.65).lerp(Color("b47a3b"), amber * 0.50)
			geometry._box(Vector3(x, 0.005, z), Vector3(0.485, 0.035, 0.485), tint)
	geometry._box(Vector3(0, 2.1, -6.4), Vector3(17, 4.2, 0.3), Color("262028"))
	geometry._box(Vector3(-8.3, 2.1, 0), Vector3(0.3, 4.2, 13), Color("292128"))
	for row in 10:
		for brick in 20:
			var x := -8.1 + brick * 0.83 + (row % 2) * 0.30
			if x > 8.1:
				continue
			var tint: Color = [Color("443039"), Color("382d32"), Color("4a3535")][(row + brick * 5) % 3]
			geometry._box(Vector3(x, 0.2 + row * 0.4, -6.19), Vector3(0.79, 0.36, 0.10), tint)
		for brick in 16:
			var z := -6.0 + brick * 0.78 + (row % 2) * 0.3
			geometry._box(Vector3(-8.09, 0.2 + row * 0.4, z), Vector3(0.10, 0.36, 0.74), Color("523439") if (row + brick) % 3 == 0 else Color("382c32"))
	# A recessed crimson entrance and small poster details on the return wall.
	geometry._box(Vector3(-8.0, 1.4, 3.7), Vector3(0.13, 2.8, 1.6), Color("171f2a"))
	for z in [2.9, 4.5]:
		geometry._box(Vector3(-7.9, 1.4, z), Vector3(0.045, 2.8, 0.045), Color("ff3a61"), "light")
	geometry._box(Vector3(-7.9, 2.8, 3.7), Vector3(0.045, 0.045, 1.65), Color("ff3a61"), "light")
	for at in [Vector3(-7.95, 2.1, -0.8), Vector3(0.0, 2.1, -6.05)]:
		geometry._box(at, Vector3(0.05, 1.0, 0.72) if at.x < -7 else Vector3(0.7, 1.0, 0.05), Color("a27a57"))
		geometry._box(at + Vector3(0.035, 0, 0.035), Vector3(0.025, 0.54, 0.35) if at.x < -7 else Vector3(0.35, 0.54, 0.025), Color("773b47"))
	for x in [-7.6, -1.2, 7.6]:
		geometry._box(Vector3(x, 2.1, -5.95), Vector3(0.3, 4.2, 0.35), Color("4d3530"))
		geometry._box(Vector3(x, 2.55, -5.69), Vector3(0.32, 0.52, 0.22), Color("211f29"))
		geometry._box(Vector3(x, 2.56, -5.54), Vector3(0.22, 0.29, 0.07), GOLD, "light")
	geometry._box(Vector3(0, 4.14, -6.1), Vector3(17, 0.18, 0.5), Color("191e2b"))
	geometry._box(Vector3(-8.1, 4.14, 0), Vector3(0.5, 0.18, 13), Color("191e2b"))
	# Bottle shelves flank a pixel-neon cat, rather than the cabaret curtains.
	for cx in [-6.8, -2.65]:
		geometry._box(Vector3(cx, 1.5, -5.7), Vector3(2.2, 2.8, 0.45), Color("191e26"))
		for shelf in [0.7, 1.35, 2.0]:
			geometry._box(Vector3(cx, shelf, -5.35), Vector3(2.3, 0.12, 0.7), Color("715340"))
			geometry._box(Vector3(cx, shelf + 0.08, -5.0), Vector3(2.2, 0.035, 0.04), GOLD, "light")
			for i in 7:
				var at := Vector3(cx - 0.9 + i * 0.3, shelf + 0.24, -5.25)
				var tint: Color = [Color("527f68"), Color("aa7544"), Color("8b4c4a"), Color("67788e")][i % 4]
				geometry._box(at, Vector3(0.14, 0.32 + (i % 2) * 0.07, 0.14), tint)
				geometry._box(at + Vector3(0, 0.21, 0), Vector3(0.07, 0.11, 0.07), tint)
	geometry._box(Vector3(-4.7, 2.65, -6.0), Vector3(1.65, 2.0, 0.08), Color("371d2c"))
	var cat := ["#......#", "##....##", "########", "#......#", "#.#..#.#", "#......#", ".#....#.", "..####.."]
	for y in cat.size():
		for x in cat[y].length():
			if cat[y][x] == "#":
				geometry._box(Vector3(-5.32 + x * 0.18, 3.35 - y * 0.18, -5.9), Vector3(0.15, 0.15, 0.05), Color("ff4875"), "light")
	# Barman remains behind a low counter, with the touch halo on the client side.
	geometry._box(Vector3(-4.8, 0.53, -1.8), Vector3(6.3, 1.06, 0.9), Color("492c31"))
	geometry._box(Vector3(-4.8, 1.13, -1.8), Vector3(6.65, 0.15, 1.15), Color("84624a"))
	geometry._box(Vector3(-4.8, 1.05, -1.19), Vector3(6.5, 0.05, 0.045), Color("ee5668"), "light")
	for x in [-7.1, -5.6, -4.1, -2.6]:
		geometry._box(Vector3(x, 0.55, -0.35), Vector3(0.10, 1.1, 0.10), Color("6a5649"))
		geometry._box(Vector3(x, 1.03, -0.35), Vector3(0.55, 0.12, 0.55), Color("803947"))
		geometry._box(Vector3(x + 0.18, 1.34, -1.85), Vector3(0.13, 0.28, 0.13), Color("77aea8"))
		geometry._box(Vector3(x - 0.2, 1.33, -1.6), Vector3(0.12, 0.21, 0.12), GOLD, "light")
	# Pool table: green cloth, brass rails, six dark pockets, scattered balls.
	var pool := Vector3(4.7, 0, -3.4)
	for x in [-1.8, 1.8]:
		for z in [-0.85, 0.85]:
			geometry._box(pool + Vector3(x, 0.52, z), Vector3(0.25, 1.04, 0.25), Color("503a30"))
	geometry._box(pool + Vector3(0, 1.04, 0), Vector3(4.6, 0.30, 2.55), Color("785039"))
	geometry._box(pool + Vector3(0, 1.21, 0), Vector3(4.08, 0.06, 2.04), Color("326453"))
	for x in [-2.2, 2.2]:
		geometry._box(pool + Vector3(x, 1.27, 0), Vector3(0.16, 0.13, 2.5), Color("b78b4f"))
	for z in [-1.19, 1.19]:
		geometry._box(pool + Vector3(0, 1.27, z), Vector3(4.6, 0.13, 0.15), Color("b78b4f"))
		for x in [-2.0, 0.0, 2.0]:
			geometry._box(pool + Vector3(x, 1.34, z * 0.84), Vector3(0.20, 0.025, 0.20), Color("151c24"))
	for i in 9:
		var ball := Vector3(-1.42 + (i * 7 % 17) * 0.17, 1.30, -0.68 + (i * 11 % 13) * 0.1)
		geometry._box(pool + ball, Vector3(0.10, 0.10, 0.10), [Color("eadcc6"), Color("c4494b"), Color("c9a248"), Color("5c83a5")][i % 4])
	geometry._box(pool + Vector3(0, 2.8, 0), Vector3(3.7, 0.3, 0.7), Color("453831"))
	geometry._box(pool + Vector3(0, 2.63, 0), Vector3(3.4, 0.05, 0.5), GOLD, "light")
	for x in [-1.3, 1.3]:
		geometry._box(pool + Vector3(x, 3.38, 0), Vector3(0.025, 1.0, 0.025), Color("786651"))
	# Cues on the rear wall and a dartboard; decorative, not false action targets.
	for x in [2.0, 2.25, 2.5]:
		geometry._box(Vector3(x, 1.5, -5.91), Vector3(0.035, 2.2, 0.035), Color("a1865d"))
	geometry._box(Vector3(6.5, 2.1, -5.95), Vector3(0.95, 0.95, 0.06), Color("292831"))
	geometry._box(Vector3(6.5, 2.1, -5.89), Vector3(0.65, 0.65, 0.035), Color("b77448"))
	geometry._box(Vector3(6.5, 2.1, -5.85), Vector3(0.20, 0.20, 0.025), Color("592b3a"))
	# Leave the central/right aisle free for the immutable crime-scene props.
	for at in [Vector3(-6.6, 0, 4.7)]:
		geometry._box(at + Vector3(0, 0.45, 0), Vector3(0.18, 0.9, 0.18), Color("5b4440"))
		geometry._box(at + Vector3(0, 0.96, 0), Vector3(1.7, 0.13, 1.2), Color("81604a"))
		geometry._box(at + Vector3(0, 1.18, 0), Vector3(0.13, 0.31, 0.13), GOLD, "light")
		for x in [-0.9, 0.9]:
			geometry._box(at + Vector3(x, 0.43, 0.9), Vector3(0.65, 0.85, 0.65), Color("5d2836"))
			geometry._box(at + Vector3(x, 1.0, 1.16), Vector3(0.65, 0.60, 0.13), Color("773447"))
	for z in [2.9, 4.8]:
		geometry._box(Vector3(6.8, 0.52, z), Vector3(2.5, 1.04, 0.8), Color("652c38"))
		geometry._box(Vector3(7.9, 1.05, z), Vector3(0.2, 1.0, 0.85), Color("833b45"))
	geometry._box(Vector3(5.8, 0.48, 3.8), Vector3(0.18, 0.96, 0.18), Color("56433a"))
	geometry._box(Vector3(5.8, 1.0, 3.8), Vector3(1.5, 0.12, 1.4), Color("80604b"))
	geometry._box(Vector3(5.8, 1.2, 3.8), Vector3(0.15, 0.35, 0.15), GOLD, "light")
	geometry._flush(bar_room, "BarStatic")
	for spec in [[Vector3(-4.7, 2.6, -2.3), Color("ff4970"), 7.0], [Vector3(4.7, 2.7, -3.4), GOLD, 5.0], [Vector3(5.6, 2.0, 3.8), GOLD, 4.0]]:
		var light := OmniLight3D.new()
		light.position = spec[0]
		# Godot does not scale a light's attenuation distance with room geometry.
		light.position.y = 2.0
		light.light_color = spec[1]
		light.light_energy = 1.3
		light.omni_range = spec[2] * 1.5
		light.shadow_enabled = false
		bar_room.add_child(light)
	bar_room.hide()

func _actor(at: Vector3, look: String, id: int, detective: bool = false, service: bool = false, appearance: Dictionary = {}, activity: String = "", guide_tint: Color = Color.TRANSPARENT, guide_offset: Vector3 = Vector3.ZERO) -> Node3D:
	var root := Node3D.new()
	root.position = at
	figures.add_child(root)
	geometry._begin()
	var coat: Color = Color("32465a") if detective else Color("653749") if service else [Color("685368"), Color("526662"), Color("77634d"), Color("596174")][absi(id) % 4]
	if not appearance.is_empty():
		coat = {"sombre": Color("293343"), "clair": Color("b1b6a7"), "coloré": Color("a8476c")}.get(appearance.get("coat", ""), coat)
		root.scale.y = 0.87 if "petite" in str(appearance.get("height", "")) else 1.15 if "grande" in str(appearance.get("height", "")) else 1.0
	var hair := Color("3b3031") if "noirs" in look else Color("ab683e") if "roux" in look else Color("c2a272") if "blonds" in look else Color("644535")
	hair = {"noirs": Color("292c38"), "bruns": Color("694537"), "blonds": Color("cda95f"), "roux": Color("b7613c")}.get(appearance.get("hair", ""), hair)
	var seated := activity in ["déjeune", "dîne"] and not detective and not service
	var body_offset := -0.18 if seated else 0.0
	for x in [-0.17, 0.17]:
		if seated:
			geometry._box(Vector3(x, 0.47, 0.17), Vector3(0.24, 0.22, 0.58), Color("1c2331"))
			geometry._box(Vector3(x, 0.25, 0.36), Vector3(0.24, 0.45, 0.25), Color("1c2331"))
		else:
			geometry._box(Vector3(x, 0.32, 0), Vector3(0.24, 0.6, 0.27), Color("1c2331"))
		geometry._box(Vector3(x, 0.08, 0.38 if seated else 0.10), Vector3(0.27, 0.16, 0.4), Color("17202b"))
	geometry._box(Vector3(0, 0.9 + body_offset, 0), Vector3(0.65, 0.65, 0.35), coat)
	for x in [-0.4, 0.4]:
		geometry._box(Vector3(x, 0.88 + body_offset, 0), Vector3(0.16, 0.58, 0.23), coat.darkened(0.12))
		geometry._box(Vector3(x, 0.60 + body_offset, 0), Vector3(0.14, 0.14, 0.22), Color("c2997e"))
	geometry._box(Vector3(0, 1.47 + body_offset, 0), Vector3(0.43, 0.45, 0.4), Color("c8a08a"))
	geometry._box(Vector3(0, 1.73 + body_offset, -0.015), Vector3(0.45, 0.15, 0.43), hair)
	if seated:
		# Bounded, batched voxel props, no new lights or interaction fixtures.
		geometry._box(Vector3(0, 0.48, -0.04), Vector3(0.75, 0.09, 0.65), Color("633346"))
		geometry._box(Vector3(0, 0.82, -0.31), Vector3(0.75, 0.62, 0.10), Color("633346"))
		geometry._box(Vector3(0, 0.37, 0.92), Vector3(0.16, 0.70, 0.16), Color("5a4143"))
		geometry._box(Vector3(0, 0.75, 0.92), Vector3(1.22, 0.08, 0.72), Color("80634f"))
		geometry._box(Vector3(-0.13, 0.81, 0.92), Vector3(0.48, 0.035, 0.40), Color("c2c2ae"))
		geometry._box(Vector3(-0.13, 0.86, 0.92), Vector3(0.24, 0.06, 0.23), Color("bf8050"))
		geometry._box(Vector3(0.37, 0.91, 0.95), Vector3(0.12, 0.23, 0.12), Color("72afa5"))
	elif activity == "prend un verre":
		geometry._box(Vector3(0.41, 0.76, 0.08), Vector3(0.15, 0.30, 0.15), Color("72afa5"))
		geometry._box(Vector3(0.41, 0.86, 0.08), Vector3(0.12, 0.06, 0.12), Color("bb7749"))
	if detective:
		geometry._box(Vector3(0, 1.77, 0), Vector3(0.56, 0.13, 0.5), Color("374252"))
		geometry._box(Vector3(0, 1.89, 0), Vector3(0.40, 0.2, 0.38), Color("354251"))
		geometry._box(Vector3(0, 1.82, 0.21), Vector3(0.42, 0.035, 0.03), CYAN, "light")
		geometry._box(Vector3(0, 0.7, 0), Vector3(0.7, 0.35, 0.36), coat)
	var tint: Color = CYAN if detective else PINK if service else GOLD
	if guide_tint.a > 0:
		tint = guide_tint
	for side in [-1, 1]:
		geometry._box(guide_offset + Vector3(side * 0.65, 0.06, 0), Vector3(0.08, 0.02, 1.1), tint, "guide")
		geometry._box(guide_offset + Vector3(0, 0.06, side * 0.55), Vector3(1.35, 0.02, 0.08), tint, "guide")
	geometry._flush(root, "Actor")
	return root

func populate(view: Dictionary) -> void:
	for child in props.get_children():
		props.remove_child(child)
		child.queue_free()
	for child in figures.get_children():
		figures.remove_child(child)
		child.queue_free()
	for target in targets:
		target.button.queue_free()
	targets.clear()
	entries.clear()
	person_buttons.clear()
	staff_buttons.clear()
	fixture_buttons.clear()
	door_buttons.clear()
	place = view.place
	var hallway: bool = view.get("hallway", false)
	var outside: bool = not hallway and view.get("outdoors", place in ["crime_scene", "alley", "victim_street"])
	var is_bar := place == "bar" and not outside and not hallway
	var is_police := place == "police" and not outside and not hallway
	geometry.visible = not outside and not hallway and not is_bar and not is_police
	bar_room.visible = is_bar
	precinct.visible = is_police
	exterior.visible = outside
	corridor.visible = hallway
	blood.visible = place == str(view.get("crime_site", {}).get("place", "crime_scene")) and view.get("scene_has_blood", true)
	var detective_index := 0
	for detective in view.get("detectives", []):
		if detective.place != view.place:
			continue
		var at := Vector3(-4.2 + detective_index * 1.5, 0, 2.4)
		if is_bar:
			at = Vector3(-6.6 + detective_index * 1.5, 0, 2.4)
		_actor(at, "", detective_index, true)
		_add_target(at, "VOUS" if detective.you else str(detective.name), {}, false)
		detective_index += 1
	for i in view.present.size():
		var person: Dictionary = view.present[i]
		var at := Vector3(-0.4 + (i % 4) * 2.1, 0, -0.3 + (i / 4) * 2.25)
		if is_bar:
			at = _bar_client_position(i)
		_actor(at, str(person.look), int(person.id), false, false, person.get("appearance", {}), str(person.get("activity", "")))
		_add_target(at, str(person.name) if person.name != null else "Inconnu", person, true)
	# Staff have a separate reception lane, not a seat among suspects.
	var staff_index := 0
	var witness_index := 0
	for person in view.get("staff", []):
		var placement: String = person.get("placement", "reception")
		var lane_index := witness_index if placement == "witness" else staff_index
		var at := Vector3(-4.8, 0, -2.9) if placement in ["bar_staff", "restaurant_staff"] or is_police else Vector3(-1.1 + (witness_index % 3) * 2.1, 0, 3.4 + (witness_index / 3) * 1.9) if placement == "witness" and not outside else Vector3(-5.4 + (lane_index % 2) * 2.1, 0, 0.8 + (lane_index / 2) * 2.2)
		if is_bar and placement == "witness":
			at = _bar_client_position(view.present.size() + witness_index)
		var verification: Dictionary = person.get("verification", {})
		var tint := Color("83e5b3") if verification.get("total", 0) > 0 and verification.get("done", 0) == verification.total else Color("eab779") if verification.get("total", 0) > 0 else PINK
		var offset := Vector3(0, 0, 2.0) if placement in ["bar_staff", "restaurant_staff"] or is_police else Vector3.ZERO
		var actor := _actor(at, str(person.look), int(person.portrait_id), false, true, {}, "", tint, offset)
		actor.set_meta("contact_id", person.id)
		actor.set_meta("contact_role", person.get("role", "Personnel"))
		_add_target(at + offset, str(person.name), person, true)
		if placement == "witness":
			witness_index += 1
		else:
			staff_index += 1
	var doors: Array = view.get("doors", [])
	door_meshes.clear()
	for i in doors.size():
		var door: Dictionary = doors[i]
		# Five doors on the back wall, well apart, then up to four along the side wall:
		# a thumb must land on one door, not two, and no door sits in the middle of the floor.
		var on_side := i >= 5
		var back_count := mini(5, doors.size())
		var at := Vector3(-8.0, 0, -1.6 + (i - 5) * 3.0) if on_side else Vector3((i - (back_count - 1) * 0.5) * 3.3, 0, -5.7)
		var out := Vector3(1, 0, 0) if on_side else Vector3(0, 0, 1)  # which way the door faces
		var along := Vector3(0, 0, 1) if on_side else Vector3(1, 0, 0)
		var before_doors := props.get_child_count()
		geometry._begin()
		geometry._box(at + Vector3(0, 1.18, 0), Vector3(0.24, 2.36, 1.55) if on_side else Vector3(1.55, 2.36, 0.24), Color("594039"))
		geometry._box(at + Vector3(0, 2.45, 0), Vector3(0.28, 0.18, 1.85) if on_side else Vector3(1.85, 0.18, 0.28), HOME, "light")
		geometry._box(at + along * 0.56 + Vector3(0, 1.12, 0) + out * 0.18, Vector3(0.08, 0.18, 0.09) if on_side else Vector3(0.09, 0.18, 0.08), GOLD)
		geometry._box(at + Vector3(0, 1.6, 0) + out * 0.16, Vector3(0.06, 0.22, 0.38) if on_side else Vector3(0.38, 0.22, 0.06), Color("b49366"))
		if not door.actions.is_empty():
			for side in [-1, 1]:
				geometry._box(at + along * (side * 0.7) + Vector3(0, 0.06, 0) + out * 0.9, Vector3(0.8, 0.025, 0.07) if on_side else Vector3(0.07, 0.025, 0.8), HOME, "guide")
		geometry._flush(props, "ApartmentDoor")
		door_meshes[str(door.place)] = {"at": at, "out": out, "along": along, "meshes": props.get_children().slice(before_doors)}
		if door.get("answered", false):
			for person in door.get("people", []):
				var person_at := at + along * 0.35 + out * 1.4
				_actor(person_at, str(person.look), int(person.id), false, false, person.get("appearance", {}))
				_add_target(person_at, str(person.name) if person.name != null else "Inconnu", person, true)
		if not door.get("answered", false):
			_add_target(at + out * 1.0, str(door.label), door, true)
	for i in view.get("fixtures", []).size():
		var fixture: Dictionary = view.fixtures[i]
		var slot: int = int(fixture.get("slot", i))
		var at := Vector3(-0.5 + (slot % 3) * 3.0, 0, 3.1 + (slot / 3) * 2.4) if not outside else Vector3(0.4 + (slot % 3) * 2.6, 0, -1.4 + (slot / 3) * 2.5)
		if fixture.prop == "kit":
			at = Vector3(-3.0, 0, 2.5)
		if is_bar:
			at = _bar_fixture_position(fixture, slot)
		geometry._begin()
		if fixture.prop == "trash":
			geometry._box(at + Vector3(0, 0.6, 0), Vector3(1.2, 1.2, 0.95), Color("36494d"))
			geometry._box(at + Vector3(0, 1.24, 0), Vector3(1.3, 0.12, 1.05), Color("526362"))
		elif fixture.prop == "blood":
			geometry._box(at + Vector3(0, 0.05, 0), Vector3(0.6, 0.04, 0.4), Color("b72b47"))
		elif fixture.prop == "body":
			geometry._box(at + Vector3(0, 0.20, 0), Vector3(0.68, 0.36, 0.88), Color("34384c"))
			geometry._box(at + Vector3(0, 0.22, -0.72), Vector3(0.42, 0.34, 0.42), Color("c2997e"))
			for side in [-1, 1]:
				geometry._box(at + Vector3(side * 0.19, 0.14, 0.74), Vector3(0.26, 0.24, 0.76), Color("202836"))
				geometry._box(at + Vector3(side * 0.48, 0.17, -0.02), Vector3(0.19, 0.25, 0.70), Color("34384c"))
		elif fixture.prop == "safe":
			geometry._box(at + Vector3(0, 0.65, 0), Vector3(1.25, 1.3, 0.95), Color("39404a"))
			geometry._box(at + Vector3(0, 0.65, 0.51), Vector3(0.92, 0.94, 0.10), Color("697079"))
			geometry._box(at + Vector3(0.25, 0.65, 0.60), Vector3(0.12, 0.4, 0.06), GOLD)
		elif fixture.prop == "drink":
			geometry._box(at + Vector3(0, 0.10, 0), Vector3(0.26, 0.20, 0.26), Color("76aaa9"))
			geometry._box(at + Vector3(0, 0.21, 0), Vector3(0.22, 0.03, 0.22), Color("aa7b49"))
		elif fixture.prop == "evidence":
			if fixture.get("shape", "") == "fictional_agent":
				geometry._box(at + Vector3(0, 0.17, 0), Vector3(0.25, 0.34, 0.25), Color("738a83"))
				geometry._box(at + Vector3(0, 0.36, 0), Vector3(0.14, 0.05, 0.14), Color("657388"))
			else:
				geometry._box(at + Vector3(0, 0.08, 0.20), Vector3(0.12, 0.12, 0.35), Color("645442"))
				geometry._box(at + Vector3(0, 0.08, -0.15), Vector3(0.45, 0.16, 0.18) if fixture.get("shape", "") == "hammer" else Vector3(0.14, 0.04, 0.40), Color("849091"))
		elif fixture.prop == "kit":
			geometry._box(at + Vector3(0, 0.20, 0), Vector3(0.85, 0.40, 0.6), Color("304959"))
			geometry._box(at + Vector3(0, 0.41, 0), Vector3(0.9, 0.05, 0.65), Color("4e6572"))
			geometry._box(at + Vector3(0, 0.45, 0), Vector3(0.25, 0.04, 0.08), CYAN)
		elif fixture.prop == "cupboard":
			geometry._box(at + Vector3(0, 1.2, 0), Vector3(1.5, 2.4, 0.75), Color("5c4840"))
			for side in [-1, 1]:
				geometry._box(at + Vector3(side * 0.36, 1.2, 0.39), Vector3(0.67, 2.2, 0.08), Color("705448"))
				geometry._box(at + Vector3(side * 0.1, 1.1, 0.45), Vector3(0.04, 0.20, 0.04), GOLD)
		else:
			geometry._box(at + Vector3(0, 0.55, 0), Vector3(1.8, 1.1, 0.8), Color("55413d"))
			geometry._box(at + Vector3(0, 1.13, 0), Vector3(2.0, 0.12, 1.0), Color("806652"))
			if fixture.prop == "phone":
				geometry._box(at + Vector3(0, 1.24, 0), Vector3(0.3, 0.07, 0.52), Color("152332"))
				geometry._box(at + Vector3(0, 1.285, 0), Vector3(0.24, 0.02, 0.42), CYAN, "light")
			elif fixture.prop == "terminal":
				geometry._box(at + Vector3(0, 1.53, -0.16), Vector3(0.92, 0.65, 0.13), Color("1c2735"))
				geometry._box(at + Vector3(0, 1.54, -0.07), Vector3(0.74, 0.48, 0.02), CYAN, "light")
			elif fixture.prop == "morgue":
				geometry._box(at + Vector3(0, 1.25, 0), Vector3(1.6, 0.23, 0.68), Color("a8b5b4"))
				if fixture.get("body_present", false):
					geometry._box(at + Vector3(0, 1.5, 0), Vector3(1.3, 0.27, 0.52), Color("bfcac4"))
					geometry._box(at + Vector3(-0.68, 1.48, 0), Vector3(0.28, 0.28, 0.32), Color("c2997e"))
			else:
				geometry._box(at + Vector3(0, 1.22, 0), Vector3(0.65, 0.05, 0.47), Color("cebea0"))
		var previous_prop_count := props.get_child_count()
		geometry._flush(props, "InteractionObject")
		for prop_index in range(previous_prop_count, props.get_child_count()):
			props.get_child(prop_index).set_meta("fixture_id", fixture.id)
			props.get_child(prop_index).set_meta("fixture_at", at)
		if not fixture.get("selectable", true):
			continue
		geometry._begin()
		for side in [-1, 1]:
			geometry._box(at + Vector3(side * 1.0, 0.06, 0.7), Vector3(0.07, 0.025, 0.8), CYAN, "guide")
		geometry._flush(props, "ObjectHalo")
		_add_target(at + Vector3(0, 0, 0.8), str(fixture.name), fixture, true)

func _bar_client_position(index: int) -> Vector3:
	# Customer lanes and the pool perimeter avoid the evidence aisle/counter.
	var seats := [Vector3(-1.7, 0, 1.3), Vector3(-4.3, 0, 3.2), Vector3(-0.8, 0, -3.6), Vector3(7.4, 0, -5.4), Vector3(-7.0, 0, 0.7), Vector3(4.4, 0, 4.8), Vector3(-0.9, 0, -5.0)]
	return seats[index % seats.size()]

func _bar_fixture_position(fixture: Dictionary, slot: int) -> Vector3:
	# Positions are keyed by physical identity, not remaining actions/list index.
	# Inspecting, collecting or transporting the body cannot shift its neighbours.
	if fixture.prop == "kit":
		return Vector3(-2.0, 0, 5.5)
	if fixture.prop == "body":
		return Vector3(2.8, 0, -0.3)
	if fixture.prop in ["drink", "blood"]:
		return Vector3(6.1, 0, -1.2)
	if fixture.prop == "evidence":
		return Vector3(1.1, 0, 3.0)
	return Vector3(0.5 + (slot % 3) * 2.8, 0, 2.1 + (slot / 3) * 2.0)

func _add_target(at: Vector3, title: String, person: Dictionary, clickable: bool) -> void:
	var button := preload("res://entrance_target.gd").new()
	button.navigation = self
	button.size = Vector2(174, 90) if person.get("object", false) or person.get("door", false) else Vector2(112, 90)
	if bar_room.visible:
		button.size = Vector2(100, 64)
	button.tooltip_text = title if person.get("object", false) or person.get("door", false) else "Parler à " + title if clickable else "Votre détective"
	button.disabled = not clickable
	button.mouse_filter = Control.MOUSE_FILTER_STOP if clickable else Control.MOUSE_FILTER_IGNORE
	for state in ["normal", "hover", "pressed", "focus", "disabled"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color(0.15, 0.35, 0.45, 0.16) if state in ["hover", "pressed", "focus"] else Color.TRANSPARENT
		style.set_corner_radius_all(20)
		button.add_theme_stylebox_override(state, style)
	var label := Label.new()
	label.text = title + ("\n● 1" if person.get("occupied", false) else "\nVide") if person.get("door", false) else title
	if bar_room.visible and person.get("object", false):
		label.text = {"body": "Corps", "drink": "Verre", "blood": "Sang", "evidence": "Objet au sol", "kit": "Empreintes"}.get(str(person.get("prop", "")), title)
	if person.get("service", false) and person.has("role"):
		label.text += "\n" + str(person.role)
		var verification: Dictionary = person.get("verification", {})
		if verification.get("total", 0) > 0:
			label.text += " · %d/%d" % [verification.done, verification.total]
			button.set_meta("verification", verification.duplicate())
	if person.get("door", false):
		button.tooltip_text += " · 1 personne présente" if person.get("occupied", false) else " · personne à l'intérieur"
	label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	label.offset_top = -36 if person.get("door", false) or person.get("service", false) else -20
	label.offset_bottom = 0
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 13)
	label.add_theme_color_override("font_color", HOME if person.get("door", false) else CYAN if person.get("object", false) else PINK if person.get("service", false) else GOLD if clickable else CYAN)
	var verification: Dictionary = person.get("verification", {})
	if verification.get("total", 0) > 0:
		label.add_theme_color_override("font_color", Color("83e5b3") if verification.done == verification.total else Color("eab779"))
	label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	label.add_theme_color_override("font_shadow_color", Color.BLACK)
	label.add_theme_constant_override("shadow_outline_size", 3)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	button.add_child(label)
	if clickable:
		button.pressed.connect(func(): person_selected.emit(person.duplicate(true)))
		if person.get("object", false):
			fixture_buttons[str(person.id)] = button
		elif person.get("door", false):
			door_buttons[str(person.place)] = button
		elif person.get("service", false):
			staff_buttons[str(person.id)] = button
		else:
			person_buttons[int(person.id)] = button
	overlay.add_child(button)
	targets.append({"at": at, "button": button})
	entries.append({"kind": "entrance", "target": button})

func open_door(place: String, then: Callable) -> void:
	# The door slides aside, someone steps onto the threshold, and only then the talk begins.
	var entry: Dictionary = door_meshes.get(place, {})
	if entry.is_empty():
		then.call()
		return
	var tween := create_tween().set_parallel()
	var slide: Vector3 = entry.get("along", Vector3(1, 0, 0)) * 1.25
	for mesh in entry.meshes:
		if is_instance_valid(mesh):
			tween.tween_property(mesh, "position", mesh.position + slide, 0.45).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	var figure := _actor(entry.at + entry.get("along", Vector3(1, 0, 0)) * 0.35 + entry.get("out", Vector3(0, 0, 1)) * 1.4, "", -1, false, false, {})
	if figure != null:
		figure.scale = Vector3(0.01, 0.01, 0.01)
		tween.tween_property(figure, "scale", Vector3.ONE, 0.35).set_delay(0.3)
	tween.chain().tween_interval(0.25)
	tween.chain().tween_callback(then)

func _process(_delta: float) -> void:
	if camera == null or not is_visible_in_tree():
		return
	for target in targets:
		var point: Vector3 = to_global(target.at)
		var foot: Vector2 = camera.unproject_position(point)
		var screen: Vector2 = overlay.get_viewport_rect().size
		# Bar targets must end above the bottom navigation; retain other framing.
		var bottom_margin := 125.0 if bar_room.visible else 95.0
		target.button.visible = not camera.is_position_behind(point) and Rect2(28, 100, screen.x - 56, screen.y - 100 - bottom_margin).has_point(foot)
		target.button.position = foot - Vector2(target.button.size.x * 0.5, 76)
