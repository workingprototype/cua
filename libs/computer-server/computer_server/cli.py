"""
Command-line interface for the Computer API server.
"""

import argparse
import logging
import sys
from typing import List, Optional

from .server import Server

logger = logging.getLogger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Start the Computer API server")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level (default: info)",
    )
    parser.add_argument(
        "--ssl-keyfile",
        type=str,
        help="Path to SSL private key file (enables HTTPS)",
    )
    parser.add_argument(
        "--ssl-certfile", 
        type=str,
        help="Path to SSL certificate file (enables HTTPS)",
    )

    return parser.parse_args(args)


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and start the server
    logger.info(f"Starting CUA Computer API server on {args.host}:{args.port}...")
    
    # Handle SSL configuration
    ssl_args = {}
    if args.ssl_keyfile and args.ssl_certfile:
        ssl_args = {
            "ssl_keyfile": args.ssl_keyfile,
            "ssl_certfile": args.ssl_certfile,
        }
        logger.info("HTTPS mode enabled with SSL certificates")
    elif args.ssl_keyfile or args.ssl_certfile:
        logger.warning("Both --ssl-keyfile and --ssl-certfile are required for HTTPS. Running in HTTP mode.")
    else:
        logger.info("HTTP mode (no SSL certificates provided)")
    
    server = Server(host=args.host, port=args.port, log_level=args.log_level, **ssl_args)

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
