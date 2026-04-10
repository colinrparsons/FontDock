const { entrypoints } = require("uxp");
const { app } = require("indesign");

let statusPanel = null;

entrypoints.setup({
  commands: {
    checkFonts: () => checkAndActivateFonts(true)
  },
  panels: {
    showPanel: {
      show({node} = {}) {
        statusPanel = node;
        updateStatusPanel("Ready - waiting for documents with missing fonts");
      }
    }
  }
});

// Listen for document open events
app.addEventListener("afterOpen", () => {
  console.log("FontDock: Document opened, checking fonts...");
  checkAndActivateFonts(false);
});

// Also check when plugin loads if document is already open
if (app.documents.length > 0) {
  console.log("FontDock: Plugin loaded with document open, checking fonts...");
  checkAndActivateFonts(false);
}

async function checkAndActivateFonts(showDialog = false) {
  try {
    const doc = app.activeDocument;
    if (!doc) {
      console.log("FontDock: No active document");
      return;
    }

    const docName = doc.name;
    console.log(`FontDock: Checking fonts in ${docName}`);
    
    // Get all fonts used in document
    const fonts = doc.fonts.everyItem().getElements();
    console.log(`FontDock: Found ${fonts.length} font references`);
    
    const allFonts = [];
    const missingFonts = [];
    
    for (let i = 0; i < fonts.length; i++) {
      const font = fonts[i];
      const fontName = font.fontFamily;
      
      console.log(`FontDock: Font ${i}: ${fontName}, status: ${font.status}`);
      
      if (!allFonts.includes(fontName)) {
        allFonts.push(fontName);
      }
      
      // Check if font is missing (status values in InDesign)
      const status = font.status.toString();
      if (status === "FontStatus.NOT_AVAILABLE" || 
          status === "FontStatus.SUBSTITUTED" ||
          status.includes("NOT_AVAILABLE") ||
          status.includes("SUBSTITUTED")) {
        if (!missingFonts.includes(fontName)) {
          missingFonts.push(fontName);
        }
      }
    }
    
    console.log(`FontDock: Found ${missingFonts.length} missing fonts`);
    
    if (missingFonts.length === 0) {
      updateStatusPanel(`✓ ${docName}: All fonts available`);
      if (showDialog) {
        showAlert("No missing fonts!", `All ${allFonts.length} fonts are available.`);
      }
      return;
    }
    
    console.log("FontDock: Missing fonts:", missingFonts.join(", "));
    updateStatusPanel(`⚠ ${docName}: ${missingFonts.length} missing fonts - activating...`);
    
    // Send request to FontDock client
    const payload = {
      document_name: docName,
      document_path: doc.fullName ? doc.fullName.fsName : "Unsaved",
      missing_fonts: missingFonts,
      all_fonts: allFonts,
      auto_activate: !showDialog
    };
    
    console.log("FontDock: Writing request to file");
    
    // Use file-based communication (UXP doesn't allow network access in InDesign)
    const fs = require('uxp').storage.localFileSystem;
    const homeFolder = await fs.getDataFolder();
    
    try {
      // Write to ~/Library/Application Support/Adobe/UXP/PluginsStorage/INDT/FontDockAutoActivate/PluginData/
      const requestFile = await homeFolder.createFile("fontdock_request.json", { overwrite: true });
      await requestFile.write(JSON.stringify(payload, null, 2));
      
      console.log("FontDock: Request written to:", requestFile.nativePath);
      
      // Trigger via curl command using ExtendScript
      const extendScript = `
        var curlCmd = "curl -X POST http://127.0.0.1:8765/open-fonts " +
                      "-H 'Content-Type: application/json' " +
                      "-d @'" + "${requestFile.nativePath}" + "' " +
                      "--max-time 2 --connect-timeout 1";
        system.callSystem(curlCmd);
      `;
      
      await app.doScript(extendScript);
      
      updateStatusPanel(`✓ ${docName}: Request sent to FontDock`);
      
      if (showDialog) {
        showAlert("Request Sent!", `Sent ${missingFonts.length} missing fonts to FontDock for activation.`);
      }
      
    } catch (fileError) {
      console.error("FontDock: File error", fileError);
      updateStatusPanel(`✗ ${docName}: Failed to write request file`);
      
      if (showDialog) {
        showAlert("Error", `Failed to communicate with FontDock: ${fileError.message}`);
      }
    }
    
  } catch (error) {
    console.error("FontDock: Error checking fonts", error);
    updateStatusPanel(`✗ Error: ${error.message}`);
    
    if (showDialog) {
      showAlert("Error", `Error checking fonts: ${error.message}`);
    }
  }
}

function updateStatusPanel(message) {
  if (statusPanel) {
    const statusDiv = statusPanel.querySelector("#status");
    if (statusDiv) {
      statusDiv.textContent = message;
    }
  }
}

function showAlert(title, message) {
  const dialog = app.dialogs.add();
  dialog.name = title;
  
  const col = dialog.dialogColumns.add();
  const text = col.staticTexts.add();
  text.staticLabel = message;
  
  dialog.canCancel = false;
  dialog.show();
  dialog.destroy();
}