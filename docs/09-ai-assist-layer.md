# AI Assist Layer

## Important principle

AI is optional.

FontDock should be useful and reliable **without** AI.

The AI layer should improve user experience, not replace deterministic logic.

## Good uses of AI in this project

### 1. Natural-language search

Examples:

- "Open the fonts for Tesco summer POS"
- "Show me the Nike brand core fonts"
- "Load the fonts we used last month for Aldi"

AI can convert these into structured filters.

### 2. Ambiguity resolution

If multiple collections are plausible:

- suggest top 2–3 likely matches
- explain why

### 3. Context-aware ranking

Given:

- document name
- folder path hints
- missing font names
- recent usage

AI can help rank likely collections.

### 4. Query interpretation

AI can map vague user phrases to:

- client
- collection keywords
- family hints
- project type

## What AI should not do

- blindly activate substitute fonts
- override exact deterministic matches
- invent non-existent fonts
- guess without showing confidence when uncertain

## Recommended architecture

Use AI as a translation layer.

Input:

- user request or document context

Output:

- structured search intent

Example output:

```json
{
  "intent": "activate_collection",
  "client": "Tesco",
  "collection_keywords": ["summer", "pos"],
  "families": ["Gotham", "Knockout"],
  "confidence": 0.91
}
```

Then the standard search and matching engine performs the real work.

## Suggested implementation stages

### Stage 1: No LLM

Use:

- aliases
- fuzzy matching
- keyword scoring
- recent usage

### Stage 2: Optional hosted AI

Use an LLM API for:

- query interpretation
- ranking assistance

### Stage 3: Optional local AI

For privacy-sensitive teams, a local model could run in the client or server.

But this should come much later.

## AI data considerations

Be careful with:

- sensitive file paths
- client names
- project names
- internal campaign data

For hosted AI, consider redacting or simplifying path data before sending.
