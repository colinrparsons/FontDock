// FontDock Auto-Activate
// This script runs automatically when a document is opened
// and activates missing fonts from FontDock

#target indesign
#targetengine "session"

// Helper function to check if array contains item (ExtendScript doesn't have indexOf)
function arrayContains(arr, item) {
    for (var i = 0; i < arr.length; i++) {
        if (arr[i] === item) {
            return true;
        }
    }
    return false;
}

// Install event listener on startup
function installEventListener() {
    try {
        // Remove existing listener if any
        try {
            app.removeEventListener("afterOpen", checkAndActivateFonts);
        } catch(e) {}
        
        // Add event listener for document open
        app.addEventListener("afterOpen", checkAndActivateFonts);
        
        // Also check current document if one is open
        if (app.documents.length > 0) {
            checkAndActivateFonts();
        }
        
    } catch (e) {
        // Silent fail - don't interrupt InDesign startup
    }
}

function checkAndActivateFonts() {
    try {
        // Check if a document is open
        if (app.documents.length === 0) {
            return;
        }
        
        var doc = app.activeDocument;
        
        // Get document info
        var docName = doc.name;
        var docPath = "";
        try {
            docPath = doc.fullName.fsName;
        } catch(e) {
            docPath = "Unsaved Document";
        }
        
        // Collect missing fonts
        var missingFonts = [];
        
        var fonts = doc.fonts;
        
        for (var i = 0; i < fonts.length; i++) {
            var font = fonts[i];
            
            // Check if font is missing (SUBSTITUTED status means font is missing)
            if (font.status === FontStatus.NOT_AVAILABLE || 
                font.status === FontStatus.SUBSTITUTED) {
                
                // Get family and style separately for exact matching
                var fontFamily = font.fontFamily;
                var fontStyle = font.fontStyleName;
                
                // Create font object with family and style
                var fontObj = {
                    "family": fontFamily,
                    "style": fontStyle
                };
                
                // Check if not already in list (compare by family+style)
                var alreadyAdded = false;
                for (var j = 0; j < missingFonts.length; j++) {
                    if (missingFonts[j].family === fontFamily && missingFonts[j].style === fontStyle) {
                        alreadyAdded = true;
                        break;
                    }
                }
                
                if (!alreadyAdded) {
                    missingFonts.push(fontObj);
                }
            }
        }
        
        // Only send request if there are missing fonts
        if (missingFonts.length > 0) {
            // Build JSON payload - client expects "fonts" array with family/style objects
            var payload = {
                "fonts": missingFonts
            };
            
            // Convert to JSON string
            var jsonString = JSON.stringify(payload);
            
            // Send to FontDock client (non-blocking)
            sendToFontDock(jsonString);
        }
        
    } catch (e) {
        // Silent fail - don't interrupt document opening
    }
}

// Send JSON payload to FontDock client via HTTP POST
function sendToFontDock(jsonString) {
    try {
        // Write JSON to a temporary file
        var tempFolder = Folder.temp;
        var jsonFile = new File(tempFolder + "/fontdock_request.json");
        
        jsonFile.open("w");
        jsonFile.write(jsonString);
        jsonFile.close();
        
        // Build curl command using the file
        var curlCmd = "curl -X POST http://127.0.0.1:8765/open-fonts " +
                      "-H 'Content-Type: application/json' " +
                      "-d @" + jsonFile.fsName + " " +
                      "--max-time 2 --connect-timeout 1";
        
        // Execute curl command using app.doScript
        // We use do shell script in AppleScript to run the curl command
        var appleScript = 'do shell script "' + curlCmd.replace(/"/g, '\\"') + '"';
        var result = 0;
        try {
            app.doScript(appleScript, ScriptLanguage.APPLESCRIPT_LANGUAGE);
            result = 0;
        } catch (e) {
            result = 1;
        }
        
        // Clean up
        jsonFile.remove();
        
        return (result === 0);
    } catch (e) {
        return false;
    }
}

// Simple JSON.stringify implementation for ExtendScript
if (typeof JSON === 'undefined') {
    JSON = {};
}

JSON.stringify = function(obj) {
    var t = typeof(obj);
    if (t != "object" || obj === null) {
        // Simple values
        if (t == "string") return '"' + obj.replace(/"/g, '\\"') + '"';
        return String(obj);
    } else {
        // Arrays and objects
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

// Install the event listener when script loads
installEventListener();
