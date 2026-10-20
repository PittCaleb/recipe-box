import socket

from waitress import serve

from app import create_app
from config import config


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
    serve(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
