extends "res://tests/fixture_stability_smoke.gd"

func _capture(name: String) -> void:
	if name in ["fixtures-before", "fixtures-inspected", "fixtures-collected"]:
		_check(client.view.place == "bar", "Use a real bar crime (seed 5)")
		await process_frame
		_check_targets()
		# Stress only the visual projection with additional customers/contacts.
		# Restore the real public view before all native investigation actions.
		var crowded: Dictionary = client.view.duplicate(true)
		var sample: Dictionary = crowded.present[0].duplicate(true)
		for index in 3:
			var person: Dictionary = sample.duplicate(true)
			person.id = 100 + index
			person.name = "Client " + str(index + 1)
			person.activity = "prend un verre"
			crowded.present.append(person)
		var contact: Dictionary = crowded.staff[0].duplicate(true)
		contact.id = "layout:witness"
		contact.name = "Contact"
		contact.placement = "witness"
		crowded.staff.append(contact)
		client.lounge.populate(crowded)
		await process_frame
		_check_targets()
		await super._capture("bar-layout-crowded-" + name)
		client.lounge.populate(client.view)
		await process_frame
		await process_frame
	if name in ["fixtures-before", "fixtures-inspected", "fixtures-collected", "fixtures-transferred"]:
		_check_targets()
	await super._capture(name)

func _check_targets() -> void:
	var lounge: Node3D = client.lounge
	for id in lounge.fixture_buttons:
		var button: Button = lounge.fixture_buttons[id]
		_check(button.is_visible_in_tree(), "Bar fixture not initially visible: " + id)
		_check(button.size.x >= 48 and button.size.y >= 48, "Touch target too small")
		var rect: Rect2 = button.get_global_rect()
		_check(rect.end.y < 448, "Fixture touch area covered by phone bottom navigation: " + id)
		_check(button._has_point(button.size * 0.5), "Wrong target owns fixture center: " + id)
		for other in lounge.person_buttons.values() + lounge.staff_buttons.values():
			_check(not rect.intersects(other.get_global_rect()), "Fixture/person touch areas overlap: " + id)
		for target in lounge.targets:
			if target.button not in lounge.person_buttons.values() + lounge.staff_buttons.values():
				continue
			for mesh in lounge.props.get_children():
				if str(mesh.get_meta("fixture_id", "")) != id:
					continue
				var fixture_at: Vector3 = mesh.get_meta("fixture_at")
				_check(fixture_at.distance_to(target.at) > 1.5, "Fixture physically overlaps a person: " + id)
		for other_id in lounge.fixture_buttons:
			if other_id == id:
				continue
			_check(not rect.intersects(lounge.fixture_buttons[other_id].get_global_rect()), "Fixture touch areas overlap: " + id + " / " + other_id)
		print("BAR TARGET ", id, " ", rect)
