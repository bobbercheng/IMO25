# Infrastructure Setup Guide

**Date**: 2025-12-01

This guide helps set up the GPT-OSS API infrastructure for running RLAC tests.

---

## Quick Start

### Option 1: Local GPT-OSS Server (Recommended for Development)

**Check if server is running**:
```bash
curl -s http://localhost:30000/v1/models
```

**If connection refused**, start the server:
```bash
# Method 1: Systemd (if configured)
sudo systemctl start gpt-oss-server
sudo systemctl status gpt-oss-server

# Method 2: Docker (if using container)
docker start gpt-oss-server
docker ps | grep gpt-oss

# Method 3: Direct python (if local deployment)
cd /path/to/gpt-oss
python -m gpt_oss.server --port 30000
```

**Verify server is responding**:
```bash
curl -s http://localhost:30000/v1/models | jq .
```

Expected response:
```json
{
  "object": "list",
  "data": [
    {
      "id": "openai/gpt-oss-120b",
      "object": "model",
      "created": 1234567890,
      "owned_by": "openai"
    }
  ]
}
```

---

### Option 2: OpenRouter (Recommended for Production)

**Advantages**:
- ✅ No local server maintenance
- ✅ Faster inference for medium/high reasoning
- ✅ Pay-per-use pricing
- ✅ Automatic failover

**Setup**:
```bash
# 1. Set OpenRouter API credentials
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=sk-or-v1-your-api-key-here

# 2. Verify configuration
env | grep GPT_OSS

# 3. Test connection
curl -s https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $GPT_OSS_API_KEY" | jq .
```

**Run RLAC test**:
```bash
# Test will automatically use OpenRouter
RLAC_SOL_REASONING=medium RLAC_MAX_ROUNDS=30 \
  ./test_rlac.sh problems/imo03.txt
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `GPT_OSS_API_URL` | API endpoint | `http://localhost:30000/v1/chat/completions` | Local or OpenRouter |
| `GPT_OSS_MODEL_NAME` | Model identifier | `openai/gpt-oss-120b` | Standard or `openrouter/...` |
| `GPT_OSS_API_KEY` | API key | None (optional for local) | Required for OpenRouter |
| `GPT_OSS_SOLUTION_REASONING` | Generator reasoning | `low` | `low`, `medium`, `high` |
| `GPT_OSS_VERIFICATION_REASONING` | Verifier reasoning | `high` | `low`, `medium`, `high` |
| `GPT_OSS_SELF_IMPROVEMENT_REASONING` | Self-improve reasoning | `high` | `low`, `medium`, `high` |

### RLAC-Specific Variables

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `RLAC_MAX_ROUNDS` | Maximum adversarial rounds | 15 | 1-50 |
| `RLAC_ROBUST_THRESHOLD` | Consecutive ROBUST needed | 3 | 1-10 |
| `RLAC_STUCK_THRESHOLD` | Failures before pivot | 4 | 2-10 |
| `RLAC_MAX_REGEN` | Max regeneration attempts | 4 | 1-10 |
| `RLAC_SOL_REASONING` | Solution reasoning (RLAC) | `low` | `low`, `medium`, `high` |
| `RLAC_CRITIC_REASONING` | Critic reasoning (RLAC) | `medium` | `low`, `medium`, `high` |

---

## Troubleshooting

### Issue: Connection Refused (localhost:30000)

**Symptoms**:
```
Error during API request: HTTPConnectionPool(host='localhost', port=30000):
Max retries exceeded with url: /v1/chat/completions
(Caused by NewConnectionError: Failed to establish a new connection: [Errno 111] Connection refused)
```

**Diagnosis**:
```bash
# Check if port is listening
sudo netstat -tlnp | grep 30000
# OR
sudo lsof -i :30000

# Check server logs
sudo journalctl -u gpt-oss-server -n 50 -f
# OR
docker logs gpt-oss-server --tail 50 -f
```

**Solutions**:
1. **Start local server** (see Option 1 above)
2. **Switch to OpenRouter** (see Option 2 above)
3. **Check firewall**: `sudo ufw status`
4. **Verify server configuration**: Check `/etc/gpt-oss/config.yaml` or similar

---

### Issue: Authentication Failed (OpenRouter)

**Symptoms**:
```
Error: 401 Unauthorized
{"error": {"message": "Invalid API key", "type": "invalid_request_error"}}
```

**Solutions**:
1. **Verify API key**:
   ```bash
   echo $GPT_OSS_API_KEY
   # Should start with "sk-or-v1-"
   ```

2. **Check key validity**:
   ```bash
   curl -s https://openrouter.ai/api/v1/auth/key \
     -H "Authorization: Bearer $GPT_OSS_API_KEY" | jq .
   ```

3. **Regenerate key**: Visit https://openrouter.ai/keys

---

### Issue: Model Not Found

**Symptoms**:
```
Error: 404 Not Found
{"error": {"message": "Model not found", "type": "invalid_request_error"}}
```

**Solutions**:
1. **List available models**:
   ```bash
   curl -s https://openrouter.ai/api/v1/models \
     -H "Authorization: Bearer $GPT_OSS_API_KEY" | jq '.data[] | .id'
   ```

2. **Use correct model name**:
   ```bash
   # For OpenRouter
   export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b

   # For local server
   export GPT_OSS_MODEL_NAME=openai/gpt-oss-120b
   ```

---

### Issue: Timeout Errors

**Symptoms**:
```
Error: Request timeout after 300 seconds
```

**Solutions**:
1. **Check reasoning level** (high reasoning is slow):
   ```bash
   # Use medium for faster inference
   export RLAC_SOL_REASONING=medium
   export RLAC_CRITIC_REASONING=medium
   ```

2. **Increase timeout** (if needed):
   ```bash
   # Edit code/agent_gpt_oss.py
   # Line ~2300: timeout = 600  # Increase from 300
   ```

3. **Monitor server load**:
   ```bash
   # Local server
   htop
   nvidia-smi  # If using GPU

   # OpenRouter
   # Check status: https://status.openrouter.ai/
   ```

---

## Performance Tuning

### Reasoning Level Selection

| Use Case | Solution | Critic | Self-Improve | Cost | Speed |
|----------|----------|--------|--------------|------|-------|
| **Development** | low | low | medium | $ | Fast |
| **Testing** | low | medium | high | $$ | Medium |
| **Production** | low | medium | high | $$ | Medium |
| **Hard Problems** | medium | medium | high | $$$ | Slow |
| **Maximum Quality** | medium | high | high | $$$$ | Very Slow |

**Recommended for IMO Problems**:
```bash
export RLAC_SOL_REASONING=medium      # Balance speed/quality
export RLAC_CRITIC_REASONING=medium   # Effective attacks
# Self-improvement uses GPT_OSS_SELF_IMPROVEMENT_REASONING=high by default
```

### Cost Optimization

**Estimated costs** (OpenRouter):
- **Low reasoning**: ~$0.50 per 1M tokens
- **Medium reasoning**: ~$2.00 per 1M tokens
- **High reasoning**: ~$8.00 per 1M tokens

**Typical IMO problem**:
- Solution tokens: 10K-30K
- Critic tokens: 5K-15K
- Total per round: 15K-45K tokens
- 15 rounds average: 225K-675K tokens

**Cost per problem**:
- low/medium: $15-25
- medium/medium: $20-30
- medium/high: $50-75

---

## Verification Tests

### Test Local Server
```bash
# Simple ping
curl -s http://localhost:30000/v1/models

# Full chat completion
curl -s http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-120b",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "reasoning": {"effort": "low"}
  }' | jq .
```

### Test OpenRouter
```bash
# List models
curl -s https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $GPT_OSS_API_KEY" | jq .

# Full chat completion
curl -s https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $GPT_OSS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openrouter/openai/gpt-oss-120b",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "extra_body": {"reasoning": {"effort": "low"}}
  }' | jq .
```

### Test RLAC Pipeline
```bash
# Quick test with Problem 1 (usually succeeds in 10 rounds)
RLAC_SOL_REASONING=medium RLAC_MAX_ROUNDS=15 \
  ./test_rlac.sh problems/imo01.txt test.log test.json

# Check for success
grep "Found a correct solution" test.log
```

---

## Common Workflows

### Workflow 1: Development (Fast Iteration)
```bash
# Use local server with low reasoning
export GPT_OSS_API_URL=http://localhost:30000/v1/chat/completions
export GPT_OSS_MODEL_NAME=openai/gpt-oss-120b
export RLAC_SOL_REASONING=low
export RLAC_CRITIC_REASONING=low
export RLAC_MAX_ROUNDS=5

# Quick test
./test_rlac.sh problems/imo01.txt
```

### Workflow 2: Production (Quality)
```bash
# Use OpenRouter with medium reasoning
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=sk-or-v1-your-key
export RLAC_SOL_REASONING=medium
export RLAC_CRITIC_REASONING=medium
export RLAC_MAX_ROUNDS=30

# Full test
./test_rlac.sh problems/imo02.txt
```

### Workflow 3: Benchmark (All Problems)
```bash
# Configure OpenRouter (recommended)
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=sk-or-v1-your-key
export RLAC_SOL_REASONING=medium
export RLAC_CRITIC_REASONING=medium

# Run all problems
for i in {1..5}; do
  echo "Testing Problem $i..."
  RLAC_MAX_ROUNDS=30 ./test_rlac.sh \
    problems/imo0${i}.txt \
    test_rlac_log/imo0${i}_output.log \
    test_rlac_log/imo0${i}_memory.json
done

# Check results
grep -h "Found a correct solution\|TIMEOUT" test_rlac_log/imo0*_output.log
```

---

## Monitoring and Debugging

### Real-time Progress Monitoring
```bash
# Monitor log file in real-time
tail -f test_rlac_log/test_rlac_output.log | grep -E "(ROUND|ROBUST|BROKEN|SUSPICIOUS)"

# Monitor with structured output
python monitor_agent_progress.py test_rlac_log/test_rlac_output.log --interval 60
```

### Debug Logging
```bash
# Enable verbose logging
export RLAC_VERBOSE=1

# Run with debug output
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --log debug_output.log \
  --verbose
```

### Memory State Inspection
```bash
# View current state
cat test_rlac_log/test_rlac_memory.json | jq .

# Extract specific fields
cat test_rlac_log/test_rlac_memory.json | jq '.current_round'
cat test_rlac_log/test_rlac_memory.json | jq '.consecutive_robust'
cat test_rlac_log/test_rlac_memory.json | jq '.answer'
```

---

## Getting Help

### Check Server Status
- **Local**: `systemctl status gpt-oss-server`
- **OpenRouter**: https://status.openrouter.ai/

### Review Logs
- **Agent logs**: `test_rlac_log/*.log`
- **Server logs**: `/var/log/gpt-oss/` or `docker logs gpt-oss-server`
- **System logs**: `journalctl -u gpt-oss-server`

### Documentation
- **CLAUDE.md**: Architecture and usage guide
- **PHASE_0_1_VALIDATION_STATUS.md**: Implementation status
- **PROBLEM_*_ANALYSIS.md**: Detailed problem analyses

### Support
- **Issues**: https://github.com/bobbercheng/IMO25/issues
- **Discussions**: https://github.com/bobbercheng/IMO25/discussions

---

**Last Updated**: 2025-12-01
**Maintainer**: bobbercheng
