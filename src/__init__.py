import asyncio
import socketio
import uvicorn

from quart import Quart, jsonify
from quart_cors import cors
from dotenv import load_dotenv

CORS_ALLOWED_ORIGINS = "*"


class QuartSIO:
    def __init__(self) -> None:
        self._sio = socketio.AsyncServer(
            async_mode="asgi", cors_allowed_origins=CORS_ALLOWED_ORIGINS
        )
        self._quart_app = Quart(__name__)
        self._quart_app = cors(self._quart_app, allow_origin=CORS_ALLOWED_ORIGINS)
        self._quart_app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit
        self._sio_app = socketio.ASGIApp(self._sio, self._quart_app)
        self.route = self._quart_app.route
        self.on = self._sio.on
        self.emit = self._sio.emit
        self.register_blueprint = self._quart_app.register_blueprint
        self._quart_app.errorhandler(Exception)(self.handle_exception)
        # Load environment variables from .env file
        load_dotenv()

    async def _run(self, host: str, port: int):
        try:
            uvconfig = uvicorn.Config(self._sio_app, host=host, port=port, reload=True)
            server = uvicorn.Server(config=uvconfig)
            await server.serve()
        except KeyboardInterrupt:
            print("Shutting down")
        finally:
            print("Bye!")

    def run(self, host: str, port: int):
        asyncio.run(self._run(host, port))

    async def handle_exception(self, error):
        response = jsonify({'error': str(error)})
        response.status_code = error.code if hasattr(error, 'code') else 500
        return response


def create_app():
    app = QuartSIO()

    @app.route('/')
    def hello():
        return '<h1>Hello, world!</h1>'

    from . import video
    from . import socket_connections
    app.register_blueprint(video.bp)
    socket_connections.register_socketio_points(app)

    return app
