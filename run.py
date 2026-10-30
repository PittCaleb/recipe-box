import socket

from waitress import serve

from app import create_app
from config import config

# Waitress drops X-Forwarded-Proto/Host/For unless told otherwise, so the app
# couldn't tell a request came in over HTTPS and built http:// links. Caddy
# sets those headers itself (it doesn't pass on what visitors send), and
# ProxyFix in create_app reads them.
SERVE_OPTIONS = {"clear_untrusted_proxy_headers": False}


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def main():
    app = create_app()
    print(f"Recipes running at http://localhost:{config.PORT}")
    ip = lan_ip()
    if ip:
        print(f"On your LAN:        http://{ip}:{config.PORT}")
    serve(app, host=config.HOST, port=config.PORT, **SERVE_OPTIONS)


if __name__ == "__main__":
    main()
