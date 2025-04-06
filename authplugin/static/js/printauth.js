$(function() {
    function PrintAuthViewModel() {
        var self = this;

        // --- Helper Function to Show Modal ---
        self.showMaterialModal = function(data) {
            var firstName = data.firstName || '';
            var lastName = data.lastName || '';
            var fullName = (firstName + ' ' + lastName).trim();
            var welcomeName = fullName || 'User';
            var materials = data.materials || [];

            // Update Modal Content
            $("#printAuthModalWelcome").text("Welcome " + welcomeName + "!"); // Set welcome message

            var materialListDiv = $("#printAuthMaterialList");
            materialListDiv.empty(); // Clear previous materials

            if (materials.length > 0) {
                var listHtml = "<strong>Materials associated with this tool:</strong><ul>";
                materials.forEach(function(material) {
                    // Format: Label - Unit - $Cost (Add buy link/QR later if possible)
                    listHtml += "<li>" +
                                _.escape(material.label || 'Unknown Material') + " - " +
                                _.escape(material.unit || '?') + " - $" +
                                _.escape(material.cost || '?.??') +
                                "</li>";
                });
                listHtml += "</ul>";
                materialListDiv.html(listHtml);
            } else {
                materialListDiv.html("<p><em>No specific materials listed for purchase for this tool.</em></p>");
            }

            // Show the modal (make it non-dismissible by clicking outside)
            $("#printAuthMaterialModal").modal({ backdrop: 'static', keyboard: false });
        };

        // --- Main Message Handler ---
        self.onDataUpdaterPluginMessage = function(plugin, data) {
            console.log("onDataUpdaterPluginMessage received:", plugin, data); // Keep for debugging

            if (plugin === "print_auth_plugin" && data.prompt) {
                var email = prompt("Please enter your MakeHaven email for authentication:");
                if (email) {
                    // Optional: Show "Checking..." notification
                    // new PNotify({...});

                    $.ajax({
                        url: API_BASEURL + "plugin/print_auth_plugin",
                        type: "POST",
                        dataType: "json",
                        contentType: "application/json",
                        data: JSON.stringify({ command: "authenticate", email: email }),
                        success: function(response) {
                            // Optional: Remove "Checking..." notification
                            // PNotify.removeAll();

                            if (response.success) {
                                // *** Instead of alert, call the modal function ***
                                self.showMaterialModal(response);
                                // Print does NOT proceed yet - waits for modal button click
                            } else {
                                // Keep the differentiated error messages from before
                                var message = response.message || "Unknown authentication error.";
                                if (message.includes("credentials failed")) {
                                     alert("Authentication Error:\nCould not log into authentication service.\nPlease notify MakeHaven staff.");
                                } else if (message.includes("Network error") || message.includes("timed out")) {
                                     alert("Network Error:\nCould not contact authentication service.\nPlease check network or notify MakeHaven staff.");
                                } else if (message.includes("Permission denied") || message.includes("not found") || message.includes("lacks required permission") || message.includes("not granted")) {
                                     alert("Authentication Failed:\n" + message + "\nPlease check email or contact MakeHaven staff.");
                                } else {
                                     alert("Authentication Failed:\n" + message);
                                }
                                // Print was likely cancelled by backend for permission errors
                            }
                        },
                        error: function(jqXHR, textStatus, errorThrown) {
                            // Optional: Remove "Checking..." notification
                            // PNotify.removeAll();
                            console.error("AJAX Error (Authenticate):", textStatus, errorThrown, jqXHR.responseText);
                            alert("Error communicating with OctoPrint authentication endpoint. Check browser console and octoprint.log.");
                        }
                    });
                } else {
                    alert("No email provided. Print canceled.");
                    // Consider sending a 'cancel' command to backend if needed
                }
            }
        }; // End of onDataUpdaterPluginMessage

        // --- Modal Button Click Handlers ---
        // Use .off().on() to prevent multiple bindings if ViewModel reloads
        $("#printAuthBtnOwnMaterial, #printAuthBtnPaid").off('click').on('click', function() {
            var choice = $(this).data('choice'); // Get 'own_material' or 'paid' from data-choice attribute
            console.log("Material choice:", choice);

             // Disable buttons while processing
             $("#printAuthBtnOwnMaterial, #printAuthBtnPaid").prop('disabled', true);

            // Make the SECOND ajax call to confirm material choice
            $.ajax({
                url: API_BASEURL + "plugin/print_auth_plugin", // Same endpoint, different command
                type: "POST",
                dataType: "json",
                contentType: "application/json",
                data: JSON.stringify({ command: "confirm_material", choice: choice }), // New command
                success: function(response) {
                    $("#printAuthMaterialModal").modal('hide'); // Hide modal on success
                    if (response.success) {
                         alert("Confirmation received. Print starting!"); // Simple alert for now
                         // Use PNotify for better UI later: new PNotify({... type: 'success'})
                    } else {
                         alert("Error confirming material choice: " + response.message);
                         // Re-enable buttons on error? Or keep modal open? Depends on desired flow.
                         $("#printAuthBtnOwnMaterial, #printAuthBtnPaid").prop('disabled', false);
                    }
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    $("#printAuthMaterialModal").modal('hide'); // Hide modal on error too
                    console.error("AJAX Error (Confirm Material):", textStatus, errorThrown, jqXHR.responseText);
                    alert("Error sending material confirmation to OctoPrint.");
                    $("#printAuthBtnOwnMaterial, #printAuthBtnPaid").prop('disabled', false); // Re-enable buttons
                }
            });
        });

        // Optional: Add handler for explicit cancel button if you add one
        // $("#printAuthBtnCancel").off('click').on('click', function() { ... });

    } // End of PrintAuthViewModel

    // Register ViewModel
    OCTOPRINT_VIEWMODELS.push([
        PrintAuthViewModel,
        [], // No dependencies
        ["#settings_plugin_print_auth"] // Optional: Bind only to settings initially? Might not be needed. Let's remove for now.
        // []
    ]);
    console.log("PrintAuthViewModel registered.");
});