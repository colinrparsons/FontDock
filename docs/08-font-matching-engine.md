# Font Matching Engine

## Purpose

The matching engine is the core intelligence of FontDock.

It should resolve missing fonts safely and predictably.

## Matching philosophy

Always prefer:

1. deterministic exact matches
2. alias matches
3. ranked collection suggestions
4. AI only when helpful

## Matching pipeline

### Step 1: Exact PostScript match

Try to match the missing font name against:

- `postscript_name`

This should be the highest-confidence path.

### Step 2: Exact full name match

Try to match against:

- `full_name`

### Step 3: Family + style normalization

Split and normalize names into likely:

- family
- style

Examples:

- Gotham-Bold -> family Gotham, style Bold
- HelveticaNeueLTStd-Bd -> family Helvetica Neue LT Std, style Bold

### Step 4: Alias lookup

Use `font_aliases`.

This is essential for real-world messy legacy naming.

### Step 5: Collection candidate scoring

If one or more fonts are found, score collections by:

- how many missing fonts they contain
- client match from document path/name
- collection keyword match from path/name
- recent user usage
- exact family overlap

### Step 6: Suggest activation plan

Possible outcomes:

- exact one-to-one matches for all fonts
- exact matches plus best collection suggestion
- partial match with user confirmation
- no match found

## Example scoring inputs

Use document context such as:

- filename
- parent folder names
- client aliases
- job codes
- recent collections activated by this user

## Safety rules

Never silently auto-activate uncertain substitutes.

If confidence is low:

- show candidates
- ask user to confirm

## Logging

Record:

- missing font names
- matched font IDs
- match method
- confidence score
- selected collection
- activation result

This improves future matching and debugging.

## Future enhancements

- better name normalization rules
- foundry-aware matching
- family completeness scoring
- user-specific ranking
- project-type ranking
- AI interpretation for ambiguous requests
