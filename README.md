# Variables

> [!IMPORTANT]
> If you're watching this page from [the repo in GitHub](https://github.com/radium226/variables), please note it's only a read-only mirror from [the repo in SourceHut](https://git.sr.ht/~radium226/variables). 
> You can follow the tickets in [this tracker](https://todo.sr.ht/~radium226/variables).


## Overview

The `variables` tool helps you to store (sensitive or not) variables next to your code  in a standardized format. 

Those variables can the be exported to multiple formats ([ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/), [.env](https://www.dotenv.org/docs/security/env.html), etc.) or directly injected as environment variables.


## Usage

### File Format

Variables are stored in YAML files with the following structure:

```yaml
---
variables:
- name: DATABASE_URL
  value: postgres://localhost:5432/mydb
  visibility: plain
  type: text
- name: API_KEY
  value: encrypted:YWJjZGVm...
  visibility: secret
  type: text
- name: CONFIG
  value: '{"setting": "value"}'
  visibility: secret
  type: file
```

- `visibility`: `plain` (unencrypted) or `secret` (encrypted)
- `type`: `text` (passed as env var) or `file` (written to temp file, path passed as env var)

### Commands

#### Encrypt secrets

```bash
variables encrypt secrets.yaml
```

#### Decrypt secrets

```bash
variables decrypt secrets.yaml
```

#### Execute a command with variables

```bash
variables exec -v secrets.yaml -- my-command --config {{ CONFIG }}
```

Variables are injected as environment variables. Use `{{ VAR_NAME }}` for Jinja2 interpolation (useful for `file` type variables).

#### Export variables

```bash
# Export to bash
variables export -t bash secrets.yaml

# Export to Kubernetes manifests
variables export -t kubectl -c name=my-app secrets.yaml
```

#### Set a variable

```bash
# Set a plain text variable
variables set -v secrets.yaml MY_VAR "my-value"

# Set a secret (auto-encrypted)
variables set -v secrets.yaml --visibility secret API_KEY "secret-value"

# Read value from stdin
echo "secret" | variables set -v secrets.yaml PASSWORD -
```

#### Check encryption

```bash
variables check secrets.yaml
```

### Override Files

Variables can be overridden by a secondary file. When loading `secrets.yaml`, the tool automatically looks for `secrets.local.yaml` and merges variables from it (override takes precedence).

```bash
# Uses secrets.yaml + secrets.local.yaml (default)
variables exec -v secrets.yaml -- env

# Disable override
variables exec --no-override -v secrets.yaml -- env

# Use custom suffix (looks for secrets.dev.yaml)
variables exec --override-suffix dev -v secrets.yaml -- env
```

This is useful for local development overrides that shouldn't be committed to version control.

### Backend Configuration

By default, the `age` backend is used for encryption. You can configure it with:

```bash
# Use a specific backend
variables -b age encrypt secrets.yaml

# Pass backend configuration
variables -b age -c key=/path/to/key.txt encrypt secrets.yaml
```

