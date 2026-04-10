# Database Schema

## Design goals

The schema should support:

- individual font files
- font families and styles
- multiple clients
- collections per client or global
- aliases for messy legacy names
- user permissions
- usage history
- audit logging
- future AI-friendly metadata

## Core tables

### users

Fields:

- id
- username
- email
- password_hash
- is_admin
- is_active
- created_at
- updated_at

### roles (optional later)

Fields:

- id
- name
- description

### clients

Fields:

- id
- name
- code
- description
- is_active
- created_at
- updated_at

### collections

Fields:

- id
- name
- slug
- description
- client_id (nullable for global collections)
- is_active
- created_at
- updated_at

Examples:

- Tesco Summer POS 2026
- Nike Brand Core
- Global Sans Serif Essentials

### tags

Fields:

- id
- name
- slug

### font_families

Fields:

- id
- name
- normalized_name
- foundry
- notes
- created_at
- updated_at

### fonts

Represents a specific font file/style.

Fields:

- id
- family_id
- filename_original
- filename_storage
- storage_path
- file_hash_sha256
- file_size_bytes
- extension
- postscript_name
- full_name
- style_name
- weight_class
- width_class
- italic_angle
- version_string
- is_variable_font
- is_active
- created_at
- updated_at

### font_aliases

Used to map weird names or legacy naming.

Fields:

- id
- font_id
- alias_name
- alias_normalized
- source_type
- created_at

Examples:

- HelveticaNeueLTStd-Bd
- Gotham-Bold
- Knockout-HTF48-Featherweight

### collection_fonts

Join table:

- id
- collection_id
- font_id
- added_at

### collection_tags

Join table:

- id
- collection_id
- tag_id

### user_client_permissions

- id
- user_id
- client_id
- can_view
- can_download
- can_activate

### user_collection_permissions (optional later)

- id
- user_id
- collection_id
- can_view
- can_download
- can_activate

### font_usage_events

Tracks usage history.

Fields:

- id
- user_id
- font_id
- collection_id (nullable)
- source
- document_name (nullable)
- document_path_hint (nullable)
- event_type
- created_at

Event examples:

- download
- activate
- deactivate
- indesign_missing_font_match

### audit_events

Broad audit trail.

Fields:

- id
- user_id (nullable)
- event_type
- entity_type
- entity_id
- payload_json
- created_at

## AI-friendly additions

To support future AI or smarter matching, it helps to store:

- normalized names
- aliases
- usage history
- document filename hints (not full sensitive paths in production if privacy matters)
- client codes
- collection keywords
- tags
