# coding=utf-8
from __future__ import absolute_import

# --- Required Imports ---
import flask
import requests # Make sure 'requests' is in setup.py install_requires
import octoprint.plugin
import json # For formatting the note if needed

# Global Plugin Identifier (optional here, but often seen)
# __plugin_identifier__ = "print_auth_plugin" # Defined by entry point key

# --- Plugin Class Definition ---
class PrintAuthPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SettingsPlugin # <-- *** The crucial fix ***
):

    def __init__(self):
        self._session = None
        # self._logger.info("PrintAuthPlugin initializing.") # Commented out or deleted

    # -- SettingsPlugin
    def get_settings_defaults(self):
        self._logger.info("Getting default settings.")
        return dict(
            # --- API Login Credentials ---
            login_url="https://makehaven.org/user/login", # Default, user should verify/change
            username="", # User MUST configure
            password="", # User MUST configure
            # --- API Endpoint Info ---
            # URL to get user details by email. Must include {email} placeholder.
            user_api_url="https://makehaven.org/api/v0/email/{email}/user",
            # --- Permission & Source Info ---
            # The permission name required in the user's API data to allow printing
            permission_name="3D Print", # Example default, user MUST configure
            # Name of this tool/printer to send as 'source' parameter
            tool_name="MyOctoPrintPrinter", # Example default, user MUST configure
            # --- Hardcoded method parameter ---
            # (Not configurable, but documented here)
            api_method="octoprint_plugin"
        )

    # -- StartupPlugin
    def on_startup(self, host, port):
         self._logger.info(f"PrintAuthPlugin started. Tool name: {self._settings.get(['tool_name'])}")

    # -- EventHandlerPlugin
    def on_event(self, event, payload):
        if event == "PrintStarted":
            self._logger.info("Print started event caught; prompting for email authentication.")
            # Use the plugin identifier from setup.py entry point key
            # to send message to the correct JS listener
            self._plugin_manager.send_plugin_message("print_auth_plugin", {"prompt": True})

    # -- SimpleApiPlugin
    def get_api_commands(self):
        # Define the command our JS will call
        return dict(
            authenticate=["email"] # Expects JSON: {"command": "authenticate", "email": "user@example.com"}
        )

    def on_api_command(self, command, data):
        if command == "authenticate":
            email = data.get("email")
            if not email:
                self._logger.warning("Authentication command received without email.")
                return flask.jsonify(success=False, message="Email missing"), 400

            self._logger.info(f"Attempting authentication via API command for email: {email}")
            result = {"success": False, "message": "Authentication failed by default."}
            try:
                 # --- Get Filament Usage Note ---
                 note_text = "Filament usage not available."
                 try:
                     job_info = self._printer.get_current_job()
                     if job_info and job_info.get("file", {}).get("origin") and job_info.get("file", {}).get("path"):
                         metadata = self._file_manager.get_metadata(job_info["file"]["origin"], job_info["file"]["path"])
                         filament_data = metadata.get("analysis", {}).get("filament", {})
                         if filament_data:
                              usage_parts = []
                              # Check for tool-specific usage first (common format)
                              tool_usage = next(iter(filament_data.values()), None) if isinstance(list(filament_data.values())[0], dict) else None
                              if tool_usage:
                                   if tool_usage.get("length"): usage_parts.append(f"{tool_usage['length']:.2f}mm")
                                   if tool_usage.get("volume"): usage_parts.append(f"{tool_usage['volume']:.2f}cm3")
                              else: # Fallback for older single-value format
                                   if filament_data.get("length"): usage_parts.append(f"{filament_data['length']:.2f}mm")
                                   if filament_data.get("volume"): usage_parts.append(f"{filament_data['volume']:.2f}cm3")

                              if usage_parts: note_text = f"Filament: {' / '.join(usage_parts)}"
                              else: self._logger.info("Filament usage data present but no length/volume found.")
                         else:
                              self._logger.info("Filament usage data not found in metadata.")
                     else:
                         self._logger.warning("Could not get current job info to determine filament usage.")
                 except Exception as e_note:
                     self._logger.error(f"Error getting filament usage for note: {e_note}", exc_info=True)
                 # --------------------------------

                 result = self.handle_authentication(email, note_text)

                 if not result.get("success", False):
                      self._logger.warning(f"Authentication failed for {email}. Canceling print. Reason: {result.get('message')}")
                      self._printer.cancel_print()
                      result["message"] = result.get("message", "Authentication failed") + ". Print canceled."
                 else:
                      self._logger.info(f"Authentication successful for {email}.")

            except Exception as e:
                 self._logger.error(f"Unhandled exception during authentication for {email}: {e}", exc_info=True)
                 self._printer.cancel_print() # Cancel on error too
                 result = {"success": False, "message": f"Server error during authentication. Print canceled. {e}"}

            return flask.jsonify(**result)
        else:
            # Return 404 or 400 for unknown commands
            self._logger.warning(f"Received unknown API command: {command}")
            return flask.make_response(f"Unknown command: {command}", 400)

    # -- Authentication Logic --
    def handle_authentication(self, email, note="N/A"):
        # Ensure session exists or login
        if not self._session:
            self._logger.info("No active session, attempting API login.")
            if not self.login_to_api():
                return dict(success=False, message="API service login failed")

        # Get required settings
        user_api_url_template = self._settings.get(["user_api_url"])
        req_permission_name = self._settings.get(["permission_name"])
        tool_name = self._settings.get(["tool_name"])
        api_method = self.get_settings_defaults()["api_method"] # Get hardcoded value

        if not all([user_api_url_template, req_permission_name, tool_name]):
            self._logger.error("Required settings (user_api_url, permission_name, tool_name) are not configured.")
            return dict(success=False, message="Plugin settings are incomplete.")

        # Construct the user API URL
        try:
            api_url = user_api_url_template.format(email=requests.utils.quote(email)) # URL-encode email
        except KeyError:
             self._logger.error(f"user_api_url setting ('{user_api_url_template}') does not contain {{email}} placeholder.")
             return dict(success=False, message="User API URL setting is misconfigured.")

        # Construct query parameters
        params = {
            'source': tool_name,
            'method': api_method,
            'note': note
        }

        self._logger.info(f"Querying User API: {api_url} with params: {params}")
        try:
            response = self._session.get(api_url, params=params, timeout=15) # Increased timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Process the response JSON
            user_data_list = response.json()

            if not user_data_list or not isinstance(user_data_list, list):
                 self._logger.warning(f"API response for {email} was empty or not a list.")
                 # Attempt to get user info without permission check for better denial message
                 # (This part requires knowing if the API returns *anything* for invalid users)
                 # If API only returns data for valid users, this denial is appropriate.
                 return dict(success=False, message="User not found or invalid API response.")

            # Assuming the list contains one user object
            user_data = user_data_list[0]
            user_name = f"{user_data.get('first_name','?')} {user_data.get('last_name','?')}"
            self._logger.info(f"Received API data for user: {user_name}")

            # --- Check required permission ---
            user_permissions = user_data.get("permissions", []) # Assuming 'permissions' key holds a list
            if not isinstance(user_permissions, list):
                 # Handle cases where permissions might be a single string or other format
                 self._logger.warning(f"Permissions data for {email} is not a list: {user_permissions}")
                 user_permissions = [str(user_permissions)] # Attempt to treat as single item list

            self._logger.info(f"User permissions: {user_permissions}. Required: '{req_permission_name}'")

            if req_permission_name in user_permissions:
                 self._logger.info(f"Permission '{req_permission_name}' granted for {user_name} ({email}).")
                 return dict(success=True, message=f"Authenticated as {user_name}")
            else:
                 self._logger.warning(f"Required permission '{req_permission_name}' NOT found for {user_name} ({email}).")
                 return dict(success=False, message=f"User {user_name} lacks required permission '{req_permission_name}'")
            # --- End Permission Check ---

        except requests.exceptions.Timeout:
             self._logger.error(f"Timeout connecting to API: {api_url}")
             return dict(success=False, message="API connection timed out")
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Error during API request to {api_url}: {e}")
            return dict(success=False, message=f"Network or API error: {e}")
        except json.JSONDecodeError:
             self._logger.error(f"Failed to decode JSON response from {api_url}. Response text: {response.text[:500]}")
             return dict(success=False, message="Invalid JSON response from API")
        except Exception as e:
            # Catch other potential errors
            self._logger.error(f"Unexpected error during authentication processing: {e}", exc_info=True)
            return dict(success=False, message=f"Unexpected server error: {e}")

    def login_to_api(self):
        # Create new session only if needed
        if not self._session:
             self._session = requests.Session()
             # Add default headers maybe?
             # self._session.headers.update({"User-Agent": "OctoPrint PrintAuthPlugin"})

        login_url = self._settings.get(["login_url"])
        username = self._settings.get(["username"])
        password = self._settings.get(["password"])

        if not all([login_url, username, password]):
             self._logger.error("API login credentials or URL missing in settings.")
             return False

        # Form data based on MakeHaven login form inspection
        data = {"name": username, "pass": password, "form_id": "user_login", "op": "Log in"}
        self._logger.info(f"Attempting login to {login_url} for user '{username}'")

        try:
            # Use existing session to make login request
            response = self._session.post(login_url, data=data, timeout=15) # Increased timeout
            response.raise_for_status() # Check for HTTP errors

            # Check for successful login - NEEDS VERIFICATION based on MakeHaven site
            # Example: Check if username or 'Log out' link appears in response body
            if username in response.text or "Log out" in response.text or "user/logout" in response.text:
                 self._logger.info(f"Successfully logged in to API server for user '{username}'.")
                 return True
            else:
                 # Inspect response body if possible
                 self._logger.error(f"Login failed for user '{username}'. Status: {response.status_code}. Response snippet: {response.text[:500]}")
                 self._session = None # Clear session on definite failure
                 return False
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Login to API failed: {e}")
            self._session = None # Clear session on failure
            return False

    # -- TemplatePlugin
    def get_template_configs(self):
        return [
            dict(type="settings", name="Print Authentication", custom_bindings=False)
        ]

    # -- AssetPlugin
    def get_assets(self):
        # self._logger.info("PrintAuthPlugin get_assets called.") # Less noisy log
        return dict(
            js=["js/printauth.js"],
            css=["css/printauth.css"]
        )


# --- Plugin Registration ---
__plugin_name__ = "Print Authentication Plugin"
__plugin_pythoncompat__ = ">=3.7,<4"
# Define identifier explicitly for clarity, must match entry point key
__plugin_identifier__ = "print_auth_plugin"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrintAuthPlugin()

    # Add hooks if needed later
    # global __plugin_hooks__
    # __plugin_hooks__ = { ... }