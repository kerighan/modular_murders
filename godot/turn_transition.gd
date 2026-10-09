extends Control
## A short fade with an explicit midpoint, never a gameplay action.
signal midpoint
var veil: ColorRect
var heading: Label
var subtitle: Label
var tween: Tween
var playing := false
var phase_waiting := false

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	veil = ColorRect.new()
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	veil.color = Color("060f1c")
	veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(veil)
	var column := VBoxContainer.new()
	column.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	column.offset_left = -350
	column.offset_right = 350
	column.offset_top = -70
	column.offset_bottom = 70
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_theme_constant_override("separation", 14)
	add_child(column)
	heading = Label.new()
	heading.add_theme_font_size_override("font_size", 38)
	heading.add_theme_color_override("font_color", Color("e5c28c"))
	heading.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	heading.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(heading)
	subtitle = Label.new()
	subtitle.add_theme_font_size_override("font_size", 16)
	subtitle.add_theme_color_override("font_color", Color("83b9cb"))
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(subtitle)
	hide()

func play(title_text: String, caption: String) -> void:
	phase_waiting = false
	if is_instance_valid(tween):
		tween.kill()
	playing = true
	heading.text = title_text
	subtitle.text = caption
	modulate.a = 0
	show()
	tween = create_tween()
	tween.tween_property(self, "modulate:a", 1.0, 0.22)
	tween.tween_callback(midpoint.emit)
	tween.tween_interval(0.65)
	tween.tween_property(self, "modulate:a", 0.0, 0.4)
	tween.tween_callback(clear)

func phase() -> void:
	play("LA VILLE CONTINUE", "Les habitants vaquent à leurs occupations…")
	tween.kill()
	phase_waiting = true
	tween = create_tween()
	tween.tween_property(self, "modulate:a", 1.0, 0.22)
	tween.tween_callback(midpoint.emit)

func finish_turn(title_text: String, caption: String) -> void:
	phase_waiting = false
	if is_instance_valid(tween):
		tween.kill()
	tween = create_tween()
	tween.tween_property(veil, "modulate:a", 0.42, 0.25)
	tween.tween_interval(1.0)
	tween.tween_property(veil, "modulate:a", 1.0, 0.2)
	tween.tween_callback(func():
		heading.text = title_text
		subtitle.text = caption)
	tween.tween_interval(0.65)
	tween.tween_property(self, "modulate:a", 0.0, 0.4)
	tween.tween_callback(clear)

func abort() -> void:
	if is_instance_valid(tween):
		tween.kill()
	clear()

func clear() -> void:
	playing = false
	phase_waiting = false
	veil.modulate.a = 1.0
	hide()
