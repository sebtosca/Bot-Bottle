# BotBottle

WhatsApp bot for bottle recycling gamification with character interactions.

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL database
- WhatsApp Cloud API credentials
- Mistral AI API key (optional, for LLM features)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```bash
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/botbottle_db
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
MISTRAL_API_KEY=your_mistral_key
```

3. Initialize database:
```bash
# See DATABASE_SETUP.md for detailed instructions
python -m endpoint.endpoint
```

4. Start the server:
```bash
python -m endpoint.endpoint
# or
python run_endpoint.py
```

### Setup Guides

- **Database**: See [DATABASE_SETUP.md](DATABASE_SETUP.md)
- **Mistral AI**: See [MISTRAL_SETUP.md](MISTRAL_SETUP.md)
- **Security**: See [SECURITY.md](SECURITY.md)
- **Webhook System**: See [endpoint/webhook/README.md](endpoint/webhook/README.md)

## Project Structure

See [MODULARIZATION_COMPLETE.md](MODULARIZATION_COMPLETE.md) for the current modular structure.

### Key Modules

- `core/` - Core business logic (game, state, points)
- `features/` - Feature modules (receipt, stats, promos)
- `services/` - External service clients (WhatsApp, LLM)
- `models/` - Data models (characters)
- `endpoint/` - Flask application (webhook, security, routes)
- `db/` - Database models and operations

## Features

- **Feeding Game**: Interactive emoji-based bottle feeding
- **Character System**: Multiple characters with unique personalities
- **Points & Rewards**: Gamification with milestones and titles
- **Receipt Verification**: OCR-based bottle return verification
- **Statistics**: User stats visualization
- **Security**: Rate limiting, input validation, secure API key handling

## Cross-Platform Support

✅ **Works on Windows, Linux, and macOS**

- All file paths use `pathlib.Path` (cross-platform)
- Font loading with platform-specific fallbacks
- UTF-8 encoding for all file operations
- Environment variables work on all platforms

## Development

### Running Locally

```bash
# Start Flask server
python -m endpoint.endpoint

# Health check
curl http://localhost:5000/health
```

### Cloudflare Tunnel (for webhooks)

```bash
cloudflared tunnel --url http://localhost:5000
```

## Emojis Used for Recycling Colors

### GREEN
🍷 🍸 🍺 🍻 🍾 🍶 🥃 🏺 🫙

### YELLOW
🍼 🛍️ 🥤 🧃 🧴

### BLUE
📦 📄 📝 📚 📰 📧 ✉️ 📁 📋 🧻

### BLACK
❤️ 💔 🎉 🎊 🎈 🎁 🎀 🎂 🍰 🧁

## License

[Your License Here]
