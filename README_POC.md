# POC: OpenRouter GPT-OSS-120b Structured Outputs

## Quick Start

### 1. Get Your OpenRouter API Key

If you don't have one yet:
1. Go to https://openrouter.ai/
2. Sign up or log in
3. Navigate to "Keys" section
4. Create a new API key

### 2. Set Environment Variable

```bash
# Option 1: OpenRouter API key
export OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE

# Option 2: Use existing GPT_OSS_API_KEY (if already set)
export GPT_OSS_API_KEY=sk-or-v1-YOUR_KEY_HERE
```

### 3. Run POC

```bash
python test_structured_output_poc.py
```

### Expected Output

```
================================================================================
OpenRouter GPT-OSS-120b Structured Output POC
================================================================================
Model: openai/gpt-oss-120b
API: https://openrouter.ai/api/v1/chat/completions
================================================================================
================================================================================
TEST 1: Basic Structured Output (Simple Schema)
================================================================================

✅ Response received:
Raw content: ...".{"greeting":"Hello!","sentiment":"positive","word_count":2}

⚠️  Detected non-JSON prefix in response (Harmony format)
Extracted JSON: {"greeting":"Hello!","sentiment":"positive","word_count":2}

✅ Valid JSON parsed:
{
  "greeting": "Hello!",
  "sentiment": "positive",
  "word_count": 2
}

✅ Schema validation PASSED
   - Greeting: Hello!
   - Sentiment: positive
   - Word Count: 2

... (Tests 2 and 3) ...

================================================================================
POC RESULTS SUMMARY
================================================================================
✅ PASS | Basic Schema
✅ PASS | Verification Schema
✅ PASS | Reasoning + Structured
================================================================================
Total: 3/3 tests passed

🎉 SUCCESS: Native structured outputs WORK with OpenRouter GPT-OSS-120b!
✅ Feasibility CONFIRMED - proceed with Option C implementation
```

## What This POC Tests

### Test 1: Basic Structured Output
- Simple 3-field JSON schema (greeting, sentiment, word_count)
- Validates enum constraints work
- Tests basic JSON extraction from Harmony format

### Test 2: Verification Verdict Schema (IMO Use Case)
- Complex nested schema with 5 required fields
- Issues array with nested objects
- **This is the exact schema needed for IMO verification**
- Tests robust JSON extraction with double-brace prefix

### Test 3: Structured Output + High Reasoning Effort
- Tests compatibility of `response_format` with `extra_body.reasoning.effort`
- **WARNING**: May generate 30K+ tokens with high reasoning (cost: ~$0.02)
- Demonstrates need to use medium/low reasoning for production

## Troubleshooting

### Error: "User not found" (401 Unauthorized)

**Cause**: Invalid or expired API key

**Solution**:
1. Check your API key is correctly set: `echo $OPENROUTER_API_KEY`
2. Verify key starts with `sk-or-v1-`
3. Get a fresh key from https://openrouter.ai/keys

### Error: "No API key found!"

**Cause**: Environment variable not set

**Solution**:
```bash
export OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
```

### Test 3 generates excessive tokens (30K+)

**Cause**: `extra_body.reasoning.effort=high` with `response_format` triggers padding

**Solution**: This is expected behavior, documented in POC_STRUCTURED_OUTPUT_RESULTS.md
- Use `medium` or `low` reasoning for production
- Test 3 is for demonstration only

## Cost Estimate

- **Test 1**: ~$0.0001 (500 tokens)
- **Test 2**: ~$0.0004 (2K tokens)
- **Test 3**: ~$0.02 (34K tokens with high reasoning)

**Total POC cost**: ~$0.021 per run

## Next Steps After Successful POC

If all 3 tests pass:

1. ✅ POC complete - feasibility confirmed
2. ⏭️ Phase 1: Design full verification verdict JSON schema
3. ⏭️ Phase 2: Integrate structured outputs into agent_gpt_oss.py
4. ⏭️ Phase 3: Run 6-test validation suite
5. ⏭️ Phase 4: Production validation (if ≥70% accuracy)

See `POC_STRUCTURED_OUTPUT_RESULTS.md` for detailed analysis and recommendations.
