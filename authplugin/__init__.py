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
    # octoprint.plugin.TemplatePlugin, # Keep commented out for now
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

    def get_api_commands(self):
        return dict(authenticate=["email"])

    def on_api_command(self, command, data):
        if command == "authenticate":
            email = data.get("email")
            if not email:
                # ... (same error handling as before) ...
                return flask.jsonify(success=False, message="Email missing"), 400

            self._logger.info(f"Attempting DIRECT permission check (HARDCODED) via API command for email: {email}")
            result = {"success": False, "message": "Authentication failed by default."}
            try:
                 result = self.handle_authentication(email, note="OctoPrint Auth Attempt")

                 # Check the specific message for cancellation logic
                 is_permission_failure = "permission denied" in result.get("message","").lower() or \
                                         "user not found" in result.get("message","").lower() or \
                                         "lacks required permission" in result.get("message","").lower()

                 if not result.get("success", False):
                      # Only cancel automatically if it's a permission/user issue
                      if is_permission_failure:
                          self._logger.warning(f"Permission check failed for {email}. Canceling print. Reason: {result.get('message')}")
                          self._printer.cancel_print()
                          result["message"] += ". Print canceled."
                      else:
                          # For login/network errors, just report the error, don't auto-cancel
                           self._logger.error(f"Authentication failed due to server/login issue for {email}: {result.get('message')}")
                           # Add advice for user
                           result["message"] += ". Please notify staff. You may proceed with caution if desired."

                 else:
                      self._logger.info(f"Authentication/Permission check successful for {email}.")

            except Exception as e:
                 # ... (same exception handling, leads to cancellation) ...
                 self._logger.error(f"Unhandled exception during permission check for {email}: {e}", exc_info=True)
                 self._printer.cancel_print()
                 result = {"success": False, "message": f"Server error during permission check. Print canceled. {e}"}

            return flask.jsonify(**result) # Return detailed result
        else:
            # ... (same handling for unknown command) ...
            return flask.make_response(f"Unknown command: {command}", 400)


    def handle_authentication(self, email, note="N/A"):
        # Attempt login only if no session exists
        if not self._session:
            self._logger.info("No active session, attempting API login.")
            login_result, login_message = self.login_to_api() # Get detailed result
            if not login_result:
                # Return specific failure reason from login_to_api
                return dict(success=False, message=login_message) # e.g., "API service login credentials failed" or "Network error during login"

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
        try:
            response = self._session.get(api_url, params=params, timeout=15)
            self._logger.info(f"API response status: {response.status_code}")
            self._logger.debug(f"API response text: {response.text[:500]}")

            if response.ok:
                 try:
                     json_data = response.json()
                     self._logger.info(f"API success response JSON: {json_data}")
                     # **NEW:** Check specifically for the expected success structure from your manual test
                     # [{"first_name":..., "access":"true", ...}]
                     if isinstance(json_data, list) and len(json_data) > 0 and json_data[0].get("access") == "true":
                         user_name = f"{json_data[0].get('first_name','?')} {json_data[0].get('last_name','?')}"
                         self._logger.info(f"Permission '{req_permission_name}' granted for {user_name} ({email}).")
                         return dict(success=True, message=f"Authenticated as {user_name}")
                     else:
                         # Response OK but didn't contain expected success data
                         self._logger.warning(f"API Status OK but response JSON did not indicate access for {email}. Response: {json_data}")
                         return dict(success=False, message=f"Permission '{req_permission_name}' not granted for user (API check).")

                 except json.JSONDecodeError:
                     self._logger.warning("API returned Status OK but response was not valid JSON. Treating as failure.")
                     return dict(success=False, message="Invalid response from permission API")
            else: # response not ok (4xx, 5xx)
                 message = f"Permission denied or user not found by API (Status: {response.status_code})"
                 try: # Try to get more detail
                     error_data = response.json()
                     if isinstance(error_data, dict) and error_data.get("message"): message = error_data["message"]
                 except json.JSONDecodeError: pass
                 self._logger.warning(f"Permission check failed for {email}. Status: {response.status_code}")
                 return dict(success=False, message=message)

        except requests.exceptions.Timeout:
             self._logger.error(f"Timeout connecting to permission API: {api_url}")
             return dict(success=False, message="Network error: API connection timed out")
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Error during permission API request to {api_url}: {e}")
            return dict(success=False, message=f"Network error during permission check: {e}")
        except Exception as e:
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

# --- Plugin Registration ---
__plugin_name__ = "Print Authentication Plugin (Hardcoded)"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_identifier__ = "print_auth_plugin"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrintAuthPlugin()