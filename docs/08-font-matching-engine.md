# Font Matching Engine

## Purpose

The matching engine is the core intelligence of FontDock.

It should resolve missing fonts safely and predictably.

## Matching philosophy

Inspired by Extensis Font Sense (US Patent #7,197,706), FontDock uses a multi-field matching approach that tries the most reliable identifiers first, falling back to broader matches only when needed.

Always prefer:

1. deterministic exact matches
2. constructed PostScript name matches
3. family + style matches
4. alias matches
5. ranked collection suggestions
6. AI only when helpful

## Implemented matching pipeline (`database.smart_match_font`)

### Strategy 1: Exact PostScript name match (case-insensitive)

Try to match the missing font name against:

- `postscript_name` (COLLATE NOCASE)

This is the highest-confidence path. PostScript names are unique per font.

Example: `KFC-Regular` matches `KFC-Regular` in DB.

### Strategy 2: Family + Style exact match + Constructed PostScript

If family and style are provided (as InDesign sends them):

1. Match `family_name` + `style_name` (case-insensitive)
2. Construct PostScript name from family+style: `family.replace(" ", "") + "-" + style.replace(" ", "")`
3. Match constructed name against `postscript_name`

Example: InDesign sends `family="KFC", style="Regular"` → constructs `KFC-Regular` → matches DB.

### Strategy 3: Full name match

Try to match against:

- `full_name` (case-insensitive)
- Also tries `"family style"` as full_name if not provided directly

Example: `KFC Regular` matches `full_name` in DB.

### Strategy 4: Family name match (all members)

Match `family_name` (case-insensitive) and return **all** fonts in the family.

This ensures all weights/styles are available when InDesign reports a missing font.

Example: `family="KFC"` returns all KFC fonts (Regular, Bold, etc.).

### Strategy 5: Fuzzy search fallback

LIKE search across `postscript_name`, `full_name`, and `family_name` (all case-insensitive).

Last resort when no exact or constructed match is found.

## Case-insensitive matching

All matching uses `COLLATE NOCASE` in SQLite to handle case discrepancies between:

- Adobe app font name reporting (e.g., `KFC`)
- Database storage after normalization (e.g., `Kfc`)

This is critical because:
- InDesign reports `font.fontFamily` using the font's internal name
- FontDock normalizes family names to title case on ingest
- These can differ in case, causing activation failures

## Activation behavior

When `smart_match_font` returns results, the activation logic determines scope:

| Match type | Behavior |
|---|---|
| Specific style match (Strategy 1/2/3) | Activate only the requested style |
| Family-wide match (Strategy 4/5) | Activate all family members |
| No exact style but family found | Activate all family members |

## Matching paths by Adobe app

| App | Font info sent | Primary strategy |
|---|---|---|
| **InDesign** | `{family, style}` objects | Strategy 2 (constructed PS name) |
| **Illustrator** | PostScript names from file | Strategy 1 (exact PS match) |
| **Photoshop** | PostScript names from DOM | Strategy 1 (exact PS match) |

## Future enhancements

- Alias lookup table for legacy name variants
- Collection candidate scoring (how many missing fonts a collection contains)
- Foundry-aware matching (version disambiguation)
- Family completeness scoring
- User-specific ranking
- Project-type ranking
- Font fingerprinting (hash-based exact version matching)
- AI interpretation for ambiguous requests
