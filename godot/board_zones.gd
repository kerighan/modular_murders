extends MeshInstance3D
## Optional board-reading experiment. Only public graph edges become passages.
## One batched, depth-tested ground surface; no labels, lights or touch blockers.

const PITCH := 12.0
const FLOOR := 0.015
const QUIET := Color(0.28, 0.47, 0.57, 0.34)
const NEIGHBOR := Color(0.25, 0.68, 0.75, 0.52)
const CURRENT := Color(0.95, 0.68, 0.26, 0.64)
var segments := []
var passages := []
var vertices := PackedVector3Array()
var colors := PackedColorArray()
var indices := PackedInt32Array()

func _init() -> void:
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var material := ShaderMaterial.new()
	material.shader = preload("res://board_zones.gdshader")
	material_override = material

func update_view(view: Dictionary, occupied: Dictionary) -> void:
	vertices.clear()
	colors.clear()
	indices.clear()
	segments.clear()
	passages.clear()
	if not view.has("adjacency"):
		mesh = null
		return # Older servers never get a guessed visual topology.
	var current: String = view["places"][view["place"]]["street"] if view["places"][view["place"]]["street"] != null else view["place"]
	var near := []
	for neighbor in view["adjacency"].get(current, []):
		var route: Dictionary = view.get("routes", {}).get(neighbor, {})
		if route.get("available", false) and route.get("cost", 0) == 1:
			near.append(neighbor)
	var seen := {}
	for cell in occupied:
		var owner: String = occupied[cell]
		for direction in [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]:
			var next: Vector2i = cell + direction
			var other: String = occupied.get(next, "")
			if owner == other:
				continue # A merged parcel is one zone, never several little squares.
			var a: Vector2i = cell if cell.x < next.x or (cell.x == next.x and cell.y < next.y) else next
			var b: Vector2i = next if a == cell else cell
			var key := Vector4i(a.x, a.y, b.x, b.y)
			if seen.has(key):
				continue
			seen[key] = true
			var at := (Vector2(cell) + Vector2(direction) * 0.5) * PITCH
			var normal := Vector2(direction)
			var tangent := Vector2(-normal.y, normal.x)
			var is_current := owner == current or other == current
			var is_near := owner in near or other in near
			var tint := CURRENT if is_current else NEIGHBOR if is_near else QUIET
			var width := 0.16 if is_current else 0.12
			var linked: bool = other in view["adjacency"].get(owner, [])
			segments.append({"owner": owner, "other": other, "linked": linked})
			if linked:
				# Break the shared frontier only where the real graph allows crossing.
				_line(at - tangent * 5.9, at - tangent * 1.15, width, tint)
				_line(at + tangent * 1.15, at + tangent * 5.9, width, tint)
				passages.append([owner, other])
				var destination: String = other if owner == current else owner
				var portal := Color(0.25, 0.8, 0.88, 0.72) if is_current and destination in near else QUIET
				for side in [-1.0, 1.0]:
					var tip: Vector2 = at + normal * side * 0.65
					_line(tip - normal * side * 0.4 - tangent * 0.35, tip, 0.13, portal)
					_line(tip - normal * side * 0.4 + tangent * 0.35, tip, 0.13, portal)
				if is_current and destination in near:
					_line(at - tangent * 0.12, at + tangent * 0.12, 0.24, portal)
			else:
				_line(at - tangent * 5.9, at + tangent * 5.9, width, tint)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_INDEX] = indices
	var batched := ArrayMesh.new()
	if not vertices.is_empty():
		batched.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh = batched

func _line(a: Vector2, b: Vector2, width: float, tint: Color) -> void:
	var side := Vector2(-(b - a).y, (b - a).x).normalized() * width * 0.5
	var points := [a - side, a + side, b + side, b - side]
	var base := vertices.size()
	for p in points:
		vertices.append(Vector3(p.x, FLOOR, p.y))
		colors.append(tint)
	indices.append_array(PackedInt32Array([base, base + 1, base + 2, base, base + 2, base + 3]))
