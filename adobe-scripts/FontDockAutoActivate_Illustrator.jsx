// FontDock Auto-Activate for Adobe Illustrator
// Writes a request file that the FontDock client watches for.
// The client parses the .ai file on disk to find and activate missing fonts.
// Uses only File operations - works in all Adobe apps.

#target illustrator

// ============================================================
// Debug logging - writes to ~/Desktop/fontdock_il_debug.txt
// Set DEBUG to false to disable
// ============================================================
var DEBUG = true;
var LOG_FILE = Folder.desktop + "/fontdock_il_debug.txt";

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
// ============================================================
var REQUEST_DIR = "~/Library/Application Support/FontDock/requests";

// ============================================================
// Main: Write a request file for the FontDock client to process
// The client watches the requests folder and activates fonts
// from the .ai file on disk, bypassing Illustrator's GFKU error
// ============================================================
function activateDocumentFonts() {
    try {
        if (app.documents.length === 0) {
            writeLog("activateDocumentFonts: no documents open");
            return;
        }

        var doc = app.activeDocument;
        var docName = doc.name;

        writeLog("activateDocumentFonts: checking document '" + docName + "'");

        // Get the file path of the document
        var filePath = "";
        try {
            filePath = doc.fullName.fsName;
        } catch (e) {
            writeLog("activateDocumentFonts: document has no file path (unsaved?)");
            return;
        }

        writeLog("activateDocumentFonts: file path = " + filePath);

        // Ensure request directory exists
        var reqDir = new Folder(REQUEST_DIR);
        if (!reqDir.exists) {
            reqDir.create();
            writeLog("activateDocumentFonts: created request directory");
        }

        // Write request file with timestamp to avoid conflicts
        var ts = new Date().getTime();
        var reqFile = new File(REQUEST_DIR + "/request_" + ts + ".json");

        // Build simple JSON payload manually
        // Escape backslashes and quotes in the file path
        var escapedPath = filePath.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        var jsonContent = '{"file_path":"' + escapedPath + '","app":"illustrator","timestamp":' + ts + '}';

        reqFile.open("w");
        reqFile.write(jsonContent);
        reqFile.close();

        writeLog("activateDocumentFonts: request file written - " + reqFile.name);
        writeLog("activateDocumentFonts: FontDock client will process this request");

    } catch (e) {
        writeLog("activateDocumentFonts ERROR: " + e.message);
    }
}

// ============================================================
// Script loaded - check current document
// Run via File > Scripts, or assign to an Action with keyboard shortcut
// ============================================================
writeLog("=== FontDock Illustrator Auto-Activate script loaded ===");

if (app.documents.length > 0) {
    writeLog("Document already open, activating fonts...");
    activateDocumentFonts();
} else {
    writeLog("No documents open - run this script after opening a document");
}

writeLog("=== Script execution complete ===");
