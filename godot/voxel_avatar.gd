# Tiny code-drawn voxel busts: no textures, viewports or hidden suspect traits.
extends Control

var look := ""
var identity := 0
var accent := Color("65d9ec")
var detective := false
var unknown := false

func _init() -> void:
	custom_minimum_size = Vector2(120, 136)

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(queue_redraw)

func _pixel(at: Vector2, dimensions: Vector2, color: Color) -> void:
	var scale_factor := minf(size.x / 32.0, size.y / 36.0)
	var origin := Vector2((size.x - 32.0 * scale_factor) / 2.0, (size.y - 36.0 * scale_factor) / 2.0)
	draw_rect(Rect2(origin + at * scale_factor, dimensions * scale_factor), color)

func _draw() -> void:
	if unknown:
		_pixel(Vector2(5, 25), Vector2(22, 9), Color("223747"))
		_pixel(Vector2(11, 21), Vector2(10, 6), Color("293e50"))
		_pixel(Vector2(9, 7), Vector2(15, 15), Color("304858"))
		_pixel(Vector2(13, 10), Vector2(7, 2), Color("6c8795"))
		_pixel(Vector2(18, 12), Vector2(2, 4), Color("6c8795"))
		_pixel(Vector2(15, 15), Vector2(5, 2), Color("6c8795"))
		_pixel(Vector2(15, 17), Vector2(2, 2), Color("6c8795"))
		_pixel(Vector2(15, 20), Vector2(2, 2), Color("6c8795"))
		return
	var hair := Color("cda95f")
	if "noirs" in look:
		hair = Color("292c38")
	elif "roux" in look:
		hair = Color("b7613c")
	elif "châtains" in look:
		hair = Color("694537")
	var coat := [Color("536379"), Color("765b76"), Color("567d78"), Color("857053")][absi(identity) % 4] as Color
	if detective:
		coat = accent.darkened(0.35)
	var skin := Color("cea389")
	_pixel(Vector2(3, 29), Vector2(26, 4), Color(accent, 0.12))
	_pixel(Vector2(5, 25), Vector2(22, 8), coat.darkened(0.3))
	_pixel(Vector2(8, 22), Vector2(16, 12), coat)
	_pixel(Vector2(11, 21), Vector2(10, 5), skin.darkened(0.1))
	_pixel(Vector2(13, 25), Vector2(6, 9), Color("202b3a"))
	_pixel(Vector2(9, 24), Vector2(4, 5), coat.lightened(0.18))
	_pixel(Vector2(19, 24), Vector2(4, 5), coat.lightened(0.18))
	_pixel(Vector2(10, 8), Vector2(13, 14), skin.darkened(0.16))
	_pixel(Vector2(10, 8), Vector2(10, 12), skin)
	_pixel(Vector2(8, 12), Vector2(2, 5), skin.darkened(0.1))
	_pixel(Vector2(23, 12), Vector2(2, 5), skin.darkened(0.2))
	_pixel(Vector2(9, 6), Vector2(15, 6), hair)
	_pixel(Vector2(9, 11), Vector2(3, 4), hair.darkened(0.12))
	_pixel(Vector2(21, 10), Vector2(3, 6), hair.darkened(0.2))
	_pixel(Vector2(13, 14), Vector2(2, 2), Color("28303a"))
	_pixel(Vector2(19, 14), Vector2(2, 2), Color("28303a"))
	_pixel(Vector2(16, 17), Vector2(2, 2), skin.lightened(0.12))
	_pixel(Vector2(14, 20), Vector2(6, 1), Color("936555"))
	if detective:
		_pixel(Vector2(10, 4), Vector2(13, 5), Color("37414c"))
		_pixel(Vector2(10, 8), Vector2(13, 2), accent)
		_pixel(Vector2(6, 10), Vector2(21, 2), Color("46515f"))
		_pixel(Vector2(21, 29), Vector2(2, 2), accent)
