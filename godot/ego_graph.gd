extends Control
# Who knows whom, around the victim: only what the detective heard or read.

signal person_tapped(id: int)

const KIND_COLORS := {
	"couple": Color("ff7fa8"), "ancien couple": Color("c98bb0"), "amis": Color("83e5b3"),
	"collègues": Color("63e1ec"), "voisins": Color("ffd386"), "fratrie": Color("f1b4ff"),
	"connaissances": Color("9fb3bd"), "messages": Color("9fb3bd"), "proche": Color("b7e3b0"),
	"rivalité": Color("ff5a74"), "ex en paix": Color("c98bb0"),
}
const RADIUS_RATIO := 0.36
const NODE := 20.0

var graph := {}
var positions := {}  # id -> Vector2
var font: Font = ThemeDB.fallback_font

func set_graph(data: Dictionary) -> void:
	graph = data.duplicate(true)
	custom_minimum_size.y = 460
	_layout()
	queue_redraw()

func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_layout()
		queue_redraw()

func _layout() -> void:
	positions.clear()
	if graph.is_empty():
		return
	var centre := size / 2.0
	var radius: float = minf(size.x, size.y) * RADIUS_RATIO
	var others := []
	for node in graph.get("nodes", []):
		if int(node.id) == int(graph.center):
			positions[int(node.id)] = centre
		else:
			others.append(int(node.id))
	for i in others.size():
		# one step more than needed, so no two people sit opposite each other through the victim
		var a := -PI / 2.0 + i * TAU / (others.size() + 1)
		positions[others[i]] = centre + Vector2.from_angle(a) * radius

func _alpha(id: int) -> float:
	# ruled out: still on the map, but faded
	for node in graph.get("nodes", []):
		if int(node.id) == id:
			return 0.35 if node.get("excluded", false) else 1.0
	return 1.0

func _name(id: int) -> String:
	for node in graph.get("nodes", []):
		if int(node.id) == id:
			return str(node.name)
	return "?"

func _gui_input(event: InputEvent) -> void:
	var pressed: bool = (event is InputEventScreenTouch and event.pressed) or (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT)
	if not pressed:
		return
	for id in positions:
		if positions[id].distance_to(event.position) <= NODE + 8 and id != int(graph.get("center", -1)):
			person_tapped.emit(id)
			accept_event()
			return

func _draw() -> void:
	if graph.is_empty():
		return
	# ties people said they do not have: faint dotted lines
	for pair in graph.get("strangers", []):
		var a: int = int(pair[0])
		var b: int = int(pair[1])
		if positions.has(a) and positions.has(b):
			_dotted(positions[a], positions[b], Color(0.45, 0.55, 0.6, 0.35))
	for edge in graph.get("edges", []):
		var a: int = int(edge.a)
		var b: int = int(edge.b)
		if not positions.has(a) or not positions.has(b):
			continue
		var kinds: Array = edge.kinds
		var color: Color = KIND_COLORS.get(str(kinds[0]), Color("9fb3bd"))
		color.a = minf(_alpha(a), _alpha(b))
		draw_line(positions[a], positions[b], color, 3.0, true)
		var mid: Vector2 = (positions[a] + positions[b]) / 2.0
		var label := ", ".join(kinds)
		var width := font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
		draw_rect(Rect2(mid - Vector2(width / 2.0 + 5, 9), Vector2(width + 10, 18)), Color(0.02, 0.055, 0.085, 0.9))
		draw_string(font, mid + Vector2(-width / 2.0, 5), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, color)
	for id in positions:
		var at: Vector2 = positions[id]
		var victim: bool = id == int(graph.center)
		var alpha := _alpha(id)
		draw_circle(at, NODE + (6 if victim else 0), Color("ff7889", alpha) if victim else Color("1b3444", alpha))
		draw_arc(at, NODE + (6 if victim else 0), 0.0, TAU, 40, Color("ffd386", alpha) if victim else Color("63e1ec", alpha), 2.0, true)
		var name := _name(id) + ("" if alpha >= 1.0 else " · écarté")
		var width := font.get_string_size(name, HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x
		draw_string(font, at + Vector2(-width / 2.0, NODE + 22 + (6 if victim else 0)), name, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("e8f1f4", maxf(alpha, 0.6)))

func _dotted(from: Vector2, to: Vector2, color: Color) -> void:
	var length := from.distance_to(to)
	var direction := (to - from) / maxf(length, 0.001)
	var at := 0.0
	while at < length:
		draw_line(from + direction * at, from + direction * minf(at + 6.0, length), color, 2.0)
		at += 12.0
