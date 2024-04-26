import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

function App() {
  const [data, setData] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [existingPlaylist, setExistingPlaylist] = useState('');
  const [newPlaylist, setNewPlaylist] = useState('');
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
    const urlParams = new URLSearchParams(window.location.search);
    const loginStatus = urlParams.get('login');
    if (loginStatus === 'success') {
      setIsLoggedIn(true);
      fetchPlaylists();
    }
    const timeoutId = setTimeout(() => {
      setIsLoggedIn(false);
      setData(null);
      setLogoutMessage('You have been logged out. Please log back in.');
    }, 60 * 30 * 1000);

    return () => clearTimeout(timeoutId);
  }, [setIsLoggedIn, fetchPlaylists]);

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
    const baseUrl = window._env_.REACT_APP_API_BASE_URL  || 'http://localhost:8000';
    window.location.href = `${baseUrl}/login`;
  };

  const handleCreatePlaylist = async (source_playlist, target_playlist) => {
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const options = {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
    };
    const response = await fetch(`${baseUrl}/create_playlist?source_playlist=${encodeURIComponent(source_playlist)}&target_playlist=${encodeURIComponent(target_playlist)}`, options);
    
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
          <button onClick={handleLogin}>Login with Spotify</button>
          {logoutMessage && 
            <div className="logout-message">
              <p>{logoutMessage}</p>
            </div>
          }
        </div>
        {isLoggedIn && (
          <>
            <button onClick={() => handleClick('get_all_playlists')}>Get All Playlists</button>
            <button onClick={() => handleClick('add_daily', 'PUT')}>Add Daily Playlist</button>
            <button onClick={() => handleClick('add_weekly', 'PUT')}>Add/Update Weekly Playlist</button>
            <button onClick={() => handleClick('delete_daily', 'PUT')}>Delete All Daily Playlists</button>
            <button onClick={() => setShowCreatePlaylist(prevState => !prevState)}>Create Playlist</button>
            {showCreatePlaylist && (
              <div className="create-playlist">
                <h2>Create a Playlist Based on an Existing One 😮</h2>
                <select value={existingPlaylist} onChange={(e) => setExistingPlaylist(e.target.value)}>
                  {playlists.map((playlist) => (
                    <option key={playlist} value={playlist}>
                      {playlist}
                    </option>
                  ))}
                </select>
                <input type="text" value={newPlaylist} onChange={(e) => setNewPlaylist(e.target.value)} placeholder="Enter new playlist name" />
                <button onClick={() => handleCreatePlaylist(existingPlaylist, newPlaylist)}>Submit</button>
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
    </div>
  );
}

export default App;