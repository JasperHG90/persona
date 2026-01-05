# How to Configure Persona

This guide explains how to configure Persona to suit your environment and storage preferences.

## Prerequisites

- You have installed Persona.
- You have initialized Persona using `persona init`.

## Configuration Methods

Persona can be configured using three methods, in order of precedence (highest to lowest):

1.  **CLI Overrides:** Using the `--set` or `-s` flag.
2.  **Configuration File:** The `~/.persona.config.yaml` file.
3.  **Environment Variables:** Using the `PERSONA_` prefix.

## Method 1: Editing the Configuration File

The primary way to configure Persona is by editing the YAML configuration file located at `~/.persona.config.yaml`.

1.  Open the configuration file in your preferred text editor.
2.  Modify the fields as needed.

### Standard Configuration Structure

```yaml
# The root directory for storing data
root: /home/user/.local/share/persona

# File storage backend configuration
file_store:
  type: local
  # Optional: Override the root for file storage
  # root: /path/to/files

# Metadata storage backend configuration
meta_store:
  type: duckdb
  # Optional: Override the root for metadata storage
  # root: /path/to/metadata
```

## Method 2: Using Environment Variables

You can override any configuration setting using environment variables. This is useful for temporary changes or containerized environments.

The format is `PERSONA_<KEY>` or `PERSONA_<SECTION>__<KEY>` (using double underscores for nested keys).

### Examples

*   **Set the root directory:**
    ```bash
    export PERSONA_ROOT="/custom/path/to/persona"
    ```

*   **Set the file store type:**
    ```bash
    export PERSONA_FILE_STORE__TYPE="local"
    ```

## Method 3: Using CLI Overrides

For single-command overrides, use the `--set` or `-s` option.

### Examples

*   **Override the root directory for a single command:**
    ```bash
    persona --set root=/tmp/persona roles list
    ```

*   **Override nested configuration:**
    ```bash
    persona --set meta_store.type=duckdb roles list
    ```

## Common Configuration Tasks

### Changing the Storage Location

To change where Persona stores roles and skills, modify the `root` parameter.

**In `~/.persona.config.yaml`:**

```yaml
root: /new/storage/location
```

**Using Environment Variable:**

```bash
export PERSONA_ROOT="/new/storage/location"
```

### Verifying Your Configuration

To verify your current configuration, you can use the `config` command group.

1.  **View the Root Directory:**
    ```bash
    persona config root_dir
    ```

2.  **View the Data Directory:**
    ```bash
    persona config data_dir
    ```
