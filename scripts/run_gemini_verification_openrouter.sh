#!/bin/bash
# Run Gemini solution verification using OpenRouter

echo "========================================================================"
echo "Verifying Gemini 3 Pro Solution with OpenRouter (High Reasoning)"
echo "========================================================================"
echo ""

# Configure OpenRouter
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME="openai/gpt-oss-120b"
export GPT_OSS_API_KEY=sk-or-...

# Use high reasoning for verification
export GPT_OSS_VERIFICATION_REASONING=high

echo "Configuration:"
echo "  API: OpenRouter"
echo "  Model: openai/gpt-oss-120b"
echo "  Verification Reasoning: high"
echo ""

# Run test
python test_gemini_problem6_verification.py

