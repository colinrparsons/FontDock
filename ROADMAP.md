# FontDock Development Roadmap

## Version 1.0.0 ✅ COMPLETE

**Released:** April 2026

### Core Features
- ✅ FastAPI backend with SQLite
- ✅ JWT authentication
- ✅ Font upload and metadata extraction
- ✅ Web admin portal
- ✅ Client and collection management
- ✅ macOS client (PyQt5)
- ✅ Font activation/deactivation
- ✅ InDesign integration
- ✅ Dark mode
- ✅ Family grouping
- ✅ Linux server deployment

---

## Version 1.1.0 🚧 IN PROGRESS

**Target:** Q2 2026

### Windows Client
- [ ] Port macOS client to Windows
- [ ] PyQt5 GUI for Windows
- [ ] Font activation via Windows Font API
- [ ] System tray integration
- [ ] Auto-start on login
- [ ] Windows installer (.exe)
- [ ] PyInstaller build script

**Technical Notes:**
- Use `%LOCALAPPDATA%\FontDock` for data
- Font activation: Copy to `C:\Windows\Fonts` or use Font Management API
- Windows service for background operation

### Adobe Photoshop Integration
- [x] Auto-activate via AppleScript font scanning
- [x] Text layer font name extraction (PostScript names)
- [x] Font activation via FontDock client
- [x] Version-independent app detection
- [ ] CEP panel for Photoshop
- [ ] Font preview in panel
- [ ] Recent fonts tracking

### Adobe Illustrator Integration
- [x] Auto-activate via AppleScript app watcher + file parsing
- [x] Font extraction from .ai files (XMP metadata)
- [x] Font activation via FontDock client
- [x] Version-independent app detection
- [ ] CEP panel for Illustrator
- [ ] Collection-based activation
- [ ] Document font list

---

## Version 1.2.0 📋 PLANNED

**Target:** Q3 2026

### Enhanced Search
- [ ] Full-text search across font metadata
- [ ] Search by foundry/designer
- [ ] Tag-based filtering
- [ ] Advanced filters (weight, width, style)
- [ ] Search history
- [ ] Saved searches

### Font Preview Improvements
- [ ] Custom preview text per font
- [ ] Multiple preview sizes
- [ ] Waterfall view
- [ ] Character map
- [ ] OpenType features display

### Performance
- [ ] PostgreSQL migration option
- [ ] Redis caching layer
- [ ] CDN support for font delivery
- [ ] Lazy loading for large libraries
- [ ] Background font processing

---

## Version 2.0.0 🎯 FUTURE

**Target:** Q4 2026

### Multi-Platform Support
- [ ] Linux client (PyQt5)
- [ ] Web-based client (Progressive Web App)
- [ ] Mobile app (iOS/Android) - read-only

### Advanced Features
- [ ] Font versioning
- [ ] Font licensing tracking
- [ ] Usage analytics
- [ ] Font recommendations
- [ ] Duplicate font detection (visual similarity)
- [ ] Font pairing suggestions

### Enterprise Features
- [ ] LDAP/Active Directory integration
- [ ] SSO support (SAML, OAuth)
- [ ] Audit logging
- [ ] Role-based permissions (granular)
- [ ] Multi-tenant support
- [ ] API rate limiting

### AI-Powered Features
- [ ] Natural language font search
- [ ] Smart font matching
- [ ] Context-aware suggestions
- [ ] Auto-tagging based on visual analysis
- [ ] Font similarity search

---

## Immediate Next Steps

### 1. Windows Client (Priority: HIGH)

**Week 1-2: Setup & Core Functionality**
- [ ] Create `windows-client/` directory
- [ ] Port GUI code from macOS client
- [ ] Implement Windows font activation
- [ ] Test on Windows 10/11

**Week 3: Packaging**
- [ ] Create PyInstaller spec for Windows
- [ ] Build .exe installer
- [ ] Test installation process
- [ ] Create uninstaller

**Week 4: Polish**
- [ ] System tray icon
- [ ] Auto-start configuration
- [ ] Windows-specific UI adjustments
- [ ] Documentation

### 2. Photoshop Integration (Priority: HIGH)

**Completed:**
- [x] Auto-activate via AppleScript font scanning (text layers)
- [x] Font name extraction from Photoshop DOM
- [x] Font activation via FontDock client
- [x] Version-independent app detection (CFBundleDisplayName)
- [x] Unified install/uninstall scripts

**Remaining:**
- [ ] CEP panel for Photoshop
- [ ] Font preview in panel
- [ ] Test on Photoshop CC 2023/2024/2025

### 3. Illustrator Integration (Priority: MEDIUM)

**Completed:**
- [x] Auto-activate via AppleScript app watcher + file-based IPC
- [x] Font extraction from .ai files (XMP stFnt:fontName)
- [x] Font activation via FontDock client
- [x] Version-independent app detection
- [x] Unified install/uninstall scripts

**Remaining:**
- [ ] CEP panel for Illustrator
- [ ] Collection-based activation
- [ ] Test on Illustrator CC 2023/2024/2025

---

## Technical Debt & Improvements

### Backend
- [ ] Add database migrations (Alembic)
- [ ] Improve error handling
- [ ] Add comprehensive logging
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Unit tests (pytest)
- [ ] Integration tests

### Frontend (Web UI)
- [ ] Modernize with React/Vue
- [ ] Responsive design improvements
- [ ] Accessibility (WCAG 2.1)
- [ ] Dark mode for web UI
- [ ] Keyboard shortcuts

### macOS Client
- [ ] Code refactoring (separate concerns)
- [ ] Better error messages
- [ ] Offline mode improvements
- [ ] Settings sync across devices
- [ ] Notification system

---

## Community & Documentation

### Documentation
- [ ] API documentation
- [ ] Developer guide
- [ ] Contributing guidelines
- [ ] Code of conduct
- [ ] Architecture diagrams

### Community
- [ ] GitHub Discussions
- [ ] Discord server
- [ ] Example workflows
- [ ] Video tutorials
- [ ] Blog posts

---

## Platform Support Matrix

| Feature | macOS | Windows | Linux | Web |
|---------|-------|---------|-------|-----|
| Client App | ✅ v1.0 | 🚧 v1.1 | 📋 v2.0 | 📋 v2.0 |
| Font Activation | ✅ | 🚧 | 📋 | ❌ |
| InDesign Auto-Activation | ✅ | 🚧 | 📋 | ❌ |
| Photoshop Auto-Activation | ✅ v1.1 | 🚧 v1.1 | 🚧 v1.1 | ❌ |
| Illustrator Auto-Activation | ✅ v1.1 | 🚧 v1.1 | 🚧 v1.1 | ❌ |

**Legend:**
- ✅ Complete
- 🚧 In Progress / Planned
- 📋 Future
- ❌ Not Applicable

---

## Contributing

Want to help build these features? Check out:
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [GitHub Issues](https://github.com/colinrparsons/FontDock/issues) - Current tasks
- [GitHub Discussions](https://github.com/colinrparsons/FontDock/discussions) - Ideas and questions

---

## Version History

### v1.0.0 - April 2026
- Initial release
- macOS client
- FastAPI backend
- InDesign integration
- Web admin portal

---

**Last Updated:** April 16, 2026  
**Maintainer:** Colin Parsons
