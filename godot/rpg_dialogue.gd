extends Control
## Modal RPG conversation. Only server-supplied choices emit action keys.
signal action_selected(key: Array)
signal closed

const Avatar := preload("res://voxel_avatar.gd")
var phone_ui := false
var ui_theme: Theme
var panel: PanelContainer
var portrait: Control
var speaker: Label
var context: Label
var question: Label
var speech: RichTextLabel
var choices: GridContainer
var choices_scroll: ScrollContainer
var next_button: Button
var shade: ColorRect
var current_person := {}
var options := []
var active := false
var waiting := false
var reading := false
var selecting := false
var choosing_subject := false
var pages := []
var reveal := 0.0
var full_text := ""

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	theme = ui_theme
	shade = ColorRect.new()
	shade.color = Color(0.005, 0.01, 0.025, 0.55)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(shade)
	panel = PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	panel.offset_left = 20
	panel.offset_right = -20
	panel.offset_top = -358 if phone_ui else -332
	panel.offset_bottom = -20
	var style := StyleBoxFlat.new()
	style.bg_color = Color("0b1a29")
	style.border_color = Color("55b7c9")
	style.set_border_width_all(2)
	style.set_corner_radius_all(14)
	style.set_content_margin_all(16)
	style.shadow_color = Color(0, 0, 0, 0.4)
	style.shadow_size = 10
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 18)
	panel.add_child(row)
	var face := VBoxContainer.new()
	face.custom_minimum_size.x = 144
	face.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(face)
	portrait = Avatar.new()
	portrait.custom_minimum_size = Vector2(144, 164)
	face.add_child(portrait)
	speaker = Label.new()
	speaker.text = "?"
	speaker.add_theme_font_size_override("font_size", 23)
	speaker.add_theme_color_override("font_color", Color("ffd386"))
	speaker.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	face.add_child(speaker)
	context = Label.new()
	context.add_theme_font_size_override("font_size", 12)
	context.modulate = Color("87b5c4")
	context.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	face.add_child(context)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.add_theme_constant_override("separation", 8)
	row.add_child(column)
	question = Label.new()
	question.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	question.add_theme_font_size_override("font_size", 13)
	question.modulate = Color("87b5c4")
	column.add_child(question)
	speech = RichTextLabel.new()
	speech.custom_minimum_size.y = 104
	speech.size_flags_vertical = Control.SIZE_EXPAND_FILL
	speech.add_theme_font_size_override("normal_font_size", 20 if phone_ui else 19)
	speech.add_theme_color_override("default_color", Color("e5f2f2"))
	speech.bbcode_enabled = false
	column.add_child(speech)
	# A tap on the actual text reveals it, but never chooses a question.
	speech.gui_input.connect(func(event):
		if (event is InputEventScreenTouch and not event.pressed) or (event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and not event.pressed):
			if reading:
				_finish_reveal())
	choices_scroll = ScrollContainer.new()
	choices_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	choices_scroll.custom_minimum_size.y = 126
	column.add_child(choices_scroll)
	choices = GridContainer.new()
	choices.columns = 2
	choices.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	choices.add_theme_constant_override("h_separation", 8)
	choices.add_theme_constant_override("v_separation", 8)
	choices_scroll.add_child(choices)
	next_button = Button.new()
	next_button.custom_minimum_size.y = 54
	next_button.pressed.connect(advance)
	column.add_child(next_button)
	visible = false

func _process(delta: float) -> void:
	if reading and visible:
		reveal += delta * 52.0
		speech.visible_characters = int(reveal)
		if int(reveal) >= full_text.length():
			_finish_reveal()

func _person(person: Dictionary) -> void:
	current_person = person.duplicate(true)
	portrait.look = person.get("look", "")
	portrait.identity = int(person.get("id", 0))
	portrait.detective = person.get("detective", false)
	portrait.queue_redraw()
	speaker.text = str(person.get("name")) if person.get("name") != null else "Inconnu"

func preview(person: Dictionary, actions: Array) -> void:
	_person(person)
	active = false
	waiting = false
	reading = false
	pages.clear()
	options = actions.duplicate(true)
	context.text = "Choisir une action"
	question.visible = false
	speech.text = person.get("look", "")
	speech.visible_characters = -1
	show()
	_show_options(false)

func show_cue(cue: Dictionary, actions: Array) -> void:
	_person(cue.person)
	active = cue.get("active", false)
	waiting = false
	pages.clear()
	options = actions.duplicate(true)
	context.text = "%d question%s restante%s" % [cue.get("remaining", 0), "s" if cue.get("remaining", 0) != 1 else "", "s" if cue.get("remaining", 0) != 1 else ""] if active else "Fin de conversation"
	question.text = "Vous · " + str(cue.question) if cue.get("question") != null else ""
	question.visible = not question.text.is_empty()
	show()
	if cue.stage == "greeting":
		_set_text("Choisissez votre première question.", false)
		_show_options(true)
	elif cue.stage == "reply":
		_set_text(cue.text, true)
	elif cue.stage == "refused":
		_set_text(cue.text if not str(cue.text).is_empty() else "Votre interlocuteur préfère en rester là.", true)
	else:
		_set_text("Vous laissez partir votre interlocuteur.", true)

func show_result(lines: Array, player_name: String) -> void:
	_person({"name": "Enquête", "look": "", "id": 0, "detective": true})
	active = false
	waiting = false
	options.clear()
	pages = lines.duplicate()
	context.text = player_name
	question.visible = false
	show()
	if not pages.is_empty():
		_set_text(str(pages.pop_front()), true)

func _set_text(text: String, animate: bool) -> void:
	full_text = text
	selecting = false
	choosing_subject = false
	speech.text = text
	reveal = 0.0
	reading = animate and not text.is_empty()
	speech.visible_characters = 0 if reading else -1
	speech.get_v_scroll_bar().value = 0
	choices_scroll.visible = false
	next_button.visible = true
	next_button.disabled = false
	next_button.text = "Afficher la réponse" if reading else "Continuer  ▾"

func _finish_reveal() -> void:
	reading = false
	speech.visible_characters = -1
	next_button.text = "Question suivante  ▾" if active else "Continuer  ▾" if not pages.is_empty() else "Retour  ▾"

func advance() -> void:
	if waiting:
		return
	if reading:
		_finish_reveal()
	elif not pages.is_empty():
		_set_text(str(pages.pop_front()), true)
	elif choosing_subject:
		_show_options(active)
	elif selecting and active:
		var stop: Array = next_button.get_meta("stop", [])
		if not stop.is_empty():
			_choose(stop)
	elif active:
		_set_text("Que souhaitez-vous lui demander ?", false)
		_show_options(true)
	else:
		hide()
		closed.emit()

func _show_options(conversation: bool) -> void:
	selecting = true
	choosing_subject = false
	for child in choices.get_children():
		choices.remove_child(child)
		child.queue_free()
	var has_subjects := false
	var has_documents := false
	var folders := {}
	for option in options:
		var key: Array = option[0]
		if conversation and key[0] not in ["ask", "talk_about"]:
			continue
		if key[0] == "talk_about":
			has_subjects = true
			continue
		if key[0] == "confront":
			has_documents = true
			continue
		if key[0] in ["file", "record", "accuse", "try_code"]:
			folders[key[0]] = true
			continue
		var button := Button.new()
		button.custom_minimum_size = Vector2(0, 56)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.text = str(option[1])
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		button.add_theme_font_size_override("font_size", 15)
		button.set_meta("key", key.duplicate(true))
		button.pressed.connect(_choose.bind(key.duplicate(true)))
		choices.add_child(button)
	if has_subjects:
		var subjects := Button.new()
		subjects.text = "Parler de quelqu'un…"
		subjects.custom_minimum_size.y = 56
		subjects.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		subjects.set_meta("subject_picker", true)
		subjects.pressed.connect(_show_people_questions)
		choices.add_child(subjects)
	if has_documents:
		var documents := Button.new()
		documents.text = "Présenter un document…"
		documents.custom_minimum_size.y = 56
		documents.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		documents.set_meta("document_picker", true)
		documents.pressed.connect(_show_people_questions.bind("confront"))
		choices.add_child(documents)
	for kind in folders:
		var folder := Button.new()
		folder.text = {"file": "Dossiers médicaux…", "record": "Casiers & identités…", "accuse": "Accuser une personne…", "try_code": "Codes du téléphone…"}[kind]
		folder.custom_minimum_size.y = 56
		folder.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		folder.set_meta("action_folder", kind)
		folder.pressed.connect(_show_people_questions.bind(str(kind)))
		choices.add_child(folder)
	choices_scroll.visible = choices.get_child_count() > 0
	next_button.visible = true
	next_button.disabled = false
	var stop: Array = []
	for option in options:
		if option[0][0] == "stop":
			stop = option[0]
	next_button.text = "Laisser partir" if not stop.is_empty() and conversation else "Retour"
	next_button.set_meta("stop", stop)

func _show_people_questions(kind: String = "talk_about") -> void:
	choosing_subject = true
	for child in choices.get_children():
		choices.remove_child(child)
		child.queue_free()
	for option in options:
		var key: Array = option[0]
		if key[0] != kind:
			continue
		var button := Button.new()
		button.text = str(option[1]).get_slice(" : ", 1) if " : " in str(option[1]) else str(option[1])
		button.custom_minimum_size.y = 56
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		button.add_theme_font_size_override("font_size", 15)
		button.set_meta("key", key.duplicate(true))
		button.pressed.connect(_choose.bind(key.duplicate(true)))
		choices.add_child(button)
	choices_scroll.scroll_vertical = 0
	next_button.text = "Retour aux questions"

func _choose(key: Array) -> void:
	if waiting:
		return
	waiting = true
	reading = false
	for option in options:
		if option[0] == key:
			question.text = "Vous · " + str(option[1])
			question.visible = true
	choices_scroll.visible = false
	speech.text = "…"
	speech.visible_characters = -1
	next_button.text = "En attente…"
	next_button.disabled = true
	action_selected.emit(key)

func set_busy_hint(text: String) -> void:
	if visible and waiting:
		speech.text = text

func recover() -> void:
	waiting = false
	if visible:
		_show_options(active)
