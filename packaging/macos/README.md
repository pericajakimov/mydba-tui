# macOS Packaging

This directory contains macOS-specific packaging resources for mydba-tui.

The macOS package is intended for DBA laptops and development environments
where mydba-tui is used as a local terminal database administration tool.

## Purpose

macOS packaging supports:

- local installation
- developer workflows
- application distribution
- dependency management
- version upgrades

## Supported Environments

Initial target:

- macOS
- Apple Silicon (ARM64)

Future support may include:

- Intel macOS (x86_64)
- additional package managers

## Packaging Goals

The macOS package should provide:

- `mydba` executable
- Python runtime dependencies
- default assets
- documentation
- configuration support

## Installation Options

Supported installation methods may include:

### Python Package Installation

Example:
```
pip install mydba-tui
```

### Local Development Installation

Example:
```
git clone <repository>
cd mydba-tui
make install-dev
```

### Standalone Bundle

Future support:

- self-contained application bundle
- embedded Python environment
- offline installation package

## Directory Structure

Expected future structure:
```
packaging/macos/
├── README.md
├── build.sh
├── install.sh
├── uninstall.sh
└── resources/
```


## Configuration Locations

macOS installations should follow standard user application locations.

Possible locations:

Application configuration:
```
~/Library/Application Support/mydba/
```

User configuration:
```
~/.config/mydba/
```

Logs:
```
~/Library/Logs/mydba/
```

## Development Workflow

The typical macOS development workflow:
```
Developer Laptop
|
v
Virtual Environment
|
v
mydba-tui Source Code
|
v
mydba Command
```


## Security Considerations

The package should:

- avoid storing passwords by default
- protect local configuration files
- respect macOS filesystem permissions
- support secure credential providers where available

Supported authentication sources may include:

- interactive password entry
- MySQL option files
- encrypted credential storage

## Future Extensions

This directory may later include:

- Homebrew formula
- signed application bundles
- notarized releases
- universal binaries
- automated update support
