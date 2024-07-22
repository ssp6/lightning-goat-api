import cv2
from aiofiles import tempfile
import aiofiles.os
from quart import Blueprint
import io

from src.libs.extract_user_id import extract_user_id_socket
from src.libs.s3 import create_s3_client, S3_BUCKET_NAME, ORIGINAL_FILE_KEY

bp = Blueprint("socketio", __name__)


def register_socketio_points(app):
    @app.on('connect')
    def handle_connect(*args):
        print(f'Client connected')
        return 'Connected'

    @app.on('get_video_stream')
    @extract_user_id_socket
    async def video_stream(connection_id, data):
        """
        Stream each frame of the mp4 video to the client
        """
        print(f'Received get_video_stream event with data: {data}')
        user_id = data.get('user_id')
        file_key = data.get('file_key')
        object_key = f"{user_id}/{file_key}/{ORIGINAL_FILE_KEY}"

        # Get the video from S3
        async with create_s3_client() as s3_client:
            s3_object = await s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=object_key)
            video_stream = io.BytesIO(await s3_object['Body'].read())

        # Create a temporary file-like object
        async with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            await temp_file.write(video_stream.read())
            temp_filename = temp_file.name

        # Open video file from the temporary file
        cap = cv2.VideoCapture(temp_filename)

        # Get the FPS of the video
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Get the total number of frames
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        current_frame = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            _, buffer = cv2.imencode('.jpg', frame)
            frame_blob = buffer.tobytes()  # Get binary data
            response = {
                'frame_image': frame_blob,
                'frame_count': current_frame,
                'total_frames': total_frames,
                'fps': fps,
                'file_key': file_key
            }
            await app.emit('stream_video', response, to=connection_id)
            current_frame += 1
            # await asyncio.sleep(1 / fps)  # Use the actual FPS from the video

        # Clean up the temporary file
        await aiofiles.os.remove(temp_filename)


    @app.on('draw_on_image')
    @extract_user_id_socket
    async def draw_on_image(connection_id, data):
        print(f'Received draw_on_image event with data: {data}')
        # Extract data
        user_id = data.get('user_id')
        file_key = data.get('file_key')
        frame_index = data.get('frame_index')
        lines = data.get('lines', [])

        # Format the extracted data into a single string
        output = f"UserId: {user_id}\nFile Key: {file_key}\nFrame Index: {frame_index}\nLines:\n"
        for line in lines:
            points = line.get('points', [])
            output += "  Line:\n"
            for point in points:
                x_percentage = point.get('xPercentage')
                y_percentage = point.get('yPercentage')
                output += f"    Point - x: {x_percentage}, y: {y_percentage}\n"

        # Print the formatted string
        print(output)

