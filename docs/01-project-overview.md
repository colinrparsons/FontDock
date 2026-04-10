# Project Overview

## What FontDock is

FontDock is a self-hosted font server and client system built for creative production teams.

The main purpose is to make it easier to:

- organise licensed fonts centrally
- assign them to clients or projects
- let users search and retrieve them quickly
- activate them locally on macOS
- reduce missing-font issues when opening Adobe InDesign files

## The workflow problem it solves

In many teams, fonts are spread across:

- shared drives
- old job folders
- packaged projects
- manually maintained font folders
- expensive proprietary font managers

This leads to problems such as:

- users cannot find the correct font quickly
- font names are inconsistent
- old projects open with missing fonts
- remote users over VPN have slow access to font shares
- users activate too many fonts or wrong versions
- no central source of truth exists

## The product vision

FontDock should eventually support a workflow where:

1. A user opens an InDesign document
2. Missing fonts are detected automatically
3. The local client receives the missing font names and document context
4. The client checks the central server
5. Exact or likely matches are found
6. The user is prompted to activate the correct set
7. Fonts are activated locally
8. InDesign refreshes with minimal manual effort

## Design principles

- Build the server first
- Use a clean API contract
- Keep client logic separate from server logic
- Prefer deterministic matching first
- Use AI only where it adds value
- Make every phase useful even before the next one exists
- Keep the project understandable for future contributors

## What v1 should be

Version 1 should **not** try to do everything.

The best first useful version is:

- Upload fonts
- Extract metadata
- Store fonts on server
- Organise by client and collection
- Search fonts in a web UI
- Download fonts manually

This alone already creates value.

## What makes this open-source worthy

This is not just a toy project.

It solves a real production problem that many studios and agencies have.

A clean open-source version could be useful to:

- small agencies
- in-house design teams
- publishers
- prepress teams
- freelancers managing licensed client font sets
