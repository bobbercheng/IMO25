# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is the IMO25 repository containing AI agents for solving International Mathematical Olympiad problems. The system implements a sophisticated mathematical reasoning architecture with asymmetric reasoning patterns, progressive verification, and advanced feedback mechanisms.

### Core Components

**Agent Architecture:**
- `code/agent.py` - Google Gemini 2.5 Pro agent (primary implementation)  
- `code/agent_oai.py` - OpenAI GPT-5 agent with shared prompt infrastructure
- `code/agent_xai.py` - XAI Grok-4-0709 agent with same interface
- `code/agent_gpt_oss.py` - GPT-OSS agent with advanced asymmetric reasoning architecture

**Key Infrastructure:**
- `code/run_parallel.py` - Parallel execution system for running multiple agents simultaneously
- `code/benchmark_loader.py` - Handles IMO benchmark data loading from CSV files
- `code/res2md.py` - JSON result parser for extracting structured outputs
- `monitor_agent_progress.py` - Real-time progress monitoring with early success indicators

### Asymmetric Reasoning System (GPT-OSS Agent)

The most sophisticated agent (`agent_gpt_oss.py`) implements a breakthrough asymmetric reasoning architecture:

**Configuration Variables:**
```python
SOLUTION_REASONING_EFFORT = "low"      # Fast generation, prevents truncation
VERIFICATION_REASONING_EFFORT = "high" # Rigorous checking catches subtle errors  
SELF_IMPROVEMENT_REASONING_EFFORT = "high" # Proactive error detection
```

**Environment Variables:**
- `GPT_OSS_API_URL` - API endpoint (default: http://localhost:30000/v1/chat/completions)
- `GPT_OSS_API_KEY` - API key (optional for local deployments)
- `GPT_OSS_MODEL_NAME` - Model name (default: openai/gpt-oss-120b)
  - Standard models: `openai/gpt-oss-120b`, `gpt-oss-120b`
  - OpenRouter: `openrouter/openai/gpt-oss-120b` (auto-detects API spec)
- `GPT_OSS_SOLUTION_REASONING` - Override solution reasoning effort
- `GPT_OSS_VERIFICATION_REASONING` - Override verification reasoning effort
- `GPT_OSS_SELF_IMPROVEMENT_REASONING` - Override self-improvement reasoning effort

**Key Functions:**
- `build_request_payload()` - Accepts optional reasoning_effort parameter for asymmetric operation
- `verify_solution()` - Uses high reasoning by default for rigorous verification
- `init_explorations()` - Uses high reasoning for self-improvement step
- Memory system with state persistence and resume capability

### RLAC (Reinforcement Learning with Adversarial Critics)

The GPT-OSS agent includes an integrated RLAC mode (`--use-rlac`) that implements adversarial refinement:

**Architecture:**
- **Location:** `code/agent_gpt_oss.py` function `rlac_agent()` (line ~2053)
- **Components:**
  - `code/adversarial_critic.py` - Adversarial attack generation with progressive intensity
  - `code/adversarial_prompts.py` - Attack templates and system prompts
- **DEPRECATED:** `code/deprecated/agent_rlac.py` - Old standalone implementation (no longer maintained)

**Key Features:**
- P0-P3: Near-success protection, counterexample verification, answer lock (auto-disabled during P5), truncation detection
- P5-P9: Answer reconsideration after 4+ BROKEN verdicts, evidence accumulation, semantic change detection
- Progressive critic reasoning: LOW (rounds 0-2) → MEDIUM (rounds 3-6) for efficiency
- Defense-first mode: Generator responds to attacks before generating new solution

**Running RLAC:**
```bash
# Recommended: Use test script
./test_rlac.sh problems/imo01.txt output.log memory.json

# Direct invocation:
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --rlac-max-rounds 15 \
  --rlac-robust-threshold 3 \
  --solution-reasoning low \
  --rlac-critic-reasoning medium \
  --log output.log
```

**RLAC Environment Variables:**
- `RLAC_MAX_ROUNDS` - Maximum adversarial rounds (default: 15)
- `RLAC_ROBUST_THRESHOLD` - Consecutive ROBUST verdicts needed (default: 3)
- `RLAC_STUCK_THRESHOLD` - Failures before strategy shift (default: 4)
- `RLAC_MAX_REGEN` - Maximum regeneration attempts (default: 4)
- `RLAC_SOL_REASONING` - Solution reasoning effort (default: low)
- `RLAC_CRITIC_REASONING` - Critic reasoning effort (default: medium)
- `RLAC_VERIFY_EVERY_N_ROUNDS` - Run verification every N rounds during RLAC (default: 2)
- `RLAC_VERIFY_START_ROUND` - Start verification from round N (default: 0)
- `RLAC_DISABLE_INLINE_VERIFICATION` - Disable in-RLAC verification (default: false)

**P0 Ablation Environment Variables (2025-12-28):**
- `RLAC_DISABLE_P0_FORMAT_VALIDATION` - Disable format validation (default: false)
- `RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION` - Disable near-success protection (default: false)
- `RLAC_DISABLE_P0_ANSWER_LOCK` - Disable answer lock mechanism (default: false)
- `RLAC_DISABLE_ADAPTIVE_TEMPERATURE` - Disable adaptive temperature (default: false, always true for ablation tests)

**In-RLAC Verification (2025-12-07):**
- **FEATURE:** Cooperative verification now runs DURING RLAC rounds (not just after)
- Catches critical errors early (e.g., wrong constructions in FIND problems)
- Default: Verification runs every 2 rounds starting from round 0
- If verification finds "Critical Error" → BROKEN verdict with verification feedback
- If verification finds "Justification Gap" → SUSPICIOUS verdict (acceptable for PROVE)
- If verification passes → continues with normal prompt-based attack
- **Use case:** Problem 1 (FIND) - catches construction errors in round 0-2 instead of missing them
- **Use case:** Problem 2 (PROVE) - allows justification gaps, focuses on method correctness

**Recent Fixes (2025-11-25):**
- **BUGFIX:** Counterexample truncation increased from 400 to 2000 chars (geometry problems need full specifications)
- Answer lock properly disabled during P5/P5.1 reconsideration
- Architecture consolidated: all RLAC code in agent_gpt_oss.py

**P0 Ablation Testing (2025-12-28):**
- **FRAMEWORK:** Systematic ablation testing of P0 features with temperature=0
- **Scripts:** `test_p0_ablation.sh` (full test), `test_p0_ablation_quick.sh` (3 rounds)
- **Features tested:** Format validation, near-success protection, answer lock, adaptive temperature
- **Purpose:** Identify which P0 features are critical vs. efficiency improvements
- **Documentation:** See `docs/P0_ABLATION_GUIDE.md` for detailed guide

## Common Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys for different providers
export GOOGLE_API_KEY=your_google_api_key
export OPENAI_API_KEY=your_openai_api_key
export XAI_API_KEY=your_xai_api_key
export GPT_OSS_API_KEY=your_gpt_oss_api_key  # Optional for local deployments

# GPT-OSS Configuration
export GPT_OSS_API_URL=http://localhost:30000/v1/chat/completions  # API endpoint
export GPT_OSS_MODEL_NAME=openai/gpt-oss-120b  # Model name (default)

# Using OpenRouter (faster for medium/high reasoning)
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=your_openrouter_api_key
```

### OpenRouter Support

The GPT-OSS agent supports **OpenRouter API** for faster inference with medium/high reasoning modes.

**Key Feature**: Automatic API spec detection based on model name prefix.

**How it works**:
- Model names with prefixes (e.g., `openrouter/`, `anthropic/`) → reasoning goes in `extra_body`
- Standard models (`openai/gpt-oss-120b` or no prefix) → reasoning at top level

**Example configurations**:

```bash
# Local deployment (standard API)
export GPT_OSS_API_URL=http://localhost:30000/v1/chat/completions
export GPT_OSS_MODEL_NAME=openai/gpt-oss-120b
# Payload: {"reasoning": {"effort": "high"}, ...}

# OpenRouter (automatically uses extra_body)
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=sk-or-...
# Payload: {"extra_body": {"reasoning": {"effort": "high"}}, ...}
```

**Why use OpenRouter**:
- ✅ Faster inference for medium/high reasoning modes
- ✅ No local deployment needed
- ✅ Pay-per-use pricing
- ✅ Automatic failover and load balancing

**Running with OpenRouter**:
```bash
# Set environment variables
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=your_openrouter_api_key

# Run RLAC with medium reasoning (recommended for IMO problems)
RLAC_SOL_REASONING=medium ./test_rlac.sh problems/imo01.txt
```

### Running Single Agents
```bash
# Google Gemini agent
python code/agent.py problems/imo01.txt --log output.log

# OpenAI GPT-5 agent  
python code/agent_oai.py problems/imo01.txt --log output_oai.log

# XAI Grok-4 agent
python code/agent_xai.py problems/imo01.txt --log output_xai.log

# GPT-OSS agent with asymmetric reasoning
python code/agent_gpt_oss.py problems/imo01.txt --log output_gpt_oss.log

# GPT-OSS with custom reasoning levels
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --self-improvement-reasoning high \
  --log output_custom.log
```

### Parallel Execution
```bash
# Run 10 agents in parallel with 5-minute timeout
python code/run_parallel.py problems/imo01.txt -n 10 -t 300

# Exit immediately on first success  
python code/run_parallel.py problems/imo01.txt -n 20 -e

# Use specific agent variant
python code/run_parallel.py problems/imo01.txt -n 10 -a agent_gpt_oss.py

# Custom log directory and additional prompts
python code/run_parallel.py problems/imo01.txt -n 15 \
  -d logs/p1_run \
  -o "focus_on_geometry,use_induction"
```

### Result Analysis
```bash
# Extract final JSON result from log
python code/res2md.py logs/agent_output.log

# Monitor agent progress in real-time
python monitor_agent_progress.py logs/agent_output.log --interval 60

# Analyze multiple log files
python code/res2md.py run_log_gpt_oss/*.log
```

### Testing and Validation
```bash
# Validate existing solution with high reasoning verification
python code/agent_gpt_oss.py problems/imo01.txt \
  --resume-from memory_state.json \
  --verification-reasoning high \
  --log validation_test.log

# Test asymmetric approach from fresh start
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --log asymmetric_fresh.log
```

### P0 Ablation Testing
```bash
# Full ablation test (10 rounds, all P0 feature combinations)
./test_p0_ablation.sh problems/imo01.txt 10

# Quick validation test (3 rounds for fast testing)
./test_p0_ablation_quick.sh problems/imo01.txt

# Test specific P0 feature disable
RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION=true ./test_rlac.sh problems/imo01.txt

# Results include:
# - Individual test logs for each configuration
# - Summary files with key metrics
# - Markdown report with comparative analysis

# View results
cat ablation_results_*/ablation_report.md
```

## Key Architectural Patterns

### Agent Initialization
All agents follow this pattern:
1. API key validation and configuration loading
2. Problem file reading and preprocessing  
3. Prompt construction with step1_prompt, self_improvement_prompt, verification prompts
4. Multi-iteration solving loop with verification and correction
5. Memory/state persistence for resume capability

### Prompt System Architecture
Shared across OpenAI/XAI/GPT-OSS agents:
- `step1_prompt` - Initial problem solving approach
- `self_improvement_prompt` - Self-review and improvement step  
- `check_verification_prompt` - Solution verification request
- `correction_prompt` - Error correction guidance
- `verification_system_prompt` - System prompt for verification
- `verification_remider` - Additional verification instructions

### Memory and Resume System
GPT-OSS agent implements sophisticated state management:
- JSON state files with iteration history, solution attempts, error tracking
- Resume capability preserves reasoning effort configurations
- Memory includes truncation detection, verification scores, and learning progression

### Success Detection
The system identifies successful solutions by searching for:
- "Found a correct solution in run" phrase in logs
- Successful verification passes in memory state
- Progressive score improvements toward acceptance threshold

### Progress Monitoring
Real-time monitoring tracks:
- Iteration count and speed
- Truncation events and format compliance
- Verification pass rates and error patterns
- Stuck pattern detection and recovery attempts
- Cost tracking and efficiency metrics

## File Structure and Data Flow

### Problem Files
- `problems/imo01.txt` through `problems/imo05.txt` - IMO 2025 problems
- Plain text format with mathematical problem statements

### Log Directories  
- `run_logs/` - Google Gemini runs
- `run_logs_gpt5/` - OpenAI GPT-5 runs  
- `run_logs_grok4/` - XAI Grok-4 runs
- `run_log_gpt_oss/` - GPT-OSS runs with memory state files

### Benchmark Data
- `imobench/` - CSV files for answer/grading/proof benchmarks
- `papers/` - Research papers documenting approaches and results

## Development Guidelines

### Configuration Management
The GPT-OSS agent supports environment-based configuration. Always check current config on startup:
```
[CONFIG] GPT_OSS API URL: http://localhost:30000/v1/chat/completions  
[CONFIG] Solution Reasoning Effort: low
[CONFIG] Self-Improvement Reasoning Effort: high
[CONFIG] Verification Reasoning Effort: high
```

### Error Handling Patterns
- Streaming response handling with repetition detection  
- Content truncation prevention via reasoning effort management
- Stuck pattern detection and strategy switching
- Graceful degradation when verification fails

### Asymmetric Reasoning Implementation
When modifying GPT-OSS agent reasoning:
1. **Generation tasks** - Use SOLUTION_REASONING_EFFORT (default: "low") for efficiency
2. **Verification tasks** - Use VERIFICATION_REASONING_EFFORT (default: "high") for rigor  
3. **Self-improvement** - Use SELF_IMPROVEMENT_REASONING_EFFORT (default: "high") for proactive error detection

### Memory System Integration
State persistence includes:
- Current reasoning effort configurations
- Solution iteration history and verification results
- Error patterns and stuck detection metrics
- Progressive scoring and acceptance thresholds

### API Compatibility
All agents maintain OpenAI-compatible API interfaces for drop-in replacement capability. The GPT-OSS agent extends this with reasoning effort parameters specific to its advanced architecture.

## Performance Expectations

Based on extensive testing documented in technical analysis:
- **Baseline Success Rate**: Google Gemini/OpenAI agents achieve variable success (0-40%)
- **GPT-OSS Asymmetric**: Target 40-60% success rate with 95% confidence
- **Cost Efficiency**: $12 per problem (GPT-OSS) vs $75+ for failed high/high approaches
- **Iteration Speed**: 17× faster with low reasoning generation (1.3 vs 23 hours)
- **Error Detection**: 80% proactive error detection with high reasoning self-improvement

The asymmetric reasoning approach represents a paradigm shift from binary reasoning switches to curriculum learning for AI mathematical reasoning, enabling systematic improvement rather than binary success/failure outcomes.