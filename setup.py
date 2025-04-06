# Corrected setup.py (No 'src' layout, corrected package_data)
from setuptools import setup, find_packages

setup(
    name="OctoPrint-AuthPluginTest", # Changed name slightly to reflect test
    version="1.0.0",
    packages=find_packages(), # Correct: Finds 'authplugin' now
    install_requires=[
        "requests",
        "flask"
    ],
    entry_points={
        "octoprint.plugin": [
            # Correct: Points to package 'authplugin'
            "print_auth_plugin = authplugin"
        ]
    },
    # Corrected package_data key VVVVVVVVVV
    package_data={
        'authplugin': ["static/js/*", "static/css/*", "templates/*"]
    },
    include_package_data=True, # Keep this to use MANIFEST.in
)