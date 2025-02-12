import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor

from dotenv import load_dotenv
import os

class Database:
    def __init__(self):
        # self.conn = psycopg2.connect(
        #     database=os.getenv("DATABASE_NAME"),
        #     user=os.getenv("DATABASE_USER"),
        #     password=os.getenv("DATABASE_PASSWORD"),
        #     host=os.getenv("DATABASE_HOST"),
        #     port=os.getenv("DATABASE_PORT"),
        # )
        self.conn = psycopg2.connect(
            database="Spotify-extention",
            user="postgres",
            password="admin",
            host="localhost",
            port=5432,
        )
        self.conn.autocommit = True

    def execute_query(self, query, params=None):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            try:
                cursor.execute(query, params)
                if query.strip().lower().startswith("select"):
                    return cursor.fetchall()
                return True
            except Exception as e:
                print(f"Database error: {e}")
                return None

class QueryManager(Database):
    def create_user(self, username, password_hash):
        query = """
        INSERT INTO Users (username, password_hash)
        VALUES (%s, %s)
        """
        return self.execute_query(query, (username, password_hash))

    def get_user(self, username):
        query = """
        SELECT * FROM Users WHERE username = %s
        """
        return  self.execute_query(query, (username,))

    def save_spotify_token(self, username, access_token, refresh_token, expires_at):
        user_query = "SELECT id FROM Users WHERE username = %s"
        user_result = self.execute_query(user_query, (username,))
        if not user_result:
            print(f"User {username} not found.")
            return None
        user_id = user_result[0]["id"]
        
        query = """
        INSERT INTO Spotify_Tokens (user_id, access_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s)
        """
        return self.execute_query(query, (user_id, access_token, refresh_token, expires_at))

    def get_spotify_token(self, username):
        query = """
        SELECT access_token, refresh_token, expires_at
        FROM Spotify_Tokens
        JOIN Users ON Spotify_Tokens.user_id = Users.id
        WHERE Users.username = %s
        """
        result = self.execute_query(query, (username,))
        return result[0] if result else None

    def update_spotify_token(self, username, access_token, expires_at):
        user_query = "SELECT id FROM Users WHERE username = %s"
        user_result = self.execute_query(user_query, (username,))
        if not user_result:
            print(f"User {username} not found.")
            return
        user_id = user_result[0]["id"]

        update_query = """
        UPDATE Spotify_Tokens
        SET access_token = %s, expires_at = %s
        WHERE user_id = %s
        """
        return self.execute_query(update_query, (access_token, expires_at, user_id))

    def save_playlist(self, playlist, prompt, username):
        user_query = "SELECT id FROM Users WHERE username = %s"
        user_result = self.execute_query(user_query, (username,))
        if not user_result:
            print(f"User {username} not found.")
            return
        user_id = user_result[0]["id"]

        query = """
        INSERT INTO Playlists (user_id, prompt, name)
        VALUES (%s, %s, %s)
        RETURNING Playlists.id
        """
        playlist_id = self.execute_query(query, (user_id, prompt, playlist['playlist_name']))

        query = """
        INSERT INTO Songs (name, artist)
        VALUES (%s, %s)
        RETURNING Songs.id
        """
        song_id = self.execute_query(query, (name, artist))

        query = """
        INSERT INTO Playlists_to_Songs (playlist_id, song_id)
        VALUES (%s, %s)
        RETURNING Songs.id
        """
        return self.execute_query(query, (playlist_id, song_id))
    