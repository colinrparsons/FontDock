// FontDock Auto-Activate for Adobe Illustrator
// Automatically detects missing fonts when a document is opened
// and activates them from FontDock

#target illustrator
#targetengine "fontdock_session"

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
// Get list of installed font names (PostScript names)
// ============================================================
function getInstalledFontNames() {
    var installed = {};
    for (var i = 0; i < app.textFonts.length; i++) {
        installed[app.textFonts[i].name] = true;
    }
    return installed;
}

// ============================================================
// Scan document for all used fonts
// Returns array of {family, style, postscriptName} objects
// ============================================================
function scanDocumentFonts(doc) {
    var fontsFound = {};
    var textFrames = doc.textFrames;

    for (var i = 0; i < textFrames.length; i++) {
        try {
            var textFrame = textFrames[i];
            // A textFrame can have multiple textRanges with different fonts
            var textRanges = textFrame.textRanges;
            for (var j = 0; j < textRanges.length; j++) {
                try {
                    var textRange = textRanges[j];
                    var font = textRange.characterAttributes.textFont;
                    var psName = font.name;        // PostScript name e.g. "HelveticaNeue-Bold"
                    var family = font.family;      // Family name e.g. "Helvetica Neue"
                    var style = font.style;        // Style name e.g. "Bold"

                    var key = psName;
                    if (!fontsFound[key]) {
                        fontsFound[key] = {
                            family: family,
                            style: style,
                            postscriptName: psName
                        };
                    }
                } catch (e) {
                    // Skip ranges where font info is unavailable
                }
            }
        } catch (e) {
            // Skip text frames that can't be read
        }
    }

    // Convert to array
    var result = [];
    for (var key in fontsFound) {
        result.push(fontsFound[key]);
    }
    return result;
}

// ============================================================
// Determine which fonts are missing
// Compares document fonts against installed system fonts
// ============================================================
function findMissingFonts(docFonts) {
    var installed = getInstalledFontNames();
    var missing = [];

    for (var i = 0; i < docFonts.length; i++) {
        var font = docFonts[i];
        // If the PostScript name is not in the installed fonts list, it's missing
        if (!installed[font.postscriptName]) {
            missing.push(font);
        }
    }

    return missing;
}

// ============================================================
// Send font activation request to FontDock client
// Uses curl via AppleScript's do shell script
// ============================================================
function sendToFontDock(missingFonts) {
    try {
        // Build payload with family/style pairs (preferred by FontDock)
        var fontList = [];
        for (var i = 0; i < missingFonts.length; i++) {
            fontList.push({
                "family": missingFonts[i].family,
                "style": missingFonts[i].style
            });
        }

        var payload = {
            "fonts": fontList
        };

        var jsonString = JSON.stringify(payload);

        // Write JSON to temp file
        var tempFolder = Folder.temp;
        var jsonFile = new File(tempFolder + "/fontdock_illustrator_request.json");

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

        // Scan document for all used fonts
        var docFonts = scanDocumentFonts(doc);

        if (docFonts.length === 0) return;

        // Find which fonts are missing
        var missingFonts = findMissingFonts(docFonts);

        if (missingFonts.length === 0) return;

        // Send to FontDock for activation
        var success = sendToFontDock(missingFonts);

        if (success) {
            // Wait a moment for font activation to take effect
            $.sleep(1000);

            // Force Illustrator to re-check fonts by toggling the document
            // This helps Illustrator recognize newly installed fonts
            try {
                var installed = getInstalledFontNames();
                var stillMissing = 0;
                for (var i = 0; i < missingFonts.length; i++) {
                    if (!installed[missingFonts[i].postscriptName]) {
                        stillMissing++;
                    }
                }

                if (stillMissing > 0) {
                    // Some fonts still missing - may need document reload
                    $.writeln("FontDock: " + stillMissing + " fonts still missing after activation. Try closing and reopening the document.");
                }
            } catch(e) {}
        }
    } catch (e) {
        // Silent fail - don't interrupt user workflow
    }
}

// ============================================================
// Install event listener for document open
// ============================================================
function installEventListener() {
    try {
        // Remove existing listener if any
        try {
            app.removeEventListener("afterOpen", checkAndActivateFonts);
        } catch(e) {}

        // Add event listener for document open
        app.addEventListener("afterOpen", checkAndActivateFonts);

        // Also check current document if one is already open
        if (app.documents.length > 0) {
            checkAndActivateFonts();
        }
    } catch (e) {
        // Silent fail
    }
}

// Install on script load
installEventListener();
