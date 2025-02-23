import os
import spacy
import numpy as np
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from transformers import pipeline

import requests

spacy.prefer_gpu()  

load_dotenv()
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

class PlaylistGenerator:
    def __init__(self):
        self.generator = pipeline("text2text-generation", model="google/flan-t5-base")
        self.embedder = SentenceTransformer("paraphrase-MiniLM-L6-v2")

    def classify_prompt(self, user_prompt):
        """
        Uses a pretrained LLM model to classify what the user needs more dynamically
        """
        prompt = (f"My user is feeling {user_prompt}. Describe the type of songs my user needs based on their prompt.")
        result = self.generator(prompt, max_length=150, do_sample=False)
        if result:
            return result[0]["generated_text"]
        return user_prompt

    def get_user_top_songs(self, sp):
        """
        Fetches the user's top 50 tracks from Spotify
        """
        results = sp.current_user_top_tracks(limit=50, time_range="medium_term")
        tracks = []

        for item in results["items"]:
            track_id = item["id"]
            track_name = item["name"]
            artist = item["artists"][0]["name"]
            tracks.append({"id": track_id, "name": track_name, "artist": artist})

        return tracks

    def get_songs_from_playlist(self, sp, id, limit=50):
        """
        Fetches the top global playlist from Spotify
        """
        results = sp.playlist_tracks(id)
        items = results['items']
        
        while results["next"] and len(items) < limit:
            results = sp.next(results)
            items.extend(results["items"])

        tracks = []
        for item in items:
            track = item['track']
            tracks.append({
                "id": track["id"],
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "image": sp.track(track["id"])["album"]["images"][0]["url"]
            })
        return tracks

    def get_song_info(self, song_name, artist_name):
        """
        Fetches metadata (tags, moods, etc.) for a given song from Last.fm
        """
        url = f"http://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "track.getInfo",
            "api_key": LASTFM_API_KEY,
            "artist": artist_name,
            "track": song_name,
            "format": "json"
        }

        response = requests.get(url, params=params)
        data = response.json()
        if "track" in data:
            tags = [tag["name"] for tag in data["track"]["toptags"]["tag"]]
            return {"song": song_name, "artist": artist_name, "tags": tags}
        return None

    def get_embedding(self, prompt):
        """
        Embeds piece of text into latent space
        """
        return self.embedder.encode(prompt)

    def create_playlist(self, sp, mood, recommended_tracks):
        """
        Creates a Spotify playlist and adds the recommended tracks
        """
        playlist = sp.user_playlist_create(user=sp.current_user()["id"], name=mood, public=True)
        track_uris = [f"spotify:track:{track}" for track in recommended_tracks]
        sp.playlist_add_items(playlist_id=playlist["id"], items=track_uris)
        return playlist["external_urls"]["spotify"]

    def generate_playlist(self, sp, token, user_prompt, username):
        """
        Main function to generate a Spotify playlist based on user mood dynamically
        """
        try:
            # Uses NLP to classify user's mood and embed
            generated_text = self.classify_prompt(user_prompt)
            print(f"Song requirements: {generated_text}")
            embedded_prompt = self.get_embedding(generated_text)

            # Get user and global top tracks to embed
            embedded_user_tracks = {}
            user_top_tracks = self.get_user_top_songs(sp)
            if not user_top_tracks:
                raise ValueError("No top tracks found for user.")
            for track in user_top_tracks:
                song_info = self.get_song_info(track['name'], track['artist'])
                embedded_user_tracks[track['id']] = self.get_embedding(' '.join(song_info['tags']))

            embedded_global_tracks = {}
            global_top_tracks = self.get_songs_from_playlist(sp, "1RDk6T6DZNnYvBaBZQ3eWh", 300)

            if not global_top_tracks:
                raise ValueError("No global top tracks playlist found.")
            for track in global_top_tracks:
                song_info = self.get_song_info(track['name'], track['artist'])  # TODO: get_song_info kinda slow
                embedded_global_tracks[track['id']] = self.get_embedding(' '.join(song_info['tags']))  # TODO: Probably need to find a better way to embed the songs aside from using the 'tags'

            # Using user's top tracks to create personalised weights by computing average embedding
            user_top_embeddings = np.array([embedded_global_tracks[track] for track in embedded_user_tracks if track in embedded_global_tracks])
            user_profile_embedding = np.mean(user_top_embeddings, axis=0) if user_top_embeddings.size != 0 else np.zeros((list(embedded_global_tracks.values())[0].shape[0],))

            # Embed global top tracks into latent space to do (cosine) similarity search using user's prompt
            knn = NearestNeighbors(n_neighbors=50, metric="cosine")
            knn.fit(np.array(list(embedded_global_tracks.values())))
            distances, indices = knn.kneighbors([embedded_prompt])
            indices = [int(idx) for _, idx in sorted(zip(distances[0], indices[0]))]
            closest_global_songs = {list(embedded_global_tracks.items())[idx][0]:list(embedded_global_tracks.items())[idx][1] for idx in indices}

            # Similarity search on sorted global stop tracks with user's top songs
            similarities = cosine_similarity(np.array(list(closest_global_songs.values())), user_profile_embedding.reshape(1, -1))
            sorted_indices = np.argsort(similarities[:, 0])[::-1]  # Sort by highest similarity
            recommended_songs = [list(closest_global_songs.keys())[i] for i in sorted_indices[:25]]  # Get song IDs
            if not recommended_songs:
                raise ValueError("No suitable songs found for this mood.")

            # Create a Spotify playlist with the recommended songs
            playlist_url = self.create_playlist(sp, user_prompt, recommended_songs)  # TODO: Playlist is currently created and saved under user's actual account
            new_playlist_tracks = self.get_songs_from_playlist(sp, playlist_url.split('/')[-1], 100)
            playlist_name = 'test'  # TODO: maybe use some LLM to create name 

            return {"success":True, "playlist_url":playlist_url, "playlist_name":playlist_name, "playlist_tracks":new_playlist_tracks}

        except Exception as e:
            print(e)
            return {"success": False, "message": str(e)}