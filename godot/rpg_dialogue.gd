extends Control
## Modal RPG conversation. Only server-supplied choices emit action keys.
signal action_selected(key: Array)
var highlights := {}  # {"victim": name, "suspects": [names], "evidence": [labels]} from the view
var _word_regex := RegEx.new()
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
var current_terminal := false
var options := []
var active := false
var waiting := false
var reading := false
var selecting := false
var choosing_subject := false
var remaining_pa := -1
var pages := []
var reveal := 0.0
var full_text := ""
var pending_thought := {}
var reply_person := {}
var reply_context := ""
var thinking := false
var scene_beats: Array = []

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
	context.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
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
	speech.bbcode_enabled = true  # names and evidence are coloured in the spoken text
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
	portrait.appearance = person.get("appearance", {})
	portrait.detective = person.get("detective", false)
	portrait.unknown = person.get("profile_known", true) == false
	portrait.identity = int(person.get("portrait_id", person.get("id", 0)))
	portrait.accent = Color("63e1ec") if portrait.detective else Color("ee4985") if person.get("service", false) else Color("ffd386")
	portrait.queue_redraw()
	speaker.text = str(person.get("name")) if person.get("name") != null else "Inconnu"
	speaker.add_theme_color_override("font_color", portrait.accent)
	var style: StyleBoxFlat = panel.get_theme_stylebox("panel").duplicate()
	style.border_color = portrait.accent
	style.bg_color = Color("0b2530") if portrait.detective else Color("251724") if person.get("service", false) else Color("0b1a29")
	panel.add_theme_stylebox_override("panel", style)

func preview(person: Dictionary, actions: Array) -> void:
	current_terminal = false
	scene_beats.clear()
	pending_thought.clear()
	thinking = false
	_person(person)
	active = false
	waiting = false
	reading = false
	pages.clear()
	options = actions.duplicate(true)
	context.text = str(person.role) + " · Choisir une action" if person.has("role") else "Choisir une action"
	question.visible = false
	speech.text = person.get("look", "")
	speech.visible_characters = -1
	show()
	_show_options(false)

func show_service_idle(person: Dictionary) -> void:
	preview(person, [])
	context.text = str(person.get("role", "Personnel")) + " · " + str(person.get("status", "Source d'information"))
	_set_text(person.get("idle_text", "Bonsoir. Vous vouliez me parler ?"), true)

func show_cue(cue: Dictionary, actions: Array) -> void:
	remaining_pa = int(cue.get("remaining_pa", -1))
	current_terminal = cue.get("terminal", false)
	scene_beats.clear()
	pending_thought = cue.get("thought", {}).duplicate(true)
	thinking = false
	reply_person = cue.person.duplicate(true)
	_person(cue.person)
	active = cue.get("active", false)
	waiting = false
	pages.clear()
	options = actions.duplicate(true)
	# Suspects: a budget of fresh questions per action point ("2/3"); rereads are free.
	var total: int = int(cue.get("slots_total", 0))
	var used: int = total - int(cue.get("remaining", 0))
	context.text = ("Questions %d/%d" % [used, total] + (" · %d PA" % remaining_pa if remaining_pa >= 0 else "")) if active and total > 0 else "%d question%s restante%s" % [cue.get("remaining", 0), "s" if cue.get("remaining", 0) != 1 else "", "s" if cue.get("remaining", 0) != 1 else ""] if active else "Fin de conversation"
	if cue.has("context"):
		context.text = str(cue.context)
		if active and total > 0:  # the suspect's question budget stays in view
			context.text += " · Questions %d/%d" % [used, total] + (" · %d PA" % remaining_pa if remaining_pa >= 0 else "")
	if cue.stage == "approach":
		context.text = "Approche" + (" · %d PA" % remaining_pa if remaining_pa >= 0 else "")
	elif active and remaining_pa == 0 and int(cue.get("remaining", 0)) == 0:
		context.text += " · Relecture gratuite"
	reply_context = context.text
	question.text = "Vous · " + str(cue.question) if cue.get("question") != null else ""
	question.visible = not question.text.is_empty()
	show()
	if cue.stage == "scene":
		active = false
		options.clear()
		context.text = "Conversation surprise"
		question.hide()
		scene_beats = cue.get("beats", []).duplicate(true)
		if not scene_beats.is_empty():
			var beat: Dictionary = scene_beats.pop_front()
			_person(beat.person)
			_set_text(str(beat.text), true)
	elif cue.stage == "approach":
		_set_text(cue.text, true)  # then "Lui parler (1 PA)" / "Quitter"
		next_button.text = "Continuer  ▾"  # a narration, not an answer
	elif cue.stage == "greeting":
		_set_text("Choisissez votre première question.", false)
		_show_options(true)
	elif cue.stage == "reply":
		_set_text(cue.text, true)
	elif cue.stage == "refused":
		_set_text(cue.text if not str(cue.text).is_empty() else "Votre interlocuteur préfère en rester là.", true)
	else:
		_set_text("Vous laissez partir votre interlocuteur.", true)

func show_result(lines: Array, player_name: String) -> void:
	current_terminal = false
	scene_beats.clear()
	pending_thought.clear()
	thinking = false
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
	speech.show()
	panel.offset_top = -318 if phone_ui else -332
	speech.clear()
	if thinking:
		speech.push_italics()
		speech.add_text(text)
		speech.pop()
	else:
		speech.text = _highlight(text)
	reveal = 0.0
	reading = animate and not text.is_empty()
	speech.visible_characters = 0 if reading else -1
	speech.get_v_scroll_bar().value = 0
	choices_scroll.visible = false
	next_button.visible = true
	next_button.disabled = false
	next_button.text = "Afficher la réponse" if reading else "Continuer  ▾"

func _highlight(text: String) -> String:
	# The victim in red, the suspects already named in gold, evidence in hand in cyan.
	var spans := []
	var groups := [[str(highlights.get("victim", "")), "ff7889"], [highlights.get("suspects", []), "ffd386"], [highlights.get("evidence", []), "63e1ec"]]
	for group in groups:
		var terms = group[0] if group[0] is Array else [group[0]]
		for term in terms:
			var word := str(term)
			if word.is_empty():
				continue
			_word_regex.compile("(?<![\\p{L}])" + _escape(word) + "(?![\\p{L}])")
			for found in _word_regex.search_all(text):
				var start := found.get_start()
				var end := found.get_end()
				var clash := false
				for span in spans:
					if start < span[1] and end > span[0]:
						clash = true
				if not clash:
					spans.append([start, end, group[1]])
	spans.sort_custom(func(a, b): return a[0] < b[0])
	var out := ""
	var cursor := 0
	for span in spans:
		out += text.substr(cursor, span[0] - cursor).replace("[", "[lb]")
		out += "[color=#%s]%s[/color]" % [span[2], text.substr(span[0], span[1] - span[0])]
		cursor = span[1]
	out += text.substr(cursor).replace("[", "[lb]")
	return out

func _escape(word: String) -> String:
	var out := ""
	for ch in word:
		out += ("\\" + ch) if ch in ".^$*+?()[]{}|\\" else ch
	return out

func _finish_reveal() -> void:
	reading = false
	speech.visible_characters = -1
	next_button.text = "Continuer  ▾" if not scene_beats.is_empty() or not pending_thought.is_empty() or not pages.is_empty() else "Choisir un enregistrement  ▾" if active and current_terminal else "Question suivante  ▾" if active else "Retour  ▾"

func advance() -> void:
	if waiting:
		return
	if reading:
		_finish_reveal()
	elif not scene_beats.is_empty():
		var beat: Dictionary = scene_beats.pop_front()
		_person(beat.person)
		_set_text(str(beat.text), true)
	elif not pages.is_empty():
		_set_text(str(pages.pop_front()), true)
	elif not pending_thought.is_empty():
		var thought := pending_thought.duplicate(true)
		pending_thought.clear()
		thinking = true
		_person(thought.person)
		context.text = "Pensée"
		question.hide()
		_set_text(str(thought.text), true)
	elif choosing_subject:
		_show_options(active)
	elif selecting and active:
		var stop: Array = next_button.get_meta("stop", [])
		if not stop.is_empty():
			_choose(stop)
	elif active:
		if thinking:
			thinking = false
			_person(reply_person)
			context.text = reply_context
		_set_text("Quel enregistrement souhaitez-vous consulter ?" if current_terminal else "Que souhaitez-vous lui demander ?", false)
		_show_options(true)
	else:
		hide()
		closed.emit()

func _show_options(conversation: bool) -> void:
	panel.offset_top = -398 if phone_ui else -390
	speech.hide()
	question.hide()
	selecting = true
	choosing_subject = false
	for child in choices.get_children():
		choices.remove_child(child)
		child.queue_free()
	var has_subjects := false
	var has_documents := false
	var has_background := false
	var has_police_records := false
	var has_verifications := false
	var folders := {}
	for option in options:
		var key: Array = option[0]
		if conversation and key[0] not in ["ask", "talk_about"]:
			continue
		if key[0] == "talk_about":
			has_subjects = true
			continue
		# Relationship is a primary investigation question, not biography.
		if key[0] == "ask" and key.size() > 1 and key[1] in ["work", "circle"]:
			has_background = true
			continue
		if key[0] == "ask" and key.size() > 2 and key[1] == "service_action" and str(key[2]).begins_with("record:"):
			has_police_records = true
			continue
		if key[0] == "ask" and key.size() > 2 and key[1] == "service_action" and str(key[2]).begins_with("verify:"):
			has_verifications = true
			continue
		if key[0] == "confront":
			has_documents = true
			continue
		if key[0] in ["file", "record", "accuse", "try_code", "verify"]:
			folders[key[0]] = true
			continue
		var button := Button.new()
		button.custom_minimum_size = Vector2(0, 56)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.text = str(option[1])
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		button.add_theme_font_size_override("font_size", 15)
		button.set_meta("key", key.duplicate(true))
		button.disabled = option.size() > 2 and not option[2].get("available", true)
		if button.disabled:
			button.tooltip_text = "Question disponible au prochain tour"
		elif option.size() > 2 and option[2].get("cost", 1) == 0 and key[0] in ["ask", "talk_about"]:
			button.tooltip_text = "Consultation gratuite"
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
	if has_background:
		var background := Button.new()
		background.text = "Votre quotidien…"
		background.custom_minimum_size.y = 56
		background.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		background.set_meta("background_picker", true)
		background.pressed.connect(_show_people_questions.bind("background"))
		choices.add_child(background)
	if has_police_records:
		var records := Button.new()
		records.text = "Casiers & fiches d'identité…"
		records.custom_minimum_size.y = 56
		records.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		records.set_meta("police_records_picker", true)
		records.pressed.connect(_show_people_questions.bind("police_records"))
		choices.add_child(records)
	if has_documents:
		var documents := Button.new()
		documents.text = "Montrer un papier…"
		documents.custom_minimum_size.y = 56
		documents.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		documents.set_meta("document_picker", true)
		documents.pressed.connect(_show_people_questions.bind("confront"))
		choices.add_child(documents)
	if has_verifications:
		var checks := Button.new()
		checks.text = "Vérifier un récit…"
		checks.custom_minimum_size.y = 56
		checks.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		checks.set_meta("verification_picker", true)
		checks.pressed.connect(_show_people_questions.bind("verifications"))
		choices.add_child(checks)
	for kind in folders:
		var folder := Button.new()
		folder.text = {"file": "Dossiers médicaux…", "record": "Casiers & identités…", "accuse": "Accuser une personne…", "try_code": "Codes du téléphone…", "verify": "Vérifier un alibi…"}[kind]
		folder.custom_minimum_size.y = 56
		folder.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		folder.set_meta("action_folder", kind)
		folder.pressed.connect(_show_people_questions.bind(str(kind)))
		choices.add_child(folder)
	choices_scroll.visible = choices.get_child_count() > 0
	choices_scroll.custom_minimum_size.y = minf(252, ceilf(choices.get_child_count() / 2.0) * 64)
	choices_scroll.scroll_vertical = 0
	next_button.visible = true
	next_button.disabled = false
	var stop: Array = []
	for option in options:
		if option[0][0] == "stop":
			stop = option[0]
	next_button.text = "Fermer les archives" if current_terminal and not stop.is_empty() else "Revenir à la ville" if remaining_pa == 0 and not stop.is_empty() and conversation else "Laisser partir" if not stop.is_empty() and conversation else "Retour"
	next_button.set_meta("stop", stop)

func _show_people_questions(kind: String = "talk_about") -> void:
	choosing_subject = true
	for child in choices.get_children():
		choices.remove_child(child)
		child.queue_free()
	for option in options:
		var key: Array = option[0]
		if kind == "background":
			if key[0] != "ask" or key.size() < 2 or key[1] not in ["work", "circle"]:
				continue
		elif kind == "police_records":
			if key[0] != "ask" or key.size() < 3 or key[1] != "service_action" or not str(key[2]).begins_with("record:"):
				continue
		elif kind == "verifications":
			if key[0] != "ask" or key.size() < 3 or key[1] != "service_action" or not str(key[2]).begins_with("verify:"):
				continue
		elif key[0] != kind:
			continue
		var button := Button.new()
		button.text = str(option[1]).get_slice(" : ", 1) if " : " in str(option[1]) else str(option[1])
		button.custom_minimum_size.y = 56
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		button.add_theme_font_size_override("font_size", 15)
		button.set_meta("key", key.duplicate(true))
		button.disabled = option.size() > 2 and not option[2].get("available", true)
		if button.disabled:
			button.tooltip_text = "Question disponible au prochain tour"
		elif option.size() > 2 and option[2].get("cost", 1) == 0:
			button.tooltip_text = "Réponse déjà obtenue · aucun PA ni temps consommé"
		button.pressed.connect(_choose.bind(key.duplicate(true)))
		choices.add_child(button)
	choices_scroll.scroll_vertical = 0
	choices_scroll.custom_minimum_size.y = minf(252, ceilf(choices.get_child_count() / 2.0) * 64)
	next_button.text = "Retour aux questions"

func _choose(key: Array) -> void:
	if waiting:
		return
	for option in options:
		if option[0] == key and option.size() > 2 and not option[2].get("available", true):
			return
	waiting = true
	reading = false
	for option in options:
		if option[0] == key:
			question.text = "Vous · " + str(option[1])
			question.visible = true
	choices_scroll.visible = false
	speech.show()
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
