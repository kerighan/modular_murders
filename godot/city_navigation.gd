# Screen-space touch targets, attached to emissive entrances in the 3D city.
# Only callbacks supplied by main.gd know about the game or its action keys.
extends Control

const CYAN := Color("69e1f0")
const GOLD := Color("ffd386")
var camera: Camera3D
var entries: Array = []
var sheet: Control
var modal_layer: CanvasLayer
var actors: Array = []
var phone_ui := false
var pinned_region := ""

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	modal_layer = CanvasLayer.new()
	modal_layer.layer = 2
	add_child(modal_layer)

func clear() -> void:
	close_sheet()
	for entry in entries:
		entry.button.queue_free()
		if entry.target != entry.button:
			entry.target.queue_free()
	entries.clear()
	for actor in actors:
		actor.badge.queue_free()
	actors.clear()

func add_actor(at: Vector3, name_text: String, avatar: Control, you: bool, follow: Node3D = null) -> void:
	var badge := PanelContainer.new()
	badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
	badge.size = Vector2(148, 62) if you else Vector2(120, 50)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.06, 0.12, 0.17, 0.5)
	style.border_color = GOLD if you else avatar.accent
	style.set_border_width_all(1)
	style.set_corner_radius_all(12)
	style.set_content_margin_all(4)
	badge.add_theme_stylebox_override("panel", style)
	var row := HBoxContainer.new()
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	badge.add_child(row)
	avatar.custom_minimum_size = Vector2(48, 48) if you else Vector2(36, 36)
	row.add_child(avatar)
	var text := VBoxContainer.new()
	text.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(text)
	var hint := Label.new()
	hint.text = "VOUS" if you else "DÉTECTIVE"
	hint.add_theme_font_size_override("font_size", 11 if you else 9)
	hint.add_theme_color_override("font_color", GOLD if you else avatar.accent)
	text.add_child(hint)
	var name_label := Label.new()
	name_label.text = name_text
	name_label.add_theme_font_size_override("font_size", 17 if you else 14)
	name_label.custom_minimum_size.x = 72 if you else 60
	name_label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	text.add_child(name_label)
	add_child(badge)
	actors.append({"at": at, "badge": badge, "follow": follow})

func add_destination(at: Vector3, title: String, subtitle: String, callback: Callable, current: bool = false, available: bool = true, offscreen: bool = true, presence: Dictionary = {}, accent: Color = Color.TRANSPARENT) -> void:
	var color := Color("8196a0") if not available else GOLD if current else CYAN
	if available and accent.a > 0:
		color = accent
	var button := _button(title, subtitle, color, presence)
	button.disabled = not available
	if callback.is_valid():
		button.pressed.connect(callback)
	if not available:
		button.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(button)
	var target := preload("res://entrance_target.gd").new()
	target.navigation = self
	target.size = Vector2(72, 72)
	target.tooltip_text = title + " : " + subtitle
	target.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	for state in ["normal", "hover", "pressed", "focus", "disabled"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color(color, 0.0 if state in ["normal", "disabled"] else 0.12)
		style.set_corner_radius_all(36)
		if state == "focus":
			style.set_border_width_all(2)
			style.border_color = color
		target.add_theme_stylebox_override(state, style)
	target.disabled = not available
	if callback.is_valid():
		target.pressed.connect(callback)
	if not available:
		target.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(target)
	move_child(target, 0) # Card hit areas always have priority over ground targets.
	entries.append({"at": at, "button": button, "target": target, "color": color, "screen": Vector2.ZERO, "offscreen": offscreen, "kind": "entrance"})

func add_district(at: Vector3, title: String, locations: Array, cost: int, callback: Callable, region: String, available: bool = true, presence: Dictionary = {}, crime: bool = false) -> void:
	# One quiet district description, not an entrance or a ground arrow.
	var button := Button.new()
	button.custom_minimum_size = Vector2(208, 42 + mini(locations.size(), 3) * 19 + (28 if presence.has("count") else 0))
	button.size = button.custom_minimum_size
	button.disabled = not available
	button.tooltip_text = "Quartier : " + title + "\n" + "\n".join(locations) + "\nAller (%d PA)" % cost
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.set_meta("region", region)
	button.set_meta("locations", locations.duplicate())
	button.set_meta("crime_scene", crime)
	var accent := Color("ff7889") if crime else CYAN
	for state in ["normal", "hover", "pressed", "focus", "disabled"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color(0.02, 0.055, 0.085, 0.28 if state == "normal" else 0.75)
		style.set_corner_radius_all(7)
		style.border_color = Color(accent, 0.7)
		style.border_width_left = 3 if crime else 2 if state in ["hover", "pressed", "focus"] else 0
		if crime:
			style.shadow_color = Color(accent, 0.18)
			style.shadow_size = 7
		button.add_theme_stylebox_override(state, style)
	var column := VBoxContainer.new()
	column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	column.offset_left = 10
	column.offset_right = -10
	column.offset_top = 7
	column.offset_bottom = -7
	column.add_theme_constant_override("separation", 3)
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	button.add_child(column)
	var heading := Label.new()
	heading.text = "SCÈNE DU CRIME" if crime else title.to_upper()
	heading.add_theme_font_size_override("font_size", 12)
	heading.add_theme_color_override("font_color", accent)
	heading.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	heading.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(heading)
	var description := Label.new()
	var lines: Array = locations.slice(0, 3)
	if locations.size() > 3:
		lines[2] = "+ %d autres entrées" % (locations.size() - 2)
	description.text = "\n".join(lines)
	description.add_theme_font_size_override("font_size", 14)
	description.add_theme_color_override("font_color", Color("b2c9d1"))
	description.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	description.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(description)
	if presence.has("count"):
		column.add_child(_presence_row(presence))
		button.set_meta("presence_count", int(presence.count))
	var budget := Label.new()
	budget.text = "%d PA · rejoindre le quartier" % cost if available else "REPÉRÉ · trajet indisponible (%d PA)" % cost
	budget.add_theme_font_size_override("font_size", 10)
	budget.add_theme_color_override("font_color", Color("73a2b2"))
	budget.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(budget)
	if callback.is_valid():
		button.pressed.connect(callback)
	add_child(button)
	entries.append({"at": at, "button": button, "target": button, "color": accent, "screen": Vector2.ZERO, "offscreen": false, "kind": "district", "region": region})

func _presence_row(presence: Dictionary) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_theme_constant_override("separation", 3)
	var people: Array = presence.get("people", [])
	for person in people.slice(0, 4):
		var avatar := preload("res://voxel_avatar.gd").new()
		avatar.custom_minimum_size = Vector2(22, 25)
		avatar.identity = int(person.get("id", 0))
		avatar.look = str(person.get("look", ""))
		avatar.appearance = person.get("appearance", {})
		avatar.unknown = not person.get("known", false) or avatar.look.is_empty()
		avatar.accent = GOLD
		avatar.tooltip_text = str(person.name) if person.get("name") != null else "Personne non identifiée"
		row.add_child(avatar)
	var count := Label.new()
	var n := int(presence.get("count", 0))
	count.text = "Aucun présent" if n == 0 else "%d présent%s" % [n, "s" if n > 1 else ""]
	if presence.get("scope", "") == "suspects":
		count.text = "Aucun suspect" if n == 0 else "%d suspect%s" % [n, "s" if n > 1 else ""]
	count.add_theme_font_size_override("font_size", 11)
	count.add_theme_color_override("font_color", GOLD if n > 0 else Color("708a98"))
	count.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(count)
	return row

func _button(title: String, subtitle: String, color: Color, presence: Dictionary = {}) -> Button:
	var button := Button.new()
	button.custom_minimum_size = Vector2(216, 98 if presence.has("count") else 72)
	button.size = button.custom_minimum_size
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.tooltip_text = title + " : " + subtitle
	for state in ["normal", "hover", "pressed", "focus", "disabled"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color(0.025, 0.065, 0.1, 0.0 if state in ["normal", "disabled"] else 0.65)
		style.border_color = Color(color, 0.7)
		style.set_border_width_all(0 if state in ["normal", "disabled"] else 1)
		style.set_corner_radius_all(10)
		style.shadow_color = Color(0, 0, 0, 0)
		style.shadow_size = 0
		button.add_theme_stylebox_override(state, style)
	var icon := Label.new()
	icon.text = "⌂" if color == GOLD else "↗"
	icon.position = Vector2(13, 18)
	icon.add_theme_font_size_override("font_size", 26)
	icon.add_theme_color_override("font_color", color)
	icon.add_theme_color_override("font_outline_color", Color("061019"))
	icon.add_theme_constant_override("outline_size", 5)
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	button.add_child(icon)
	var text := VBoxContainer.new()
	text.anchor_right = 1.0
	text.offset_left = 48
	text.offset_right = -12
	text.offset_top = 14
	text.offset_bottom = 88 if presence.has("count") else 59
	text.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text.add_theme_constant_override("separation", 2)
	button.add_child(text)
	var hint := Label.new()
	hint.text = title
	hint.add_theme_font_size_override("font_size", 12)
	hint.add_theme_color_override("font_color", color)
	hint.add_theme_color_override("font_outline_color", Color("061019"))
	hint.add_theme_constant_override("outline_size", 4)
	hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text.add_child(hint)
	var name_label := Label.new()
	name_label.text = subtitle
	name_label.add_theme_font_size_override("font_size", 19 if phone_ui else 17)
	name_label.add_theme_color_override("font_color", Color("8196a0") if color == Color("8196a0") else Color("e6f2f4"))
	name_label.add_theme_color_override("font_outline_color", Color("061019"))
	name_label.add_theme_constant_override("outline_size", 5)
	name_label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	name_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text.add_child(name_label)
	if presence.has("count"):
		text.add_child(_presence_row(presence))
		button.set_meta("presence_count", int(presence.count))
	return button

func _process(_delta: float) -> void:
	if camera == null:
		return
	var viewport_size := get_viewport_rect().size
	var occupied: Array[Rect2] = []
	var ground_targets: Array = []
	for entry in entries:
		var point := camera.unproject_position(entry.at)
		if not entry.button.disabled and entry.kind == "entrance":
			ground_targets.append({"owner": entry.button, "rect": Rect2(point - Vector2(36, 36), Vector2(72, 72))})
	for actor in actors:
		if is_instance_valid(actor.get("follow")):
			actor.at = actor.follow.position + Vector3(0, 1.8, 0)
		var point := camera.unproject_position(actor.at)
		actor.badge.visible = not camera.is_position_behind(actor.at) and Rect2(Vector2.ZERO, viewport_size).has_point(point)
		actor.badge.position = point - Vector2(actor.badge.size.x / 2, actor.badge.size.y + 8)
		if actor.badge.visible:
			occupied.append(Rect2(actor.badge.position, actor.badge.size).grow(8))
	var ordered := entries.duplicate()
	var center := viewport_size * 0.5
	ordered.sort_custom(func(a, b):
		var pinned_a: bool = not pinned_region.is_empty() and a.get("region", "") == pinned_region
		var pinned_b: bool = not pinned_region.is_empty() and b.get("region", "") == pinned_region
		if pinned_a != pinned_b:
			return pinned_a
		return camera.unproject_position(a.at).distance_squared_to(center) < camera.unproject_position(b.at).distance_squared_to(center))
	for entry in ordered:
		var button: Button = entry.button
		var point := camera.unproject_position(entry.at)
		var in_view := Rect2(Vector2(20, 94), viewport_size - Vector2(40, 190)).has_point(point)
		if entry.kind == "entrance":
			entry.target.position = point - Vector2(36, 36)
			entry.target.visible = not camera.is_position_behind(entry.at) and in_view
		point.x = clampf(point.x, 28, viewport_size.x - 28)
		point.y = clampf(point.y, 106, viewport_size.y - 100)
		entry.screen = point
		button.visible = not camera.is_position_behind(entry.at) and in_view
		if not button.visible:
			continue
		var best := Vector2.ZERO
		var best_cost := INF
		# Find a nearby free label position; targets never stack over each other.
		var offsets := [Vector2(-108, 20), Vector2(20, -32), Vector2(-236, -32), Vector2(-108, -84), Vector2(20, 42), Vector2(-236, 42), Vector2(-108, 96), Vector2(-108, -158)]
		if entry.kind == "district":
			offsets.push_front(-button.size * 0.5)
		for x in [-1, 0, 1]:
			for y in [-2, -1, 0, 1, 2]:
				offsets.append(Vector2(-108 + x * (button.size.x + 16), 20 + y * (button.size.y + 12)))
		for offset in offsets:
			var candidate: Vector2 = point + offset
			candidate.x = clampf(candidate.x, 20, viewport_size.x - button.size.x - 20)
			candidate.y = clampf(candidate.y, 94, viewport_size.y - button.size.y - 88)
			var rect := Rect2(candidate, button.size).grow(8)
			var nearest := Vector2(clampf(point.x, candidate.x, candidate.x + button.size.x), clampf(point.y, candidate.y, candidate.y + button.size.y))
			if nearest.distance_to(point) > 72.0:
				continue # Do not relocate labels across the screen to avoid a collision.
			var cost := candidate.distance_squared_to(point + Vector2(-108, 20))
			for other in occupied:
				if rect.intersects(other):
					cost += 1000000.0 + rect.intersection(other).get_area() * 100.0
			for target in ground_targets:
				if target.owner != button and rect.intersects(target.rect):
					cost += 1000000.0 + rect.intersection(target.rect).get_area() * 100.0
			if cost < best_cost:
				best_cost = cost
				best = candidate
		var pinned: bool = not pinned_region.is_empty() and entry.get("region", "") == pinned_region
		if best_cost == INF or (best_cost >= 1000000.0 and not pinned):
			button.visible = false # The glowing ground entrance stays touchable.
			continue
		button.position = best
		if pinned:
			for actor in actors:
				if Rect2(best, button.size).intersects(actor.badge.get_rect()):
					actor.badge.hide()
		occupied.append(Rect2(best, button.size))
	queue_redraw()

func _draw() -> void:
	for entry in entries:
		var button: Button = entry.button
		if not button.visible or entry.kind == "district":
			continue
		var point: Vector2 = entry.screen
		# No leader lines: entrances remain in the world, not connected across the HUD.
		draw_circle(point, 9, Color(entry.color, 0.12), true, -1, true)
		draw_circle(point, 4, entry.color, true, -1, true)

func close_sheet() -> void:
	if is_instance_valid(sheet):
		sheet.queue_free()
	sheet = null

func _choose(callback: Callable) -> void:
	close_sheet()
	callback.call()

func show_choices(title: String, choices: Array) -> void:
	close_sheet()
	sheet = Control.new()
	sheet.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	modal_layer.add_child(sheet)
	var backdrop := Button.new()
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var shade := StyleBoxFlat.new()
	shade.bg_color = Color(0.015, 0.035, 0.06, 0.74)
	for state in ["normal", "hover", "pressed", "focus"]:
		backdrop.add_theme_stylebox_override(state, shade)
	backdrop.pressed.connect(close_sheet)
	sheet.add_child(backdrop)
	var panel := PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	var width := minf(560, get_viewport_rect().size.x - 40)
	var height := minf(400, get_viewport_rect().size.y - 120)
	panel.offset_left = -width / 2
	panel.offset_right = width / 2
	panel.offset_top = -height - 24
	panel.offset_bottom = -24
	var style := StyleBoxFlat.new()
	style.bg_color = Color("0c1b29")
	style.border_color = Color("3a8293")
	style.set_border_width_all(1)
	style.set_corner_radius_all(16)
	style.set_content_margin_all(16)
	panel.add_theme_stylebox_override("panel", style)
	sheet.add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	panel.add_child(column)
	var bar := HBoxContainer.new()
	column.add_child(bar)
	var heading := Label.new()
	heading.text = title
	heading.add_theme_font_size_override("font_size", 21)
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.add_child(heading)
	var close := Button.new()
	close.text = "Fermer"
	close.custom_minimum_size = Vector2(88, 52)
	close.pressed.connect(close_sheet)
	bar.add_child(close)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	column.add_child(scroll)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 10)
	scroll.add_child(list)
	for choice in choices:
		var available: bool = choice.get("available", true)
		var button := _button(choice.get("hint", "Aller à"), choice.label, CYAN if available else Color("8196a0"), choice.get("presence", {}))
		button.disabled = not available
		var row_style := StyleBoxFlat.new()
		row_style.bg_color = Color("122b39")
		row_style.border_color = Color("397e90")
		row_style.set_border_width_all(1)
		row_style.set_corner_radius_all(10)
		button.add_theme_stylebox_override("normal", row_style)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if choice.callback.is_valid():
			button.pressed.connect(_choose.bind(choice.callback))
		list.add_child(button)
