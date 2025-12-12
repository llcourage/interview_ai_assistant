# Windows Tile Icons

This directory contains the tile icons required for Windows AppX/MSIX packages.

## Required Files

For Windows Store submission, the following tile icon files are required:

1. **StoreLogo.png** (50x50 pixels)
   - Store logo used in Windows Store app listings
   
2. **Square44x44Logo.png** (44x44 pixels)
   - Used for taskbar and small tile representations
   
3. **Square150x150Logo.png** (150x150 pixels)
   - Standard square tile size
   
4. **Wide310x150Logo.png** (310x150 pixels)
   - Wide tile format for Start menu
   
5. **Square310x310Logo.png** (310x310 pixels)
   - Large square tile format

## Configuration

The tile icons are automatically detected by electron-builder when:
- `buildResources` is set to `"resources"` in `package.json`
- Tile icons are placed in `resources/tiles/` directory
- Files are named exactly as required (Square44x44Logo.png, etc.)

## Generating Tile Icons

To generate all tile icons from the base `icon.png`, run:

```powershell
.\scripts\generate-tile-icons.ps1
```

Or manually specify paths:

```powershell
.\scripts\generate-tile-icons.ps1 -SourceIcon "resources\icon.png" -OutputDir "resources\tiles"
```

## Design Guidelines

According to Microsoft's requirements:

1. **Unique Representation**: Tile icons must uniquely represent your product so users can associate icons with the appropriate products and not confuse one product for another.

2. **Clear Metaphor**: Icons should clearly convey the application's core functionality and value proposition.

3. **Readability**: Icons must be readable at all required sizes (44x44 to 310x310).

4. **Contrast**: Ensure sufficient contrast for both light and dark themes.

5. **Simple Design**: Use simple shapes and avoid unnecessary decorative elements.

## References

- [Windows App Icon Design Guidelines](https://learn.microsoft.com/en-us/windows/apps/design/style/iconography/app-icon-design)
- [Windows Tiles and Notifications](https://docs.microsoft.com/en-us/windows/uwp/controls-and-patterns/tiles-and-notifications-app-assets)
- [3D App Launcher Design (for Mixed Reality)](https://docs.microsoft.com/en-us/windows/mixed-reality/3d-app-launcher-design-guidance)

