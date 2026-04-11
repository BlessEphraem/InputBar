import os
import json
import shutil
from Core.Paths import THEMES_DIR, BUILTIN_THEMES_DIR
from Core.Logging import dprint, eprint

def _deep_merge(default: dict, user: dict) -> tuple[dict, bool]:
    """
    Recursively merges `user` into `default`.
    User values take priority; missing keys are filled from default.
    Returns (merged_dict, was_updated) where was_updated=True if keys were added.
    """
    merged  = dict(default)
    updated = False
    for key, default_val in default.items():
        if key not in user:
            updated = True
        elif isinstance(default_val, dict) and isinstance(user[key], dict):
            merged[key], child_updated = _deep_merge(default_val, user[key])
            if child_updated:
                updated = True
        else:
            merged[key] = user[key]
    # Preserve keys the user added that aren't in the default schema
    for key, val in user.items():
        if key not in default:
            merged[key] = val
    return merged, updated


def sync_builtin_themes() -> None:
    """
    Synchronises built-in themes (from Assets/Themes/) into Data/Themes/.

    Rules:
    - If a built-in theme does NOT exist in Data/Themes/ → copy it (first install or new theme).
    - If it already exists (user may have modified it) → only inject missing keys via
      _deep_merge, never overwrite existing values. User changes are always preserved.
    - Custom user themes (not present in Assets/Themes/) are never touched.
    """
    if not os.path.isdir(BUILTIN_THEMES_DIR):
        dprint(f"Theme sync: built-in themes directory not found ({BUILTIN_THEMES_DIR})")
        return

    for filename in os.listdir(BUILTIN_THEMES_DIR):
        if not filename.endswith(".json"):
            continue

        src  = os.path.join(BUILTIN_THEMES_DIR, filename)
        dest = os.path.join(THEMES_DIR, filename)

        try:
            with open(src, "r", encoding="utf-8") as f:
                builtin_data = json.load(f)
        except Exception as e:
            eprint(f"Theme sync: error reading built-in '{filename}' ({e})")
            continue

        if not os.path.exists(dest):
            # First install or new built-in theme → copy as-is
            try:
                shutil.copy2(src, dest)
                dprint(f"Theme sync: copied '{filename}' to Data/Themes/")
            except Exception as e:
                eprint(f"Theme sync: error copying '{filename}' ({e})")
        else:
            # Theme already exists → inject only missing keys, preserve user values
            try:
                with open(dest, "r", encoding="utf-8") as f:
                    user_data = json.load(f)

                merged, was_updated = _deep_merge(builtin_data, user_data)

                if was_updated:
                    with open(dest, "w", encoding="utf-8") as f:
                        json.dump(merged, f, indent=4)
                    dprint(f"Theme sync: new keys injected into '{filename}'")
            except Exception as e:
                eprint(f"Theme sync: error merging '{filename}' ({e})")


def load_theme(theme_name: str = "theme_default") -> dict:
    default_theme = {
        "window": {
            "width": 620,
            "height": 500,
            "margin": 50
        },
        "container": {
            "background":      "rgba(46, 46, 46, 0.85)",
            "border":          "1px solid #444",
            "border_radius":   "8px",
            "shadow_color":    [0, 0, 0, 180],
            "shadow_blur":     25,
            "shadow_x_offset": 0,
            "shadow_y_offset": 5,
            "padding":         10,
            "spacing":         8
        },
        "search_bar": {
            "background":   "rgba(61, 61, 61, 0.90)",
            "text_color":   "white",
            "border":       "1px solid #555",
            "border_radius":"4px",
            "padding":      "12px",
            "font_size":    "18px",
            "font_family":  "Segoe UI",
            "placeholder":  "Search..."
        },
        "results_list": {
            "background":          "transparent",
            "text_color":          "#ddd",
            "selected_background": "rgba(0, 120, 212, 1.0)",
            "selected_text_color": "white",
            "font_size":           "15px",
            "font_family":         "Segoe UI",
            "item_padding":        "8px",
            "item_border_radius":  "4px",
            "height":              350
        },
        "scrollbar": {
            "width":             "0px",
            "background":        "transparent",
            "handle_color":      "rgba(100, 100, 100, 0.6)",
            "handle_hover_color":"rgba(150, 150, 150, 0.8)",
            "border_radius":     "3px"
        }
    }

    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")

    if not os.path.exists(theme_file):
        if theme_name != "theme_default":
            eprint(f"Theme not found: '{theme_name}'. Falling back to theme_default.")
            theme_file = os.path.join(THEMES_DIR, "theme_default.json")

        if not os.path.exists(theme_file):
            try:
                with open(theme_file, "w", encoding="utf-8") as f:
                    json.dump(default_theme, f, indent=4)
                dprint(f"Default theme created: {theme_file}")
            except Exception as e:
                eprint(f"Error creating theme: {e}")
            return default_theme

    try:
        with open(theme_file, "r", encoding="utf-8") as f:
            user_theme = json.load(f)
    except Exception as e:
        eprint(f"Error reading theme '{theme_name}': {e}")
        return default_theme

    merged, was_updated = _deep_merge(default_theme, user_theme)

    if was_updated:
        try:
            with open(theme_file, "w", encoding="utf-8") as f:
                json.dump(merged, f, indent=4)
            dprint(f"Theme '{theme_name}' updated with new default keys.")
        except Exception as e:
            eprint(f"Error saving theme: {e}")

    return merged
