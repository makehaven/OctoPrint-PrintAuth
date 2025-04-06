# Modified setup.py (No 'src' layout)
from setuptools import setup, find_packages

setup(
    name="OctoPrint-PrintAuth",
    version="1.0.0",
    # --- Changed Here ---
    # Look for packages in the current directory where setup.py is
    packages=find_packages(),
    # --- Removed This Line ---
    # package_dir={"": "src"}, # Removed: No longer using a 'src' layout

    install_requires=[
        "requests",
        "flask"
    ],
    entry_points={
        "octoprint.plugin": [
            # Assuming you kept the rename from printauth.py -> plugin.py
            "print_auth_plugin = octoprint_printauth.plugin:PrintAuthPlugin"
        ]
    },
    # package_data paths are relative to the package, so they remain the same
    package_data={
        "octoprint_printauth": ["static/js/*", "static/css/*", "templates/*"]
    },
    include_package_data=True, # Keep this to use MANIFEST.in
)