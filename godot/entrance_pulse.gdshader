shader_type spatial;
render_mode unshaded;

void fragment() {
	// Slow 10% breathing, never flashing or disappearing. Text stays steady.
	float pulse = 0.95 + 0.05 * sin(TIME * 2.41661);
	ALBEDO = COLOR.rgb;
	EMISSION = COLOR.rgb * 1.7 * pulse;
}
