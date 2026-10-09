# Global touch arbitration runs before GUI: buttons are taps, drags are gestures.
extends Node

var host: Node
var touches := {}
var primary := -1
var origin := Vector2.ZERO
var active := false
var pinching := false
var mode := ""
var scroll: ScrollBar
var scroll_container: ScrollContainer
var horizontal := false
var velocity := Vector2.ZERO
var last_motion := 0
const THRESHOLD := 10.0
const FRICTION := 6.5

func cancel_inertia() -> void:
	velocity = Vector2.ZERO

func _cancel_button_presses() -> void:
	# Disabling clears a pending press without toggling selected equipment.
	# Re-enable immediately; let the real release reach GUI to clear touch indices.
	for button in host.find_children("*", "BaseButton", true, false):
		if not button.disabled:
			button.disabled = true
			button.disabled = false

func _begin(at: Vector2) -> void:
	active = false
	pinching = false
	velocity = Vector2.ZERO
	origin = at
	last_motion = Time.get_ticks_msec()
	scroll = null
	scroll_container = null
	mode = "world" if host._map_gestures_allowed() else ""
	if mode.is_empty():
		var containers := host.find_children("*", "ScrollContainer", true, false)
		for container in containers:
			if container.is_visible_in_tree() and container.get_global_rect().has_point(at):
				scroll_container = container
				var vertical: ScrollBar = container.get_v_scroll_bar()
				horizontal = vertical.max_value <= vertical.page
				scroll = container.get_h_scroll_bar() if horizontal else vertical
				mode = "scroll"
		for rich_text in host.find_children("*", "RichTextLabel", true, false):
			if rich_text.is_visible_in_tree() and rich_text.get_global_rect().has_point(at):
				scroll = rich_text.get_v_scroll_bar()
				scroll_container = null
				horizontal = false
				mode = "scroll"

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed:
			var stopping := touches.is_empty() and velocity.length_squared() >= 25
			if touches.is_empty():
				primary = event.index
				_begin(event.position)
			touches[event.index] = event.position
			if stopping:
				# A tap arrests a fling without activating the placard underneath.
				_cancel_button_presses()
				get_viewport().set_input_as_handled()
			if touches.size() > 1:
				velocity = Vector2.ZERO
				pinching = true
				_cancel_button_presses()
		else:
			touches.erase(event.index)
			if event.index == primary:
				# Allow one slow render frame between the final drag and release.
				# A stationary held finger still stops the fling after two frames.
				var idle_limit := maxf(120.0, host.get_process_delta_time() * 1500.0)
				if pinching or not active or Time.get_ticks_msec() - last_motion > idle_limit:
					velocity = Vector2.ZERO
				active = false
				primary = -1
			if touches.is_empty():
				pinching = false
		return # GUI receives the release, but canceled presses cannot click.
	if not event is InputEventScreenDrag or not touches.has(event.index):
		return
	if mode == "world" and touches.size() == 2:
		var ids := touches.keys()
		var before: float = touches[ids[0]].distance_to(touches[ids[1]])
		touches[event.index] = event.position
		var after: float = touches[ids[0]].distance_to(touches[ids[1]])
		if before > 1 and after > 1:
			host._stop_camera_focus()
			host.cam.size = clampf(host.cam.size * before / after, 8.0, 68.0)
		velocity = Vector2.ZERO
		get_viewport().set_input_as_handled()
		return
	touches[event.index] = event.position
	if event.index != primary or mode.is_empty() or pinching:
		return
	if not active:
		if origin.distance_to(event.position) < THRESHOLD:
			return
		active = true
		if is_instance_valid(scroll_container):
			var hbar := scroll_container.get_h_scroll_bar()
			var vbar := scroll_container.get_v_scroll_bar()
			if hbar.max_value > hbar.page and vbar.max_value > vbar.page:
				horizontal = absf(event.relative.x) > absf(event.relative.y)
				scroll = hbar if horizontal else vbar
		_cancel_button_presses()
		if mode == "world":
			host._stop_camera_focus()
	var now := Time.get_ticks_msec()
	var dt := clampf(float(now - last_motion) / 1000.0, 0.008, 0.25)
	last_motion = now
	velocity = velocity.lerp(event.relative / dt, 0.65).limit_length(2600)
	_apply(event.relative)
	get_viewport().set_input_as_handled() # No competing native scroll or camera drag.

func _apply(pixels: Vector2) -> void:
	if mode == "world" and host._map_gestures_allowed():
		host._pan(pixels)
	elif mode == "scroll" and is_instance_valid(scroll) and scroll.is_visible_in_tree():
		var before := scroll.value
		scroll.value -= pixels.x if horizontal else pixels.y
		if is_equal_approx(before, scroll.value):
			velocity = Vector2.ZERO # Stop at a menu boundary, do not bounce.
	else:
		velocity = Vector2.ZERO

func _process(delta: float) -> void:
	if not touches.is_empty() or velocity.length_squared() < 25:
		return
	var decay := exp(-FRICTION * delta)
	_apply(velocity * (1.0 - decay) / FRICTION)
	velocity *= decay
