shader_type spatial;
render_mode unshaded;
uniform sampler2D artwork : source_color, filter_linear_mipmap;
uniform float district_visibility = 1.0;

void fragment() {
	vec3 ink = texture(artwork, UV).rgb;
	ALBEDO = ink * district_visibility;
	EMISSION = ink * 1.8 * district_visibility * district_visibility;
}
