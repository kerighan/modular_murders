shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never;

void fragment() {
	ALBEDO = COLOR.rgb;
	EMISSION = COLOR.rgb * 0.32;
	ALPHA = COLOR.a;
}
