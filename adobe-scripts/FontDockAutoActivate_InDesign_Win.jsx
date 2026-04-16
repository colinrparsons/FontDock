// FontDock Auto-Activate for Adobe InDesign (Windows)
// This script runs automatically when a document is opened
// and activates missing fonts from FontDock.
// Uses file-based IPC instead of app.doScript/AppleScript (which don't work on Windows).

#target indesign
#targetengine "session"

// ============================================================
// Debug logging - writes to Desktop/fontdock_id_debug.txt
// Set DEBUG to false to disable
// ============================================================
var DEBUG = true;
var LOG_FILE = Folder.desktop + "/fontdock_id_debug.txt";

function writeLog(msg) {
    if (!DEBUG) return;
    try {
        var f = new File(LOG_FILE);
        f.open("a");
        f.write(new Date().toString() + " | " + msg + "\n");
        f.close();
    } catch(e) {}
}

// ============================================================
// Request directory - FontDock client watches this folder
// Windows: %LOCALAPPDATA%\FontDock\requests
// ============================================================
var REQUEST_DIR = "";
try {
    // Folder.myAppData = Roaming AppData; go up to AppData, then into Local
    var appDataDir = Folder.myAppData.parent;
    if (appDataDir !== null && appDataDir !== undefined) {
        REQUEST_DIR = appDataDir.fsName + "/Local/FontDock/requests";
    } else {
        // Fallback: construct path manually from user profile
        var userProfile = Folder.myDocuments.parent.fsName;
        REQUEST_DIR = userProfile + "/AppData/Local/FontDock/requests";
    }
} catch(e) {
    // Last resort fallback
    REQUEST_DIR = "C:/Users/" + $.getenv("USERNAME") + "/AppData/Local/FontDock/requests";
}

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
        
        writeLog("installEventListener: event listener installed successfully");
        
    } catch (e) {
        writeLog("installEventListener ERROR: " + e.message);
    }
}

function checkAndActivateFonts(event) {
    try {
        var doc = null;
        
        // If called from an event, use event.target as the document
        // afterOpen fires before the doc appears in app.documents,
        // so app.activeDocument throws "No documents are open"
        if (event !== undefined && event !== null && event.target !== undefined) {
            // afterOpen also fires for libraries, books, etc. - skip those
            if (!(event.target instanceof Document)) {
                writeLog("checkAndActivateFonts: skipping non-document open event");
                return;
            }
            doc = event.target;
        } else {
            // Called manually (e.g. from installEventListener) - use activeDocument
            if (app.documents.length === 0) {
                return;
            }
            doc = app.activeDocument;
        }
        
        // Get document info
        var docName = doc.name;
        var docPath = "";
        try {
            docPath = doc.fullName.fsName;
        } catch(e) {
            docPath = "Unsaved Document";
        }
        
        writeLog("checkAndActivateFonts: checking document '" + docName + "'");
        
        // Collect missing fonts
        var missingFonts = [];
        
        var fonts = doc.fonts;
        writeLog("checkAndActivateFonts: document has " + fonts.length + " total fonts");
        
        for (var i = 0; i < fonts.length; i++) {
            var font = fonts[i];
            var fontFamily = font.fontFamily;
            var fontStyle = font.fontStyleName;
            var statusStr = "";
            // Log all font statuses for debugging
            if (font.status === FontStatus.INSTALLED) statusStr = "INSTALLED";
            else if (font.status === FontStatus.NOT_AVAILABLE) statusStr = "NOT_AVAILABLE";
            else if (font.status === FontStatus.SUBSTITUTED) statusStr = "SUBSTITUTED";
            else if (font.status === FontStatus.FAUX) statusStr = "FAUX";
            else statusStr = "UNKNOWN(" + font.status + ")";
            writeLog("  font[" + i + "]: " + fontFamily + " / " + fontStyle + " -> " + statusStr);
            
            // Check if font is missing (SUBSTITUTED status means font is missing)
            if (font.status === FontStatus.NOT_AVAILABLE || 
                font.status === FontStatus.SUBSTITUTED) {
                
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
            writeLog("checkAndActivateFonts: found " + missingFonts.length + " missing fonts");
            
            // Build JSON payload - client expects "fonts" array with family/style objects
            var payload = {
                "fonts": missingFonts,
                "document_name": docName,
                "document_path": docPath
            };
            
            // Convert to JSON string
            var jsonString = JSON.stringify(payload);
            
            // Send to FontDock client via file-based IPC
            sendToFontDock(jsonString);
        } else {
            writeLog("checkAndActivateFonts: no missing fonts found");
        }
        
    } catch (e) {
        writeLog("checkAndActivateFonts ERROR: " + e.message);
    }
}

// Send JSON payload to FontDock client via file-based IPC
// On Windows, we can't use app.doScript with AppleScript, so we write
// a request file that the FontDock client watches for.
function sendToFontDock(jsonString) {
    try {
        // Ensure request directory exists
        var reqDir = new Folder(REQUEST_DIR);
        if (!reqDir.exists) {
            reqDir.create();
            writeLog("sendToFontDock: created request directory");
        }
        
        // Write request file with timestamp to avoid conflicts
        var ts = new Date().getTime();
        var reqFile = new File(REQUEST_DIR + "/request_" + ts + ".json");
        
        reqFile.open("w");
        reqFile.write(jsonString);
        reqFile.close();
        
        writeLog("sendToFontDock: request file written - " + reqFile.name);
        return true;
        
    } catch (e) {
        writeLog("sendToFontDock ERROR: " + e.message);
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
        if (t == "string") return '"' + obj.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
        return String(obj);
    } else {
        // Arrays and objects
        var n, v, json = [], arr = (obj && obj.constructor == Array);
        for (n in obj) {
            v = obj[n];
            t = typeof(v);
            if (t == "string") v = '"' + v.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
            else if (t == "object" && v !== null) v = JSON.stringify(v);
            json.push((arr ? "" : '"' + n + '":') + String(v));
        }
        return (arr ? "[" : "{") + String(json) + (arr ? "]" : "}");
    }
};

// ============================================================
// Script loaded - install event listener
// ============================================================
try {
    writeLog("=== FontDock InDesign Auto-Activate script loaded (Windows) ===");
    installEventListener();
    writeLog("=== Script initialization complete ===");
} catch (e) {
    // Last-resort error reporting - write to desktop even if writeLog failed
    try {
        var f = new File(Folder.desktop + "/fontdock_id_error.txt");
        f.open("w");
        f.write("FontDock InDesign script FATAL ERROR: " + e.message + " (line " + e.line + ")");
        f.close();
    } catch(e2) {}
}
