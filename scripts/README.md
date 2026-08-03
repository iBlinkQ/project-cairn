# Scripts

## macOS / Linux

Project Cairn scripts are primarily Bash scripts.

Example:

```bash
bash ./scripts/notion-preflight.sh --db "<database_id>"
```

## Windows

Windows users should prefer WSL.

Check the environment first:

```powershell
pwsh ./scripts/check-windows-env.ps1
```

Run an existing Bash script through the PowerShell wrapper:

```powershell
pwsh ./scripts/run-cairn-script.ps1 notion-preflight --db "<database_id>"
```

## Execution priority

1. WSL
2. Git Bash
3. Native PowerShell scripts may be added later

## Important note

The PowerShell wrapper does not replace the Bash scripts. It only detects WSL or Git Bash and forwards the call to the existing `.sh` script.
