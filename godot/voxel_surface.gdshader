shader_type spatial;
render_mode diffuse_lambert_wrap;
uniform float district_visibility = 1.0;

void fragment() {
	ALBEDO = mix(vec3(0.008, 0.014, 0.025), COLOR.rgb, district_visibility);
	ROUGHNESS = 0.82;
	METALLIC = 0.12;
}
