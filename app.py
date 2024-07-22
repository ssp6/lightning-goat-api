import argparse
from src import create_app

def main():
    parser = argparse.ArgumentParser(description='Run the application.')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Hostname of the app')
    parser.add_argument('--port', type=int, default=5000, help='Port of the app')
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()

