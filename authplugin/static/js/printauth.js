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
                                // --- Construct Welcome Message ---
                                var firstName = response.firstName || ''; // Default to empty string if missing
                                var lastName = response.lastName || '';
                                var fullName = (firstName + ' ' + lastName).trim();
                                var welcomeName = fullName || 'User'; // Use "User" if names are blank

                                // Add logging confirmation text
                                var logMessage = "Print logged for " + welcomeName + ". Starting print.";

                                alert("Welcome " + welcomeName + "!\n" + logMessage);
                                // --- End Welcome Message ---

                                // Print proceeds automatically as auth succeeded
                            } else {
                                // Differentiated Error Messages (keep as is from previous step)
                                var message = response.message || "Unknown authentication error.";
                                if (message.includes("credentials failed")) {
                                    alert("Authentication Error:\nCould not log into authentication service.\nPlease notify MakeHaven staff.\n\n(Print Canceled? Check server log)");
                                } else if (message.includes("Network error") || message.includes("timed out")) {
                                    alert("Network Error:\nCould not contact authentication service.\nPlease check network or notify MakeHaven staff.\n\n(Print Canceled? Check server log)");
                                } else if (message.includes("Permission denied") || message.includes("not found") || message.includes("lacks required permission") || message.includes("not granted")) {
                                    alert("Authentication Failed:\n" + message + "\nPlease check email address or contact MakeHaven staff.");
                                } else {
                                    alert("Authentication Failed:\n" + message);
                                }
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
