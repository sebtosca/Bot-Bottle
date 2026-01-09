#!/usr/bin/env python3
"""Entry point script to run the endpoint module."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import and run the endpoint
if __name__ == "__main__":
    from endpoint.endpoint import app
    
    PORT = 5000
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Starting BotBottle Flask server", extra={
        "port": PORT,
        "health_check": f"http://localhost:{PORT}/health",
        "webhook": f"http://localhost:{PORT}/whatsapp-webhook"
    })
    app.run(host="0.0.0.0", port=PORT, debug=True)
