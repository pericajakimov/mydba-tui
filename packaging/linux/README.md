# Linux Packaging

This directory contains Linux-specific packaging resources for mydba-tui.

The primary target environment is Linux-based DBA tooling servers, especially
offline or restricted environments where external package downloads may not be
available.

## Purpose

Linux packaging supports:

- application distribution
- offline installation
- dependency bundling
- deployment automation
- environment-specific installation workflows

## Supported Environments

Initial target:

- Ubuntu Linux
- x86_64 architecture

Future support may include:

- ARM64 Linux
- Debian-based distributions
- Red Hat Enterprise Linux compatible systems

## Packaging Goals

The Linux package should provide:

- `mydba` executable
- Python runtime dependencies
- configuration directories
- default assets
- documentation
- upgrade capability

## Offline Installation

The package should support installation without internet access.

Expected workflow:
```
Build Machine
|
v
Offline Package Bundle
|
v
DBA Tooling Server
|
v
mydba
```

The build process should collect:

- Python wheels
- application package
- required assets
- installation scripts
- checksums

## Directory Structure

Expected future structure:
```
packaging/linux/
├── README.md
├── build.sh
├── install.sh
├── uninstall.sh
├── systemd/
└── files/
```


## Installation Principles

The installer should:

- avoid modifying system Python packages
- use an isolated virtual environment
- preserve user configuration
- support multiple environments
- provide clear installation logs

## Configuration Locations

Linux installations should follow standard conventions.

Possible locations:

System-wide:
```
/etc/mydba/
```

Application:
```
/opt/mydba/
```


User data:
```
~/.config/mydba/
~/.local/share/mydba/
```


## Security Considerations

Packaging should consider:

- file permissions
- credential storage protection
- configuration ownership
- executable permissions
- auditability

Passwords should not be stored by default.

Supported authentication sources may include:

- interactive password entry
- MySQL option files
- encrypted credential stores

## Future Extensions

This directory may later include:

- `.deb` package generation
- RPM package support
- systemd service definitions
- automated upgrade scripts
- checksum verification
- enterprise deployment helpers
