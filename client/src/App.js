import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

function App() {
  const [data, setData] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [existingPlaylist, setExistingPlaylist] = useState('');
  const [newPlaylist, setNewPlaylist] = useState('');
  const [numberOfSongs, setNumberOfSongs] = useState('');
  const [playlists, setPlaylists] = useState([]);
  const [showCreatePlaylist, setShowCreatePlaylist] = useState(false);
  const [logoutMessage, setLogoutMessage] = useState('');

  const fetchPlaylists = useCallback(async () => {
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${baseUrl}/get_all_playlists`);

    if (response.ok) {
      const data = await response.json();
      if (Array.isArray(data.message)) {
        setPlaylists(data.message);
      }
    } else {
      setData("Error: The operation could not be completed.");
    }
  }, []);

  useEffect(() => {
    // Set the page title
    document.title = 'SpotifyProject';
  
    // Set the favicon
    let link = document.querySelector("link[rel*='icon']") || document.createElement('link');
    link.type = 'image/x-icon';
    link.rel = 'shortcut icon';
    link.href = `${process.env.PUBLIC_URL}/favicon.ico`; // Use local favicon
    document.getElementsByTagName('head')[0].appendChild(link);
  }, []);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const loginStatus = urlParams.get('login');
    if (loginStatus === 'success') {
      console.log('Login succeeded');
      setIsLoggedIn(true);
      fetchPlaylists();
    }
    const timeoutId = setTimeout(() => {
      setIsLoggedIn(false);
      setData(null);
      setLogoutMessage('You have been logged out. Please log back in.');
    }, 60 * 30 * 1000);

    return () => clearTimeout(timeoutId);
  }, [fetchPlaylists]);

  useEffect(() => {
    if (data) {
      setShowCreatePlaylist(false);
    }
  }, [data]);

  const handleClick = async (endpoint, method = 'GET') => {
    setShowCreatePlaylist(false)
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${baseUrl}/${endpoint}`, { method });

    if (response.ok) { // Check if the response status is 200
      var data = await response.json();
      setData(data.message);
    } else {
      setData("Error: The operation could not be completed.");
    }
  };

  const handleLogin = () => {
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    window.location.href = `${baseUrl}/login`;
  };

  const handleCreatePlaylist = async (source_playlist, target_playlist, num_songs) => {
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const options = {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_playlist, target_playlist, num_songs }) // Send data as JSON in the body
    };
    const response = await fetch(`${baseUrl}/create_playlist`, options);

    setData(""); // Reset the state
  
    if (response.ok) {
      const data = await response.json();
      setData(data.message);
    } else {
      setData("Error: The operation could not be completed.");
    }
  };

  return (
    <div className="App">
      <div className="button-group">
        <div className="login-section">
          <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={handleLogin}>Login with Spotify</button>
          {logoutMessage &&
            <div className="logout-message">
              <p>{logoutMessage}</p>
            </div>
          }
        </div>
        {isLoggedIn && (
          <>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => setShowCreatePlaylist(prevState => !prevState)}>Create Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('add_daily', 'PUT')}>Add Daily Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('add_weekly', 'PUT')}>Add/Update Weekly Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('delete_daily', 'PUT')}>Delete All Daily Playlists</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('get_all_playlists')}>Get All Playlists</button>
            {showCreatePlaylist && (
              <div className="create-playlist">
                <h2>Create a Playlist Based on an Existing One 😮</h2>
                <select className="playlist-select" value={existingPlaylist} onChange={(e) => setExistingPlaylist(e.target.value)}>
                  {playlists.map((playlist) => (
                    <option key={playlist} value={playlist}>
                      {playlist}
                    </option>
                  ))}
                </select>
                <input type="text" className="playlist-input" value={newPlaylist} onChange={(e) => setNewPlaylist(e.target.value)} placeholder="Enter new playlist name" />
                <select className="playlist-input" value={numberOfSongs} onChange={(e) => setNumberOfSongs(e.target.value)}>
                    {Array.from({length: 10}, (_, i) => (i + 1) * 20).map((value) => 
                        <option key={value} value={value}>{value} songs</option>
                    )}
                </select>
                <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleCreatePlaylist(existingPlaylist, newPlaylist, numberOfSongs)}>Submit</button>
              </div>
            )}
          </>
        )}
      </div>
      {!showCreatePlaylist && data &&
        <div className="data-display">
          {Array.isArray(data) ? data.map((item, index) => <p key={index}>{item}</p>) : <p>{data}</p>}
        </div>
      }
      <div className="footer">created by parmati 😄</div>
    </div>
  );
}

export default App;