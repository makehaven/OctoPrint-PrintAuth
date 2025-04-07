$(function() {
    function PrintAuthViewModel() {
        var self = this;

        // --- Helper Function to Show Modal ---
        self.showMaterialModal = function(data) {
            // ... (keep the implementation from the previous step that generates links) ...
             var firstName = data.firstName || '';
             var lastName = data.lastName || '';
             var fullName = (firstName + ' ' + lastName).trim();
             var welcomeName = fullName || 'User';
             var materials = data.materials || [];

             $("#printAuthModalWelcome").text("Welcome " + welcomeName + "!");

             var materialListDiv = $("#printAuthMaterialList");
             materialListDiv.empty();

             if (materials.length > 0) {
                 var listHtml = "<strong>Materials for Purchase:</strong><ul>";
                 materials.forEach(function(material) {
                     var label = _.escape(material.label || 'Unknown Material');
                     var unit = _.escape(material.unit || '?');
                     var cost = _.escape(material.cost || '?.??');
                     var purchaseUrl = material.purchase || '#';
                     var linkTarget = purchaseUrl !== '#' ? ' target="_blank" rel="noopener noreferrer"' : '';

                     listHtml += '<li>' + '<a href="' + purchaseUrl + '"' + linkTarget + '>' +
                                 label + ' - ' + unit + ' - $' + cost + '</a>' + '</li>';
                 });
                 listHtml += "</ul>";
                 materialListDiv.html(listHtml);
             } else {
                 materialListDiv.html("<p><em>No specific materials listed for purchase for this tool. You may use your own.</em></p>");
             }
             $("#printAuthMaterialModal").modal({ backdrop: 'static', keyboard: false });
        }; // End showMaterialModal

        // --- Main Message Handler ---
        self.onDataUpdaterPluginMessage = function(plugin, data) {
            console.log("onDataUpdaterPluginMessage received:", plugin, data);

            if (plugin === "print_auth_plugin" && data.prompt) {
                var email = prompt("Please enter your MakeHaven email for authentication:");
                if (email) {
                    $.ajax({
                        url: API_BASEURL + "plugin/print_auth_plugin",
                        type: "POST",
                        dataType: "json",
                        contentType: "application/json",
                        data: JSON.stringify({ command: "authenticate", email: email }),
                        success: function(response) {
                            if (response.success) {
                                self.showMaterialModal(response);
                            } else {
                                // Keep differentiated error alerts
                                var message = response.message || "Unknown authentication error.";
                                if (message.includes("credentials failed") || message.includes("Plugin settings error")) {
                                     alert("Configuration Error:\nCould not log into authentication service or plugin settings are incomplete.\nPlease check settings or notify MakeHaven staff.");
                                } else if (message.includes("Network error") || message.includes("timed out")) {
                                     alert("Network Error:\nCould not contact authentication service.\nPlease check network or notify MakeHaven staff.");
                                } else if (message.includes("Permission denied") || message.includes("not found") || message.includes("lacks required permission") || message.includes("not granted")) {
                                     alert("Authentication Failed:\n" + message + "\nPlease check email address or contact MakeHaven staff.");
                                } else {
                                     alert("Authentication Failed:\n" + message);
                                }
                            }
                        },
                        error: function(jqXHR, textStatus, errorThrown) {
                            console.error("AJAX Error (Authenticate):", textStatus, errorThrown, jqXHR.responseText);
                            alert("Error communicating with OctoPrint authentication endpoint. Check browser console and octoprint.log.");
                        }
                    });
                } else {
                    alert("No email provided. Print canceled.");
                }
            }
        }; // End of onDataUpdaterPluginMessage

        // --- Modal Button Click Handlers ---
        // Ensure these handlers are correctly placed and select the right buttons
        $("#printAuthBtnOwnMaterial, #printAuthBtnPaid").off('click').on('click', function() {
            var choice = $(this).data('choice');
            console.log("Material choice:", choice);
            $("#printAuthBtnOwnMaterial, #printAuthBtnPaid").prop('disabled', true);

            $.ajax({
                url: API_BASEURL + "plugin/print_auth_plugin",
                type: "POST",
                dataType: "json",
                contentType: "application/json",
                data: JSON.stringify({ command: "confirm_material", choice: choice }),
                success: function(response) {
                    $("#printAuthMaterialModal").modal('hide');
                     $("#printAuthBtnOwnMaterial, #printAuthBtnPaid").prop('disabled', false); // Re-enable on hide
                    if (response.success) {
                         new PNotify({title: 'Material Confirmed', text: response.message, type: 'success', delay: 5000});
                    } else {
                         new PNotify({title: 'Confirmation Error', text: response.message, type: 'error', delay: 5000});
                    }
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    $("#printAuthMaterialModal").modal('hide');
                     $("#printAuthBtnOwnMaterial, #printAuthBtnPaid").prop('disabled', false); // Re-enable on hide/error
                    console.error("AJAX Error (Confirm Material):", textStatus, errorThrown, jqXHR.responseText);
                    new PNotify({title: 'Communication Error', text: 'Error sending material confirmation to OctoPrint.', type: 'error', delay: 5000});
                }
            });
        }); // End button click handlers

    } // End of PrintAuthViewModel

    // Register the ViewModel (Simplified Version)
    OCTOPRINT_VIEWMODELS.push([
        PrintAuthViewModel,
        [], // No Dependencies
        []  // No Specific Elements to bind to
    ]);
    console.log("PrintAuthViewModel registered.");
}); // End of $(function() {})