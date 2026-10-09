shader_type spatial;
render_mode unshaded;
uniform float district_visibility = 1.0;

void fragment() {
	ALBEDO = COLOR.rgb * district_visibility;
	EMISSION = COLOR.rgb * 1.5 * district_visibility * district_visibility;
}
