# Overlapping mobile hit areas select the closest glowing entrance.
extends Button

var navigation: Node

func _has_point(point: Vector2) -> bool:
	if not Rect2(Vector2.ZERO, size).has_point(point):
		return false
	var at := global_position + point
	var distance := at.distance_squared_to(get_global_rect().get_center())
	if navigation != null:
		for entry in navigation.entries:
			if entry.kind != "entrance":
				continue
			var other: Button = entry.target
			if other == self or other.disabled or not other.is_visible_in_tree():
				continue
			var rect := other.get_global_rect()
			if rect.has_point(at) and at.distance_squared_to(rect.get_center()) < distance - 0.01:
				return false
	return true
