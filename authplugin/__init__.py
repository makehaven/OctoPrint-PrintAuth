# coding=utf-8
from __future__ import absolute_import

# --- Add back necessary imports ---
import flask
import requests # Make sure 'requests' is in setup.py install_requires
import octoprint.plugin

# Global Plugin Identifier (optional here, but often seen)
# __plugin_identifier__ = "print_auth_plugin" # Defined by entry point key

# --- Plugin Class Definition with Restored Methods ---
class PrintAuthPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.EventHandlerPlugin, # Added back for on_event
    octoprint.plugin.SimpleApiPlugin,  # Added back for on_api_command
    octoprint.plugin.TemplatePlugin,   # Added back for get_template_configs
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SettingsPlugin
):

    # --- Added back __init__ ---
    def __init__(self):
        self._session = None
        # Initialize logger here if needed, though usually available via self._logger
        # self._logger.info("PrintAuthPlugin initialized.") # Example log

    # --- Added back get_settings_defaults ---
    def get_settings_defaults(self):
        # Consider making these more user-friendly later
        return dict(
            login_url="https://makehaven.org/user/login",
            username="your_username", # Should be configured by user
            password="your_password", # Should be configured by user
            api_url="https://makehaven.org/api/v0/email/{email}/user",
            permission_id="", # Needs explanation or configuration
            workstation_id=""  # Needs explanation or configuration
        )

    def on_startup(self, host, port):
         self._logger.info("PrintAuthPlugin started.") # Updated log

    # --- Added back on_event ---
    def on_event(self, event, payload):
        if event == "PrintStarted":
            self._logger.info("Print started event caught; prompting for email authentication.")
            # Use the plugin identifier from setup.py entry point key
            self._plugin_manager.send_plugin_message("print_auth_plugin", {"prompt": True})

    # --- Added back on_api_command ---
    def on_api_command(self, command, data):
        # Check if the command is 'authenticate' and proceed
        if command == "authenticate":
            email = data.get("email")
            if not email:
                self._logger.warning("Authentication command received without email.")
                return flask.jsonify(success=False, message="Email missing"), 400 # Bad request

            self._logger.info(f"Attempting authentication for email: {email}")
            # Use a default dictionary for the result
            result = {"success": False, "message": "Authentication failed."}
            try:
                 result = self.handle_authentication(email)
                 # Cancel print only if authentication explicitly fails after trying
                 if not result.get("success", False):
                      self._logger.warning(f"Authentication failed for {email}. Canceling print.")
                      self._printer.cancel_print()
                      result["message"] = result.get("message", "Authentication failed") + ". Print canceled."
                 else:
                      self._logger.info(f"Authentication successful for {email}.")

            except Exception as e:
                 self._logger.error(f"Exception during authentication for {email}: {e}", exc_info=True)
                 self._printer.cancel_print() # Cancel on error too
                 result = {"success": False, "message": f"Server error during authentication. Print canceled. {e}"}

            return flask.jsonify(**result)
        else:
            # Return 404 or 400 for unknown commands
            return flask.make_response(f"Unknown command: {command}", 400)


    # --- Added back get_api_commands ---
    # Required for SimpleApiPlugin to know which commands expect which parameters
    def get_api_commands(self):
        return dict(
            authenticate=["email"] # The 'authenticate' command expects an 'email' field in JSON data
        )

    # --- Added back handle_authentication ---
    def handle_authentication(self, email):
        # Ensure session exists or login
        if not self._session:
            self._logger.info("No active session, attempting API login.")
            if not self.login_to_api():
                # Return specific failure message without cancelling print yet
                # Cancellation should happen in on_api_command if needed
                return dict(success=False, message="API login failed")

        # Get API URL from settings and format it
        api_url_template = self._settings.get(["api_url"])
        if not api_url_template:
            return dict(success=False, message="API URL not configured in settings.")
        api_url = api_url_template.format(email=email)

        self._logger.info(f"Querying API: {api_url}")
        try:
            response = self._session.get(api_url, timeout=10) # Added timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Assuming the API returns JSON with an "authenticated" boolean field
            data = response.json()
            if data.get("authenticated", False):
                 # Check for specific permissions if configured
                 # permission_id = self._settings.get(["permission_id"])
                 # workstation_id = self._settings.get(["workstation_id"])
                 # Add logic here to check permissions/workstation if needed
                 return dict(success=True, message="Authentication successful")
            else:
                 # Log the reason if provided by the API, else generic failure
                 api_message = data.get("message", "User not authenticated by API")
                 self._logger.warning(f"Authentication failed for {email} via API: {api_message}")
                 return dict(success=False, message=api_message)

        except requests.exceptions.RequestException as e:
            self._logger.error(f"Error during API request to {api_url}: {e}")
            return dict(success=False, message=f"Network or API error: {e}")
        except Exception as e:
            # Catch other potential errors like JSON decoding
            self._logger.error(f"Unexpected error during authentication processing: {e}", exc_info=True)
            return dict(success=False, message=f"Unexpected server error: {e}")


    # --- Added back login_to_api ---
    def login_to_api(self):
        self._session = requests.Session()
        login_url = self._settings.get(["login_url"])
        username = self._settings.get(["username"])
        password = self._settings.get(["password"])

        if not all([login_url, username, password]):
             self._logger.error("API login credentials or URL missing in settings.")
             return False

        # Check form data required by makehaven.org/user/login
        # Inspecting the form suggests: name, pass, form_id=user_login, op=Log in
        data = {"name": username, "pass": password, "form_id": "user_login", "op": "Log in"}
        self._logger.info(f"Attempting login to {login_url} for user {username}")

        try:
            response = self._session.post(login_url, data=data, timeout=10) # Added timeout
            response.raise_for_status() # Check for HTTP errors

            # How to check for successful login? Check response URL, content, status?
            # This is highly dependent on the target site's behavior.
            # Assuming success if no error and maybe checking response content/URL:
            if "Log out" in response.text or response.url != login_url: # Example check
                 self._logger.info(f"Successfully logged in to API server for user {username}.")
                 return True
            else:
                 self._logger.error(f"Login failed for user {username}. Status: {response.status_code}. Check credentials/URL.")
                 self._session = None # Clear session on failure
                 return False
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Login to API failed: {e}")
            self._session = None # Clear session on failure
            return False


    # --- Added back get_template_configs ---
    # This enables the settings UI template
    def get_template_configs(self):
        return [
            # Use 'settings' type for standard settings dialog integration
            dict(type="settings", custom_bindings=False) # Assuming standard knockout bindings for settings
        ]

    # --- AssetPlugin ---
    def get_assets(self):
        self._logger.info("PrintAuthPlugin get_assets called from __init__.py.")
        return dict(
            js=["js/printauth.js"],
            css=["css/printauth.css"] # Keep CSS even if empty for now
        )

# --- Plugin Registration ---
__plugin_name__ = "Print Authentication Plugin" # Changed name back
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_identifier__ = "print_auth_plugin" # Define identifier explicitly here too

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrintAuthPlugin()

    # Add hooks if needed later
    # global __plugin_hooks__
    # __plugin_hooks__ = { ... }

    # Add routes if using BlueprintPlugin instead of SimpleApiPlugin
    # global __plugin_routes__
    # __plugin_routes__ = [ ... ]