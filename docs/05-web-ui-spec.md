# Web UI Specification

## Purpose

The web UI is the first usable product.

It should allow admins and normal users to:

- browse fonts
- search fonts
- manage collections
- upload fonts
- view families
- download fonts

## Recommended approach

Start with:

- **FastAPI + Jinja2 templates**
- minimal JavaScript
- server-rendered forms and tables

This is faster and simpler for an MVP.

## Main pages

### 1. Login page

- username/email
- password
- remember me (optional)

### 2. Dashboard

Show:

- total fonts
- total families
- total collections
- recent uploads
- recent activations/downloads
- quick links

### 3. Fonts page

List with:

- family
- style
- PostScript name
- client/collections
- tags
- download button
- detail link

Filters:

- client
- collection
- tag
- active status

### 4. Font detail page

Show:

- file info
- family
- style
- PostScript name
- aliases
- collections
- tags
- usage history (admin)

### 5. Families page

Group fonts by family.

Show:

- family name
- style count
- foundry
- linked collections

### 6. Clients page

Show:

- all clients
- collection counts
- font counts

### 7. Client detail page

Show:

- collections for that client
- core brand sets
- seasonal/project sets

### 8. Collections page

This is a key page.

Show:

- collection name
- client
- description
- included fonts
- tags
- download all / export manifest (later)

### 9. Upload page (admin)

Features:

- multi-file upload
- drag and drop later
- validation messages
- duplicate detection
- preview metadata before save (later)

### 10. User management page (admin)

- create user
- edit user
- assign permissions

## Search behaviour

Search should match:

- family names
- style names
- PostScript names
- aliases
- client names
- collection names
- tags

## Nice future additions

- font preview text rendering (server-side image or browser CSS preview if practical)
- recently used collections
- favourite collections
- collection templates
- CSV import/export
