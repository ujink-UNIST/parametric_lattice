# Agents

## Shell preference

- Prefer **bash** for running commands in this repo (avoid PowerShell unless explicitly required).

## Python environment

This project uses the Conda environment **`param_lattice`**.

- When running any Python code/commands/tests for this repo, use this environment.

### PowerShell activation (if needed)

```powershell
& "C:\ProgramData\miniconda3\shell\condabin\conda-hook.ps1"
conda activate param_lattice
```

### Bash activation (preferred)

```bash
conda activate param_lattice
# If conda isn't initialized in bash, source conda.sh first (path may vary), e.g.:
# source /c/ProgramData/miniconda3/etc/profile.d/conda.sh
# conda activate param_lattice
```
