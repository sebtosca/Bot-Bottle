import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")


# WhatsApp Cloud API configuration
# Support both standard and alternative variable names for flexibility
WHATSAPP_ACCOUNT_ID = os.environ.get("WHATSAPP_ACCOUNT_ID") or os.environ.get("WHATSAPP_BUSINESS_ID")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or os.environ.get("WHATSAPP_NUMBER")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN") or os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")  # For webhook verification

# LLM Provider configuration
# Using Mistral AI for cloud inference
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mistral")

# Mistral AI API configuration
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_MODEL_NAME = os.environ.get("MISTRAL_MODEL_NAME", "ministral-3b")

