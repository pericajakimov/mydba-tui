# Assets

This directory contains static application assets used by mydba-tui.

Assets are files that are packaged with the application but are not Python
source code or configuration files.

## Purpose

Assets may include:

- application icons
- logos
- default themes
- syntax highlighting definitions
- static templates
- documentation resources
- sample files

## Directory Structure

The directory may contain:
```
assets/
├── icons/
├── themes/
├── syntax/
├── templates/
└── samples/
```

## Asset Management

Application code should access assets through the dedicated utility layer.

Avoid:

- hardcoded absolute paths
- direct filesystem assumptions
- modifying packaged assets at runtime

The application should support:

- development environment paths
- installed package paths
- offline deployments

## Themes

Theme-related assets should be stored separately:
```
assets/themes/
```

Examples:

- color definitions
- Textual CSS files
- user interface style resources

## SQL and Syntax Assets

Syntax-related resources should be stored under:
```
assets/syntax/
```

Examples:

- SQL keyword definitions
- highlighting rules
- editor configuration

## Packaging Requirements

All required runtime assets must be included in the Python package.

Verify that:

- assets are available after installation
- offline installation contains all required files
- development and production layouts behave consistently

## Future Extensions

This directory may later include:

- custom DBA themes
- MySQL version-specific syntax definitions
- plugin assets
- export templates
- report layouts
- user interface resources
