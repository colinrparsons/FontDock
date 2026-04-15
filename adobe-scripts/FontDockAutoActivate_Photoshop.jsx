// FontDock Auto-Activate for Adobe Photoshop
// Automatically detects missing fonts when a document is opened
// and activates them from FontDock

#target photoshop
#targetengine "fontdock_ps_session"

// ============================================================
// JSON.stringify polyfill for ExtendScript
// ============================================================
if (typeof JSON === 'undefined') {
    JSON = {};
}

JSON.stringify = function(obj) {
    var t = typeof(obj);
    if (t != "object" || obj === null) {
        if (t == "string") return '"' + obj.replace(/"/g, '\\"') + '"';
        return String(obj);
    } else {
        var n, v, json = [], arr = (obj && obj.constructor == Array);
        for (n in obj) {
            v = obj[n];
            t = typeof(v);
            if (t == "string") v = '"' + v.replace(/"/g, '\\"') + '"';
            else if (t == "object" && v !== null) v = JSON.stringify(v);
            json.push((arr ? "" : '"' + n + '":') + String(v));
        }
        return (arr ? "[" : "{") + String(json) + (arr ? "]" : "}");
    }
};

// ============================================================
// Helper: check if array contains item
// ============================================================
function arrayContains(arr, item) {
    for (var i = 0; i < arr.length; i++) {
        if (arr[i] === item) return true;
    }
    return false;
}

// ============================================================
// Get list of installed font PostScript names
// Photoshop doesn't have app.textFonts like Illustrator,
// so we use the font descriptor from a temporary text layer
// ============================================================
function getInstalledFontNames() {
    var installed = {};
    try {
        // Use Photoshop's font list from the application
        // app.fonts returns an array of available fonts
        if (typeof app.fonts !== 'undefined') {
            for (var i = 0; i < app.fonts.length; i++) {
                installed[app.fonts[i].postScriptName] = true;
            }
        } else {
            // Fallback: create a temp doc and enumerate fonts
            // This is a best-effort approach
            var wasDocOpen = app.documents.length > 0;
            
            // Try to get font list from a temporary document
            var tempDoc;
            if (!wasDocOpen) {
                tempDoc = app.documents.add();
            }
            
            try {
                // Access available fonts through the application
                // In newer Photoshop versions, we can use:
                var fontList = app.fonts;
                if (fontList) {
                    for (var i = 0; i < fontList.length; i++) {
                        installed[fontList[i].postScriptName] = true;
                    }
                }
            } catch(e) {}
            
            if (!wasDocOpen && tempDoc) {
                try { tempDoc.close(SaveOptions.DONOTSAVECHANGES); } catch(e) {}
            }
        }
    } catch (e) {
        // If we can't get the font list, return empty
        // The script will still try to activate all document fonts
    }
    return installed;
}

// ============================================================
// Recursively scan layers for text layers and collect font names
// Photoshop uses layer groups (LayerSet) that need recursive scanning
// Returns array of PostScript font names used in the document
// ============================================================
function scanDocumentFonts(doc) {
    var fontsFound = {};

    function processLayer(layer) {
        try {
            // Check if this is a text layer
            if (layer.kind === LayerKind.TEXT) {
                try {
                    var fontName = layer.textItem.font;
                    // Photoshop returns PostScript name (e.g., "HelveticaNeue-Bold")
                    if (fontName && !fontsFound[fontName]) {
                        fontsFound[fontName] = true;
                    }
                } catch (e) {
                    // Some text layers may not expose font info
                }
            }

            // Process layer sets (groups) recursively
            if (layer.typename === "LayerSet") {
                for (var i = 0; i < layer.layers.length; i++) {
                    processLayer(layer.layers[i]);
                }
            }
        } catch (e) {
            // Skip layers that can't be accessed
        }
    }

    // Process all top-level layers
    var layers = doc.layers;
    for (var i = 0; i < layers.length; i++) {
        processLayer(layers[i]);
    }

    // Convert to array of PostScript names
    var result = [];
    for (var name in fontsFound) {
        result.push(name);
    }
    return result;
}

// ============================================================
// Determine which fonts are missing
// Compares document fonts against installed system fonts
// ============================================================
function findMissingFonts(docFontNames) {
    var installed = getInstalledFontNames();
    var missing = [];

    // If we couldn't get the installed font list,
    // try to activate all document fonts (safer approach for Photoshop)
    var hasInstalledList = false;
    for (var key in installed) {
        hasInstalledList = true;
        break;
    }

    if (!hasInstalledList) {
        // Can't determine which are missing, so try to activate all
        // FontDock will skip fonts that are already active
        return docFontNames;
    }

    for (var i = 0; i < docFontNames.length; i++) {
        if (!installed[docFontNames[i]]) {
            missing.push(docFontNames[i]);
        }
    }

    return missing;
}

// ============================================================
// Send font activation request to FontDock client
// Uses curl via AppleScript's do shell script
// ============================================================
function sendToFontDock(missingFontNames) {
    try {
        // Build payload with PostScript font names
        // FontDock's activate_font_by_name() handles PostScript name matching
        var fontList = [];
        for (var i = 0; i < missingFontNames.length; i++) {
            fontList.push(missingFontNames[i]);
        }

        var payload = {
            "fonts": fontList
        };

        var jsonString = JSON.stringify(payload);

        // Write JSON to temp file
        var tempFolder = Folder.temp;
        var jsonFile = new File(tempFolder + "/fontdock_photoshop_request.json");

        jsonFile.open("w");
        jsonFile.write(jsonString);
        jsonFile.close();

        // Build curl command
        var curlCmd = "curl -s -X POST http://127.0.0.1:8765/open-fonts " +
                      "-H 'Content-Type: application/json' " +
                      "-d @" + jsonFile.fsName + " " +
                      "--max-time 5 --connect-timeout 2";

        // Execute via AppleScript
        var appleScript = 'do shell script "' + curlCmd.replace(/"/g, '\\"') + '"';
        var result = 0;
        try {
            app.doScript(appleScript, ScriptLanguage.APPLESCRIPT_LANGUAGE);
            result = 0;
        } catch (e) {
            result = 1;
        }

        // Clean up temp file
        try { jsonFile.remove(); } catch(e) {}

        return (result === 0);
    } catch (e) {
        return false;
    }
}

// ============================================================
// Main: Check document and activate missing fonts
// ============================================================
function checkAndActivateFonts() {
    try {
        if (app.documents.length === 0) return;

        var doc = app.activeDocument;
        var docName = doc.name;

        // Scan document for all used font PostScript names
        var docFontNames = scanDocumentFonts(doc);

        if (docFontNames.length === 0) return;

        // Find which fonts are missing
        var missingFontNames = findMissingFonts(docFontNames);

        if (missingFontNames.length === 0) return;

        // Send to FontDock for activation
        var success = sendToFontDock(missingFontNames);

        if (success) {
            // Wait for font activation to take effect
            $.sleep(1500);

            // Photoshop may need a document close/reopen to recognize new fonts
            // We can't force a refresh, so log a message
            $.writeln("FontDock: Activation request sent for " + missingFontNames.length + " fonts.");
        }
    } catch (e) {
        // Silent fail - don't interrupt user workflow
    }
}

// ============================================================
// Install event listener for document open
// Photoshop uses app.notifiers for event handling
// ============================================================
function installEventListener() {
    try {
        // Register for document open event using notifiers
        // Photoshop event ID for "open" document
        var openEventID = charIDToTypeID("Opn ");
        
        // Remove existing notifier if any
        try {
            for (var i = app.notifiers.length - 1; i >= 0; i--) {
                if (app.notifiers[i].event == openEventID) {
                    app.notifiers[i].remove();
                }
            }
        } catch(e) {}

        // Add notifier for document open
        // The notifier runs a script file when the event fires
        // We need to get the path of this script file
        var scriptFile = new File($.fileName);
        app.notifiers.add(openEventID, scriptFile);

        // Also check current document if one is already open
        if (app.documents.length > 0) {
            checkAndActivateFonts();
        }
    } catch (e) {
        // If notifiers fail, we can still register via addEventListener (newer PS versions)
        try {
            app.addEventListener("afterOpen", checkAndActivateFonts);
            
            // Check current document
            if (app.documents.length > 0) {
                checkAndActivateFonts();
            }
        } catch(e2) {
            // Silent fail
        }
    }
}

// ============================================================
// Check if this script was triggered by a notifier event
// (vs being run manually or as a startup script)
// ============================================================
function isNotifierTrigger() {
    try {
        // When triggered by a notifier, the current document is the newly opened one
        // We can detect this by checking if there's an active document
        return app.documents.length > 0;
    } catch(e) {
        return false;
    }
}

// Install on script load
installEventListener();
