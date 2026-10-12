extends Node3D
## Deterministic art layer. No game rules or network state live here.
## Static boxes/quads are merged by material, separately in each city block.

const PITCH := 12.0
const CYAN := Color("38dfff")
const PINK := Color("ed43eb")
const BLUE := Color("426dff")
const AMBER := Color("ffbe68")
const CONCRETE := Color("626572")
const DARK := Color("111b2a")
const PALETTES := [Color("294c50"), Color("4c3548"), Color("354454"), Color("584743"), Color("455357")]
const GLYPHS := {
	"A": [14,17,17,31,17,17,17], "B": [30,17,17,30,17,17,30],
	"C": [14,17,16,16,16,17,14], "D": [30,17,17,17,17,17,30],
	"E": [31,16,16,30,16,16,31], "F": [31,16,16,30,16,16,16],
	"G": [14,17,16,23,17,17,15], "H": [17,17,17,31,17,17,17],
	"I": [31,4,4,4,4,4,31], "J": [7,2,2,2,18,18,12],
	"K": [17,18,20,24,20,18,17], "L": [16,16,16,16,16,16,31],
	"M": [17,27,21,21,17,17,17], "N": [17,25,21,19,17,17,17],
	"O": [14,17,17,17,17,17,14], "P": [30,17,17,30,16,16,16],
	"Q": [14,17,17,17,21,18,13], "R": [30,17,17,30,20,18,17],
	"S": [15,16,16,14,1,1,30], "T": [31,4,4,4,4,4,4],
	"U": [17,17,17,17,17,17,14], "V": [17,17,17,17,17,10,4],
	"W": [17,17,17,21,21,21,10], "X": [17,17,10,4,10,17,17],
	"Y": [17,17,10,4,4,4,4], "Z": [31,1,2,4,8,16,31],
	"0": [14,17,19,21,25,17,14], "1": [4,12,4,4,4,4,14],
	"2": [14,17,1,2,4,8,31], "3": [30,1,1,14,1,1,30],
	"4": [2,6,10,18,31,2,2], "5": [31,16,16,30,1,1,30],
	"6": [14,16,16,30,17,17,14], "7": [31,1,2,4,8,8,8],
	"8": [14,17,17,14,17,17,14], "9": [14,17,17,15,1,1,14],
	" ": [0,0,0,0,0,0,0], ".": [0,0,0,0,0,12,12],
	"/": [1,2,2,4,8,8,16], "-": [0,0,0,31,0,0,0],
}
const ADS := [
	["KAZE", "A CLEANER", "TOMORROW", CYAN],
	["SILVA", "DATA SEES", "TOMORROW", BLUE],
	["NEXUS", "PEOPLE", "DATA", CYAN],
	["BETTER", "BRIGHTER", "CITIES", PINK],
	["CTRL", "A BETTER", "YOU", PINK],
	["WATCH", "ANALYZE", "REPEAT", CYAN],
	["ALL MOVES", "LEAVE", "A TRACE", BLUE],
	["PRIVACY", "WAS A", "NICE LIE", PINK],
]

var solid_material := ShaderMaterial.new()
var light_material := ShaderMaterial.new()
var guide_material := ShaderMaterial.new()
var road_material := ShaderMaterial.new()
var sign_materials: Array[ShaderMaterial] = []
var pool_materials: Array[ShaderMaterial] = []
var batches := {}
var geometry_origin := Vector3.ZERO
var building_forms := {}
var campus_cell := Vector2i(-100, -100)
var parcel_spans := {}
var occupied_cells := {}
# Street life: a few cars cruising the free lanes, and the skyrail train passing now and then.
const CAR_SPEED := 1.9  # units per second: a block in about six seconds
const TRAIN_SPEED := 7.5
const TRAIN_INTERVAL := 34.0
var grid_rows := 0
var grid_cols := 0
var free_vertical: Array[int] = []  # column lines (x = c * PITCH - PITCH / 2) no merged parcel crosses
var free_horizontal: Array[int] = []
var traffic: Array[Dictionary] = []
var train: Node3D
var train_span := 0.0
var train_clock := 1.0  # the first train shows up as the city appears
var train_direction := 1.0
var train_running := false
var muted_materials := {}
var geometry_visibility := 1.0
var streets := {}
var streets_finished := false
var triangle_count := 0
var mesh_count := 0
var rng := RandomNumberGenerator.new()
var city_center := Vector3.ZERO
var grade_material: ShaderMaterial
var saturation_tween: Tween
var world_saturation := 1.0

func _init() -> void:
	solid_material.shader = preload("res://voxel_surface.gdshader")
	light_material.shader = preload("res://voxel_light.gdshader")
	guide_material.shader = preload("res://entrance_pulse.gdshader")
	road_material.shader = preload("res://wet_street.gdshader")
	for i in ADS.size():
		var mat := ShaderMaterial.new()
		mat.shader = preload("res://neon_sign.gdshader")
		mat.set_shader_parameter("artwork", _advertisement(i))
		sign_materials.append(mat)
	for i in ADS.size():
		var mat := ShaderMaterial.new()
		mat.shader = preload("res://neon_sign.gdshader")
		mat.set_shader_parameter("artwork", _landscape_ad(i))
		sign_materials.append(mat)
	for color in [CYAN, PINK, BLUE, AMBER]:
		var mat := ShaderMaterial.new()
		mat.shader = preload("res://neon_pool.gdshader")
		mat.set_shader_parameter("tint", color)
		pool_materials.append(mat)

func dress_world() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.0015, 0.003, 0.007)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("8d9db6")
	env.ambient_light_energy = 0.23
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	# One controlled screen bloom below the HUD; no second post-processing glow.
	env.glow_enabled = false
	env.fog_enabled = true
	env.fog_light_color = Color(0.009, 0.015, 0.028)
	env.fog_density = 0.0018
	var world := WorldEnvironment.new()
	world.environment = env
	add_child(world)
	var moon := DirectionalLight3D.new()
	moon.rotation_degrees = Vector3(-52, -28, 0)
	moon.light_color = Color("acb8cf")
	moon.light_energy = 0.4
	moon.shadow_enabled = "--low-fx" not in OS.get_cmdline_user_args()
	moon.directional_shadow_max_distance = 100.0
	moon.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	moon.shadow_bias = 0.12
	moon.shadow_normal_bias = 1.8
	add_child(moon)
	# Always retain the world-only grade so the 0 PA state also works in low FX.
	var grade_layer := CanvasLayer.new()
	grade_layer.layer = 0
	add_child(grade_layer)
	var grade := ColorRect.new()
	grade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	grade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	grade_material = ShaderMaterial.new()
	grade_material.shader = preload("res://city_grade.gdshader")
	if "--low-fx" in OS.get_cmdline_user_args():
		grade_material.set_shader_parameter("bloom_strength", 0.0)
	grade.material = grade_material
	grade_layer.add_child(grade)

func set_actions_exhausted(exhausted: bool) -> void:
	var target := 0.0 if exhausted else 1.0
	if grade_material == null or is_equal_approx(world_saturation, target):
		return
	if saturation_tween != null:
		saturation_tween.kill()
	saturation_tween = create_tween()
	saturation_tween.tween_method(func(value: float):
		world_saturation = value
		grade_material.set_shader_parameter("saturation", value), world_saturation, target, 0.45)

func build(grid: Array) -> void:
	var rows := grid.size()
	var cols: int = grid[0].size()
	var origins := {}
	for r in rows:
		for c in cols:
			if grid[r][c] != null:
				origins[grid[r][c]] = Vector2i(c, r)
				occupied_cells[Vector2i(c, r)] = grid[r][c]
	var suppressed_crossings := []
	for id in ["hospital", "victim_street", "cabaret"]:
		if not origins.has(id):
			continue
		var origin: Vector2i = origins[id]
		var direction := Vector2i.DOWN if id == "cabaret" else Vector2i.RIGHT
		var next := origin + direction
		if next.x < cols and next.y < rows and not occupied_cells.has(next):
			occupied_cells[next] = id
			parcel_spans[id] = Vector2i(1, 2) if id == "cabaret" else Vector2i(2, 1)
			if id == "hospital":
				campus_cell = origin
			if direction == Vector2i.RIGHT:
				suppressed_crossings.append(origin + Vector2i.RIGHT)
				suppressed_crossings.append(origin + Vector2i.ONE)
			else:
				suppressed_crossings.append(origin + Vector2i.DOWN)
				suppressed_crossings.append(origin + Vector2i.ONE)
	city_center = Vector3((cols - 1) * PITCH / 2.0, 0, (rows - 1) * PITCH / 2.0)
	grid_rows = rows
	grid_cols = cols
	var blocked_columns := []
	var blocked_rows := []
	for id in parcel_spans:
		if parcel_spans[id].x == 2:
			blocked_columns.append(origins[id].x + 1)
		else:
			blocked_rows.append(origins[id].y + 1)
	for c in cols + 1:
		if c not in blocked_columns:
			free_vertical.append(c)
	for r in rows + 1:
		if r not in blocked_rows:
			free_horizontal.append(r)
	_begin()
	_box(city_center + Vector3(0, -0.16, 0), Vector3((cols + 4) * PITCH, 0.25, (rows + 4) * PITCH), Color("182433"), "road")
	for r in range(-1, rows + 2):
		for c in range(-1, cols + 2):
			if Vector2i(c, r) in suppressed_crossings:
				continue  # no four-way junction at the middle of the merged parcel
			var near_playable := false
			for offset in [Vector2i.ZERO, Vector2i.LEFT, Vector2i.UP, -Vector2i.ONE]:
				near_playable = near_playable or occupied_cells.has(Vector2i(c, r) + offset)
			geometry_visibility = 1.0 if near_playable else 0.13
			var at := Vector3(c * PITCH - PITCH / 2.0, 0, r * PITCH - PITCH / 2.0)
			_crossing(at)
	geometry_visibility = 1.0
	_flush(self, "RoadNetwork")
	for r in range(-1, rows + 1):
		for c in range(-1, cols + 1):
			var at := Vector3(c * PITCH, 0, r * PITCH)
			var inside := r >= 0 and r < rows and c >= 0 and c < cols
			if inside and grid[r][c] != null:
				continue
			if inside and occupied_cells.has(Vector2i(c, r)):
				continue
			if inside:
				_plaza(at, c + r * 7)
				continue
			make_place("district_%d_%d" % [c, r], at, true)
	if "--no-transit" not in OS.get_cmdline_user_args():
		_transit(cols)
	_spawn_traffic(4 if "--low-fx" in OS.get_cmdline_user_args() else 9)
	if "--low-fx" not in OS.get_cmdline_user_args():
		for spec in [[Vector3(2.0, 0, 0.25), CYAN], [Vector3(1.0, 0, 1.25), PINK], [Vector3(2.0, 0, 1.7), AMBER]]:
			var light := OmniLight3D.new()
			light.position = spec[0] * PITCH + Vector3(0, 1.2, 0)
			light.light_color = spec[1]
			light.light_energy = 1.15
			light.omni_range = 5.5
			light.shadow_enabled = false
			add_child(light)

func make_place(id: String, at: Vector3, scenery: bool = false) -> Node3D:
	var root := Node3D.new()
	root.name = id
	root.position = at
	root.set_meta("decorative", scenery)
	var entrance := Vector3(0, 0.25, 3.35)
	if id == "hospital":
		entrance.x = 6.0
	elif id == "victim_street":
		entrance.x = 4.6
	elif id == "cabaret":
		entrance = Vector3(1.2, 0.25, 15.45) if parcel_spans.has(id) else Vector3(0, 0.25, 3.35)
	root.set_meta("entrance", entrance)
	add_child(root)
	var h := absi(hash(id))
	rng.seed = h
	var height := 4.6 + float(h % 9) * 1.05
	if scenery and h % 3 != 0:
		height = 2.6 + float(h % 4) * 0.8
	if id in ["bar", "cabaret", "den", "restaurant"]:
		height = 3.2 + float(h % 3) * 0.6
	elif id == "alley" or id == "crime_scene":
		height = 3.4
	elif id == "police" or id == "cctv":
		height = 10.2
	elif id == "victim_street":
		height = 8.0
	elif id == "victim_house" or id == "promenade":
		height = 6.7
	elif id in ["lab", "morgue"]:
		height = 4.6
	elif id == "hospital":
		height = 5.4
	var color: Color = PALETTES[h % PALETTES.size()]
	var ad := h % ADS.size()
	var accent: Color = ADS[ad][3]
	if id == "bar":
		accent = CYAN
	elif id == "restaurant":
		accent = AMBER
	elif id == "cabaret" or id == "den":
		accent = PINK
	_begin()
	var parcel: Vector2i = parcel_spans.get(id, Vector2i.ONE)
	var parcel_width := (parcel.x - 1) * PITCH + 7.6
	var parcel_depth := (parcel.y - 1) * PITCH + 7.6
	geometry_origin = Vector3((parcel_width - 7.6) / 2.0, 0, (parcel_depth - 7.6) / 2.0)
	_pavement(parcel_width, parcel_depth)
	_street_props(h, accent, parcel_width, parcel_depth, scenery)
	if id == "crime_scene":
		# Small static voxel drops on the pavement, no imported texture.
		for drop in [[Vector2(-1.3, 2.8), 0.22], [Vector2(-0.9, 2.45), 0.14], [Vector2(-0.5, 2.2), 0.10], [Vector2(-1.65, 2.6), 0.12], [Vector2(-1.1, 3.05), 0.09]]:
			var point: Vector2 = drop[0]
			var width: float = drop[1]
			_box(Vector3(point.x, 0.175, point.y), Vector3(width, 0.012, width * 0.75), Color("9d253b"))
	geometry_origin = Vector3.ZERO
	_flush(root, "Streetscape")
	var architecture := Node3D.new()
	architecture.name = "Building"
	root.add_child(architecture)
	var recipe := _building_recipe(id, h, height)
	var volumes: Array = recipe["volumes"]
	var hero_index: int = recipe["hero"]
	var hero: Dictionary = volumes[hero_index]
	building_forms[id] = {"root": root, "shape": recipe["shape"], "volumes": volumes}
	_begin()
	for i in volumes.size():
		var volume: Dictionary = volumes[i]
		_volume(architecture, volume["at"], volume["size"], color.lightened(i * 0.035), h + i * 71, accent, ad, i == hero_index)
	if recipe["shape"] == "courtyard" or recipe["shape"] == "long_courtyard":
		_courtyard(accent, h)
		if recipe["shape"] == "long_courtyard":
			_box(Vector3(0.9, 0.22, 5.5), Vector3(3.1, 0.12, 7.0), CONCRETE.darkened(0.25))
			for z in [3.3, 5.0, 6.7]:
				_tree(Vector3(1.25, 0.2, z), h + int(z))
				_person(Vector3(0.0, 0.24, z), h + int(z) * 7)
			for x in [-0.3, 2.7]:
				_box(Vector3(x, 1.05, 14.7), Vector3(0.16, 1.8, 0.16), DARK)
			_box(Vector3(1.2, 2.0, 14.7), Vector3(3.2, 0.15, 0.28), DARK)
			_box(Vector3(1.2, 2.08, 14.86), Vector3(3.1, 0.055, 0.055), PINK, "light")
	elif recipe["shape"] == "twins":
		_box(Vector3(0.1, height * 0.42, -0.5), Vector3(1.15, 0.18, 1.0), CONCRETE.darkened(0.3))
		_box(Vector3(0.1, height * 0.42 + 0.25, 0.03), Vector3(1.15, 0.055, 0.05), accent, "light")
	elif recipe["shape"] == "campus":
		# A recessed entrance court and planted terrace break up the long hospital frontage.
		for i in 4:
			_box(Vector3(1.3 + i * 2.8, 0.35, 2.9), Vector3(1.6, 0.3, 0.6), DARK)
			_box(Vector3(1.3 + i * 2.8, 0.53, 2.9), Vector3(1.4, 0.07, 0.5), Color("315041"))
		_box(Vector3(8.2, 3.8, 1.6), Vector3(1.15, 0.23, 0.04), CYAN, "light")
		_box(Vector3(8.2, 3.8, 1.62), Vector3(0.23, 1.15, 0.04), CYAN, "light")
		# A genuinely separate medical-services entrance on the same frontage.
		_box(Vector3(10.2, 1.05, 2.15), Vector3(1.45, 2.1, 0.08), Color("162533"))
		for x in [9.4, 11.0]:
			_box(Vector3(x, 1.08, 2.23), Vector3(0.06, 2.15, 0.05), CYAN, "light")
		_box(Vector3(10.2, 2.18, 2.23), Vector3(1.65, 0.06, 0.05), CYAN, "light")
	elif recipe["shape"] == "terraced":
		var terrace_y: float = volumes[0]["size"].y + 0.6
		for x in [-0.45, 1.4]:
			_box(Vector3(x, terrace_y, 1.65), Vector3(1.25, 0.3, 0.62), DARK)
			for i in 4:
				_box(Vector3(x - 0.42 + i * 0.28, terrace_y + 0.26, 1.65), Vector3(0.24, 0.28, 0.45), Color("39554e"))
		_box(Vector3(2.05, terrace_y, 0.7), Vector3(0.64, 0.15, 0.33), CONCRETE.darkened(0.3))
	_flush(architecture, "Architecture")
	_pool(root, Vector3(0, -0.014, 4.9), Vector2(4.8, 2.8), ad % 3)
	_pool(root, Vector3(4.9, -0.012, 0), Vector2(2.8, 4.8), (ad + 1) % 3)
	if h % 5 == 0 or id == "police":
		var mount := Node3D.new()
		mount.position = hero["at"]
		architecture.add_child(mount)
		_roof_ad(mount, hero["size"].y, ad, minf(hero["size"].x * 0.92, 4.8))
	if not scenery:
		var shop_mount := Node3D.new()
		var street_volume: Dictionary = volumes[0]
		shop_mount.position = street_volume["at"] + Vector3(0, 0, street_volume["size"].z / 2.0 - 3.0 + 0.1)
		shop_mount.scale.x = minf(street_volume["size"].x / 5.0, 1.0)
		architecture.add_child(shop_mount)
		_shop_sign(shop_mount, id, accent)
		var marker := MeshInstance3D.new()
		marker.name = "Box"
		var box := BoxMesh.new()
		box.size = Vector3(0.75, 0.045, 0.45)
		marker.mesh = box
		marker.position = Vector3(0.9, 0.35, 3.0)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = accent.darkened(0.45)
		marker.set_surface_override_material(0, mat)
		root.add_child(marker)
		var label := Label3D.new()
		label.name = "Label"
		label.position = Vector3(0, height + 0.9, 0)
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.font_size = 28
		label.pixel_size = 0.012
		label.set_meta("base", 0.012)
		label.modulate = CYAN.lerp(Color.WHITE, 0.35)
		label.outline_size = 8
		label.add_to_group("labels")
		root.add_child(label)
	building_forms[id]["meshes"] = architecture.find_children("*", "MeshInstance3D", true, false)
	building_forms[id]["labels"] = architecture.find_children("*", "Label3D", true, false)
	building_forms[id]["fade_materials"] = {}
	building_forms[id]["opacity"] = 1.0
	return root

func update_camera_fade(camera: Camera3D, target: Vector3, protected: String, delta: float) -> void:
	var forward := Vector3(camera.position.x - target.x, 0, camera.position.z - target.z).normalized()
	var candidates: Array = []
	var strength := clampf((40.0 - camera.size) / 13.0, 0.0, 1.0)
	for id in building_forms:
		var form: Dictionary = building_forms[id]
		var closest := INF
		var in_front := false
		for volume in form.volumes:
			var at: Vector3 = form.root.position + volume.at
			var dimensions: Vector3 = volume.size
			var bounds := AABB(at - Vector3(dimensions.x / 2, 0, dimensions.z / 2), dimensions + Vector3(0, 2.0, 0))
			var nearest := Vector3(clampf(camera.position.x, bounds.position.x, bounds.end.x), clampf(camera.position.y, bounds.position.y, bounds.end.y), clampf(camera.position.z, bounds.position.z, bounds.end.z))
			closest = minf(closest, camera.position.distance_to(nearest))
			in_front = in_front or (at - target).dot(forward) > 3.5
		if id != protected and in_front and closest < camera.size * 1.18 and strength > 0.0:
			candidates.append({"id": id, "distance": closest})
	candidates.sort_custom(func(a, b): return a.distance < b.distance)
	var wanted := {}
	for i in mini(3, candidates.size()):
		var candidate: Dictionary = candidates[i]
		var near := 1.0 - smoothstep(camera.size * 0.78, camera.size * 1.18, candidate.distance)
		wanted[candidate.id] = 1.0 - near * strength * 0.8
	for id in building_forms:
		var form: Dictionary = building_forms[id]
		var opacity := lerpf(float(form.opacity), float(wanted.get(id, 1.0)), 1.0 - exp(-delta * 8.0))
		if absf(opacity - float(form.opacity)) < 0.001 and absf(opacity - float(wanted.get(id, 1.0))) < 0.002:
			continue
		form.opacity = opacity
		_apply_building_opacity(form, opacity)

func _apply_building_opacity(form: Dictionary, opacity: float) -> void:
	for node in form.meshes:
		if not node.has_meta("opaque_material"):
			node.set_meta("opaque_material", node.material_override)
			node.set_meta("opaque_shadow", node.cast_shadow)
		var original: ShaderMaterial = node.get_meta("opaque_material")
		if opacity > 0.995:
			node.material_override = original
			node.cast_shadow = node.get_meta("opaque_shadow")
			continue
		if not form.fade_materials.has(original):
			var ghost := original.duplicate() as ShaderMaterial
			if original.shader == solid_material.shader:
				ghost.shader = preload("res://building_fade_surface.gdshader")
			elif original.shader == light_material.shader:
				ghost.shader = preload("res://building_fade_light.gdshader")
			else:
				ghost.shader = preload("res://building_fade_sign.gdshader")
			form.fade_materials[original] = ghost
		var material: ShaderMaterial = form.fade_materials[original]
		material.set_shader_parameter("fade_opacity", opacity)
		node.material_override = material
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for label in form.labels:
		label.modulate.a = opacity

func navigation_marker(at: Vector3, current: bool = false, accent: Color = Color.TRANSPARENT) -> Node3D:
	var root := Node3D.new()
	root.position = at
	var color := Color("ffd386") if current else CYAN
	if accent.a > 0:
		color = accent
	_begin()
	# Illuminated doormat and two chevrons point towards the actual entrance.
	for x in [-0.85, 0.85]:
		_box(Vector3(x, 0.035, 0), Vector3(0.06, 0.025, 1.65), color, "light")
	for z in [-0.8, 0.8]:
		_box(Vector3(0, 0.035, z), Vector3(1.75, 0.025, 0.06), color, "light")
	for z in [0.25, -0.2]:
		_beam(Vector3(-0.38, 0.06, z + 0.22), Vector3(0, 0.06, z - 0.15), 0.075, color, "light")
		_beam(Vector3(0, 0.06, z - 0.15), Vector3(0.38, 0.06, z + 0.22), 0.075, color, "light")
	_flush(root, "EntranceGuide")
	return root

func _building_recipe(id: String, h: int, height: float) -> Dictionary:
	if id == "victim_street" and parcel_spans.has(id):
		return {"shape": "residential_sprawl", "hero": 0, "volumes": [
			{"at": Vector3(-0.9, 0, -0.2), "size": Vector3(3.3, height, 5.6)},
			{"at": Vector3(PITCH / 2.0, 0, 1.25), "size": Vector3(PITCH + 5.5, 2.3, 2.1)},
			{"at": Vector3(PITCH - 0.8, 0, -1.05), "size": Vector3(3.4, 4.3, 2.6)}]}
	if id == "cabaret" and parcel_spans.has(id):
		return {"shape": "long_courtyard", "hero": 0, "volumes": [
			{"at": Vector3(0, 0, -1.45), "size": Vector3(6.0, height, 2.6)},
			{"at": Vector3(-1.75, 0, PITCH / 2.0), "size": Vector3(2.5, height * 0.8, PITCH + 2.3)},
			{"at": Vector3(1.7, 0, PITCH - 1.5), "size": Vector3(2.1, height * 0.66, 5.6)}]}
	if id == "hospital" and campus_cell.x >= 0:
		return {"shape": "campus", "hero": 1, "volumes": [
			{"at": Vector3(PITCH / 2.0, 0, -0.1), "size": Vector3(PITCH + 5.9, 2.15, 4.4)},
			{"at": Vector3(4.2, 2.15, -0.35), "size": Vector3(9.0, height - 2.15, 3.5)},
			{"at": Vector3(PITCH + 1.0, 0, -0.1), "size": Vector3(2.6, 4.1, 5.6)}]}
	var shapes := ["crossbar", "longitudinal", "courtyard", "terraced", "twins", "corner"]
	var shape: String = shapes[h % shapes.size()]
	var landmarks := {"bar": "crossbar", "cabaret": "courtyard", "den": "corner", "restaurant": "corner",
		"hospital": "terraced", "police": "terraced", "cctv": "longitudinal",
		"victim_street": "longitudinal", "victim_house": "crossbar", "promenade": "crossbar", "lab": "corner", "morgue": "terraced",
		"crime_scene": "courtyard", "alley": "twins"}
	shape = landmarks.get(id, shape)
	var volumes: Array = []
	var hero := 0
	match shape:
		"crossbar":
			volumes = [
				{"at": Vector3(0, 0, -1.0), "size": Vector3(6.0, height, 3.0)},
				{"at": Vector3(1.5, 0, 1.35), "size": Vector3(2.5, minf(2.2, height * 0.55), 1.7)}]
		"longitudinal":
			volumes = [
				{"at": Vector3(-0.9, 0, -0.2), "size": Vector3(3.3, height, 5.6)},
				{"at": Vector3(1.65, 0, 1.2), "size": Vector3(1.8, minf(2.8, height * 0.5), 2.8)}]
		"courtyard":
			volumes = [
				{"at": Vector3(0, 0, -1.65), "size": Vector3(6.0, height, 2.4)},
				{"at": Vector3(-1.95, 0, 0.9), "size": Vector3(2.1, height * 0.8, 3.8)}]
		"terraced":
			var podium := minf(2.2, height * 0.4)
			volumes = [
				{"at": Vector3(0, 0, -0.25), "size": Vector3(5.9, podium, 5.1)},
				{"at": Vector3(-0.85, podium, -0.85), "size": Vector3(3.6, height - podium, 3.6)},
				{"at": Vector3(1.95, podium, -1.6), "size": Vector3(1.0, 0.65, 1.7)}]
			hero = 1
		"twins":
			volumes = [
				{"at": Vector3(-1.6, 0, -0.4), "size": Vector3(2.5, height, 4.8)},
				{"at": Vector3(1.45, 0, 0.15), "size": Vector3(2.3, height * 0.75, 3.7)}]
		"corner":
			volumes = [
				{"at": Vector3(-1.0, 0, -0.9), "size": Vector3(3.8, height, 3.8)},
				{"at": Vector3(0.0, 0, 1.75), "size": Vector3(5.8, minf(2.4, height * 0.65), 1.5)},
				{"at": Vector3(1.85, 0, -1.0), "size": Vector3(1.7, minf(3.1, height * 0.75), 3.9)}]
	return {"shape": shape, "volumes": volumes, "hero": hero}

func _volume(root: Node3D, at: Vector3, size: Vector3, color: Color, h: int, accent: Color, ad: int, hero: bool) -> void:
	geometry_origin = at
	var width := size.x
	var height := size.y
	var depth := size.z
	_box(Vector3(0, height / 2.0 + 0.18, 0), size, color.darkened(0.12))
	for x in [-width / 2.0 + 0.12, width / 2.0 - 0.12]:
		_box(Vector3(x, height / 2.0 + 0.18, 0), Vector3(0.2, height, depth + 0.06), color.lightened(0.04))
	_facade(width, depth, height, color, h, hero)
	var front := depth / 2.0
	if at.y == 0.0:
		_box(Vector3(0, 0.76, front + 0.04), Vector3(width - 0.3, 1.1, 0.12), DARK)
		var columns := maxi(3, int((width - 0.5) / 0.48))
		for i in columns:
			var x := -width / 2.0 + 0.4 + i * (width - 0.8) / (columns - 1)
			_box(Vector3(x, 0.69, front + 0.12), Vector3(0.3, 0.85, 0.03), AMBER.darkened(0.18) if i % 3 else accent.darkened(0.3), "light")
			_box(Vector3(x + 0.18, 0.77, front + 0.14), Vector3(0.05, 1.1, 0.065), DARK)
		_box(Vector3(0, 1.42, front + 0.12), Vector3(width + 0.15, 0.17, 0.42), color.lightened(0.08))
		_box(Vector3(0, 1.53, front + 0.35), Vector3(width - 0.4, 0.11, 0.03), accent * 0.8, "light")
	_rooftop(width, depth, height, h, not _is_decorative(root))
	if hero:
		for y in range(5, int(height * 3.0)):
			_box(Vector3(width / 2.0 + 0.04, float(y) / 3.0, front + 0.04), Vector3(0.065, 0.23, 0.065), accent, "light")
		_box(Vector3(-width / 2.0 - 0.035, height / 2.0, -depth / 2.0 + 0.3), Vector3(0.075, height, 0.075), CONCRETE.darkened(0.35))
	geometry_origin = Vector3.ZERO
	if hero and height > 5.6:
		var panel_width := minf(width * 0.66, 3.0)
		_panel(root, at + Vector3(0, height * 0.58, front + 0.22), Vector2(panel_width, height * 0.62), ad)
		if depth > 4.0:
			_panel(root, at + Vector3(width / 2.0 + 0.2, height * 0.61, -0.1), Vector2(minf(depth * 0.54, 2.8), height * 0.6), (ad + 1) % ADS.size(), PI / 2.0)
	elif hero and height > 2.4:
		_panel(root, at + Vector3(0, height * 0.69, front + 0.22), Vector2(minf(width - 0.35, 3.85), minf(height * 0.35, 1.4)), ad + ADS.size())
	if h % 5 == 0 and width > 2.0:
		geometry_origin = at
		for i in 3:
			_box(Vector3(width / 2.0 + 0.17, 1.8 + i * 0.7, 0), Vector3(0.3, 0.32, 0.6), CONCRETE.darkened(0.25))
		geometry_origin = Vector3.ZERO

func _courtyard(accent: Color, h: int) -> void:
	_box(Vector3(0.9, 0.22, 1.15), Vector3(2.6, 0.12, 2.7), CONCRETE.darkened(0.25))
	_box(Vector3(1.15, 0.42, 0.65), Vector3(1.35, 0.3, 0.62), DARK)
	_box(Vector3(1.15, 0.6, 0.65), Vector3(1.2, 0.05, 0.5), Color("314a3f"))
	_tree(Vector3(1.0, 0.2, 0.5), h)
	_box(Vector3(1.35, 0.55, 2.25), Vector3(1.25, 0.17, 0.34), DARK)
	_box(Vector3(2.65, 1.0, 1.7), Vector3(0.25, 1.5, 0.25), DARK)
	_box(Vector3(2.65, 1.5, 1.85), Vector3(0.15, 0.5, 0.04), accent, "light")

func _plaza(at: Vector3, h: int) -> void:
	var root := Node3D.new()
	root.name = "PocketGarden"
	root.position = at
	root.set_meta("decorative", true)
	add_child(root)
	rng.seed = h + 97
	_begin()
	_box(Vector3(0, 0.08, 0), Vector3(7.6, 0.16, 7.6), Color("515c67"))
	for x in [-2.5, 2.5]:
		for z in [-2.4, 0.0, 2.4]:
			_tree(Vector3(x, 0.18, z), h)
			_person(Vector3(x - 0.7, 0.18, z), h + int(z))
	for i in 7:
		_box(Vector3(-1.5 + i * 0.5, 0.18, 0), Vector3(0.46, 0.035, 6.8), CONCRETE.lightened(0.1))
	_box(Vector3(0, 0.35, 0), Vector3(1.5, 0.38, 1.5), DARK)
	_box(Vector3(0, 0.57, 0), Vector3(1.2, 0.07, 1.2), CYAN * 0.35, "light")
	for i in 5:
		_box(Vector3(sin(float(i)) * 0.34, 0.75 + i * 0.27, cos(float(i)) * 0.34), Vector3(0.35, 0.3, 0.35), CYAN * (0.6 + i * 0.08), "light")
	for z in [-3.2, 3.2]:
		for x in [-1.7, 1.7]:
			_lamp(Vector3(x, 0.18, z))
			_box(Vector3(x, 0.48, z - 0.35), Vector3(1.0, 0.14, 0.34), DARK)
	_flush(root, "Garden")
	_pool(root, Vector3(0, 0.18, 0), Vector2(4.0, 4.0), 0)

func make_house(at: Vector3) -> Node3D:
	var root := Node3D.new()
	root.position = at
	add_child(root)
	_begin()
	_box(Vector3(0, 0.63, 0), Vector3(0.75, 0.95, 0.35), DARK)
	_box(Vector3(0, 1.16, 0.08), Vector3(0.84, 0.12, 0.48), CONCRETE)
	_box(Vector3(0.27, 0.63, 0.2), Vector3(0.04, 0.85, 0.04), CYAN, "light")
	_flush(root, "Doorframe")
	var box := MeshInstance3D.new()
	box.name = "Box"
	box.mesh = BoxMesh.new()
	box.mesh.size = Vector3(0.5, 0.54, 0.025)
	box.position = Vector3(0, 0.75, 0.19)
	box.set_surface_override_material(0, StandardMaterial3D.new())
	root.add_child(box)
	var label := Label3D.new()
	label.name = "Label"
	label.position = Vector3(0, 1.45, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.font_size = 22
	label.pixel_size = 0.009
	label.set_meta("base", 0.009)
	label.add_to_group("labels")
	root.add_child(label)
	return root

func _facade(width: float, depth: float, height: float, color: Color, h: int, hero: bool = true) -> void:
	var floors := maxi(0, int((height - 1.6) / 0.66))
	for side in 2:
		var span := width if side == 0 else depth
		var columns := maxi(2, int(span / 0.57))
		var pitch := span / columns
		for floor_index in floors:
			var y := 1.93 + float(floor_index) * 0.66
			for col in columns:
				var along := -span / 2.0 + pitch * (col + 0.5)
				var v := rng.randf()
				var tile := color.lightened(v * 0.13) if v > 0.45 else color.darkened(v * 0.32)
				var at := Vector3(along, y, depth / 2.0 + 0.02) if side == 0 else Vector3(width / 2.0 + 0.02, y, -along)
				_face_tile(at, Vector2(pitch - 0.035, 0.6), tile, side)
				var outside_ad := not hero or side == 1 or absf(along) > width * 0.33
				if outside_ad and rng.randf() < 0.48:
					var warm := AMBER if rng.randf() < 0.78 else CYAN
					var window_at := at + (Vector3(0, 0, 0.016) if side == 0 else Vector3(0.016, 0, 0))
					_face_tile(window_at, Vector2(minf(pitch * 0.55, 0.3), 0.35), warm * rng.randf_range(0.5, 1.0), side, "light")
					_box(window_at + Vector3(0, -0.21, 0), Vector3(0.38, 0.055, 0.12) if side == 0 else Vector3(0.12, 0.055, 0.38), DARK)
		for floor_index in range(0, floors, 3):
			var y := 1.62 + floor_index * 0.66
			_box(Vector3(0, y, depth / 2.0 + 0.065) if side == 0 else Vector3(width / 2.0 + 0.065, y, 0), Vector3(width, 0.09, 0.13) if side == 0 else Vector3(0.13, 0.09, depth), color.darkened(0.32))
	for side in [-1.0, 1.0]:
		_box(Vector3(side * (width / 2.0 - 0.15), height / 2.0, 0), Vector3(0.065, height, depth), color.darkened(0.22))

func _rooftop(width: float, depth: float, height: float, h: int, detailed: bool = true) -> void:
	var y := height + 0.22
	_box(Vector3(0, y, 0), Vector3(width + 0.18, 0.25, depth + 0.18), CONCRETE.darkened(0.46))
	_box(Vector3(0, y + 0.13, 0), Vector3(width - 0.4, 0.08, depth - 0.4), DARK)
	var columns := maxi(1, int((width - 0.4) / 0.7))
	var rows := maxi(1, int((depth - 0.4) / 0.7))
	for row in rows:
		for col in columns:
			var tile_color := DARK.lightened(float((h + row * 3 + col * 7) % 5) * 0.006)
			var pitch_x := (width - 0.4) / columns
			var pitch_z := (depth - 0.4) / rows
			_flat_mark(Vector3(-width / 2.0 + 0.2 + (col + 0.5) * pitch_x, y + 0.175, -depth / 2.0 + 0.2 + (row + 0.5) * pitch_z), Vector2(pitch_x - 0.025, pitch_z - 0.025), tile_color)
	for x in [-width / 2.0 - 0.05, width / 2.0 + 0.05]:
		_box(Vector3(x, y + 0.25, 0), Vector3(0.15, 0.35, depth + 0.2), CONCRETE.darkened(0.18))
	for z in [-depth / 2.0 - 0.05, depth / 2.0 + 0.05]:
		_box(Vector3(0, y + 0.25, z), Vector3(width + 0.2, 0.35, 0.15), CONCRETE.darkened(0.18))
	var area := width * depth
	for i in clampi(int(area / 3.2), 1, 8 if detailed else 3):
		var at := Vector3(rng.randf_range(-width * 0.32, width * 0.32), y + 0.32, rng.randf_range(-depth * 0.32, depth * 0.32))
		var size := Vector3(minf(width * 0.4, rng.randf_range(0.35, 0.85)), rng.randf_range(0.2, 0.5), minf(depth * 0.4, rng.randf_range(0.4, 0.85)))
		_box(at, size, CONCRETE.darkened(0.23 + rng.randf() * 0.23))
		_box(at + Vector3(0, size.y / 2.0 + 0.025, 0), Vector3(size.x * 0.68, 0.06, size.z * 0.68), DARK)
		for j in 2:
			_box(at + Vector3(-size.x * 0.23 + j * size.x * 0.46, size.y / 2.0 + 0.065, 0), Vector3(0.055, 0.03, size.z * 0.62), CONCRETE.darkened(0.4))
	if area > 10.0:
		_box(Vector3(-width * 0.17, y + 0.52, -depth * 0.22), Vector3(minf(width * 0.3, 1.15), 0.9, minf(depth * 0.3, 1.1)), PALETTES[h % PALETTES.size()])
		for j in 5:
			_box(Vector3(width * 0.15 + j * 0.16, y + 0.13 + j * 0.06, -depth * 0.22), Vector3(0.15, 0.1 + j * 0.12, 0.6), CONCRETE.darkened(0.3))
		_box(Vector3(0, y + 0.25, depth * 0.16), Vector3(width * 0.58, 0.22, 0.24), CONCRETE.darkened(0.45))
		_box(Vector3(width * 0.28, y + 0.25, 0), Vector3(0.24, 0.22, depth * 0.4), CONCRETE.darkened(0.45))
		for i in 5:
			_box(Vector3(-width * 0.24 + i * width * 0.12, y + 0.37, depth * 0.16), Vector3(0.04, 0.04, 0.28), DARK.lightened(0.08))
	if area > 12.0 and h % 2 == 0:
		var aerial := Vector3(-width * 0.32, y + 1.05, -depth * 0.3)
		_box(aerial, Vector3(0.085, 2.0, 0.085), DARK)
		_box(aerial + Vector3(0, 1.05, 0), Vector3(0.12, 0.12, 0.12), Color("ff3c69"), "light")
		for i in 2:
			_box(aerial + Vector3(0, 0.25 + i * 0.3, 0), Vector3(0.4 + i * 0.2, 0.065, 0.065), CONCRETE)

func _pavement(width: float, depth: float = 7.6) -> void:
	_box(Vector3(0, 0.08, 0), Vector3(width, 0.16, depth), Color("485361"))
	var columns := int(width / 0.38)
	for i in columns:
		var x := -width / 2.0 + (i + 0.5) * width / columns
		for z in [-depth / 2.0, depth / 2.0]:
			_box(Vector3(x, 0.19, z), Vector3(width / columns - 0.035, 0.12, 0.16), Color("6a7580"))
		for j in 2:
			_flat_mark(Vector3(x, 0.166, depth / 2.0 - 0.78 + j * 0.39), Vector2(width / columns - 0.035, 0.35), Color("52606b").lightened(float((i + j) % 3) * 0.02))
	var rows := int(depth / 0.38)
	for i in rows:
		var z := -depth / 2.0 + (i + 0.5) * depth / rows
		for x in [-width / 2.0, width / 2.0]:
			_box(Vector3(x, 0.19, z), Vector3(0.16, 0.12, 0.34), Color("6a7580"))
		for j in 2:
			_flat_mark(Vector3(width / 2.0 - 0.78 + j * 0.39, 0.166, z), Vector2(0.35, 0.34), Color("52606b").lightened(float((i + j) % 3) * 0.02))

func _street_props(h: int, accent: Color, width: float = 7.6, depth: float = 7.6, decorative: bool = false) -> void:
	for x in [-width / 2.0 + 0.3, width / 2.0 - 0.3]:
		for z in [-depth / 2.0 + 0.65, depth / 2.0 - 0.65]:
			_lamp(Vector3(x, 0.18, z))
	for i in 2:
		_tree(Vector3((-width / 2.0 + 0.5) * (1.0 if i == 0 else -1.0), 0.18, 0.3), h + i)
	var count := 3 if decorative else int(width / 1.08)
	for i in count:
		var at := Vector3(-width / 2.0 + 1.0 + i * (width - 2.0) / (count - 1) + rng.randf_range(-0.15, 0.15), 0.18, depth / 2.0 + rng.randf_range(-0.93, -0.35))
		if i == 4:
			continue
		_person(at, h + i)
	# Benches, bollards, a vending machine, and a bin.
	_box(Vector3(-2.0, 0.5, 3.06), Vector3(0.85, 0.15, 0.3), CONCRETE.darkened(0.25))
	_box(Vector3(-2.0, 0.7, 2.96), Vector3(0.85, 0.3, 0.09), DARK)
	_box(Vector3(2.91, 0.67, 1.6), Vector3(0.35, 1.0, 0.4), DARK)
	_box(Vector3(2.91, 0.85, 1.82), Vector3(0.26, 0.5, 0.03), accent, "light")
	for i in int(width / 1.35):
		_box(Vector3(-width / 2.0 + 0.8 + i * 1.35, 0.43, depth / 2.0 - 0.17), Vector3(0.1, 0.5, 0.1), DARK)
	# Parked along the kerb: the two lanes between the kerbs belong to the traffic.
	_car(Vector3(-1.5, 0.01, depth / 2.0 + 0.45), h, false)
	_car(Vector3(width / 2.0 + 0.45, 0.01, -1.0), h + 3, true)
	if h % 2 == 0:
		_car(Vector3(1.9, 0.01, depth / 2.0 + 3.95), h + 1, false)

func _person(at: Vector3, h: int, coat: Color = Color.TRANSPARENT) -> void:
	var clothing := [Color("293645"), Color("454050"), Color("82736a"), Color("253e4b")][absi(h) % 4] as Color
	if coat.a > 0.0:
		clothing = coat
	_box(at + Vector3(0, 0.28, 0), Vector3(0.16, 0.25, 0.12), clothing)
	_box(at + Vector3(0, 0.49, 0), Vector3(0.14, 0.16, 0.14), Color("b9947b"))
	_box(at + Vector3(0, 0.58, -0.02), Vector3(0.15, 0.05, 0.14), DARK)
	for x in [-0.045, 0.045]:
		_box(at + Vector3(x, 0.1, 0), Vector3(0.06, 0.2, 0.09), DARK)
	for x in [-0.11, 0.11]:
		_box(at + Vector3(x, 0.28, 0), Vector3(0.06, 0.2, 0.1), clothing)
	if h % 4 == 0:
		_box(at + Vector3(0, 0.72, 0), Vector3(0.5, 0.07, 0.45), PALETTES[absi(h) % 5])
		_box(at + Vector3(0.1, 0.54, 0), Vector3(0.025, 0.33, 0.025), CONCRETE)

func figure(at: Vector3, color: Color, h: int) -> Node3D:
	var root := Node3D.new()
	root.position = at
	_begin()
	_person(Vector3.ZERO, h, color)
	_flush(root, "VoxelFigure")
	return root

func detective_figure(at: Vector3, accent: Color, you: bool) -> Node3D:
	var root := Node3D.new()
	root.position = at
	_begin()
	var coat := accent.darkened(0.38)
	for x in [-0.11, 0.11]:
		_box(Vector3(x, 0.21, 0), Vector3(0.12, 0.4, 0.17), DARK)
		_box(Vector3(x, 0.04, 0.035), Vector3(0.14, 0.09, 0.25), DARK)
	_box(Vector3(0, 0.66, 0), Vector3(0.42, 0.65, 0.25), coat)
	_box(Vector3(0, 0.8, 0.14), Vector3(0.07, 0.38, 0.025), DARK)
	for x in [-0.26, 0.26]:
		_box(Vector3(x, 0.71, 0), Vector3(0.12, 0.43, 0.2), coat)
		_box(Vector3(x, 0.45, 0.015), Vector3(0.1, 0.13, 0.13), Color("cea389"))
	_box(Vector3(0, 1.1, 0), Vector3(0.28, 0.31, 0.26), Color("cea389"))
	_box(Vector3(0, 1.29, 0), Vector3(0.36, 0.13, 0.32), CONCRETE)
	_box(Vector3(0, 1.22, 0.02), Vector3(0.49, 0.055, 0.4), CONCRETE)
	_box(Vector3(0, 1.26, 0.166), Vector3(0.35, 0.035, 0.02), accent, "light")
	_box(Vector3(-0.13, 0.84, 0.142), Vector3(0.065, 0.09, 0.02), accent, "light")
	for i in 24:
		var angle := float(i) * TAU / 24.0
		var next := float(i + 1) * TAU / 24.0
		var radius := 0.62 if you else 0.44
		_beam(Vector3(cos(angle) * radius, 0.03, sin(angle) * radius), Vector3(cos(next) * radius, 0.03, sin(next) * radius), 0.045 if you else 0.025, accent, "light")
	_flush(root, "DetectiveFigure")
	return root

func _lamp(at: Vector3) -> void:
	_box(at + Vector3(0, 0.1, 0), Vector3(0.22, 0.2, 0.22), DARK)
	_box(at + Vector3(0, 1.12, 0), Vector3(0.075, 2.2, 0.075), DARK)
	_box(at + Vector3(0.15, 2.23, 0), Vector3(0.38, 0.09, 0.16), DARK)
	_box(at + Vector3(0.15, 2.18, 0), Vector3(0.27, 0.035, 0.13), AMBER, "light")
	# Baked-looking pavement light tiles, no per-lamp realtime light.
	_box(at + Vector3(0, 0.006, 0.2), Vector3(0.65, 0.006, 0.9), Color("6a6156"))

func _tree(at: Vector3, h: int) -> void:
	_box(at + Vector3(0, 0.15, 0), Vector3(0.8, 0.25, 0.8), DARK)
	_box(at + Vector3(0, 0.32, 0), Vector3(0.75, 0.08, 0.75), Color("273c34"))
	_box(at + Vector3(0, 0.75, 0), Vector3(0.12, 1.0, 0.12), Color("443948"))
	var blossom := Color("9656a1") if h % 3 else Color("445e56")
	for i in 11:
		var offset := Vector3(rng.randf_range(-0.4, 0.4), rng.randf_range(1.08, 1.85), rng.randf_range(-0.4, 0.4))
		_box(at + offset, Vector3(0.32, 0.31, 0.32), blossom.lightened(rng.randf() * 0.2))
		if i % 3 == 0:
			_box(at + offset + Vector3(0.17, 0, 0.17), Vector3(0.09, 0.09, 0.09), PINK * 0.75, "light")

func _car(at: Vector3, h: int, turn: bool, lit: bool = false) -> void:
	# Parked cars keep their lamps off; traffic drives with warm headlights and red tail lamps.
	var color := [Color("285368"), Color("433b55"), Color("273341"), Color("65676b")][absi(h) % 4] as Color
	var head := Color("fff1c4") if lit else Color("3c4752")
	var tail := Color("ff2f4f") if lit else Color("4a2630")
	var parts := [
		[Vector3(0, 0.25, 0), Vector3(1.05, 0.3, 0.49), color],
		[Vector3(-0.07, 0.49, 0), Vector3(0.54, 0.23, 0.43), DARK],
		[Vector3(-0.09, 0.61, 0), Vector3(0.48, 0.05, 0.46), color],
		[Vector3(0.23, 0.5, 0), Vector3(0.04, 0.17, 0.4), CYAN.darkened(0.55)],
	]
	for part in parts:
		var p: Vector3 = part[0]
		var s: Vector3 = part[1]
		_box(at + (Vector3(p.z, p.y, p.x) if turn else p), Vector3(s.z, s.y, s.x) if turn else s, part[2])
	for x in [-0.35, 0.35]:
		for z in [-0.26, 0.26]:
			var p := Vector3(x, 0.15, z)
			_box(at + (Vector3(p.z, p.y, p.x) if turn else p), Vector3(0.16, 0.23, 0.16), DARK)
	for z in [-0.16, 0.16]:
		var front := Vector3(0.54, 0.3, z)
		var back := Vector3(-0.54, 0.3, z)
		_box(at + (Vector3(front.z, front.y, front.x) if turn else front), Vector3(0.09, 0.07, 0.11), head, "light" if lit else "solid")
		_box(at + (Vector3(back.z, back.y, back.x) if turn else back), Vector3(0.06, 0.06, 0.09), tail, "light" if lit else "solid")

func _crossing(at: Vector3) -> void:
	# Zebra crossings sit at the four edges; tiny dashes leave the junction clear.
	for i in 10:
		var k := -1.8 + i * 0.4
		for sign_value in [-1.0, 1.0]:
			_flat_mark(at + Vector3(k, 0.009, sign_value * 2.65), Vector2(0.22, 0.7), Color("969aa2"))
			_flat_mark(at + Vector3(sign_value * 2.65, 0.009, k), Vector2(0.7, 0.22), Color("969aa2"))
	for i in 5:
		_flat_mark(at + Vector3(3.4 + i * 0.95, 0.008, 0), Vector2(0.36, 0.045), Color("b7a570"))
		_flat_mark(at + Vector3(0, 0.008, 3.4 + i * 0.95), Vector2(0.045, 0.36), Color("b7a570"))
	_box(at + Vector3(2.4, 0.92, 2.4), Vector3(0.06, 1.85, 0.06), DARK)
	_box(at + Vector3(2.4, 1.86, 2.4), Vector3(0.16, 0.38, 0.16), DARK)
	_box(at + Vector3(2.4, 1.96, 2.49), Vector3(0.09, 0.09, 0.03), Color("ff355c"), "light")
	_box(at + Vector3(2.49, 1.72, 2.4), Vector3(0.03, 0.09, 0.09), CYAN, "light")

func _transit(cols: int) -> void:
	var root := Node3D.new()
	root.name = "NexusSkyrail"
	root.position = Vector3((cols - 1) * PITCH / 2.0, 0, PITCH * 1.5)
	add_child(root)
	_begin()
	var length := (cols + 2) * PITCH
	_box(Vector3(0, 2.6, 0), Vector3(length, 0.32, 0.72), DARK)
	for z in [-0.31, 0.31]:
		_box(Vector3(0, 2.87, z), Vector3(length, 0.07, 0.065), CONCRETE)
		_box(Vector3(0, 2.65, z * 1.35), Vector3(length, 0.055, 0.05), CYAN * 0.65, "light")
	for i in cols + 2:
		var x := -length / 2.0 + PITCH / 2.0 + i * PITCH
		_box(Vector3(x, 1.25, 0), Vector3(0.45, 2.5, 0.45), CONCRETE.darkened(0.3))
	# The train lives in its own transform: animate() slides it along the viaduct.
	_flush(root, "Viaduct")
	train = Node3D.new()
	train.name = "Train"
	root.add_child(train)
	train_span = length / 2.0 + 10.0
	train.position.x = -train_span
	_begin()
	for k in 2:  # two carriages
		var x0 := -3.2 + k * 6.4
		_box(Vector3(x0, 3.17, 0), Vector3(6.0, 0.53, 0.57), Color("495967"))
		_box(Vector3(x0, 3.48, 0), Vector3(5.85, 0.1, 0.55), DARK)
		for i in 16:
			for z in [-0.3, 0.3]:
				_box(Vector3(x0 - 2.75 + i * 0.36, 3.24, z), Vector3(0.26, 0.2, 0.025), CYAN * 0.7, "light")
	for z in [-0.17, 0.17]:
		_box(Vector3(6.25, 3.12, z), Vector3(0.05, 0.1, 0.1), Color("fff2c0"), "light")
		_box(Vector3(-6.25, 3.12, z), Vector3(0.05, 0.1, 0.1), Color("ff3359"), "light")
	_box(Vector3(0, 3.55, 0), Vector3(12.2, 0.05, 0.12), CYAN, "light")  # roof strip, visible from above
	_box(Vector3(6.3, 3.3, 0), Vector3(0.06, 0.2, 0.34), Color("fff2c0"), "light")
	_flush(train, "Carriage")

func _spawn_traffic(count: int) -> void:
	if free_vertical.is_empty() and free_horizontal.is_empty():
		return
	for i in count:
		var node := Node3D.new()
		node.name = "Car%d" % i
		_begin()
		_car(Vector3.ZERO, i * 5 + 2, false, true)
		_flush(node, "Traffic")
		add_child(node)
		var car := {"node": node}
		_assign_route(car, true)
		traffic.append(car)

func _assign_route(car: Dictionary, scatter: bool) -> void:
	# Right-hand traffic along one free street line, from beyond one edge of the city to the other.
	var vertical := rng.randf() < 0.5 if not free_horizontal.is_empty() else true
	if free_vertical.is_empty():
		vertical = false
	var line: int = free_vertical[rng.randi() % free_vertical.size()] if vertical else free_horizontal[rng.randi() % free_horizontal.size()]
	var direction := 1.0 if rng.randf() < 0.5 else -1.0
	var extent := (grid_rows if vertical else grid_cols) * PITCH
	car.vertical = vertical
	car.axis = line * PITCH - PITCH / 2.0
	car.direction = direction
	car.from = -1.6 * PITCH if direction > 0 else extent + 0.6 * PITCH
	car.to = extent + 0.6 * PITCH if direction > 0 else -1.6 * PITCH
	car.progress = rng.randf_range(0.0, 1.0) if scatter else 0.0
	car.speed = CAR_SPEED * rng.randf_range(0.8, 1.15)
	var node: Node3D = car.node
	# The mesh faces +x; its right-hand side is +z, so the lane sits to the right of travel.
	node.rotation.y = (-PI / 2.0 if direction > 0 else PI / 2.0) if vertical else (0.0 if direction > 0 else PI)
	_place_car(car)

func _place_car(car: Dictionary) -> void:
	var along: float = lerpf(car.from, car.to, car.progress)
	var lane: float = car.axis + (-0.95 if car.vertical else 0.95) * car.direction
	var node: Node3D = car.node
	node.position = Vector3(lane, 0.01, along) if car.vertical else Vector3(along, 0.01, lane)

func animate(delta: float) -> void:
	for car in traffic:
		car.progress += car.speed * delta / absf(car.to - car.from)
		if car.progress >= 1.0:
			_assign_route(car, false)
		else:
			_place_car(car)
	if train == null:
		return
	if train_running:
		train.position.x += TRAIN_SPEED * train_direction * delta
		if absf(train.position.x) >= train_span:
			train_running = false
			train_direction = -train_direction
			train_clock = TRAIN_INTERVAL * rng.randf_range(0.8, 1.2)
	else:
		train_clock -= delta
		if train_clock <= 0.0:
			train_running = true
			train.position.x = -train_span * train_direction
			train.rotation.y = 0.0 if train_direction > 0 else PI

func _begin() -> void:
	batches = {}
	geometry_origin = Vector3.ZERO
	geometry_visibility = 1.0

func _batch(kind: String) -> Dictionary:
	if not batches.has(kind):
		batches[kind] = {"vertices": PackedVector3Array(), "normals": PackedVector3Array(), "colors": PackedColorArray(), "indices": PackedInt32Array()}
	return batches[kind]

func _quad(a: Vector3, b: Vector3, c: Vector3, d: Vector3, normal: Vector3, color: Color, kind: String = "solid") -> void:
	var batch := _batch(kind)
	var index: int = batch.vertices.size()
	batch.vertices.append_array(PackedVector3Array([a + geometry_origin, b + geometry_origin, c + geometry_origin, d + geometry_origin]))
	for i in 4:
		batch.normals.append(normal)
		batch.colors.append(color * geometry_visibility)
	batch.indices.append_array(PackedInt32Array([index, index + 1, index + 2, index, index + 2, index + 3]))

func _box(at: Vector3, size: Vector3, color: Color, kind: String = "solid") -> void:
	var p := at - size * 0.5
	var q := at + size * 0.5
	_quad(Vector3(p.x,q.y,q.z), Vector3(q.x,q.y,q.z), Vector3(q.x,p.y,q.z), Vector3(p.x,p.y,q.z), Vector3.BACK, color, kind)
	_quad(Vector3(q.x,q.y,p.z), Vector3(p.x,q.y,p.z), Vector3(p.x,p.y,p.z), Vector3(q.x,p.y,p.z), Vector3.FORWARD, color.darkened(0.15), kind)
	_quad(Vector3(q.x,q.y,q.z), Vector3(q.x,q.y,p.z), Vector3(q.x,p.y,p.z), Vector3(q.x,p.y,q.z), Vector3.RIGHT, color.darkened(0.07), kind)
	_quad(Vector3(p.x,q.y,p.z), Vector3(p.x,q.y,q.z), Vector3(p.x,p.y,q.z), Vector3(p.x,p.y,p.z), Vector3.LEFT, color.darkened(0.2), kind)
	_quad(Vector3(p.x,q.y,p.z), Vector3(q.x,q.y,p.z), Vector3(q.x,q.y,q.z), Vector3(p.x,q.y,q.z), Vector3.UP, color.lightened(0.035) if kind == "solid" else color, kind)
	# Bottom faces cannot be seen; intentionally omitted.

func _face_tile(at: Vector3, size: Vector2, color: Color, side: int, kind: String = "solid") -> void:
	var dx := Vector3(size.x / 2.0, 0, 0) if side == 0 else Vector3(0, 0, -size.x / 2.0)
	var dy := Vector3(0, size.y / 2.0, 0)
	_quad(at - dx + dy, at + dx + dy, at + dx - dy, at - dx - dy, Vector3.BACK if side == 0 else Vector3.RIGHT, color, kind)

func _flat_mark(at: Vector3, size: Vector2, color: Color) -> void:
	var dx := Vector3(size.x / 2.0, 0, 0)
	var dz := Vector3(0, 0, size.y / 2.0)
	_quad(at - dx - dz, at + dx - dz, at + dx + dz, at - dx + dz, Vector3.UP, color)

func finish() -> void:
	# Pavements and street furniture share two city-wide surfaces.
	if streets_finished:
		return
	streets_finished = true
	batches = streets
	_flush(self, "SharedStreetscape")
	streets = {}
	_connect_skybridge("victim_street", "victim_house")
	_connect_skybridge("victim_street", "promenade")

func _connect_skybridge(first: String, second: String) -> void:
	if not building_forms.has(first) or not building_forms.has(second):
		return
	var first_form: Dictionary = building_forms[first]
	var second_form: Dictionary = building_forms[second]
	var a: Dictionary = first_form["volumes"][0]
	var b: Dictionary = second_form["volumes"][0]
	var first_at: Vector3 = first_form["root"].position + a["at"]
	var second_at: Vector3 = second_form["root"].position + b["at"]
	# Only join neighboring east/west blocks; other server layouts keep their streets open.
	if absf(first_at.z - second_at.z) > PITCH * 0.35 or second_at.x <= first_at.x:
		return
	var shared_min := maxf(first_at.z - a["size"].z / 2.0, second_at.z - b["size"].z / 2.0)
	var shared_max := minf(first_at.z + a["size"].z / 2.0, second_at.z + b["size"].z / 2.0)
	if shared_max - shared_min < 1.3:
		return
	var shared_z := (shared_min + shared_max) / 2.0
	var start := Vector3(first_at.x + a["size"].x / 2.0 - 0.08, 0, shared_z)
	var end := Vector3(second_at.x - b["size"].x / 2.0 + 0.08, 0, shared_z)
	var length := end.x - start.x
	if length < 1.0 or length > PITCH * 2.0:
		return
	var level := minf(a["size"].y, b["size"].y) * 0.73
	var bridge := Node3D.new()
	bridge.name = "VerlaineSuspensionBridge"
	bridge.position = (start + end) / 2.0
	add_child(bridge)
	_begin()
	_box(Vector3(0, level, 0), Vector3(length, 0.24, 1.12), CONCRETE.darkened(0.22))
	_box(Vector3(0, level - 0.18, 0), Vector3(length, 0.12, 0.76), DARK)
	for z in [-0.55, 0.55]:
		_box(Vector3(0, level + 0.45, z), Vector3(length, 0.075, 0.075), DARK)
		_box(Vector3(0, level + 0.49, z), Vector3(length, 0.04, 0.04), CYAN * 0.75, "light")
		for i in 19:
			var t := float(i) / 18.0
			var x := -length / 2.0 + t * length
			var cable_y := level + 1.35 + 1.4 * pow(2.0 * t - 1.0, 2.0)
			_box(Vector3(x, level + 0.26, z), Vector3(0.045, 0.52, 0.045), DARK)
			_box(Vector3(x, (level + 0.52 + cable_y) / 2.0, z), Vector3(0.033, cable_y - level - 0.52, 0.033), CONCRETE.darkened(0.25))
			if i < 18:
				var next_t := float(i + 1) / 18.0
				var next_y := level + 1.35 + 1.4 * pow(2.0 * next_t - 1.0, 2.0)
				_beam(Vector3(x, cable_y, z), Vector3(-length / 2.0 + next_t * length, next_y, z), 0.06, CONCRETE.lightened(0.12))
	for x in [-length / 2.0 + 0.12, length / 2.0 - 0.12]:
		for z in [-0.63, 0.63]:
			_box(Vector3(x, level + 1.4, z), Vector3(0.14, 2.8, 0.14), DARK.lightened(0.1))
			_box(Vector3(x, level + 2.86, z), Vector3(0.16, 0.12, 0.16), PINK, "light")
		_box(Vector3(x, level + 2.65, 0), Vector3(0.14, 0.14, 1.38), CONCRETE.darkened(0.25))
	for i in 14:
		_flat_mark(Vector3(-length / 2.0 + (i + 0.5) * length / 14.0, level + 0.126, 0), Vector2(length / 14.0 - 0.025, 0.94), Color("606d78"))
	_person(Vector3(-1.0, level + 0.13, 0), 37)
	_person(Vector3(1.6, level + 0.13, -0.12), 44)
	_flush(bridge, "SuspendedWalkway")
	_panel(bridge, Vector3(0, level - 0.15, 0.6), Vector2(2.7, 0.64), 2 + ADS.size())

func _beam(start: Vector3, end: Vector3, thickness: float, color: Color, kind: String = "solid") -> void:
	var direction := (end - start).normalized()
	var right := direction.cross(Vector3.UP).normalized()
	var up := right.cross(direction).normalized()
	var r := right * thickness / 2.0
	var u := up * thickness / 2.0
	_quad(start + r + u, end + r + u, end + r - u, start + r - u, right, color, kind)
	_quad(end - r + u, start - r + u, start - r - u, end - r - u, -right, color.darkened(0.18), kind)
	_quad(start - r + u, end - r + u, end + r + u, start + r + u, up, color.lightened(0.04), kind)
	_quad(end - r - u, start - r - u, start + r - u, end + r - u, -up, color.darkened(0.2), kind)

func _flush(parent: Node3D, label: String) -> void:
	if label == "Streetscape" or label == "Garden":
		for kind in batches:
			var district_kind: String = kind + ("_decorative" if _is_decorative(parent) else "")
			if not streets.has(district_kind):
				streets[district_kind] = {"vertices": PackedVector3Array(), "normals": PackedVector3Array(), "colors": PackedColorArray(), "indices": PackedInt32Array()}
			var target: Dictionary = streets[district_kind]
			var source: Dictionary = batches[kind]
			var offset: int = target.vertices.size()
			for vertex in source.vertices:
				target.vertices.append(vertex + parent.position)
			target.normals.append_array(source.normals)
			target.colors.append_array(source.colors)
			for index in source.indices:
				target.indices.append(index + offset)
		batches = {}
		return
	for kind in batches:
		var batch: Dictionary = batches[kind]
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = batch.vertices
		arrays[Mesh.ARRAY_NORMAL] = batch.normals
		arrays[Mesh.ARRAY_COLOR] = batch.colors
		arrays[Mesh.ARRAY_INDEX] = batch.indices
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		var node := MeshInstance3D.new()
		node.name = label + "_" + kind
		node.mesh = mesh
		var base := light_material if kind.begins_with("light") else road_material if kind == "road" else solid_material
		if label == "EntranceGuide" or kind == "guide":
			base = guide_material
		node.material_override = _district_material(base, _is_decorative(parent) or kind.ends_with("_decorative"))
		if not kind.begins_with("solid"):
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		parent.add_child(node)
		triangle_count += batch.indices.size() / 3
		mesh_count += 1
	batches = {}

func _is_decorative(node: Node) -> bool:
	var cursor := node
	while cursor != null and cursor != self:
		if cursor.has_meta("decorative"):
			return bool(cursor.get_meta("decorative"))
		cursor = cursor.get_parent()
	return false

func _district_material(base: ShaderMaterial, decorative: bool) -> ShaderMaterial:
	if not decorative:
		return base
	if not muted_materials.has(base):
		var muted := base.duplicate() as ShaderMaterial
		muted.set_shader_parameter("district_visibility", 0.18)
		muted_materials[base] = muted
	return muted_materials[base]

func _panel(root: Node3D, at: Vector3, size: Vector2, ad: int, angle: float = 0.0) -> void:
	var node := MeshInstance3D.new()
	var mesh := QuadMesh.new()
	mesh.size = size
	node.mesh = mesh
	node.position = at
	node.rotation.y = angle
	node.material_override = _district_material(sign_materials[ad], _is_decorative(root))
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(node)
	mesh_count += 1

func _shop_sign(root: Node3D, id: String, color: Color) -> void:
	var names := {"bar": "LE NÉON BLEU", "restaurant": "LE COMPTOIR", "cabaret": "LE PALACE", "den": "LUCKY 7", "police": "NCPD / SECTOR 07", "hospital": "CLINIQUE NEXUS", "cctv": "CITY WATCH", "victim_street": "VERLAINE", "victim_house": "RÉSIDENCE 03", "alley": "NIGHT MARKET", "crime_scene": "SECTOR 07", "promenade": "CANAL / RÉSIDENCES", "lab": "NEXUS LAB", "morgue": "MÉDECINE LÉGALE"}
	var sign := Label3D.new()
	sign.text = names.get(id, "NEXUS")
	sign.position = Vector3(0, 1.62, 3.0)
	sign.font_size = 40
	sign.pixel_size = 0.0045
	sign.modulate = color
	sign.outline_modulate = DARK
	sign.outline_size = 6
	root.add_child(sign)

func _roof_ad(root: Node3D, height: float, ad: int, width: float = 4.1) -> void:
	_begin()
	for x in [-width * 0.4, width * 0.4]:
		_box(Vector3(x, height + 0.9, 0), Vector3(0.14, 1.4, 0.14), DARK)
	_box(Vector3(0, height + 1.88, 0), Vector3(width, 1.6, 0.22), DARK)
	_box(Vector3(0, height + 2.72, 0), Vector3(width + 0.1, 0.09, 0.26), CONCRETE.darkened(0.4))
	_flush(root, "BillboardFrame")
	_panel(root, Vector3(0, height + 1.88, 0.14), Vector2(width - 0.2, 1.42), ad + ADS.size())

func _pool(root: Node3D, at: Vector3, size: Vector2, color_index: int) -> void:
	var node := MeshInstance3D.new()
	var mesh := PlaneMesh.new()
	mesh.size = size
	node.mesh = mesh
	node.position = at
	node.material_override = _district_material(pool_materials[color_index], _is_decorative(root))
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(node)
	mesh_count += 1

func _pixel_rect(img: Image, rect: Rect2i, color: Color) -> void:
	img.fill_rect(rect.intersection(Rect2i(0, 0, img.get_width(), img.get_height())), color)

func _text(img: Image, text: String, at: Vector2i, color: Color, scale_value: int = 1) -> void:
	var x := at.x
	for letter in text:
		var glyph: Array = GLYPHS.get(letter, GLYPHS[" "])
		for y in 7:
			for bit in 5:
				if glyph[y] & (1 << (4 - bit)):
					_pixel_rect(img, Rect2i(x + bit * scale_value, at.y + y * scale_value, scale_value, scale_value), color)
		x += 6 * scale_value

func _advertisement(index: int) -> ImageTexture:
	var img := Image.create(96, 160, false, Image.FORMAT_RGB8)
	img.fill(Color("07132e"))
	var color: Color = ADS[index][3]
	for y in range(0, 160, 4):
		for x in range(0, 96, 4):
			var value := absi(hash(Vector3i(x, y, index))) % 8
			_pixel_rect(img, Rect2i(x, y, 3, 3), Color("101a39").lightened(value * 0.004))
	_pixel_rect(img, Rect2i(4, 4, 2, 152), color.darkened(0.75))
	_pixel_rect(img, Rect2i(90, 4, 2, 152), color.darkened(0.75))
	if index == 3 or index == 4:
		# Voxel portrait: asymmetric hair, eyes and jaw made from discrete pixels.
		for y in 23:
			for x in 21:
				var skin := x > 4 and x < 17 and y > 4 and y < 20 and not (y > 16 and (x < 7 or x > 14))
				var hair := y < 7 and x > 2 and x < 18 or x < 6 and y < 16 and y > 3
				if skin or hair:
					var ink := color if skin else color.darkened(0.42)
					if y == 11 and (x == 8 or x == 14) or y == 16 and x > 9 and x < 14:
						ink = Color("10112a")
					_pixel_rect(img, Rect2i(16 + x * 3, 12 + y * 3, 3, 3), ink)
	elif index == 6:
		for y in 19:
			for x in 23:
				var p := Vector2((x - 11) / 11.0, (y - 9) / 9.0)
				if absf(p.y) < (1.0 - absf(p.x)) * 0.62 and absf(p.y) > (1.0 - absf(p.x)) * 0.35 or p.length() < 0.28:
					_pixel_rect(img, Rect2i(13 + x * 3, 18 + y * 3, 3, 3), color)
	else:
		for y in 17:
			for x in 17:
				var p := Vector2(x - 8, y - 8)
				if (p.length() > 5.0 and p.length() < 7.5) or (absi(x - 8) < 2 and absi(y - 8) < 4) or (absi(y - 8) < 2 and absi(x - 8) < 4):
					_pixel_rect(img, Rect2i(22 + x * 3, 18 + y * 3, 3, 3), color)
	var title: String = ADS[index][0]
	var scale_value := 2 if title.length() < 7 else 1
	_text(img, title, Vector2i((96 - title.length() * 6 * scale_value) / 2, 88), color, scale_value)
	_text(img, ADS[index][1], Vector2i(11, 113), color)
	_text(img, ADS[index][2], Vector2i(11, 125), color)
	_text(img, "SECTOR 07", Vector2i(11, 146), color.darkened(0.35))
	if "--dump-art" in OS.get_cmdline_user_args():
		img.save_png("/tmp/nexus-ad-%d.png" % index)
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)

func _landscape_ad(index: int) -> ImageTexture:
	var img := Image.create(192, 72, false, Image.FORMAT_RGB8)
	img.fill(Color("08132c"))
	var color: Color = ADS[index][3]
	for y in range(0, 72, 4):
		for x in range(0, 192, 4):
			_pixel_rect(img, Rect2i(x, y, 3, 3), Color("101a39"))
	_text(img, ADS[index][0], Vector2i(10, 10), color, 2 if str(ADS[index][0]).length() < 7 else 1)
	_text(img, ADS[index][1], Vector2i(10, 35), color)
	_text(img, ADS[index][2], Vector2i(10, 48), color)
	for y in 17:
		for x in 23:
			var p := Vector2((x - 11) / 11.0, (y - 8) / 8.0)
			if absf(p.y) < (1.0 - absf(p.x)) * 0.72 and absf(p.y) > (1.0 - absf(p.x)) * 0.4 or p.length() < 0.28:
				_pixel_rect(img, Rect2i(115 + x * 3, 10 + y * 3, 3, 3), color)
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)
