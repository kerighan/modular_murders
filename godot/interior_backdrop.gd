extends Control
## Lightweight pixel-stage backdrop. No imported art, lights or extra viewports.
var place := "bar"

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(queue_redraw)

func _draw() -> void:
	var accent := Color("327689")
	if place in ["cabaret", "den"]:
		accent = Color("89507f")
	elif place == "hospital":
		accent = Color("478a7d")
	elif place.begins_with("house_") or place == "victim_house":
		accent = Color("a08057")
	var w := size.x
	var h := size.y
	draw_rect(Rect2(Vector2.ZERO, size), Color("0d1723"))
	draw_rect(Rect2(0, h * 0.61, w, h * 0.39), Color("111f2c"))
	for i in 9:
		var x := w * float(i) / 8.0
		draw_line(Vector2(w * 0.5, h * 0.58), Vector2(x, h), Color(0.2, 0.35, 0.42, 0.2), 1)
	for i in 4:
		var y := h * (0.66 + float(i * i) * 0.018)
		draw_line(Vector2(0, y), Vector2(w, y), Color(0.2, 0.35, 0.42, 0.2), 1)
	var window := Rect2(w * 0.34, h * 0.18, w * 0.34, h * 0.34)
	draw_rect(window.grow(5), accent.darkened(0.63))
	draw_rect(window, Color("091326"))
	for i in 10:
		var bw := window.size.x / 11.0
		var bh := window.size.y * (0.3 + float((i * 7) % 6) * 0.095)
		var bx := window.position.x + i * bw * 1.1
		var by := window.end.y - bh
		draw_rect(Rect2(bx, by, bw, bh), Color("172738"))
		for j in 3:
			draw_rect(Rect2(bx + 4, by + 8 + j * 15, 3, 5), Color(accent, 0.7))
	draw_line(Vector2(window.get_center().x, window.position.y), Vector2(window.get_center().x, window.end.y), Color("324854"), 5)
	draw_line(Vector2(window.position.x, window.get_center().y), Vector2(window.end.x, window.get_center().y), Color("324854"), 4)
	draw_rect(Rect2(w * 0.73, h * 0.2, w * 0.15, h * 0.3), accent.darkened(0.75))
	for i in 4:
		draw_rect(Rect2(w * 0.745, h * (0.22 + i * 0.065), w * 0.115, 3), Color(accent, 0.33))
	if place in ["bar", "den", "cabaret"]:
		draw_rect(Rect2(w * 0.16, h * 0.57, w * 0.68, 14), Color("415465"))
		draw_rect(Rect2(w * 0.17, h * 0.595, w * 0.66, h * 0.16), Color("253344"))
		draw_line(Vector2(w * 0.17, h * 0.605), Vector2(w * 0.83, h * 0.605), Color(accent, 0.7), 3)
	else:
		draw_rect(Rect2(w * 0.2, h * 0.57, w * 0.55, 10), Color("415465"))
		for x in [0.23, 0.7]:
			draw_rect(Rect2(w * x, h * 0.59, 6, h * 0.2), Color("28394b"))
