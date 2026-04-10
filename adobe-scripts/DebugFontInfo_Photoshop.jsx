// Debug Font Info for Photoshop
// Run this manually to see what font information Photoshop provides

#target photoshop

if (app.documents.length === 0) {
    alert("No document open!");
} else {
    var doc = app.activeDocument;
    var output = "Font Information for: " + doc.name + "\n\n";
    var fontsFound = {};
    
    // Collect unique fonts from all text layers
    var layers = doc.layers;
    var count = 0;
    
    function processLayer(layer) {
        try {
            if (layer.kind === LayerKind.TEXT) {
                var textItem = layer.textItem;
                var fontName = textItem.font;
                var fontFamily = textItem.font; // Photoshop may not separate family/style
                
                if (!fontsFound[fontName]) {
                    count++;
                    fontsFound[fontName] = true;
                    output += "Font " + count + ":\n";
                    output += "  font: " + fontName + "\n";
                    output += "  size: " + textItem.size + "\n\n";
                }
            }
            
            // Process layer sets (groups) recursively
            if (layer.typename === "LayerSet") {
                for (var i = 0; i < layer.layers.length; i++) {
                    processLayer(layer.layers[i]);
                }
            }
        } catch (e) {
            // Skip if layer doesn't have text or font info unavailable
        }
    }
    
    // Process all layers
    for (var i = 0; i < layers.length; i++) {
        processLayer(layers[i]);
    }
    
    if (count === 0) {
        output += "No text layers with fonts found in document.\n";
    }
    
    // Write to desktop
    var logFile = new File("~/Desktop/photoshop_font_debug.txt");
    logFile.open("w");
    logFile.write(output);
    logFile.close();
    
    alert("Font info written to ~/Desktop/photoshop_font_debug.txt\nFound " + count + " unique fonts.");
}
