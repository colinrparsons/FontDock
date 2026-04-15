// FontDock Auto-Activate for Adobe Photoshop
// Scans text layers for font PostScript names and writes them to a request file.
// The FontDock client watches for request files and activates the fonts.
// Photoshop CAN read font names from its DOM (unlike Illustrator which throws GFKU).
// Uses only File operations for communication - works in all Adobe apps.

#target photoshop

// ============================================================
// Debug logging - writes to ~/Desktop/fontdock_ps_debug.txt
// Set DEBUG to false to disable
// ============================================================
var DEBUG = true;
var LOG_FILE = Folder.desktop + "/fontdock_ps_debug.txt";

function writeLog(msg) {
    if (!DEBUG) return;
    try {
        var f = new File(LOG_FILE);
        f.open("a");
        f.write(new Date().toString() + " | " + msg + "\n");
        f.close();
    } catch (e) {}
}

// ============================================================
// Request directory - FontDock client watches this folder
// ============================================================
var REQUEST_DIR = "~/Library/Application Support/FontDock/requests";

// ============================================================
// Recursively scan layers for text layers and collect font names
// Photoshop uses LayerSets (groups) that need recursive scanning
// ============================================================
function scanDocumentFonts(doc) {
    var fontsFound = {};

    function processLayer(layer) {
        try {
            if (layer.kind === LayerKind.TEXT) {
                try {
                    var fontName = layer.textItem.font;
                    if (fontName && !fontsFound[fontName]) {
                        fontsFound[fontName] = true;
                        writeLog("scanDocumentFonts: found font " + fontName);
                    }
                } catch (e) {
                    writeLog("scanDocumentFonts: error reading text layer font: " + e.message);
                }
            }

            // Process layer sets (groups) recursively
            if (layer.typename === "LayerSet") {
                for (var i = 0; i < layer.layers.length; i++) {
                    processLayer(layer.layers[i]);
                }
            }
        } catch (e) {
            writeLog("scanDocumentFonts: error processing layer: " + e.message);
        }
    }

    var layers = doc.layers;
    for (var i = 0; i < layers.length; i++) {
        processLayer(layers[i]);
    }

    var result = [];
    for (var name in fontsFound) {
        result.push(name);
    }
    return result;
}

// ============================================================
// Main: Scan document fonts and write request file
// The FontDock client processes the request file and activates fonts
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

        // Get file path (for reference, may not be available for unsaved docs)
        var filePath = "";
        try {
            filePath = doc.fullName.fsName;
        } catch (e) {
            writeLog("activateDocumentFonts: document has no file path (unsaved?)");
        }

        // Scan document for font PostScript names
        var fontNames = scanDocumentFonts(doc);

        if (fontNames.length === 0) {
            writeLog("activateDocumentFonts: no fonts found in document");
            return;
        }

        writeLog("activateDocumentFonts: found " + fontNames.length + " fonts: " + fontNames.join(", "));

        // Ensure request directory exists
        var reqDir = new Folder(REQUEST_DIR);
        if (!reqDir.exists) {
            reqDir.create();
            writeLog("activateDocumentFonts: created request directory");
        }

        // Write request file with timestamp
        var ts = new Date().getTime();
        var reqFile = new File(REQUEST_DIR + "/request_" + ts + ".json");

        // Build JSON payload manually
        // Include both font_names (for direct activation) and file_path (for file parsing fallback)
        var escapedPath = filePath.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        var fontNamesJson = "";
        for (var i = 0; i < fontNames.length; i++) {
            if (i > 0) fontNamesJson += ",";
            fontNamesJson += '"' + fontNames[i].replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
        }

        var jsonContent = '{"file_path":"' + escapedPath + '","app":"photoshop","timestamp":' + ts +
                          ',"font_names":[' + fontNamesJson + ']}';

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
// Run via File > Scripts, or the FontDock client watches via AppleScript
// ============================================================
writeLog("=== FontDock Photoshop Auto-Activate script loaded ===");

if (app.documents.length > 0) {
    writeLog("Document already open, activating fonts...");
    activateDocumentFonts();
}

writeLog("=== Script execution complete ===");
