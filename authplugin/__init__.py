# coding=utf-8
from __future__ import absolute_import

import flask
import requests
import octoprint.plugin
import json
import os # Keep just in case needed later

# --- Plugin Class Definition (Ensuring all mixins) ---
class PrintAuthPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SettingsPlugin,  # <-- For settings
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,   # <-- For templates
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SimpleApiPlugin
):

    def __init__(self):
        self._session = None
        # Cannot use self._logger here

    # -- SettingsPlugin --
    def get_settings_defaults(self):
        # Define all configurable settings and their defaults
        return dict(
            login_url="https://makehaven.org/user/login",
            username="", # MUST BE CONFIGURED by user
            password="", # MUST BE CONFIGURED by user
            permission_check_url_template="https://makehaven.org/api/v0/email/{email}/permission/{permission}",
            permission_name="printer_3d", # Default permission name
            tool_name="OctoPrintPrinter", # Default 'source' name for this printer
            api_method="octoprint_plugin", # Hardcoded info, shown in settings
            enable_material_prompt=True, # Default to enabled
            material_tool_id="6046" # Default Material Tool ID, store as string
        )

    # -- StartupPlugin --
    def on_startup(self, host, port):
         self._logger.info(f"PrintAuthPlugin started. Tool: {self._settings.get(['tool_name'])}. Permission Check: {self._settings.get(['permission_name'])}. Material Prompt Enabled: {self._settings.get_boolean(['enable_material_prompt'])}. Material Tool ID: {self._settings.get(['material_tool_id'])}")
         self._session = None # Ensure clean session on startup


    # -- TemplatePlugin --
    def get_template_configs(self):
            return [
                # Settings dialog template
                dict(type="settings", name="Print Authentication", template="printauth_settings.jinja2", custom_bindings=False),
                # Generic template for the modal injection
                dict(type="generic", template="print_auth_material_modal.jinja2", custom_bindings=False)
            ]

    # -- AssetPlugin --
    def get_assets(self):
        return dict(
            js=["js/printauth.js"],
            css=["css/printauth.css"]
        )

    # -- EventHandlerPlugin --
    def on_event(self, event, payload):
        if event == "PrintStarted":
            self._logger.info("Print started event caught.")
            # Check if essential settings are configured
            api_user = self._settings.get(["username"])
            api_pass = self._settings.get(["password"])
            if not api_user or not api_pass:
                self._logger.error("Plugin cannot authenticate: API username or password not configured in settings. Prompt will not be shown.")
                return # Stop processing if not configured

            self._logger.info("Settings OK, sending prompt message to frontend.")
            self._plugin_manager.send_plugin_message("print_auth_plugin", {"prompt": True})

    # -- SimpleApiPlugin --
    def get_api_commands(self):
        # Define commands callable from JS
        return dict(
            authenticate=["email"],
            confirm_material=["choice"]
        )

    def on_api_command(self, command, data):
        # --- Authenticate Command ---
        if command == "authenticate":
            email = data.get("email")
            if not email:
                return flask.jsonify(success=False, message="Email missing"), 400

            self._logger.info(f"Attempting permission check via API command for email: {email}")

            # --- Construct Note ---
            note_text = "File: N/A, Filament: N/A" # Default note
            try:
                job_info = self._printer.get_current_job()
                filename = "N/A"; filament_str = "N/A"
                if job_info and job_info.get("file", {}).get("path"):
                    file_path = job_info["file"]["path"]; file_origin = job_info["file"]["origin"]
                    filename = job_info["file"].get("display", file_path)
                    self._logger.info(f"Current job: {filename} (origin: {file_origin})")
                    metadata = self._file_manager.get_metadata(file_origin, file_path)
                    filament_data = metadata.get("analysis", {}).get("filament", {})
                    if filament_data:
                        usage_parts = []
                        # Check modern tool-specific format first
                        tool_usage = next(iter(filament_data.values()), None) if filament_data and isinstance(list(filament_data.values())[0], dict) else None
                        if tool_usage:
                             if tool_usage.get("length"): usage_parts.append(f"{tool_usage['length']:.1f}mm")
                             if tool_usage.get("volume"): usage_parts.append(f"{tool_usage['volume']:.1f}cm3")
                        else: # Fallback for older format
                             if filament_data.get("length"): usage_parts.append(f"{filament_data['length']:.1f}mm")
                             if filament_data.get("volume"): usage_parts.append(f"{filament_data['volume']:.1f}cm3")
                        if usage_parts: filament_str = ' / '.join(usage_parts)
                        else: self._logger.info("Filament usage data present but no length/volume found.")
                    else:
                         self._logger.info("No filament analysis data found in metadata.")
                else:
                    self._logger.warning("Could not get current job info to include in note.")

                note_text = f"File: {filename}, Filament: {filament_str}"
                self._logger.info(f"Generated note for API: {note_text}")
            except Exception as e_note:
                self._logger.error(f"Error generating note: {e_note}", exc_info=True)
            # --- End Construct Note ---

            # --- Call Authentication Logic ---
            result = {"success": False, "message": "Authentication failed by default."}
            try:
                 result = self.handle_authentication(email, note=note_text) # Pass the detailed note

                 # Check result and decide if print should be cancelled
                 is_permission_failure = not result.get("success", False) and \
                                         ("permission denied" in result.get("message","").lower() or \
                                          "user not found" in result.get("message","").lower() or \
                                          "lacks required permission" in result.get("message","").lower() or \
                                          "not granted" in result.get("message","").lower())

                 if not result.get("success", False):
                      if is_permission_failure:
                          self._logger.warning(f"Permission check failed for {email}. Canceling print. Reason: {result.get('message')}")
                          self._printer.cancel_print()
                          result["message"] += ". Print canceled."
                      else: # Login, Network, or Settings Error
                           self._logger.error(f"Authentication failed due to server/login/network/settings issue for {email}: {result.get('message')}")
                           # Add advice for user in message already includes "notify staff" if login/network
                           # result["message"] += ". Please notify staff." # Maybe redundant
                 else:
                      # Success case: message includes name, potentially materials list
                      self._logger.info(f"Authentication/Permission check successful for {email}. Materials fetched (if enabled).")
                      # Don't automatically proceed print here, wait for confirm_material if materials included

            except Exception as e:
                 # Catch unexpected errors during handle_authentication call
                 self._logger.error(f"Unhandled exception during handle_authentication call for {email}: {e}", exc_info=True)
                 self._printer.cancel_print() # Cancel on unexpected error
                 result = {"success": False, "message": f"Server error during authentication. Print canceled. {e}"}

            # Return the result (including name/materials if successful) to JS
            return flask.jsonify(**result)
            # --- End Call Authentication Logic ---

        # --- Confirm Material Command ---
        elif command == "confirm_material":
            choice = data.get("choice")
            self._logger.info(f"Received material confirmation choice from frontend: '{choice}'")
            if choice in ["paid", "own_material"]:
                # TODO: Add actual print resume logic if pausing is implemented
                self._logger.info("Acknowledging choice. TODO: Add logic to actually resume/confirm print start if it was paused.")
                # For now, just return success. The print likely continued already.
                return flask.jsonify(success=True, message=f"Choice '{choice}' acknowledged. Print starting/continuing.")
            else:
                self._logger.warning(f"Received invalid material choice: {choice}")
                return flask.jsonify(success=False, message=f"Invalid choice received: {choice}"), 400

        # --- Unknown Command ---
        else:
            self._logger.warning(f"Received unknown API command: {command}")
            return flask.make_response(f"Unknown command: {command}", 400)


    # -- Authentication Logic (Uses Settings) --
    def handle_authentication(self, email, note="N/A"):
        # Ensure session exists or login
        if not self._session:
            self._logger.info("No active session, attempting API login.")
            login_result, login_message = self.login_to_api()
            if login_result is None: # Network error during login
                return dict(success=False, message=login_message)
            if not login_result: # Login credentials failed
                return dict(success=False, message=login_message)
            # If login_result is True, proceed

        # --- Get values from Settings ---
        perm_check_url_template = self._settings.get(["permission_check_url_template"])
        req_permission_name = self._settings.get(["permission_name"])
        tool_name = self._settings.get(["tool_name"])
        api_method = self._settings.get(["api_method"])
        material_prompt_enabled = self._settings.get_boolean(["enable_material_prompt"])
        material_tool_id_str = self._settings.get(["material_tool_id"])
        # --- End Get values from Settings ---

        # Validate essential settings needed BEFORE API call
        if not all([perm_check_url_template, req_permission_name, tool_name, api_method]):
            self._logger.error("Required settings are not fully configured (URL Template, Permission Name, Tool Name).")
            return dict(success=False, message="Plugin settings error: Core API/Permission settings missing.")

        # Validate Material Tool ID *if* material prompt is enabled
        material_tool_id = None
        if material_prompt_enabled:
            if not material_tool_id_str:
                self._logger.error("Material prompt enabled, but Material Tool ID setting is empty.")
                return dict(success=False, message="Plugin settings error: Material Tool ID missing.")
            try:
                material_tool_id = int(material_tool_id_str)
                if material_tool_id <= 0: raise ValueError("Tool ID must be positive")
            except (ValueError, TypeError):
                 self._logger.error(f"Invalid Material Tool ID configured: '{material_tool_id_str}'. Must be a positive number.")
                 return dict(success=False, message="Plugin settings error: Invalid Material Tool ID.")

        # Construct URL
        try:
            safe_email = requests.utils.quote(email); safe_permission = requests.utils.quote(req_permission_name)
            api_url = perm_check_url_template.format(email=safe_email, permission=safe_permission)
        except Exception as e:
            self._logger.error(f"Error formatting permission check URL: {e}", exc_info=True)
            return dict(success=False, message="Plugin settings error: Permission URL template invalid.")

        # Construct params
        params = {'source': tool_name, 'method': api_method}
        if note: params['note'] = note

        self._logger.info(f"Checking permission API: {api_url} with params: {params}")
        try:
            response = self._session.get(api_url, params=params, timeout=15)
            self._logger.info(f"API response status: {response.status_code}")
            self._logger.debug(f"API response text: {response.text[:500]}") # Log response start

            if response.ok: # Status < 400
                 try:
                     json_data = response.json()
                     self._logger.info(f"API success response JSON: {json_data}")

                     # Check MakeHaven API success response format
                     if isinstance(json_data, list) and len(json_data) > 0 and json_data[0].get("access") == "true":
                         # --- Permission Granted ---
                         user_data = json_data[0]
                         first_name = user_data.get('first_name', '')
                         last_name = user_data.get('last_name', '')
                         user_name = f"{first_name} {last_name}".strip()
                         if not user_name: user_name = "User" # Fallback

                         self._logger.info(f"Permission '{req_permission_name}' granted for {user_name} ({email}).")

                         # Prepare return data
                         return_data = dict(success=True,
                                            message=f"Authenticated as {user_name}",
                                            firstName=first_name,
                                            lastName=last_name)

                         # Fetch materials ONLY if setting is enabled
                         if material_prompt_enabled:
                             self._logger.info(f"Material prompt enabled, fetching materials for Tool ID: {material_tool_id}...")
                             material_list = self.fetch_materials(material_tool_id) # Use validated ID
                             return_data["materials"] = material_list # Add key ONLY if enabled
                         else:
                             self._logger.info("Material prompt disabled via settings.")

                         return return_data # Return success dict
                         # --- End Permission Granted ---
                     else:
                         # Status OK but JSON doesn't indicate access
                         self._logger.warning(f"API Status OK but response JSON did not indicate access for {email}. Response: {json_data}")
                         return dict(success=False, message=f"Permission '{req_permission_name}' not granted for user (API check).")

                 except json.JSONDecodeError:
                     # Status OK but response not JSON
                     self._logger.warning("API returned Status OK but response was not valid JSON. Treating as failure.")
                     return dict(success=False, message="Invalid response from permission API")
            else: # response not ok (e.g., 403, 404)
                 message = f"Permission denied or user not found by API (Status: {response.status_code})"
                 try: # Attempt to get error message from API JSON response
                     error_data = response.json()
                     if isinstance(error_data, dict) and error_data.get("message"):
                         message = error_data["message"]
                 except json.JSONDecodeError: pass # Keep original status code message
                 self._logger.warning(f"Permission check failed for {email}. Status: {response.status_code}")
                 return dict(success=False, message=message)

        # --- Exception handling for the requests.get call and processing ---
        except requests.exceptions.Timeout:
             self._logger.error(f"Timeout connecting to permission API: {api_url}")
             return dict(success=False, message="Network error: API connection timed out")
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Network/Request error during permission API request to {api_url}: {e}")
            return dict(success=False, message=f"Network error during permission check: {e}")
        except Exception as e:
            self._logger.error(f"Unexpected error during permission check processing: {e}", exc_info=True)
            return dict(success=False, message=f"Unexpected server error during permission check: {e}")


    # -- Login Logic (Uses Settings) --
    def login_to_api(self):
        if not self._session:
            self._logger.info("Creating new requests session for API login.")
            self._session = requests.Session()
            headers = { # Add headers from working example
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.155 Safari/537.36",
                "cache-control": "private, max-age=0, no-cache",
            }
            self._session.headers.update(headers)

        # Get login credentials from settings
        login_url = self._settings.get(["login_url"])
        username = self._settings.get(["username"])
        password = self._settings.get(["password"])

        # Check if settings are actually configured
        if not all([login_url, username, password]):
             self._logger.error("API login credentials or URL missing in plugin settings.")
             return False, "Plugin settings error: API Login credentials/URL missing."

        # Login form data
        data = {"name": username, "pass": password, "form_id": "user_login", "op": "Log in"}
        self._logger.info(f"Attempting login post to {login_url} for configured user '{username}'")
        try:
            response = self._session.post(login_url, data=data, timeout=15)
            self._logger.info(f"Login POST response status: {response.status_code}")
            self._logger.debug(f"Login POST response URL after request: {response.url}")
            self._logger.debug(f"Login POST response text snippet: {response.text[:500]}")

            # Check for non-OK status first
            if not response.ok:
                 self._logger.error(f"Login failed for user '{username}'. HTTP Status: {response.status_code}.")
                 return False, f"API service login failed (HTTP Status {response.status_code})"

            # Refined Success Check
            logged_in_check = "Log out" in response.text or "user/logout" in response.text
            # Check if still looks like login page (indicates failure)
            on_login_page_check = "user/login" in response.url and "form_id=user_login" in response.text

            if response.ok and (logged_in_check or not on_login_page_check):
                 self._logger.info(f"Login successful for user '{username}'.")
                 return True, "Login successful"
            else:
                 self._logger.error(f"Login failed for user '{username}'. Status OK but success indicators not found.")
                 self._session = None # Clear potentially bad session
                 return False, "API service login credentials failed or unexpected response"

        except requests.exceptions.Timeout:
             self._logger.error(f"Timeout during login to API: {login_url}")
             self._session = None
             return None, "Network error during login: Timeout" # Return None for success status on network error
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Login to API failed with exception: {e}", exc_info=True)
            self._session = None
            return None, f"Network error during login: {e}" # Return None for success status on network error


    # -- Fetch Materials Function --
    def fetch_materials(self, tool_id):
        if not self._session:
            self._logger.error("Cannot fetch materials: No active API session.")
            return []
        if not tool_id: # Added check for valid tool_id
            self._logger.error("Cannot fetch materials: Invalid Tool ID provided.")
            return []

        materials_url = f"https://makehaven.org/api/v0/materials/equipment/{tool_id}"
        self._logger.info(f"Fetching materials from: {materials_url}")
        try:
            response = self._session.get(materials_url, timeout=10)
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
            self._logger.error(f"Unexpected error fetching/processing materials: {e}", exc_info=True)
            return []


# --- Plugin Registration ---
__plugin_name__ = "Print Authentication Plugin"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_identifier__ = "print_auth_plugin" # Must match settings keys and JS checks

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrintAuthPlugin()

    # If you needed hooks:
    # global __plugin_hooks__
    # __plugin_hooks__ = { ... }