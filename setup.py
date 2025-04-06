# Simplified setup.py for hardcoded version
from setuptools import setup, find_packages

setup(
    name="OctoPrint-AuthPluginTest",
    version="1.0.0",
    packages=find_packages(), # Finds 'authplugin'
    install_requires=[
        "requests",
        "flask" # Still needed by SimpleApiPlugin potentially
    ],
    entry_points={
        "octoprint.plugin": [
            "print_auth_plugin = authplugin"
        ]
    },
    # Keep package_data for static files (JS/CSS)
    package_data={
        'authplugin': ["static/js/*", "static/css/*"] # Removed templates/*
    },
    include_package_data=True,
)