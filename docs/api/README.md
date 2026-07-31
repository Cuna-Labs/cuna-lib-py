# API reference generation status

The release API reference must be generated with `griffe==2.1.0`, `extensions = []`, from the
clean candidate wheel. Generation is currently fail-closed because PRD-091 requires four
normalized errors as root imports while the accepted PRD-058 root manifest keeps errors in
`runa.errors`. No release reference is rendered until that prerequisite is reconciled.
