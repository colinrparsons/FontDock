// Debug Font Info for Illustrator
// Run this manually to see what font information Illustrator provides

#target illustrator

if (app.documents.length === 0) {
    alert("No document open!");
} else {
    var doc = app.activeDocument;
    var textFrames = doc.textFrames;
    var output = "Font Information for: " + doc.name + "\n\n";
    var fontsFound = {};
    
    // Collect unique fonts from all text frames
    for (var i = 0; i < textFrames.length; i++) {
        try {
            var textRange = textFrames[i].textRange;
            var fontName = textRange.characterAttributes.textFont.name;
            var fontFamily = textRange.characterAttributes.textFont.family;
            var fontStyle = textRange.characterAttributes.textFont.style;
            
            var key = fontFamily + "|" + fontStyle;
            if (!fontsFound[key]) {
                fontsFound[key] = {
                    name: fontName,
                    family: fontFamily,
                    style: fontStyle
                };
            }
        } catch (e) {
            // Skip if no text or font info unavailable
        }
    }
    
    // Output collected fonts
    var count = 0;
    for (var key in fontsFound) {
        count++;
        var font = fontsFound[key];
        output += "Font " + count + ":\n";
        output += "  name: " + font.name + "\n";
        output += "  family: " + font.family + "\n";
        output += "  style: " + font.style + "\n\n";
    }
    
    if (count === 0) {
        output += "No text frames with fonts found in document.\n";
    }
    
    // Write to desktop
    var logFile = new File("~/Desktop/illustrator_font_debug.txt");
    logFile.open("w");
    logFile.write(output);
    logFile.close();
    
    alert("Font info written to ~/Desktop/illustrator_font_debug.txt\nFound " + count + " unique fonts.");
}
