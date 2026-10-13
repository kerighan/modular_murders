extends Control
## Concise, non-interactive floating notes, shown one after another; never a stack covering the dialogue.
var queue := []  # [heading, body] waiting their turn
var card: PanelContainer
var title: Label
var detail: Label
var tween: Tween

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	card = PanelContainer.new()
	card.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	card.offset_left = -340
	card.offset_right = -20
	card.offset_top = 22
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.035, 0.095, 0.14, 0.88)
	style.border_color = Color(0.28, 0.75, 0.78, 0.65)
	style.border_width_left = 3
	style.set_corner_radius_all(8)
	style.set_content_margin_all(12)
	card.add_theme_stylebox_override("panel", style)
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(card)
	var column := VBoxContainer.new()
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.add_child(column)
	title = Label.new()
	title.add_theme_font_size_override("font_size", 14)
	title.add_theme_color_override("font_color", Color("9fe7dc"))
	title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(title)
	detail = Label.new()
	detail.add_theme_font_size_override("font_size", 13)
	detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	detail.max_lines_visible = 2
	detail.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	detail.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(detail)
	card.visible = false

func note(heading: String, body: String = "") -> void:
	if card.visible:
		queue.append([heading, body])
		return
	_show(heading, body)

func clear() -> void:
	queue.clear()
	if is_instance_valid(tween):
		tween.kill()
	card.hide()

func _next() -> void:
	card.hide()
	if not queue.is_empty():
		var row: Array = queue.pop_front()
		_show(row[0], row[1])

func _show(heading: String, body: String) -> void:
	if is_instance_valid(tween):
		tween.kill()
	title.text = heading
	detail.text = body
	detail.visible = not body.is_empty()
	card.visible = true
	card.modulate.a = 0
	card.offset_top = 32
	# Physics steps: a frame stalled by the engine's Python call cannot swallow the whole note.
	# Parallel by default; chain() opens each new step (set_parallel() after chain() would
	# merge the fade-out into the hold, and the note vanished after 0.7 s).
	tween = create_tween().set_process_mode(Tween.TWEEN_PROCESS_PHYSICS).set_parallel(true)
	tween.tween_property(card, "modulate:a", 1.0, 0.2)
	tween.tween_property(card, "offset_top", 22.0, 0.25)
	tween.chain().tween_interval(2.6 if not queue.is_empty() else 3.3)
	tween.chain().tween_property(card, "modulate:a", 0.0, 0.45)
	tween.tween_property(card, "offset_top", 10.0, 0.45)
	tween.chain().tween_callback(_next)
