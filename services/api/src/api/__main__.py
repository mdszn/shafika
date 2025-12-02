import os

from .server import app


def main():
    """Start the Flask API server."""
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("FLASK_ENV") == "development"

    print("ETHEREUM INDEXER API")
    print(f"Starting server on port {port}")
    print(f"Debug mode: {debug}")

    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
