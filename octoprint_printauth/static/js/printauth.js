console.log("printauth.js loaded");

$(function() {
    function PrintAuthViewModel() {
        var self = this;
        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin === "print_auth_plugin" && data.prompt) {
                var email = prompt("Please enter your email for authentication:");
                if (email) {
                    $.ajax({
                        url: API_BASEURL + "plugin/print_auth_plugin",
                        type: "POST",
                        dataType: "json",
                        contentType: "application/json",
                        data: JSON.stringify({ command: "authenticate", email: email }),
                        success: function(response) {
                            if (response.success) {
                                alert("Authentication successful.");
                            } else {
                                alert("Authentication failed: " + response.message);
                            }
                        },
                        error: function() {
                            alert("Error communicating with authentication server.");
                        }
                    });
                } else {
                    alert("No email provided. Print job canceled.");
                }
            }
        };
    }
    OCTOPRINT_VIEWMODELS.push([
        PrintAuthViewModel,
        [],
        []
    ]);
    console.log("PrintAuthViewModel registered.");
});
