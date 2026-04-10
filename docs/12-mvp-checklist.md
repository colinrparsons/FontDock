# MVP Checklist

## Server

- [ ] FastAPI project created
- [ ] Config system added
- [ ] SQLite DB connected
- [ ] SQLAlchemy models created
- [ ] Alembic added (optional in first local prototype)

## Font ingestion

- [ ] Upload route works
- [ ] Accepts OTF/TTF
- [ ] Saves file to storage folder
- [ ] Computes SHA256 hash
- [ ] Extracts metadata
- [ ] Saves DB record

## Web UI

- [ ] Login page
- [ ] Dashboard page
- [ ] Fonts list page
- [ ] Font detail page
- [ ] Families page
- [ ] Collections page
- [ ] Upload page

## Data model

- [ ] Users table
- [ ] Clients table
- [ ] Collections table
- [ ] Font families table
- [ ] Fonts table
- [ ] Font aliases table
- [ ] Collection-font join table

## Search

- [ ] Search by family
- [ ] Search by style
- [ ] Search by PostScript name
- [ ] Search by alias
- [ ] Search by collection

## Security

- [ ] Password hashing
- [ ] Protected routes
- [ ] Download permission checks
- [ ] Audit logging basics

## Client (later MVP)

- [ ] Login to server
- [ ] Sync metadata
- [ ] Search collections
- [ ] Download fonts
- [ ] Cache locally
- [ ] Prototype activation

## InDesign bridge (later MVP)

- [ ] JSX script reads current document
- [ ] Detects missing fonts
- [ ] Sends JSON to local client
- [ ] Client receives and logs request
