import argparse
from . import create_app


def main():
    parser = argparse.ArgumentParser(description='Run the Quart application.')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Hostname of the Quart app')
    parser.add_argument('--port', type=int, default=5000, help='Port of the Quart app')
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
