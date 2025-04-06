# OctoPrint-PrintAuth Plugin

*Plugin for OctoPrint to authenticate makerspace members before printing.*

## Project Goal

This plugin aims to integrate with OctoPrint to require email authentication before starting a print job. It is intended to interact with the MakeHaven user/API system (details TBD in full implementation).

## Current Status (As of 2025-04-06)

**Working:** The plugin now successfully loads in OctoPrint (tested on v1.10.3, Python 3.11.x). The core loading `ImportError` has been resolved. Basic JavaScript assets (`printauth.js`) are being served and executed correctly in the browser, allowing frontend development to proceed. The current state uses a simplified version of the plugin logic for testing purposes.

## Key Fix for Loading Issue

The persistent `ImportError: No module named ...` during plugin load was resolved by restructuring the plugin to match patterns seen in other working OctoPrint plugins:

1.  **Non-`src` Layout:** The main Python package directory (e.g., `authplugin`) is located directly under the project root, alongside `setup.py`.
2.  **Class in `__init__.py`:** The main plugin class (`PrintAuthPlugin`) was moved from a separate module (`plugin.py`) into the package's root `__init__.py` file (`authplugin/__init__.py`).
3.  **`__plugin_load__()` Function:** A `__plugin_load__()` function was added to `authplugin/__init__.py` to handle the instantiation of the plugin class and assign it to the global `__plugin_implementation__`.
4.  **Entry Point:** The `entry_points` definition in `setup.py` was modified to point directly to the package name (`print_auth_plugin = authplugin`) instead of the `package.module:Class` format.

This structure appears to be more compatible with OctoPrint's plugin loader, especially when using editable installs or potentially on newer Python versions.

## Development Environment Setup (Working - Python 3.11)

These instructions reflect the setup confirmed to work during troubleshooting.

1.  **Install Python 3.11 (if needed, using deadsnakes PPA on Ubuntu/Debian):**
    ```bash
    sudo apt update
    sudo apt install software-properties-common -y
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install python3.11 python3.11-venv python3.11-dev python3.11-distutils
    python3.11 --version # Verify
    ```

2.  **Create Project Structure (Example):**
    * Clone this repository (e.g., into `~/dev/OctoPrint-PrintAuth`).
    * Create a separate directory for the virtual environment (e.g., `~/dev/octoprint_venv`).

3.  **Create and Activate Virtual Environment:**
    ```bash
    # cd ~/dev/octoprint_venv # Or preferred location
    python3.11 -m venv ./venv
    source ./venv/bin/activate
    # Your prompt should now start with (venv)
    ```

4.  **Upgrade Pip:**
    ```bash
    pip install --upgrade pip
    ```

5.  **Install OctoPrint:**
    ```bash
    pip install octoprint
    ```

6.  **Install Plugin in Editable Mode:**
    * Navigate to the cloned plugin source directory:
        ```bash
        cd ~/dev/OctoPrint-PrintAuth # Or wherever you cloned it
        ```
    * Install using `-e`:
        ```bash
        # Make sure venv is active
        pip install -e .
        ```
    * *(The current structure uses a non-`src` layout, package name `authplugin`, and main class in `authplugin/__init__.py`)*

7.  **Run OctoPrint:**
    ```bash
    # Make sure venv is active
    octoprint serve
    ```
    Access via `http://127.0.0.1:5000`. Check `~/.octoprint/logs/octoprint.log` for errors. The plugin should load, appear in Plugin Manager, and serve `js/printauth.js`.

## Brief Troubleshooting History

Initial attempts faced a persistent `ImportError` during plugin load, preventing the plugin and its JS assets from loading. This occurred despite verifying file structure, using different install methods (`sdist`, editable), testing different project layouts (`src` vs non-`src`), renaming modules, recreating the venv, and testing on Python 3.12/3.11. Direct Python imports worked, indicating an issue specific to OctoPrint's loading context. The issue was resolved by adopting the structure described in "Key Fix for Loading Issue".

## Next Steps (Development)

1.  Restore the original, full functionality to the `PrintAuthPlugin` class within `authplugin/__init__.py`.
2.  Add back necessary imports (e.g., `requests`, `flask`).
3.  Implement the frontend JavaScript logic in `authplugin/static/js/printauth.js` to handle user interaction and communication with the backend.
4.  Implement the backend API endpoint (`on_api_command`) to handle authentication requests.
5.  Implement the event handler (`on_event`) to trigger the authentication prompt.
6.  Add and configure necessary settings (`get_settings_defaults`, `templates/costestimation_settings.jinja2`).
7.  Test all features thoroughly.
8.  Finalize package name, plugin name, versioning.
9.  Consider packaging for distribution (`sdist`, `wheel`).