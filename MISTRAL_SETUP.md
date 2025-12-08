# Mistral AI Setup Guide

## ✅ What's Already Done

- Configuration system ready
- Mistral AI integration code added

## Step 1: Install Mistral AI Package

Install the official Mistral AI Python SDK:

```bash
pip install mistralai
```

## Step 2: Get Your Mistral AI API Key

1. Go to: https://console.mistral.ai/
2. Sign up or log in (free account available)
3. Navigate to **API Keys** section
4. Click **Create API Key**
5. Copy your API key

## Step 3: Add API Key to .env File

Add these lines to your `.env` file:

```bash
MISTRAL_API_KEY=your_actual_api_key_here
LLM_PROVIDER=mistral
MISTRAL_MODEL_NAME=ministral-3b
```

**Important:** 
- Replace `your_actual_api_key_here` with your actual API key from Step 2
- `LLM_PROVIDER` defaults to `mistral` (no need to set it unless you want to override)
- `MISTRAL_MODEL_NAME` is optional (defaults to `ministral-3b`)

## Step 4: Verify Setup

Test the integration:

```bash
python tests/test_mistral.py
```

You should see a successful response from Mistral AI.

## Configuration Options

### Mistral AI Settings
- `MISTRAL_API_KEY`: Your Mistral AI API key (required)
- `MISTRAL_MODEL_NAME`: Model to use (default: `ministral-3b`)
  - Available models: `ministral-3b`, `mistral-small`, `mistral-medium`, `mistral-large`, etc.
- `LLM_PROVIDER`: Set to `"mistral"` to use Mistral AI (default: `"mistral"`)

## Expected Performance

- **Mistral AI**: Fast inference with Ministral 3B model
- Response times vary based on model and load

## Troubleshooting

### "MISTRAL_API_KEY is required"
- Make sure you added `MISTRAL_API_KEY=...` to your `.env` file
- Restart your Flask server after adding the key

### "mistralai package not installed"
- Run: `pip install mistralai`

### "Invalid LLM_PROVIDER"
- Make sure `LLM_PROVIDER` is set to `"mistral"` (lowercase)

## Free Tier Limits

Mistral AI offers free tier access:
- Check https://console.mistral.ai/ for current limits and pricing
- Ministral 3B is available at competitive pricing

