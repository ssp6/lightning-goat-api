import asyncio
import os
import subprocess
import tempfile
import uuid
import cv2

import aiofiles
from botocore.exceptions import ClientError
from quart import Blueprint, request, jsonify

from src.libs.extract_user_id import extract_user_id
from src.libs.s3 import S3_BUCKET_NAME, STREAM_FILE_KEY, ORIGINAL_FILE_KEY, create_s3_client, S3_EXPIRATION


bp = Blueprint("video", __name__, url_prefix="/video")


async def run_ffmpeg(input_file, output_dir):
    process = await asyncio.create_subprocess_exec(
        'ffmpeg', '-i', input_file,
        '-c:v', 'libx264', '-preset', 'medium', '-b:v', '5000k', '-maxrate', '5350k', '-bufsize', '7500k',
        '-c:a', 'aac', '-b:a', '192k',
        '-strict', 'experimental', '-movflags', '+faststart',
        '-f', 'hls', '-hls_time', '1', '-hls_playlist_type', 'vod',
        '-hls_segment_filename', os.path.join(output_dir, 'segment_%03d.ts'),
        os.path.join(output_dir, 'output.m3u8'),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        print(f"Error during FFmpeg conversion: {stderr.decode()}")
        raise subprocess.CalledProcessError(process.returncode, process.args)
    print(f"FFmpeg output: {stdout.decode()}")


async def convert_video_to_hls_and_upload(file_content, user_id, file_key):
    async with create_s3_client() as s3_client:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary input and output files
            print(f"Creating temp files: {user_id}/{file_key}")
            input_file = os.path.join(temp_dir, 'input.mp4')
            output_dir = temp_dir  # Directory for HLS output

            # Write the file content to the temporary input file
            async with aiofiles.open(input_file, 'wb') as f:
                await f.write(file_content)

            # Run FFmpeg to create HLS stream
            try:
                print(f"Running run_ffmpeg: {user_id}/{file_key}")
                await run_ffmpeg(input_file, output_dir)
            except subprocess.CalledProcessError:
                return None

            # Upload HLS playlist and segments to S3
            output_key_base = f'{user_id}/{file_key}/'
            try:
                # Upload playlist file
                playlist_file = os.path.join(output_dir, 'output.m3u8')
                await s3_client.upload_file(playlist_file, S3_BUCKET_NAME, output_key_base + 'output.m3u8')

                # Upload segment files
                segment_files = [f for f in os.listdir(output_dir) if f.startswith('segment_')]
                for segment_file in segment_files:
                    await s3_client.upload_file(os.path.join(output_dir, segment_file), S3_BUCKET_NAME, output_key_base + segment_file)
            except ClientError as e:
                print(f"Error uploading file to S3: {e}")
                return None

    return output_key_base + 'output.m3u8'


async def upload_original_file_to_s3(file_content, user_id, file_key):
    async with create_s3_client() as s3_client:
        try:
            # Upload original file to S3 bucket
            original_s3_key = f'{user_id}/{file_key}/{ORIGINAL_FILE_KEY}'
            print(f"Uploading original file to S3: {original_s3_key}")
            await s3_client.put_object(Body=file_content, Bucket=S3_BUCKET_NAME, Key=original_s3_key)

            return True, original_s3_key
        except Exception as e:
            print(f"Failed to process and upload file: {e}")
            return False, None


@bp.route('/upload', methods=['POST'])
@extract_user_id
async def upload_file_handler(user_id):
    """
    Upload an MP4 file to S3 and convert it to HLS format
    :return:
    """
    files = await request.files
    print(f"Files: {files}")
    # Check if the POST request has the file part
    if 'file' not in files:
        return {'error': 'No file part'}, 400
    file = files['file']

    # If the user does not select a file, the browser submits an empty part without filename
    if not file or file.filename == '':
        return {"error": 'No selected file'}, 400

    file_key = str(uuid.uuid4())

    # Read file content
    file_content = file.read()

    # Upload file to S3 and initiate asynchronous conversion
    success, s3_key = await upload_original_file_to_s3(file_content, user_id, file_key)

    print(f"Success: {success}, S3 Key: {s3_key}")
    if success:
        # Convert using ffmpeg asynchronously
        asyncio.create_task(convert_video_to_hls_and_upload(file_content, user_id, file_key))
        return {"file_key": file_key, "s3_key": s3_key}, 200
    else:
        return {"error": 'Failed to upload file to S3'}, 500


async def get_video_info(playlist_url):
    """
    Function to get video information from a playlist URL.
    TODO: Doesn't work, better being done when creating and storing in a db
    :param playlist_url:
    :return:
    """
    cap = cv2.VideoCapture(playlist_url)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps

    cap.release()

    video_info = {
        "fps": fps,
        "width": width,
        "height": height,
        "duration": duration
    }

    return video_info


async def update_playlist_with_presigned_urls(playlist_content, segment_urls, base_key):
    playlist_lines = playlist_content.decode().splitlines()
    updated_playlist_lines = []

    for line in playlist_lines:
        if line.endswith('.ts'):
            segment_key = f'{base_key}{line}'
            if segment_key in segment_urls:
                updated_playlist_lines.append(segment_urls[segment_key])
            else:
                updated_playlist_lines.append(line)
        else:
            updated_playlist_lines.append(line)

    updated_playlist_text = '\n'.join(updated_playlist_lines)
    return updated_playlist_text


async def generate_presigned_urls(s3_client, base_key):
    segment_urls = {}
    playlist_url = await s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET_NAME, 'Key': f'{base_key}output.m3u8'},
        ExpiresIn=S3_EXPIRATION
    )

    response = await s3_client.list_objects_v2(
        Bucket=S3_BUCKET_NAME,
        Prefix=base_key
    )

    for obj in response.get('Contents', []):
        key = obj['Key']
        if key.endswith('.ts'):
            presigned_url = await s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': key},
                ExpiresIn=S3_EXPIRATION
            )
            segment_urls[key] = presigned_url

    return playlist_url, segment_urls


@bp.route('/stream', methods=['GET'])
async def stream_video():
    """
    Function for streaming HLS version of video
    :return:
    """
    user_id = request.args.get('user_id')
    file_key = request.args.get('file_key')

    if not user_id or not file_key:
        return jsonify({'error': 'Missing user_id or file_key'}), 400

    base_key = f'{user_id}/{file_key}/'

    async with create_s3_client() as s3_client:
        try:
            # Generate presigned URLs for playlist and segments
            playlist_url, segment_urls = await generate_presigned_urls(s3_client, base_key)

            # Download the playlist file
            playlist_content_response = await s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=f'{base_key}output.m3u8')
            playlist_content = await playlist_content_response['Body'].read()

            # Update playlist with presigned URLs
            updated_playlist_text = await update_playlist_with_presigned_urls(playlist_content, segment_urls, base_key)

            # Write the updated playlist to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".m3u8") as temp_file:
                temp_file.write(updated_playlist_text.encode())
                temp_file_path = temp_file.name


            # Upload the updated playlist back to S3
            await s3_client.put_object(Body=updated_playlist_text.encode(), Bucket=S3_BUCKET_NAME, Key=f'{base_key}output_signed.m3u8')

            # Generate a presigned URL for the updated playlist
            signed_playlist_url = await s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': f'{base_key}output_signed.m3u8'},
                ExpiresIn=S3_EXPIRATION
            )

            return jsonify({
                'playlist_url': signed_playlist_url,
                'segment_urls': list(segment_urls.values()),
            })
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            return jsonify({'error': 'Error generating presigned URL'}), 500
