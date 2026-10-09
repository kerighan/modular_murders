extends Control
## Short district banner, beneath interiors. Camera motion remains owned by main.
var banner: PanelContainer
var label: Label
var tween: Tween
var playing := false

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	banner = PanelContainer.new()
	banner.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	banner.offset_left = -230
	banner.offset_right = 230
	banner.offset_top = 92
	banner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.025, 0.07, 0.11, 0.88)
	style.border_color = Color("62ced4")
	style.border_width_bottom = 2
	style.set_corner_radius_all(6)
	style.set_content_margin_all(12)
	banner.add_theme_stylebox_override("panel", style)
	add_child(banner)
	label = Label.new()
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 19)
	label.add_theme_color_override("font_color", Color("d0eff0"))
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	banner.add_child(label)
	banner.hide()

func arrive(name_text: String) -> void:
	if is_instance_valid(tween):
		tween.kill()
	playing = true
	label.text = name_text.to_upper() if name_text.begins_with("Quartier") or name_text.begins_with("Résidence") else "QUARTIER  /  " + name_text
	banner.show()
	banner.modulate.a = 0
	banner.offset_top = 78
	tween = create_tween()
	tween.set_parallel(true)
	tween.tween_property(banner, "modulate:a", 1.0, 0.25)
	tween.tween_property(banner, "offset_top", 92.0, 0.4).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tween.chain().tween_interval(0.7)
	tween.chain().tween_property(banner, "modulate:a", 0.0, 0.35)
	tween.tween_callback(func(): banner.hide(); playing = false)
