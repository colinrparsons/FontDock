# Open Source Plan

## Why open source this project

FontDock solves a real workflow problem that many teams share.

An open-source release could help:

- small studios
- agencies
- in-house marketing teams
- publishers
- freelancers
- prepress and packaging teams

## Recommended license

### MIT

Best if you want:

- maximum adoption
- easy reuse
- low friction

### Apache-2.0

Best if you want:

- explicit patent grant
- slightly more formal enterprise comfort

## Repository structure suggestion

```text
fontdock/
  README.md
  LICENSE
  CONTRIBUTING.md
  .gitignore
  docs/
  app/
  scripts/
  tests/
  examples/
```

## Good open-source hygiene

Before public release:

- remove internal client names from sample data
- remove real font files
- use fake/example metadata
- include sample JSON fixtures only
- document what users need to provide themselves

## What not to include

- proprietary font files
- real agency client data
- real job folder names
- internal credentials or URLs

## Great contributor targets

Good first issues:

- improve font metadata extraction
- add TTC support
- improve macOS activation method
- build collection import/export
- add search ranking improvements
- build better admin pages
- add Docker support

## Nice future public milestones

- v0.1: server MVP
- v0.2: collections + permissions
- v0.3: macOS client prototype
- v0.4: InDesign bridge
- v0.5: matching engine
- v0.6: smart search
- v1.0: stable creative-team workflow

## Community angle

This project will be strongest if positioned as:

- a workflow-first tool
- practical for creative production
- not trying to replace every enterprise feature on day one

That focus makes it credible.
