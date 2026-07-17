# Packaging

## Purpose

The Packaging strategy defines how `mydba` is built, distributed, installed, and maintained across supported platforms.

The primary deployment targets are shared Ubuntu tooling servers and individual macOS laptops used by MySQL DBAs.

The packaging approach must support environments without Internet access.

---

# Design Goals

The packaging system should:

- Produce self-contained releases.
- Support offline installation.
- Minimize installation complexity.
- Be reproducible.
- Produce identical behavior across supported platforms.
- Keep the executable simple for end users.

---

# Supported Platforms

The initial supported platforms are:

- Ubuntu 24.04 LTS
- macOS

Future Linux distributions may be supported if required.

Windows is not a target platform.

---

# Development Workflow

Development is expected to take place primarily on macOS.

Typical workflow:

```
Mac Laptop
    ↓

Develop
    ↓

Test
    ↓

Commit

    ↓

Ubuntu Build VM

    ↓

Create Release Bundle

    ↓

Deploy to Tooling Servers
```

Cross-platform compatibility should be verified during the Ubuntu build process.

---

# Build Environment

Official release packages should be built on Ubuntu.

Building on the target operating system minimizes compatibility issues and ensures that release artifacts match the production environment.

macOS builds should also be produced for local workstation users.

---

# Offline Installation

Offline installation is a primary requirement.

Production tooling servers may not have Internet access.

Release packages should therefore contain:

- Application code
- Python runtime (if required by the chosen packaging approach)
- Third-party dependencies
- Static resources

Installation must not require downloading additional packages.

---

# Distribution Format

The exact packaging technology is an implementation detail.

Regardless of implementation, the delivered package should:

- Be self-contained.
- Require minimal installation steps.
- Avoid dependency conflicts.
- Behave consistently across installations.

---

# Executable

The installed executable is named:

```
mydba
```

The executable should behave like other standard MySQL command-line tools.

Examples:

```
mydba

mydba -h db.example.com

mydba -u admin

mydba -D test
```

Command-line compatibility is provided for familiarity and convenience, while interactive profile selection remains the primary workflow.

---

# Repository Structure

Repository name:

```
mydba-tui
```

Python package:

```
mydba_tui
```

Executable:

```
mydba
```

These names remain consistent throughout the project.

---

# Dependency Management

All required Python dependencies should be pinned.

Releases must be reproducible.

The build process should always generate the same output from the same source revision.

---

# Versioning

The project follows semantic versioning.

```
MAJOR.MINOR.PATCH
```

Examples:

```
0.1.0
0.2.0
1.0.0
```

Major versions indicate breaking changes.

Minor versions introduce new functionality.

Patch versions contain bug fixes only.

---

# Release Contents

Each release should include:

- Executable package
- Release notes
- License (when applicable)
- Version information
- Documentation
- Checksums

Documentation generated as part of the bootstrap repository should accompany official releases whenever practical.

---

# Installation

Installation should be straightforward.

The preferred workflow is:

1. Copy the release package to the target machine.
2. Extract or install it.
3. Run `mydba`.

No manual dependency installation should be required.

---

# Upgrades

Upgrading should preserve:

- Configuration
- Connection profiles
- User-defined rules
- Themes

Application binaries may be replaced independently of user configuration.

---

# Configuration Separation

Application configuration must remain outside the installation directory.

This ensures that reinstalling or upgrading the application does not overwrite user settings.

---

# Logging

Application logs and SQL logs must also be stored outside the installation directory.

This allows upgrades without losing diagnostic information.

---

# Build Automation

The build process should be fully automated.

Typical build steps include:

- Dependency installation
- Static analysis
- Unit tests
- Packaging
- Release artifact generation

The same build process should be usable both locally and in CI environments.

---

# Future Distribution

The project is initially intended for internal use.

If released publicly in the future, packaging should support standard distribution channels while preserving the ability to create offline release bundles.

The packaging architecture should not assume a specific distribution mechanism.

---

# Design Principles

The Packaging strategy follows these principles:

- Offline-first.
- Reproducible builds.
- Minimal installation effort.
- Clear separation of binaries and configuration.
- Consistent behavior across supported platforms.
- Familiar command-line experience.
- Easy deployment to shared tooling servers.
