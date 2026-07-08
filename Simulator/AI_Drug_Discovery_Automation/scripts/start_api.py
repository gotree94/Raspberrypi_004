#!/usr/bin/env python
"""
API Server Startup Script
==========================
FastAPI 기반 REST API 서버 시작 스크립트.

Usage:
    python scripts/start_api.py                    # Default (port 8000)
    python scripts/start_api.py --port 8080        # Custom port
    python scripts/start_api.py --reload           # Auto-reload for development
    python scripts/start_api.py --host 127.0.0.1   # Local only
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Start AI Drug Discovery API Server",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to (default: config value or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (default: config value or 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)",
    )
    parser.add_argument(
        "--ssl-certfile",
        type=str,
        help="SSL certificate file path (for HTTPS)",
    )
    parser.add_argument(
        "--ssl-keyfile",
        type=str,
        help="SSL key file path (for HTTPS)",
    )

    args = parser.parse_args()

    # Set up Python path
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    try:
        # Load configuration
        from src.config import get_config, setup_logging

        cfg = get_config(args.config)
        setup_logging(cfg)

        # Override host/port from command line
        host = args.host or cfg.api.host
        port = args.port or cfg.api.port

        print(f"Starting AI Drug Discovery API Server...")
        print(f"  Host: {host}")
        print(f"  Port: {port}")
        print(f"  API docs: http://{host if host != '0.0.0.0' else 'localhost'}:{port}{cfg.api.api_prefix}/docs")
        print(f"  Workers: {args.workers}")
        print(f"  Reload: {'enabled' if args.reload else 'disabled'}")
        print(f"  Log level: {args.log_level}")
        print()

        # Import and start uvicorn
        import uvicorn

        # Set up SSL
        ssl_kwargs = {}
        if args.ssl_certfile and args.ssl_keyfile:
            ssl_kwargs["ssl_certfile"] = args.ssl_certfile
            ssl_kwargs["ssl_keyfile"] = args.ssl_keyfile
            print("  SSL: enabled")
        print()

        uvicorn.run(
            "src.api.rest_api:get_app",
            host=host,
            port=port,
            reload=args.reload,
            workers=args.workers,
            log_level=args.log_level,
            factory=True,
            **ssl_kwargs,
        )

    except ImportError as e:
        print(f"Error: Failed to import API module: {e}")
        print("\nMake sure you're running from the project root directory.")
        print("Try: python scripts/setup_environment.py")
        sys.exit(1)

    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
