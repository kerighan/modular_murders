shader_type canvas_item;
render_mode unshaded;
uniform sampler2D city_frame : hint_screen_texture, filter_linear;
uniform float bloom_strength = 0.8;

vec3 bright(vec2 uv) {
	vec3 c = texture(city_frame, uv).rgb;
	float peak = max(c.r, max(c.g, c.b));
	return c * smoothstep(0.4, 0.85, peak);
}

void fragment() {
	vec2 uv = SCREEN_UV;
	vec2 px = SCREEN_PIXEL_SIZE;
	vec3 scene = texture(city_frame, uv).rgb;
	vec3 halo = vec3(0.0);
	for (int i = 0; i < 8; i++) {
		float angle = float(i) * 0.785398;
		vec2 offset = vec2(cos(angle), sin(angle));
		halo += bright(uv + offset * px * 4.0) * 0.085;
		halo += bright(uv + offset * px * 10.0) * 0.04;
	}
	float vignette = smoothstep(0.25, 0.85, length((uv - 0.5) * vec2(1.0, 0.85)));
	COLOR = vec4((scene + halo * bloom_strength) * (1.0 - vignette * 0.32), 1.0);
}
