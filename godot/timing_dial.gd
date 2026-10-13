extends Control
# A rotating needle, a target arc: tap when the needle crosses the arc.
# Skills skip this entirely; without them, this is where the hand matters.

signal answered(score: float)

const RADIUS := 86.0
const TURNS_BEFORE_TIMEOUT := 2.0

var active := false
var kind := ""
var angle := 0.0  # needle, radians
var speed := 4.0  # radians per second
var target := 0.0  # centre of the arc, radians
var half_width := 0.4  # radians
var elapsed := 0.0
var flash := 0.0  # seconds of result flash left
var last_score := -1.0
var title := Label.new()
var hint := Label.new()

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false
	title.add_theme_font_size_override("font_size", 20)
	title.add_theme_color_override("font_color", Color("e8f1f4"))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(title)
	hint.add_theme_font_size_override("font_size", 14)
	hint.add_theme_color_override("font_color", Color("8cc6d7"))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(hint)

func start(challenge_kind: String, difficulty: float) -> void:
	# difficulty 0..1: a narrower arc and a faster needle
	kind = challenge_kind
	var level := clampf(difficulty, 0.0, 1.0)
	half_width = lerpf(0.55, 0.22, level)
	speed = lerpf(3.2, 6.0, level)
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	target = rng.randf_range(0.0, TAU)
	angle = fposmod(target + PI, TAU)  # start opposite the arc: a half turn to read it
	elapsed = 0.0
	flash = 0.0
	last_score = -1.0
	active = true
	title.text = {"lockpick": "Crochetage", "search": "Fouille", "persuasion": "Persuasion", "fingerprint": "Relevé d'empreintes"}.get(kind, kind.capitalize())
	hint.text = "Touchez quand l'aiguille est dans la zone"
	visible = true
	_layout()
	queue_redraw()

func _layout() -> void:
	var centre := size / 2.0
	title.position = Vector2(0, centre.y - RADIUS - 64)
	title.size = Vector2(size.x, 30)
	hint.position = Vector2(0, centre.y + RADIUS + 22)
	hint.size = Vector2(size.x, 24)

func hit() -> void:
	if not active:
		return
	var delta := absf(angle_difference(angle, target))
	# Inside the arc scores at least 0.5, the centre scores 1; outside fades to 0.
	var score := clampf(1.0 - delta / (half_width * 2.0), 0.0, 1.0)
	_finish(score)

func _finish(score: float) -> void:
	active = false
	last_score = score
	flash = 0.55
	hint.text = "Réussi" if score >= 0.5 else "Raté"
	queue_redraw()
	answered.emit(score)

func _process(delta: float) -> void:
	if active:
		angle = fposmod(angle + speed * delta, TAU)
		elapsed += delta
		if elapsed * speed >= TAU * TURNS_BEFORE_TIMEOUT:
			_finish(0.0)
		queue_redraw()
	elif flash > 0.0:
		flash -= delta
		if flash <= 0.0:
			visible = false
		queue_redraw()

func _gui_input(event: InputEvent) -> void:
	if active and (event is InputEventScreenTouch and event.pressed or event is InputEventMouseButton and event.pressed):
		hit()
		accept_event()

func _draw() -> void:
	var centre := size / 2.0
	draw_circle(centre, RADIUS + 26, Color(0.02, 0.055, 0.085, 0.82))
	draw_arc(centre, RADIUS, 0.0, TAU, 96, Color("355564"), 10.0, true)
	var arc_color := Color("83e5b3") if last_score < 0.0 or last_score >= 0.5 else Color("ff5a74")
	if flash > 0.0:
		arc_color = arc_color.lightened(0.3)
	draw_arc(centre, RADIUS, target - half_width, target + half_width, 32, arc_color, 12.0, true)
	for i in 12:  # ticks, so the speed reads
		var a := i * TAU / 12.0
		draw_line(centre + Vector2.from_angle(a) * (RADIUS - 14), centre + Vector2.from_angle(a) * (RADIUS - 8), Color("5d7f8c"), 2.0)
	var tip := centre + Vector2.from_angle(angle) * (RADIUS - 4)
	draw_line(centre, tip, Color("ffd386"), 4.0, true)
	draw_circle(centre, 7.0, Color("ffd386"))
	if last_score >= 0.0:
		var text := "%d %%" % int(round(last_score * 100.0))
		draw_string(ThemeDB.fallback_font, centre + Vector2(-20, 6), text, HORIZONTAL_ALIGNMENT_CENTER, 40, 18, Color("e8f1f4"))
