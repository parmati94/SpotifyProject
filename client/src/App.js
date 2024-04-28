import React, { useState, useEffect, useCallback } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch, faPlus } from '@fortawesome/free-solid-svg-icons';
import './App.css';

function App() {
  const [data, setData] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [existingPlaylist, setExistingPlaylist] = useState('');
  const [newPlaylist, setNewPlaylist] = useState('');
  const [numberOfSongs, setNumberOfSongs] = useState('');
  const [playlists, setPlaylists] = useState([]);
  const [showCreatePlaylist, setShowCreatePlaylist] = useState(false);
  const [logoutMessage, setLogoutMessage] = useState('');
  const [playlistError, setPlaylistError] = useState('');
  const [songsError, setSongsError] = useState('');  
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [lastAction, setLastAction] = useState('');

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  const toggleSearch = () => {
    setIsSearchOpen(!isSearchOpen);
  };

  const fetchPlaylists = useCallback(async () => {
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${baseUrl}/get_all_playlists`, {
      credentials: 'include',  // Include credentials in the request
    });

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
      setIsLoading(false); 
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

  useEffect(() => {
    if (isLoading) {
      setData(null);
    }
  }, [isLoading]);

  const handleClick = async (action, endpoint, method = 'GET') => {
    setShowCreatePlaylist(false)
    setIsLoading(true);
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${baseUrl}/${endpoint}`, { 
      method,
      credentials: 'include',  // Include credentials in the request
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) { // Check if the response status is 200
      var data = await response.json();
      setIsLoading(false);
      setData(data.message);
      setLastAction(action);
    } else {
      setIsLoading(false);
      setData("Error: The operation could not be completed.");
      setLastAction(action + "_failed");
    }
  };

  const handleLogin = () => {
    setIsLoading(true);
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    window.location.href = `${baseUrl}/login`;
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setData(null);
  };

  const handleCreatePlaylist = async (source_playlist, target_playlist, num_songs) => {
    if (!source_playlist) {
    setPlaylistError('Please select an existing playlist.');
    return;
  }
    if (!num_songs) {
      setSongsError('Please select the number of songs.');
      return;
    }
    setIsLoading(true);
    setShowCreatePlaylist(false);
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const options = {
      method: 'PUT',
      credentials: 'include',  // Include credentials in the request
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_playlist, target_playlist, num_songs }) // Send data as JSON in the body
    };
    const response = await fetch(`${baseUrl}/create_playlist`, options);

    setData(""); // Reset the state
  
    if (response.ok) {
      const data = await response.json();
      setIsLoading(false);
      setData(data.message);
      setLastAction("create_playlist");
    } else {
      setIsLoading(false);
      setData("Error: The operation could not be completed.");
      setLastAction("create_playlist_failed");
    }
    setShowCreatePlaylist(true);
  };

  const handleSelectPlaylist = (playlist) => {
    setExistingPlaylist(playlist);
    setShowCreatePlaylist(true);
  };

  return (
    <div className="App">
      <div className="button-group">
        <div className="login-section">
          {!isLoggedIn ? (
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={handleLogin}>Login with Spotify</button>
          ) : (
            <button className="btn btn-moving-gradient btn-moving-gradient--blue logout-button" onClick={handleLogout}>Logout</button>
          )}
          {logoutMessage &&
            <div className="logout-message">
              <p>{logoutMessage}</p>
            </div>
          }
        </div>
        {isLoggedIn && (
          <>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('get_all_playlists', 'get_all_playlists')}>Get All Playlists</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => setShowCreatePlaylist(prevState => !prevState)}>Create Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('add_daily', 'add_daily', 'PUT')}>Add Daily Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('add_weekly', 'add_weekly', 'PUT')}>Add/Update Weekly Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('delete_daily', 'delete_daily', 'PUT')}>Delete All Daily Playlists</button>
            {showCreatePlaylist && (
              <div className="create-playlist">
                <h2>Create a Playlist Based on an Existing One 😮</h2>
                <select className="playlist-select" value={existingPlaylist} onChange={(e) => { setExistingPlaylist(e.target.value); setPlaylistError(''); }}>
                  <option disabled value="">Select Existing Playlist</option>
                  {playlists.map((playlist) => (
                    <option key={playlist} value={playlist}>
                      {playlist}
                    </option>
                  ))}
                </select>
                {playlistError && <div className="error">{playlistError}</div>}
                <select className="playlist-input" value={numberOfSongs} onChange={(e) => { setNumberOfSongs(e.target.value); setSongsError(''); }}>
                  <option disabled value="">Select Number of Songs</option>
                  {Array.from({length: 10}, (_, i) => (i + 1) * 20).map((value) => 
                    <option key={value} value={value}>{value} songs</option>
                  )}
                </select>
                {songsError && <div className="error">{songsError}</div>}
                <input type="text" className="playlist-input" value={newPlaylist} onChange={(e) => setNewPlaylist(e.target.value)} placeholder="Enter new playlist name" />
                <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleCreatePlaylist(existingPlaylist, newPlaylist, numberOfSongs)}>Submit</button>
              </div>
            )}
          </>
        )}
      </div>
      {!showCreatePlaylist && isLoading && (
        <div className="spinner">
          <div className="double-bounce1"></div>
          <div className="double-bounce2"></div>
        </div>)}
      {!showCreatePlaylist && data &&
        <div className={`data-display ${Array.isArray(data) && data.length > 1 ? 'multiple-cards' : ''}`}>
          {lastAction === 'get_all_playlists' && (
            <>
              <FontAwesomeIcon icon={faSearch} onClick={toggleSearch} className="search-icon" />
              {isSearchOpen && (
                <input
                  type="text"
                  placeholder="Search for playlist..."
                  value={searchTerm}
                  onChange={handleSearchChange}
                  className="search-input"
                />
              )}
            </>
          )}
          {Array.isArray(data)
            ? data.filter(item => item.toLowerCase().includes(searchTerm.toLowerCase())).map((item, index) => (
              <div key={index} className="card">
                <FontAwesomeIcon icon={faPlus} onClick={() => handleSelectPlaylist(item)} style={{ cursor: 'pointer' }} className="fa-plus" title="Create new playlist" />
                <p>{item}</p>
              </div>
            ))
            : <div className="card"><p>{data}</p></div>
          }
        </div>
      }
      <div className="footer">created by parmati 😄</div>
    </div>
  );
}

export default App;