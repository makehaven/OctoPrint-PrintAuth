# coding=utf-8
from __future__ import absolute_import

import flask
import requests
import octoprint.plugin
import json

# --- Hardcoded Values ---
# !! Double-check these credentials !!
HARDCODED_LOGIN_URL = "https://makehaven.org/user/login"
HARDCODED_USERNAME = "octoprint" # <-- Is this correct?
HARDCODED_PASSWORD = "dreams8make" # <-- Is this correct?
HARDCODED_PERMISSION_CHECK_URL_TEMPLATE = "https://makehaven.org/api/v0/email/{email}/permission/{permission}"
HARDCODED_PERMISSION_NAME = "printer_3d"
HARDCODED_TOOL_NAME = "OctoPrint_Test_Printer"
HARDCODED_API_METHOD = "octoprint_plugin"
# ------------------------

class PrintAuthPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin
    # octoprint.plugin.SettingsPlugin  # Keep commented out for now
):

    def __init__(self):
        self._session = None

    def on_startup(self, host, port):
         self._logger.info(f"PrintAuthPlugin started (HARDCODED). Tool: {HARDCODED_TOOL_NAME}. Check: {HARDCODED_PERMISSION_NAME}")

    def on_event(self, event, payload):
        if event == "PrintStarted":
            self._logger.info("Print started event caught; prompting for email authentication.")
            self._plugin_manager.send_plugin_message("print_auth_plugin", {"prompt": True})

# Inside class PrintAuthPlugin:
    def get_api_commands(self):
        return dict(
            authenticate=["email"],
            confirm_material=["choice"] # <<< Add this line
        )

    # -- TemplatePlugin --
    def get_template_configs(self):
        return [
            # We don't have settings UI right now, so only include the modal template
            dict(
                type="generic", # Use 'generic' to inject HTML somewhere in the main page
                template="print_auth_material_modal.jinja2",
                custom_bindings=False # We will use jQuery selectors, not Knockout bindings here
            )
            # If you bring settings back later, add that dict here too:
            # dict(type="settings", name="Print Authentication", custom_bindings=False)
        ]


# Inside class PrintAuthPlugin:
    def on_api_command(self, command, data):
        if command == "authenticate":
            # --- Keep all your existing 'authenticate' logic here ---
            email = data.get("email")
            if not email:
                self._logger.warning("Authentication command received without email.")
                return flask.jsonify(success=False, message="Email missing"), 400

            self._logger.info(f"Attempting DIRECT permission check (HARDCODED) via API command for email: {email}")
            result = {"success": False, "message": "Authentication failed by default."}
            try:
                 result = self.handle_authentication(email, note="OctoPrint Auth Attempt")
                 # ... (rest of your existing try/except block for authenticate) ...
                 # ... (which should end with returning flask.jsonify(**result)) ...

            except Exception as e:
                 # ... (keep existing exception handling) ...
                 self._logger.error(f"Unhandled exception during permission check for {email}: {e}", exc_info=True)
                 self._printer.cancel_print()
                 result = {"success": False, "message": f"Server error during permission check. Print canceled. {e}"}

            # Ensure the final result is returned for authenticate command
            return flask.jsonify(**result)
            # --- End of 'authenticate' block ---

        # --- Add this 'elif' block for the new command ---
        elif command == "confirm_material":
            choice = data.get("choice") # Should be "paid" or "own_material" from JS button click

            # Log the received choice
            self._logger.info(f"Received material confirmation choice from frontend: '{choice}'")

            # Placeholder for future logic:
            # - If print was paused here, call self._printer.resume_print()
            # - Log choice permanently? Send API call to log material usage?

            if choice in ["paid", "own_material"]:
                # Just acknowledge receipt successfully for now
                return flask.jsonify(success=True, message=f"Choice '{choice}' acknowledged by server.")
            else:
                # Handle unexpected choice value
                self._logger.warning(f"Received invalid material choice: {choice}")
                return flask.jsonify(success=False, message=f"Invalid choice received: {choice}"), 400
        # --- End of 'confirm_material' block ---

        else:
            # Keep existing handling for unknown commands
            self._logger.warning(f"Received unknown API command: {command}")
            return flask.make_response(f"Unknown command: {command}", 400)


# -- Authentication Logic (Checks permission directly - CORRECTED try/except) --
    def handle_authentication(self, email, note="N/A"):
        # Attempt login only if no session exists
        if not self._session:
            self._logger.info("No active session, attempting API login.")
            login_result, login_message = self.login_to_api() # Get detailed result
            if not login_result:
                # Return specific failure reason from login_to_api
                return dict(success=False, message=login_message)

        # --- Use Hardcoded Values ---
        perm_check_url_template = HARDCODED_PERMISSION_CHECK_URL_TEMPLATE
        req_permission_name = HARDCODED_PERMISSION_NAME
        tool_name = HARDCODED_TOOL_NAME
        api_method = HARDCODED_API_METHOD
        # ---------------------------

        # Construct the permission check URL
        try:
            safe_email = requests.utils.quote(email)
            safe_permission = requests.utils.quote(req_permission_name)
            api_url = perm_check_url_template.format(email=safe_email, permission=safe_permission)
        except Exception as e:
             self._logger.error(f"Error formatting permission check URL: {e}", exc_info=True)
             return dict(success=False, message="Internal error formatting API URL.")

        # Construct query parameters
        params = {'source': tool_name, 'method': api_method}
        if note: params['note'] = note

        self._logger.info(f"Checking permission API: {api_url} with params: {params}")

        # --- CORRECTED try...except block structure ---
        try:
            # Make the request
            response = self._session.get(api_url, params=params, timeout=15)
            self._logger.info(f"API response status: {response.status_code}")
            self._logger.debug(f"API response text: {response.text[:500]}")

            # Process the response (status check, JSON decoding, permission logic)
            if response.ok: # Status < 400
                 try:
                     json_data = response.json()
                     self._logger.info(f"API success response JSON: {json_data}")

                     # Check for expected success structure from MakeHaven API
                     if isinstance(json_data, list) and len(json_data) > 0 and json_data[0].get("access") == "true":
                         user_data = json_data[0]
                         first_name = user_data.get('first_name', '')
                         last_name = user_data.get('last_name', '')
                         user_name = f"{first_name} {last_name}".strip()
                         if not user_name: user_name = "User" # Fallback

                         self._logger.info(f"Permission '{req_permission_name}' granted for {user_name} ({email}). Fetching materials...")

                         # Fetch materials (assuming function exists and handles errors)
                         tool_id = 6046
                         material_list = self.fetch_materials(tool_id)

                         # Return success with user names and materials
                         return dict(success=True,
                                     message=f"Authenticated as {user_name}",
                                     firstName=first_name,
                                     lastName=last_name,
                                     materials=material_list)
                     else:
                         # Response OK but didn't contain expected success data
                         self._logger.warning(f"API Status OK but response JSON did not indicate access for {email}. Response: {json_data}")
                         return dict(success=False, message=f"Permission '{req_permission_name}' not granted for user (API check).")

                 except json.JSONDecodeError:
                     # Response OK but wasn't valid JSON
                     self._logger.warning("API returned Status OK but response was not valid JSON. Treating as failure.")
                     return dict(success=False, message="Invalid response from permission API")
            else:
                 # Response was not OK (e.g., 403 Forbidden, 404 Not Found)
                 message = f"Permission denied or user not found by API (Status: {response.status_code})"
                 try: # Attempt to get a more specific error message from API response body
                     error_data = response.json()
                     if isinstance(error_data, dict) and error_data.get("message"):
                         message = error_data["message"]
                 except json.JSONDecodeError:
                     pass # Stick to the status code message if JSON fails
                 self._logger.warning(f"Permission check failed for {email}. Status: {response.status_code}")
                 return dict(success=False, message=message)

        # --- Exception handling covers the self._session.get call and response processing ---
        except requests.exceptions.Timeout:
             self._logger.error(f"Timeout connecting to permission API: {api_url}")
             return dict(success=False, message="Network error: API connection timed out")
        except requests.exceptions.RequestException as e:
            # Catches connection errors, DNS errors, invalid URL errors etc.
            self._logger.error(f"Error during permission API request to {api_url}: {e}")
            return dict(success=False, message=f"Network error during permission check: {e}")
        except Exception as e:
            # Catch-all for any other unexpected errors (like within JSON processing if not caught above)
            self._logger.error(f"Unexpected error during permission check processing: {e}", exc_info=True)
            return dict(success=False, message=f"Unexpected server error during permission check: {e}")
        

# --- Login Logic (Adapted from Tkinter Example) ---
    def login_to_api(self):
        # Ensure session exists, create if not and set headers
        if not self._session:
            self._logger.info("Creating new requests session for API login.")
            self._session = requests.Session()
            # --- Add Headers similar to Tkinter example ---
            # Websites can be picky about User-Agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.155 Safari/537.36",
                "cache-control": "private, max-age=0, no-cache",
            }
            self._session.headers.update(headers)
            # ---------------------------------------------

        # --- Use Hardcoded Values (Ensure these are correct!) ---
        login_url = "https://makehaven.org/user/login"
        username = "octoprint" # Currently "octoprint"
        password = "dreams8make" # Currently "dreams8make"
        # ---------------------------

        # Form data matching MakeHaven's Drupal login form
        data = {"name": username, "pass": password, "form_id": "user_login", "op": "Log in"}
        self._logger.info(f"Attempting login post to {login_url} for HARDCODED user '{username}'")

        try:
            # Use the persistent session with updated headers
            response = self._session.post(login_url, data=data, timeout=15) # 15 sec timeout

            # Log details for debugging
            self._logger.info(f"Login POST response status: {response.status_code}")
            self._logger.debug(f"Login POST response URL after request: {response.url}") # See if redirected
            # Log first 500 chars of response body to help check success/failure reason
            self._logger.debug(f"Login POST response text snippet: {response.text[:500]}")

            # --- Refined Success Check ---
            # First, check for non-OK status (e.g., 4xx client errors, 5xx server errors)
            if not response.ok: # Equivalent to status_code >= 400
                 self._logger.error(f"Login failed for user '{username}'. HTTP Status: {response.status_code}. Check credentials/URL/server status.")
                 # Decide if session should be cleared based on error (e.g., maybe not for 5xx?)
                 # self._session = None # Optional: clear session on certain errors
                 return False, f"API service login failed (HTTP Status {response.status_code})"

            # If status is OK (2xx), assume success like the Tkinter example.
            # You could add more checks here based on the logged response text/URL if needed.
            # For example, explicitly check if "Log out" is present OR if the URL is no longer the login page.
            # logged_in_check = "Log out" in response.text or "user/logout" in response.text
            # on_login_page_check = "user/login" in response.url or "form_id=user_login" in response.text
            # if response.ok and (logged_in_check or not on_login_page_check):
            if response.ok: # Simplified check - relies on status code mostly
                 self._logger.info(f"Login successful for user '{username}' (Status OK).")
                 return True, "Login successful" # Return tuple: (Success Status, Message)

            # If response.ok was true but somehow didn't hit the condition above (unlikely with simple check)
            # self._logger.warning(f"Login response status OK but didn't meet detailed success criteria for user '{username}'.")
            # return False, "API service login failed (Unexpected OK response)"


        except requests.exceptions.Timeout:
             self._logger.error(f"Timeout during login to API: {login_url}")
             self._session = None # Clear session on network error
             return None, "Network error during login: Timeout" # Use None for network errors
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Login to API failed with exception: {e}", exc_info=True) # Log full traceback
            self._session = None # Clear session on network error
            return None, f"Network error during login: {e}"

    # -- AssetPlugin
    def get_assets(self):
        return dict(js=["js/printauth.js"], css=["css/printauth.css"])

# Inside class PrintAuthPlugin within authplugin/__init__.py

# --- Add this entire method inside the PrintAuthPlugin class ---

    def fetch_materials(self, tool_id):
        """Fetches materials list for a given tool ID from the API."""
        if not self._session:
            self._logger.error("Cannot fetch materials: No active API session.")
            return [] # Return empty list on error

        # Construct URL using the provided tool ID
        materials_url = f"https://makehaven.org/api/v0/materials/equipment/{tool_id}"
        self._logger.info(f"Fetching materials from: {materials_url}")

        try:
            response = self._session.get(materials_url, timeout=10) # Use existing session
            response.raise_for_status() # Check for HTTP errors

            materials_list = response.json()
            if isinstance(materials_list, list):
                 self._logger.info(f"Successfully fetched {len(materials_list)} materials.")
                 return materials_list
            else:
                 self._logger.error(f"Materials API response was not a list: {materials_list}")
                 return []

        except requests.exceptions.Timeout:
             self._logger.error(f"Timeout connecting to materials API: {materials_url}")
             return []
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Error during materials API request to {materials_url}: {e}")
            return []
        except json.JSONDecodeError:
             self._logger.error(f"Failed to decode JSON response from materials API: {materials_url}. Response text: {response.text[:500]}")
             return []
        except Exception as e:
            self._logger.error(f"Unexpected error fetching materials: {e}", exc_info=True)
            return []
    # --- End of fetch_materials method ---



# --- Plugin Registration ---
__plugin_name__ = "Print Authentication Plugin (Hardcoded)"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_identifier__ = "print_auth_plugin"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrintAuthPlugin()