import os

import aioboto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

S3_EXPIRATION = 60 * 60 # 1 hour
S3_BUCKET_NAME = 'lightning-goat'

ORIGINAL_FILE_KEY = 'original.mp4'
STREAM_FILE_KEY = 'for-streaming.mov'

aws_access_key_id = os.getenv('AWS_ACCESS_KEY')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')


def create_s3_client():
    session = aioboto3.Session()
    return session.client('s3',
                                      aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
