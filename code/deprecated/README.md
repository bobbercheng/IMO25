# Deprecated Code

This directory contains code that has been superseded by newer implementations.

## agent_rlac.py

**Status:** DEPRECATED (as of 2025-11-25)

**Reason:** All RLAC functionality has been integrated directly into `code/agent_gpt_oss.py` via the `rlac_agent()` function (line ~2053). The standalone agent_rlac.py is no longer maintained and may have bugs that have been fixed in the integrated version.

**Use Instead:** Run `code/agent_gpt_oss.py --use-rlac`

**Migration Guide:**
```bash
# OLD (deprecated):
python code/agent_rlac.py problems/imo01.txt --log output.log

# NEW (current):
./test_rlac.sh problems/imo01.txt output.log
# OR directly:
python code/agent_gpt_oss.py problems/imo01.txt --use-rlac --log output.log
```

**Test Files Affected:**
- `test_rlac_integration.py` - Uses deprecated agent_rlac classes
- `code/test_rlac_fixes.py` - Uses deprecated agent_rlac classes

These test files are also deprecated. New tests should use the integrated RLAC in agent_gpt_oss.py.

**Why Keep This File:**
- Historical reference for development
- Some documentation still references the old architecture
- Test files haven't been migrated yet

**Fixes in agent_gpt_oss.py NOT in agent_rlac.py:**
- P0-P3: Near-success protection, counterexample verification, answer lock, truncation detection
- P5-P9: Answer reconsideration, evidence accumulation, semantic change detection
- BUGFIX: Counterexample truncation (400→2000 chars)
- Progressive reasoning effort for critic attacks
- Defense-first mode with proper answer lock interaction
