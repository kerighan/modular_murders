package fr.nexuscity.solo;

import android.content.Context;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.File;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.godotengine.godot.Godot;
import org.godotengine.godot.plugin.GodotPlugin;
import org.godotengine.godot.plugin.UsedByGodot;
import org.json.JSONArray;
import org.json.JSONObject;

/** Non-blocking JSON bridge. Python's worker handles rules, saves and QTE waits. */
public final class NexusSolo extends GodotPlugin {
    private final Context context;
    private final ExecutorService startup = Executors.newSingleThreadExecutor();
    private volatile PyObject session;
    private volatile String failure;

    public NexusSolo(Godot godot, Context context) {
        super(godot);
        this.context = context;
    }

    @Override public String getPluginName() { return "NexusSolo"; }

    @UsedByGodot public void open_session(int seed, String name) {
        startup.execute(() -> {
            try {
                if (!Python.isStarted()) Python.start(new AndroidPlatform(context));
                close_session();
                String save = new File(context.getFilesDir(), "nexus-causal-solo.json").getAbsolutePath();
                session = Python.getInstance().getModule("solo_runtime")
                    .callAttr("SoloSession", save, seed, name, "causal");
            } catch (Exception e) {
                failure = "Démarrage solo impossible : " + e;
            }
        });
    }

    @UsedByGodot public void send_message(String json) {
        PyObject current = session;
        if (current != null) current.callAttr("send", json);
    }

    @UsedByGodot public String poll_messages() {
        if (failure != null) {
            String error = failure;
            failure = null;
            try {
                JSONObject msg = new JSONObject().put("type", "error").put("message", error);
                return new JSONArray().put(msg).toString();
            } catch (Exception ignored) { return "[]"; }
        }
        PyObject current = session;
        return current == null ? "[]" : current.callAttr("poll").toString();
    }

    @UsedByGodot public void close_session() {
        PyObject previous = session;
        session = null;
        if (previous != null) previous.callAttr("close");
    }

    @Override public void onGodotTerminating() {
        startup.execute(this::close_session);
        startup.shutdown();
    }
}
