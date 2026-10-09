shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled;
uniform vec4 tint : source_color = vec4(0.0, 0.6, 1.0, 1.0);
uniform float strength = 0.24;
uniform float district_visibility = 1.0;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float falloff = pow(max(0.0, 1.0 - dot(p, p)), 2.0);
	vec2 cells = floor(UV * vec2(34.0, 48.0));
	float broken = 0.14 + 0.86 * smoothstep(0.48, 0.9, hash(cells));
	ALBEDO = tint.rgb;
	ALPHA = falloff * broken * strength * district_visibility;
}
