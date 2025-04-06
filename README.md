# OctoPrint-PrintAuth
Plugin for Octoprint to authenticate makerspace member 

# OctoPrint-PrintAuth Plugin

## Project Goal

This plugin aims to integrate with OctoPrint to require email authentication before starting a print job. It is intended to interact with the MakeHaven user/API system (details TBD in full implementation).

## Current Status (As of 2025-04-05)

**Blocked:** The plugin currently fails to load within OctoPrint due to a persistent `ImportError`, even after extensive troubleshooting. This prevents the plugin from appearing in the UI and consequently stops the JavaScript assets (`printauth.js`) from loading or executing.

### The Problem

After installation (either via `sdist` ZIP or `pip install -e .`), OctoPrint fails during startup with the following error in `octoprint.log`:

ERROR - Could not locate plugin print_auth_plugin
Traceback (most recent call last):
  File ".../octoprint/plugin/core.py", line 1211, in _import_plugin_from_module
    location, spec = _find_module(module_name)
  File ".../octoprint/plugin/core.py", line 45, in _find_module
    spec = imp.find_module(name)  # <-- Note: Uses deprecated 'imp' module
  File ".../octoprint/vendor/imp.py", line 288, in find_module
    raise ImportError(_ERR_MSG.format(name), name=name)
ImportError: No module named 'octoprint_printauth.plugin'

*(Note: The module name was `'octoprint_printauth.printauth'` before renaming tests).*

This error occurs despite the following conditions being met:
* The necessary files (`__init__.py`, `plugin.py` [formerly `printauth.py`]) exist in the correct installed location (`.../site-packages/octoprint_printauth/` or linked via editable install).
* The Python `sys.path` correctly includes the path to the plugin source for editable installs.
* A direct import (`import octoprint_printauth.plugin`) **succeeds** in a plain Python interpreter session within the same activated virtual environment.

The issue seems specific to OctoPrint 1.10.3's plugin loading mechanism, possibly interacting with Python 3.11/3.12 or the system environment.

## Development Environment Setup (Linux/Ubuntu)

These instructions reflect the setup used during troubleshooting, targeting Python 3.11.

1.  **Install Python 3.11 (if needed, using deadsnakes PPA):**
    ```bash
    sudo apt update
    sudo apt install software-properties-common -y
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install python3.11 python3.11-venv python3.11-dev python3.11-distutils
    python3.11 --version # Verify
    ```

2.  **Create Project Structure (Example):**
    ```bash
    # Example parent directory for the venv
    mkdir -p ~/dev/octoprint_dev
    cd ~/dev/octoprint_dev
    # Venv will be created inside this directory
    ```

3.  **Create and Activate Virtual Environment:**
    ```bash
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

6.  **Clone/Place Plugin Source Code:**
    * Ensure your plugin source code (e.g., `OctoPrint-PrintAuth` directory containing `setup.py` and the `octoprint_printauth` package directory) is accessible.
    * Example location assumed below: `/home/jrlogan/.octoprint/plugins/OctoPrint-PrintAuth/`
    * *(Current state uses non-`src` layout and `plugin.py`)*

7.  **Install Plugin in Editable Mode:**
    ```bash
    cd /home/jrlogan/.octoprint/plugins/OctoPrint-PrintAuth/
    pip install -e .
    ```

8.  **Run OctoPrint:**
    ```bash
    # Make sure venv is active
    # Delete old log for clean testing: rm ~/.octoprint/logs/octoprint.log
    octoprint serve
    ```
    Access via `http://127.0.0.1:5000`. Check `~/.octoprint/logs/octoprint.log` for errors.

## Troubleshooting Summary (Things Tried - Failed)

The `ImportError` persisted despite trying the following:
* Verifying file structure (`__init__.py`, module file, static assets).
* Using standard install (`sdist` generated ZIP uploaded via UI).
* Using editable install (`pip install -e .`).
* Using a `src` layout vs. a non-`src` layout in the project structure.
* Renaming the main plugin module file (`printauth.py` -> `plugin.py`) and updating `setup.py`.
* Verifying direct Python import works in the venv (`import octoprint_printauth.plugin`).
* Verifying `sys.path` includes the correct source path during editable installs.
* Completely recreating the virtual environment from scratch.
* Testing with both Python 3.12.3 and Python 3.11.x.
* Using a simplified version of the plugin code containing only minimal boilerplate and `AssetPlugin` requirements.

## Next Steps (When Resuming)

1.  **Check for OctoPrint Updates/Bug Reports:** Look at the OctoPrint GitHub issues and community forums for reports similar to `ImportError` with `imp.find_module` on Python 3.11/3.12, or for fixes in newer OctoPrint releases (beyond 1.10.3).
2.  **Report the Bug:** If no existing report covers this, consider submitting one with the detailed information gathered.
3.  **Try Different Versions:** Test with Python 3.10 or potentially OctoPrint 1.11+ (if available) or development branches.
4.  **Review Full Code:** Re-examine the original, non-simplified plugin code for any less obvious import issues or dependencies that might interfere, although the error persisting with minimal code makes this less likely to be the root cause.
5.  **Consider `pyproject.toml`:** Modernize the packaging away from `setup.py` by using a `pyproject.toml` file, although this is unlikely to fix the runtime `ImportError` seen here.
