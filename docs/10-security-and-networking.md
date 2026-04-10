# Security and Networking

## Security goals

FontDock should:

- protect licensed font files
- restrict access by user/team/client
- avoid exposing storage publicly
- support remote users securely
- coexist with existing office VPN setups

## Recommended production model

### Best practical setup

- Host FontDock on an internal Ubuntu server or VM
- Put the server behind **Tailscale**
- Allow browser access over the Tailscale IP / MagicDNS name
- Allow the macOS client to connect over Tailscale

## Why Tailscale is a strong fit

Tailscale gives you:

- encrypted private networking
- no need to expose public ports
- simple client connectivity for remote users
- easier access control than opening services to the internet

## VPN coexistence concern

If users also need an office VPN, avoid routing everything through Tailscale.

Recommended:

- use Tailscale only for FontDock server access
- do not force full-tunnel behaviour
- do not use exit nodes for this workflow unless needed
- let the office VPN continue to handle office shares and other services

This reduces network conflicts.

## Client networking recommendation

The FontDock client should:

- connect only to the FontDock server hostname/IP over Tailscale
- avoid trying to become a general VPN replacement

## Authentication recommendations

### v1

- username/password for web
- API token/session for client

### v2+

- optional SSO / LDAP / OIDC

## Authorization recommendations

Permissions should be checked for:

- viewing clients
- viewing collections
- downloading fonts
- activating fonts

## Storage security

- do not store fonts in a public web root
- use internal storage paths
- stream downloads through authenticated endpoints
- log download and activation events

## Audit logging

Log at minimum:

- login events
- upload events
- download events
- activation events
- permission changes
- admin edits

## macOS local security

The client should:

- store tokens in Keychain if possible
- store cache in Application Support
- avoid world-readable cache directories
- validate downloaded file hashes if practical
