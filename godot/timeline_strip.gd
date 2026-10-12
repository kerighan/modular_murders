extends Control
## A comparison of acquired times only. No private event or culprit identity.
var events: Array = []

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	custom_minimum_size.y = 46 + events.size() * 29
	resized.connect(queue_redraw)

func _clock(at: int) -> String:
	return "%02d:%02d" % [at / 60, at % 60]

func _draw() -> void:
	if events.is_empty():
		return
	var first := 1440
	var last := 0
	for event in events:
		first = mini(first, int(event.start))
		last = maxi(last, int(event.end))
	first = (first / 15) * 15
	last = maxi(first + 30, ((last + 14) / 15) * 15)
	var left := 160.0
	var width := maxf(80, size.x - left - 28)
	var font := get_theme_default_font()
	var tick_minutes := maxi(15, int(ceil(float(last - first) / 60.0)) * 15)
	for minute in range(first, last + 1, tick_minutes):
		var fraction := float(minute - first) / (last - first)
		var x := left + fraction * width
		draw_line(Vector2(x, 24), Vector2(x, size.y - 5), Color("264452"), 1)
		draw_string(font, Vector2(x - 15, 16), _clock(minute), HORIZONTAL_ALIGNMENT_LEFT, 55, 11, Color("89b5c5"))
	for event in events:
		if event.kind == "medical":
			var x := left + (float(event.start) - first) / (last - first) * width
			var span := maxf(2, float(event.end - event.start) / (last - first) * width)
			draw_rect(Rect2(x, 24, span, size.y - 29), Color("ff7889", 0.09))
	for i in events.size():
		var event: Dictionary = events[i]
		var y := 40.0 + i * 29
		var color := Color("ff7889") if event.kind == "medical" else Color("63dce9") if event.kind == "camera" else Color("83e5b3") if event.status == "verified" else Color("eab779")
		var title := "Crime · rapport" if event.kind == "medical" else "CCTV" if event.kind == "camera" else str(event.title).get_slice(" · ", 0)
		while font.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x > left - 22 and title.length() > 2:
			title = title.left(title.length() - 2) + "…"
		draw_string(font, Vector2(4, y + 4), title, HORIZONTAL_ALIGNMENT_LEFT, left - 15, 12, color)
		var from := Vector2(left + (float(event.start) - first) / (last - first) * width, y)
		var to := Vector2(left + (float(event.end) - first) / (last - first) * width, y)
		if event.status == "verified":
			draw_line(from, to, Color(color, 0.15), 12, true)
		draw_line(from, to, color, 4, true)
		draw_circle(from, 4, color, event.status == "verified", -1, true)
		draw_circle(to, 4, color, event.status == "verified", -1, true)
