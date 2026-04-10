// FontDock - Check Missing Fonts
// This script detects missing fonts in the active InDesign document
// and sends them to the local FontDock client for activation

#target indesign

// Helper function to check if array contains item (ExtendScript doesn't have indexOf)
function arrayContains(arr, item) {
    for (var i = 0; i < arr.length; i++) {
        if (arr[i] === item) {
            return true;
        }
    }
    return false;
}

function main() {
    // Check if a document is open
    if (app.documents.length === 0) {
        alert("Please open a document first.");
        return;
    }
    
    var doc = app.activeDocument;
    
    // Get document info
    var docName = doc.name;
    var docPath = doc.fullName.fsName;
    
    // Collect all fonts used in the document
    var allFonts = [];
    var missingFonts = [];
    
    try {
        // Get all fonts used in the document
        var fonts = doc.fonts;
        
        for (var i = 0; i < fonts.length; i++) {
            var font = fonts[i];
            var fontName = font.fontFamily;
            
            // Add to all fonts list
            if (!arrayContains(allFonts, fontName)) {
                allFonts.push(fontName);
            }
            
            // Check if font is missing
            if (font.status === FontStatus.NOT_AVAILABLE || 
                font.status === FontStatus.SUBSTITUTED) {
                if (!arrayContains(missingFonts, fontName)) {
                    missingFonts.push(fontName);
                }
            }
        }
        
        // Build JSON payload
        var payload = {
            "document_name": docName,
            "document_path": docPath,
            "missing_fonts": missingFonts,
            "all_fonts": allFonts
        };
        
        // Convert to JSON string
        var jsonString = JSON.stringify(payload);
        
        // Send to FontDock client
        var success = sendToFontDock(jsonString);
        
        if (success) {
            if (missingFonts.length > 0) {
                alert("Found " + missingFonts.length + " missing font(s).\n\n" +
                      "Missing fonts:\n" + missingFonts.join("\n") + "\n\n" +
                      "Request sent to FontDock.");
            } else {
                alert("No missing fonts found!\n\n" +
                      "All " + allFonts.length + " fonts are available.");
            }
        } else {
            alert("Error: Could not connect to FontDock client.\n\n" +
                  "Please make sure FontDock is running.\n\n" +
                  "Missing fonts:\n" + missingFonts.join("\n"));
        }
        
    } catch (e) {
        alert("Error checking fonts: " + e.message);
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
        
        // Execute curl command
        var result = system.callSystem(curlCmd);
        
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

// Run the main function
main();
