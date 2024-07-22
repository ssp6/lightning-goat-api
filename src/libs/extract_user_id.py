import functools
from quart import request, jsonify
from jwt import ExpiredSignatureError, InvalidTokenError
from src.libs.clerk import Clerk


def extract_user_id(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract the Clerk token from the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header is missing'}), 401
        clerk_token = auth_header.split('Bearer ')[-1]
        if not clerk_token:
            return jsonify({'error': 'Bearer token is missing'}), 401

        # Debug: Print the token
        clerk = Clerk()
        try:
            user_id = await clerk.get_user_id(clerk_token)
            # Pass user_id to the decorated function
            kwargs['user_id'] = user_id
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        except ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return await func(*args, **kwargs)

    return wrapper


def extract_user_id_socket(func):
    @functools.wraps(func)
    async def wrapper(sid, data, *args, **kwargs):
        token = data.get('clerk_token')
        if not token:
            return jsonify({'error': 'Authorization token is missing'}), 401

        clerk = Clerk()
        try:
            user_id = await clerk.get_user_id(token)
            # Pass user_id to the decorated function
            data['user_id'] = user_id
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        except ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return await func(sid, data, *args, **kwargs)

    return wrapper
