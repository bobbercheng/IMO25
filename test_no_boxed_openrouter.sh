#!/bin/bash
# Test no boxed format with OpenRouter API
# Usage: ./test_no_boxed_openrouter.sh

set -e

echo "=================================================="
echo "Testing No Boxed Format with OpenRouter"
echo "=================================================="
echo ""

# Check if API key is set
if [ -z "$GPT_OSS_API_KEY" ]; then
    echo "ERROR: GPT_OSS_API_KEY environment variable not set"
    echo ""
    echo "Please set your OpenRouter API key:"
    echo "  export GPT_OSS_API_KEY=sk-or-v1-..."
    echo ""
    exit 1
fi

# Configure OpenRouter settings
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openai/gpt-oss-120b

echo "Configuration:"
echo "  API URL: $GPT_OSS_API_URL"
echo "  Model: $GPT_OSS_MODEL_NAME"
echo "  API Key: ${GPT_OSS_API_KEY:0:10}..."
echo ""
echo "=================================================="
echo ""

# Run LLM integration test
RUN_LLM_TESTS=1 python test_no_boxed_format.py TestNoBoxedFormat.test_llm_generates_correct_format

echo ""
echo "=================================================="
echo "Test completed!"
echo "=================================================="
