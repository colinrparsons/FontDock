# Illustrator & Photoshop Auto-Activation Plan

**Date:** April 9, 2026  
**Status:** Planning Phase

## Overview

Extend FontDock auto-activation to Adobe Illustrator and Photoshop using the same approach as InDesign.

## Key Differences from InDesign

### InDesign
- ✅ Has `document.fonts` collection with status (NOT_AVAILABLE, SUBSTITUTED)
- ✅ Can detect missing fonts automatically
- ✅ Has `afterOpen` event for documents

### Illustrator
- ❓ Font detection via text frames (`textFrame.textRange.characterAttributes.textFont`)
- ❓ No built-in "missing fonts" status
- ❓ May need to check if font is installed vs used
- ✅ Has document events

### Photoshop
- ❓ Font detection via text layers (`layer.textItem.font`)
- ❓ No built-in "missing fonts" status
- ❓ Different layer structure (groups, nested layers)
- ✅ Has document events

## Research Needed

### Step 1: Test Font Information
Run debug scripts to see what font data is available:

**Illustrator:**
1. Open Illustrator document with text
2. Run `DebugFontInfo_Illustrator.jsx` from File > Scripts > Other Script
3. Check `~/Desktop/illustrator_font_debug.txt`

**Photoshop:**
1. Open Photoshop document with text layers
2. Run `DebugFontInfo_Photoshop.jsx` from File > Scripts > Browse
3. Check `~/Desktop/photoshop_font_debug.txt`

### Step 2: Determine Missing Font Detection

**Questions:**
- Can we detect if a font is missing/substituted?
- Do these apps have a "missing fonts" API?
- Can we compare used fonts vs installed fonts?

**Possible Approaches:**

1. **Check Font Availability** - Try to access font properties, catch errors
2. **Compare with System Fonts** - Get list of installed fonts, compare with used fonts
3. **User Trigger** - Manual script run (not automatic like InDesign)

### Step 3: Event Handling

**Illustrator Events:**
- `app.notifiers` - Can register for document open/close events
- May need polling or manual trigger

**Photoshop Events:**
- Limited event system compared to InDesign
- May need manual script execution

## Implementation Options

### Option A: Automatic (Like InDesign)
- Install startup script
- Detect missing fonts on document open
- Auto-activate via FontDock client
- **Pros:** Seamless user experience
- **Cons:** May not be possible if missing font detection unavailable

### Option B: Manual Script
- User runs script from Scripts menu
- Script scans document for fonts
- Activates all fonts (or only missing ones if detectable)
- **Pros:** Always works, simple implementation
- **Cons:** Requires user action

### Option C: Hybrid
- Startup script registers menu item or keyboard shortcut
- User triggers activation when needed
- **Pros:** Easy access, reliable
- **Cons:** Not fully automatic

## Script Locations

### Illustrator
**Startup Scripts:**
```
~/Library/Application Support/Adobe/Startup Scripts CS6/Illustrator/
```
or
```
/Applications/Adobe Illustrator 2026/Presets/en_US/Scripts/
```

**User Scripts:**
```
~/Library/Application Support/Adobe/Illustrator [version]/en_US/Scripts/
```

### Photoshop
**Startup Scripts:**
```
~/Library/Application Support/Adobe/Startup Scripts CS6/Adobe Photoshop/
```

**User Scripts:**
```
~/Library/Application Support/Adobe/Adobe Photoshop 2026/Presets/Scripts/
```

## Next Steps

1. ✅ Create debug scripts for Illustrator and Photoshop
2. ⏳ Test with documents containing fonts
3. ⏳ Analyze font information available
4. ⏳ Determine if missing font detection is possible
5. ⏳ Choose implementation approach
6. ⏳ Build auto-activation scripts
7. ⏳ Test and refine

## Expected Challenges

1. **Font Detection** - May not have InDesign's robust font API
2. **Missing Font Status** - May need workarounds to detect missing fonts
3. **Event System** - May not have reliable document open events
4. **Performance** - Scanning all text elements may be slow for large documents
5. **Font Name Format** - May differ from InDesign's family/style separation

## Fallback Plan

If automatic detection isn't possible:
- Create manual "Activate Document Fonts" script
- Add to Scripts menu in both apps
- User runs when opening documents with missing fonts
- Still uses FontDock client API for activation
- Better than nothing, still saves time vs manual activation

---

**Status:** Awaiting font information from debug scripts
