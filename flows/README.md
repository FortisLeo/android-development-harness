# Device flows

Put repeatable UI flows here. Maestro is optional and intentionally not required by the base harness.

Install on macOS if desired:

```bash
brew install maestro
```

Run a flow:

```bash
maestro test flows/login.yaml
```

Keep selectors stable: resource IDs and content descriptions are preferred over coordinates. Use `scripts/accessibility_check.py` against a collected `accessibility.xml` for semantic assertions.
