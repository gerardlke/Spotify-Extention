import os 
import re
import time
import requests

import streamlit as st
from streamlit_javascript import st_javascript
from dotenv import load_dotenv

ADMIN_USERNAME = 'test'
ADMIN_PASSWORD = 'test'

class APIManager:
    def __init__(self, path='./.env'):
        load_dotenv(path)
        self.BACKEND_ENDPOINT = os.getenv("BACKEND_ENDPOINT")

    def signup_user(self, username, password):
        """
        Function:   Signs a user up if they have a valid username and password
        Input:      username:str, password:str
        Output:     {"success":bool, "message":str}
        """
        if not username or len(username) < 3:
            return {"success": False, "message": "Username must be at least 3 characters long."}
        if not password or len(password) < 8:
            return {"success": False, "message": "Password must be at least 8 characters long."}

        data = {"username": username, "password": password}

        try:
            response = requests.post(self.BACKEND_ENDPOINT + "/signUp", json=data, timeout=10)
            response_data = response.json()

            if response.status_code == 200:
                return response_data

            elif response.status_code == 400:  # Handle client-side errors (e.g., username taken, invalid password)
                backend_detail = response_data.get("detail", "Invalid input. Please try again.")
                return {"success": False, "message": backend_detail}

            elif response.status_code == 500:  # Handle server-side errors
                backend_detail = response_data.get("detail", "Unexpected server error.")
                return {"success": False, "message": f"Server error: {backend_detail}"}

            else:  # Handle unexpected status codes
                return {"success": False, "message": f"Unexpected error occurred: {response.status_code}"}

        except requests.exceptions.Timeout:  # Handle timeout explicitly
            return {"success": False, "message": "The signup request timed out. Please try again later."}

        except requests.exceptions.RequestException as e:  # Handle other network errors
            return {"success": False, "message": f"Failed to connect to the server: {str(e)}"}
    
    def login_user(self, username, password):
        """
        Function:   Logs a user into their account if their account exists and their password is correct
        Input:      username:str, password:str
        Output:     {"success":bool, "message":str}
        """
        data = {"username": username, "password": password}
        try:
            response = requests.post(self.BACKEND_ENDPOINT + "/login", json=data)
            response_data = response.json()

            if response.status_code == 200:  # Expected success response -> parse JSON response
                return response_data
            elif response.status_code == 400:
                backend_detail = response_data.get("detail", "Invalid username or password.")
                return {"success": False, "message": backend_detail}
            elif response.status_code == 500:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Server error: {backend_detail}"}
            else:
                return {"success": False, "message": f"Unexpected error occurred: {response.status_code}"}

        except requests.exceptions.Timeout:  # Handle timeout explicitly
            return {"success": False, "message": "The login request timed out. Please try again later."}

        except requests.exceptions.RequestException as e:  # Handle connection errors or timeouts
            return {"success": False, "message": f"Failed to connect to the server: {str(e)}"}

    def login_spotify(self, username):
        """
        Function:   Authenticates a user's spotify account access via extention app and saves tokens to database
        Input:      None
        Output:     None
        """
        data = {"username": username}
        try:
            response = requests.post(self.BACKEND_ENDPOINT + "/loginSpotify", json=data)
            response_data = response.json()

            if response.status_code == 200:  # Expected success response -> parse JSON response
                return response_data
            elif response.status_code == 500:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Server error: {backend_detail}"}
            else:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Unexpected error occurred: {backend_detail}"}

        except requests.exceptions.Timeout:  # Handle timeout explicitly
            return {"success": False, "message": "The spotify login request timed out. Please try again later."}

        except requests.exceptions.RequestException as e:  # Handle connection errors or timeouts
            return {"success": False, "message": f"Failed to connect to the server: {str(e)}"}

    def create_playlist(self, prompt, username):
        """
        Function:   Takes in a mood prompt from UI and uses k-nearest neighbors and NLP to curate a playlist of songs
        Input:      prompt:str
        Output:     [{'name':name:str, }, ...]
        """
        data = {"username": username}
        try:
            response = requests.post(self.BACKEND_ENDPOINT + "/authenticateSpotify", json=data)
            response_data = response.json()
        
            if response.status_code == 200:  
                access_token = response_data['access_token']
            elif response.status_code == 500:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Server error: {backend_detail}"}
            else:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Unexpected error occurred: {backend_detail}"}
        except requests.exceptions.Timeout:  # Handle timeout explicitly
            return {"success": False, "message": "The spotify authentication request timed out. Please try again later."}
        except requests.exceptions.RequestException as e:  # Handle connection errors or timeouts
            return {"success": False, "message": f"Failed to connect to the server: {str(e)}"}
        
        data = {"prompt": prompt, "access_token": access_token, "username": st.session_state.username}
        try:
            response = requests.post(self.BACKEND_ENDPOINT + "/createPlaylist", json=data)
            response_data = response.json()
        
            if response.status_code == 200:  
                return response_data
            elif response.status_code == 500:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Server error: {backend_detail}"}
            else:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Unexpected error occurred: {backend_detail}"}
        except requests.exceptions.Timeout:  # Handle timeout explicitly
            return {"success": False, "message": "The spotify authentication request timed out. Please try again later."}
        except requests.exceptions.RequestException as e:  # Handle connection errors or timeouts
            return {"success": False, "message": f"Failed to connect to the server: {str(e)}"}

    def retrieve_playlists(self):
        """
        Function:   Retrieves previously created playlists by user based on different moods
        Input:      username:str
        Output:     
        """
        data = {"username": st.session_state.username}
        try:
            response = requests.post(self.BACKEND_ENDPOINT + "/retrievePlaylists", json=data)
            response_data = response.json()
        
            if response.status_code == 200:  
                return response_data
            elif response.status_code == 500:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Server error: {backend_detail}"}
            else:
                backend_detail = response_data.get("detail", "Server error.")
                return {"success": False, "message": f"Unexpected error occurred: {backend_detail}"}
        except requests.exceptions.Timeout:  # Handle timeout explicitly
            return {"success": False, "message": "The spotify authentication request timed out. Please try again later."}
        except requests.exceptions.RequestException as e:  # Handle connection errors or timeouts
            return {"success": False, "message": f"Failed to connect to the server: {str(e)}"}

class StreamlitApp(APIManager):
    def __init__(self):
        super().__init__()
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False
        if "user_credentials" not in st.session_state or type(st.session_state) != dict:
            st.session_state.user_credentials = {
                'username':None, 
                'password':None,
                'spotify_credentials':None 
            }

    def logout(self):
        """
        Logs user out by clearing session state
        """
        st.session_state.logged_in = False
        st.session_state.user_credentials = {'username':None, 'password':None, 'spotify_credentials':None}
        st.rerun()

    def show_popup(self, message, duration=3):
        """
        Helper function to show pop up message on screen 
        """
        popup_container = st.empty() 
        popup_container.write(message) 
        time.sleep(duration)  
        popup_container.empty() 

    def show_login_page(self):
        """
        Log in page, interacts with backend to determine validity of user details
        """
        st.title("Log In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Log In"):
            if not username or len(username) < 3:
                st.error("Username must be at least 3 characters long.")
            elif not password or len(password) < 8:
                st.error("Password must be at least 8 characters long.")
            else:
                res = self.login_user(username, password)
                if not res['success']:
                    st.error(f"{res['message']} Please try again.")
                else:
                    st.session_state.username = username
                    # Authenticate Spotify account during sign-up
                    try:
                        res = self.login_spotify(username)
                        if res['success']:
                            st.session_state.logged_in = True
                            if res['redirect_url']:
                                st_javascript(f'window.location.href="{res['redirect_url']}";')  # Redirect user
                            else:
                                st.error("Invalid redirect URL from backend.")

                            # st.markdown(
                            #     f'<script>window.open("{res['redirect_url']}","_blank");</script>',
                            #     unsafe_allow_html=True
                            # )
                            # st.rerun()
                        else:
                            st.error(f"Failed to link Spotify account: {res['message']}. Please try again.")
                    except Exception as e:
                        st.error(f"Failed to link Spotify account: {e}. Please try again.")

    def show_signup_page(self):
        """
        Sign up page, interacts with backend to determine validity of inputted details
        """
        st.title("Sign Up")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign Up"):
            if not username or len(username) < 3:
                st.error("Username must be at least 3 characters long.")
            elif not password or len(password) < 8:
                st.error("Password must be at least 8 characters long.")
            else:
                res = self.signup_user(username, password)
                if not res['success']:
                    st.error(f"{res['message']} Please try again.")
                else:
                    st.session_state.logged_in = False
                    st.success("Account created successfully! Please log in.")

    def show_main_page(self):
        """
        Main page, implements playlist generation logic
        """
        st.title("Mood-Based Playlist Generator")
        st.text("Tell us how you feel and we will help you find some fitting tunes!")

        mood = st.text_input("Describe what type of playlist you would like me to offer...", placeholder="eg. I am feeling lethargic and lazy so I need some tunes to motivate me!")
        if st.button("Generate Playlist"):
            if not mood:
                st.error("Sorry, I can't read your mind... yet. Try keying a prompt in!")
            else:
                st.success(f"Generating a playlist to... {mood}")
                
                res = self.create_playlist(mood, st.session_state.username)
                if res['success']:

                    st.write("### Here are some tunes you might like;")
                    st.write(f"#### **Playlist name:** {res['playlist']['playlist_name']}")
                    st.write(f"##### **Playlist url:**  {res['playlist']['playlist_url']}")
                    for song in res['playlist']['songs']:
                        with st.container():
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.image(song["image"], width=100)

                            with col2:
                                st.subheader(song["name"])
                                st.write(f"**Artist:** {song['artist']}")
                else:
                    st.error(res['message'])

    def show_history_page(self):
        """
        History page, displays previous prompts and playlists 
        """
        st.title("History")
        st.text("Your previously generated playlists will appear here.")
        data = self.retrieve_playlists()
        if not data['success']:
            st.error(f'Error retrieving playlist history: {data['message']}')
        else:
            for playlist in data['playlists']:
                with st.container():
                    
                    col1, col2 = st.columns([1, 3])  # Playlist Image and Prompt (Left and Right Layout)
                    with col1:
                        st.image(playlist["playlist_image"], width=100)  # Playlist image

                    with col2:
                        st.write(f'## {playlist["playlist_name"]}')
                        st.write(f'#### {playlist["playlist_url"]}')
                        st.write(f'#### **You were feeling a lil...** {playlist['mood']}')

                        with st.expander("View Songs"):  # Dropdown for songs
                            for song in playlist["songs"]:
                                with st.container():
                                    col1, col2 = st.columns([1, 3])
                                    with col1:
                                        st.image(song["image"], width=100)
                                    with col2:
                                        st.subheader(song["name"])
                                        st.write(f"**Artist:** {song['artist']}")
                st.write(f'---')

        st.markdown("""
            <style>
                .stContainer {
                    background-color: #f9f9f9;
                    padding: 10px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
                }
            </style>
            """, unsafe_allow_html=True
        )

if __name__=='__main__':
    app = StreamlitApp()

    # Render appropriate page based on session state
    if not st.session_state.logged_in:
        page_selection = st.sidebar.radio("Select Page", ["Log In", "Sign Up"])
        if page_selection == "Log In":
            app.show_login_page()
        elif page_selection == "Sign Up":
            app.show_signup_page()
    else:
        if st.sidebar.button("Log Out"):
            app.logout()
        page_selection = st.sidebar.radio("Select Page", ["Home", "History"])
        if page_selection == "Home":
            app.show_main_page()
        elif page_selection == "History":
            app.show_history_page()