from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import uvicorn

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from bcrypt import hashpw, gensalt, checkpw

from dotenv import load_dotenv
import os
import re
import ast

load_dotenv()
app = FastAPI()

auth_manager = SpotifyOAuth(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
    redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
    scope='user-read-recently-played user-library-read playlist-read-private user-top-read playlist-modify-public playlist-modify-private user-read-private',
    cache_path=None  # No local caching; use the database for storage
)

from db import QueryManager
from generator import PlaylistGenerator

db = QueryManager()
generator = PlaylistGenerator()

# ------------------ Helper ------------------ 

def hash_password(password):
    """
    Function:   Hashes a password for storing in db
    Input:      password:str
    Output:     hashed_password:bool, salt:??
    """
    salt = gensalt()
    hashed_password = hashpw(password.encode('utf-8'), salt)
    return hashed_password

def verify_password(input_password, stored_hashed_password):
    """
    Function:   Verifies inputted text password with hashed password in db
    Input:      input_password:str, stored_hashed_password:str
    Output:     success:bool
    """
    return checkpw(input_password.encode('utf-8'), stored_hashed_password.tobytes())

def validate_password(password):
    """
    Function:   Validates the user's inputted password and returns a response.
                Criteria:
                - At least 8 characters long
                - Includes at least one uppercase letter
                - Includes at least one lowercase letter
                - Includes at least one digit
                - Includes at least one special character (!@#$%^&* etc.)
    Input:      password (str)
    Output:     (success:bool, response:str)
    """
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long.'
    if not any(char.isupper() for char in password):
        return False, 'Password must include at least one uppercase letter.'
    if not any(char.islower() for char in password):
        return False, 'Password must include at least one lowercase letter.'
    if not any(char.isdigit() for char in password):
        return False, 'Password must include at least one digit.'
    if not re.search(r"[!@#$%^&*(),.?':{}|<>]", password):
        return False, 'Password must include at least one special character (e.g., !@#$%^&*).'
    
    return True, 'Password is valid.'

def validate_mood(mood):
    """
    Function:   Validates mood prompt when user tries to generate playlist
    Input:      mood:str
    Output:     success:bool
    """
    return True


# ------------------ Models ------------------ 

class SignUpRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class SpotifyLoginRequest(BaseModel):
    username: str

class AuthenticateSpotifyCredentialsRequest(BaseModel):
    username: str

class createPlaylistRequest(BaseModel):
    prompt: str
    access_token: str
    username: str

class retrievePlaylistRequest(BaseModel):
    username: str


# ------------------ Routes ------------------

@app.post('/signUp')
def signup(request: SignUpRequest):
    """
    Creates a new account for the user if their username and password are valid.
    """
    try:
        user_details = db.get_user(request.username)
        if user_details:
            raise HTTPException(status_code=400, detail='Username already exists.')

        if not validate_password(request.password):
            raise HTTPException(status_code=400, detail='Password is invalid.')

        db.create_user(request.username, hash_password(request.password))
        return {'success': True, 'message': 'Successfully signed up.'}

    except HTTPException as e:  # Reraise known exceptions specified above
        raise e
    except Exception as e:  # Handle other unexpected errors
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')

@app.post('/login')
def login(request: LoginRequest):
    """
    Redirects users to Spotify's login page for authentication after verifying username and password.
    """
    try:
        user_details = db.get_user(request.username)
        if not user_details:
            raise HTTPException(status_code=400, detail='Invalid username.')

        stored_password_hash = user_details[0][2]

        if not verify_password(request.password, stored_password_hash):
            raise HTTPException(status_code=400, detail='Invalid password.')

        try:
            auth_url = auth_manager.get_authorize_url()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to generate login URL: {str(e)}')

        return {'success': True, 'message': 'Successfully logged in.', 'auth_url': auth_url}

    except HTTPException as e:  # Reraise known exceptions with appropriate status codes as specified above
        raise e
    except Exception as e:  # Catch unexpected server-side errors
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')

@app.post('/loginSpotify')
def initiate_spotify_login(request: SpotifyLoginRequest):
    """
    Generates Spotify login URL for user OAuth.
    """
    try:
        auth_url = auth_manager.get_authorize_url(state=request.username)  # Use `username` as state to identify the user
        return {'success': True, 'redirect_url': auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to generate Spotify login URL: {str(e)}')

@app.get('/callback')
def spotify_callback(code: str, state :str):
    """
    Handles Spotify's OAuth callback to exchange the authorization code for tokens 
    """
    try:
        token_info = auth_manager.get_access_token(code)
        user_tokens = db.get_spotify_token(state)

        if not user_tokens:
            if db.save_spotify_token(
                username=state,
                access_token=token_info['access_token'],
                refresh_token=token_info['refresh_token'],
                expires_at=datetime.fromtimestamp(token_info['expires_at'])
            ):
                return {'success': True, 'message': 'Spotify tokens saved successfully'}
            raise HTTPException(status_code=500, detail=f'Error saving new spotify tokens: {str(e)}')
        else:
            if db.update_spotify_token(
                username=state,
                access_token=token_info['access_token'],
                expires_at=datetime.fromtimestamp(token_info['expires_at'])
            ):
                return {'success': True, 'message': 'Spotify tokens updated successfully'}
            raise HTTPException(status_code=500, detail=f'Error updating new spotify tokens: {str(e)}')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to process Spotify callback: {str(e)}')

@app.post('/authenticateSpotify')
def authenticate_spotify_credentials(request: AuthenticateSpotifyCredentialsRequest):
    """
    Authenticates and refreshes Spotify tokens for a user.
    """
    try:
        user_tokens = db.get_spotify_token(request.username)
        if not user_tokens:
            raise HTTPException(status_code=404, detail='Spotify account not linked for this user')

        access_token, refresh_token, expires_at = user_tokens

        if datetime.now() > expires_at:
            token_info = auth_manager.refresh_access_token(refresh_token)
            db.update_spotify_token(
                username=request.username,
                access_token=token_info['access_token'],
                expires_at=datetime.fromtimestamp(token_info['expires_at'])
            )
            access_token = token_info['access_token']

        return {'success': True, 'message': 'Spotify authentication successful', 'access_token': access_token}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to authenticate Spotify credentials: {str(e)}')

@app.post('/createPlaylist')
def create_playlist(request: createPlaylistRequest):
    """
    Takes in a mood prompt from UI and uses k-nearest neighbors and NLP to curate a playlist of songs    
    """
    if validate_mood(request.prompt):
        res = generator.generate_playlist(Spotify(auth_manager=auth_manager), request.access_token, request.prompt, request.username)
        if res['success']:
            try:
                db.save_playlist(res, request.prompt, request.username)
                return {
                    'success': True, 
                    'playlist': {
                        'mood': request.prompt,
                        'playlist_url': res['playlist_url'],
                        'playlist_name': res['playlist_name'],
                        'songs': [
                            {
                                'name':track['name'],
                                'artist':track['artist'],
                                'image':track['image']
                            } for track in res['playlist_tracks']
                        ]
                    }
                }
            except Exception as e:
                return {'success':False, 'message':f'Failure saving playlist to database: {e}'}
        return res
    return {'success':False, 'message':'Invalid mood input.'}

@app.post('/retrievePlaylists')
def retrieve_playlist(request: retrievePlaylistRequest):
    """
    Retrieves previously created playlists by user based on different prompts in a dictionary format
    """
    playlists = db.retrieve_playlists(request.username)
    message = 'Error pulling playlist data from database'
    if playlists:
        print(playlists)
        try:
            return {
                'success': True, 
                'playlists': [
                    {
                        'mood': playlist[0],
                        'playlist_name': playlist[1],
                        'playlist_image': 'https://i.scdn.co/image/ab67616d00001e0206a9b8e06598b5e580a3a05a',
                        'created_at': playlist[2].strftime('%m/%d/%Y'),
                        'playlist_url': playlist[3],
                        'songs': [
                            {
                                'name': song.replace('"', '').strip('()').split(',')[0],
                                'artist': song.replace('"', '').strip('()').split(',')[1],
                                'image': song.replace('"', '').strip('()').split(',')[2]
                            } for song in ast.literal_eval(playlist[4])
                        ]
                    } for playlist in playlists
                ]
            }
        except Exception as e:
            message = f'Error formatting playlist information due to {e}'
    raise HTTPException(status_code=500, detail=f'Failure retrieving playlist data: {message}')

@app.get('/')
def root():
    return {'message': 'Welcome to the Moodify API'}
