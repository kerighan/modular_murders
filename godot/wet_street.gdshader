shader_type spatial;
render_mode diffuse_lambert_wrap;
varying vec3 world_position;

float noise(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = world_position.xz;
	float grain = noise(floor(p * 12.0));
	float puddle = smoothstep(0.25, 0.8, sin(p.x * 1.7 + sin(p.y * 2.1)) * sin(p.y * 1.8));
	ALBEDO = COLOR.rgb * (0.96 + grain * 0.06 + puddle * 0.025);
	ROUGHNESS = mix(0.42, 0.25, puddle);
	METALLIC = 0.08;
	SPECULAR = 0.22;
}
