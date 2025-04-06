# coding=utf-8
from __future__ import absolute_import

# Required imports for the plugin class
import octoprint.plugin

# --- Your Simplified Plugin Class Definition ---
# (Copied from your previous plugin.py, with logger messages updated slightly)

class PrintAuthPlugin(octoprint.plugin.StartupPlugin,
                      octoprint.plugin.AssetPlugin):

    # No __init__(self) needed for simplified version

    # No get_settings_defaults(self) needed for simplified version

    def on_startup(self, host, port):
         # Added 'from __init__.py' to confirm this code runs
         self._logger.info("Minimal PrintAuthPlugin started from __init__.py.")
         pass

    # No event/api handlers needed for simplified version

    def get_assets(self):
        # Added 'from __init__.py' to confirm this code runs
        self._logger.info("Minimal PrintAuthPlugin get_assets called from __init__.py.")
        return {
            "js": ["js/printauth.js"],
            "css": ["css/printauth.css"]
        }

    # No get_template_configs needed for simplified version
    # No get_api_commands needed for simplified version
    # No on_api_get needed for simplified version

# --- End of Plugin Class Definition ---


# --- Plugin Registration ---
# Define plugin name and Python compatibility globally
__plugin_name__ = "Print Authentication Plugin Test" # Or your preferred name
__plugin_pythoncompat__ = ">=3.7,<4" # Compatible with Python 3.7+ (including 3.11)

# Define the special __plugin_load__ function OctoPrint looks for
def __plugin_load__():
    # Make implementation global so OctoPrint finds it
    global __plugin_implementation__
    __plugin_implementation__ = PrintAuthPlugin()

    # If you add hooks later (like software update check), define them here:
    # global __plugin_hooks__
    # __plugin_hooks__ = { ... }

    # If you add blueprint routes later, define them here:
    # global __plugin_routes__
    # __plugin_routes__ = { ... }