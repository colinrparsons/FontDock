# InDesign Integration Specification

## Goal

Allow Adobe InDesign to trigger the local FontDock client when a document has missing fonts.

## Recommended v1 approach

Use **ExtendScript / JSX**.

This is the most practical first implementation.

## Why not parse INDD directly first?

INDD files are not the best first target for external parsing.

InDesign already knows:

- which fonts are used
- which fonts are missing
- document path
- document name

So the cleanest design is to let InDesign report that context.

## Responsibilities of the JSX script

The script should:

1. Detect the active document
2. Read document name and path
3. Inspect fonts used in the document
4. Identify missing fonts
5. Build a JSON payload
6. Send it to the local FontDock client (or write to a watched file)

## Suggested payload shape

```json
{
  "document_name": "Tesco_Summer_POS_2026.indd",
  "document_path": "/Volumes/Jobs/Tesco/Summer/POS/Tesco_Summer_POS_2026.indd",
  "missing_fonts": [
    "Gotham-Bold",
    "Gotham-Book",
    "Knockout-HTF48-Featherweight"
  ],
  "all_fonts": [
    "Gotham-Bold",
    "Gotham-Book",
    "Knockout-HTF48-Featherweight",
    "HelveticaNeueLTStd-Bd"
  ]
}
```

## Delivery methods to local client

### Option A (preferred)

POST JSON to local HTTP endpoint:

- `http://127.0.0.1:8765/open-fonts`

### Option B

Write JSON to a watched file location:

- `~/Library/Application Support/FontDock/requests/pending_request.json`

## Trigger modes

### Manual menu command (best for v1)

- User opens document
- User runs "Check Missing Fonts" script
- Script sends request to client

### Semi-automatic later

- Script can be run from startup or custom workflow
- Potential event-based hooks if practical

## Expected client response flow

1. Receive request
2. Run exact matching
3. Run alias matching
4. Rank likely collections
5. Prompt user if ambiguous
6. Activate selected fonts
7. Show result

## Important practical note

The InDesign integration should be treated as a bridge only.

Do not put heavy matching logic inside the JSX script.

Keep it simple and stable.
