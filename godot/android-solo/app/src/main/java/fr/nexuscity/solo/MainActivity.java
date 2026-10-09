package fr.nexuscity.solo;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.godotengine.godot.Godot;
import org.godotengine.godot.GodotActivity;
import org.godotengine.godot.plugin.GodotPlugin;

public class MainActivity extends GodotActivity {
    private NexusSolo solo;

    @Override public List<String> getCommandLine() {
        List<String> args = new ArrayList<>(super.getCommandLine());
        args.add("--rendering-method"); args.add("gl_compatibility");
        args.add("--rendering-driver"); args.add("opengl3");
        return args;
    }

    @Override public Set<GodotPlugin> getHostPlugins(Godot godot) {
        if (solo == null) solo = new NexusSolo(godot, getApplicationContext());
        Set<GodotPlugin> plugins = new HashSet<>();
        plugins.add(solo);
        return plugins;
    }
}
