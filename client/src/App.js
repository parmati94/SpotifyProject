import React, { useState, useEffect, useCallback } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch, faPlus } from '@fortawesome/free-solid-svg-icons';
import './App.css';

let inactivityTimeoutId;

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
  const [activeCard, setActiveCard] = useState(null);

  // Handles changes in the search input
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  // Toggles the visibility of the search form
  const toggleSearch = () => {
    setIsSearchOpen(!isSearchOpen);
  };

  // Toggles the active card
  const toggleCard = (index) => {
    setActiveCard(activeCard === index ? null : index);
  };

  // Fetches the list of playlists for playlist creation dropdown
const fetchPlaylists = useCallback(async () => {
  try {
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${baseUrl}/get_all_playlists`, {
      credentials: 'include',  // Include credentials in the request
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    if (Array.isArray(data.message)) {
      // Extract only the playlist names for now
      const playlistNames = data.message.map(playlist => playlist.name);
      setPlaylists(playlistNames);
    }
  } catch (error) {
    console.error('An error occurred:', error);
    setData(`Error: The operation could not be completed. ${error.message}`);
  }
}, []);

  // Sets the page title and favicon
  useEffect(() => {
    document.title = 'SpotifyProject';
    let link = document.querySelector("link[rel*='icon']") || document.createElement('link');
    link.type = 'image/x-icon';
    link.rel = 'shortcut icon';
    link.href = `${process.env.PUBLIC_URL}/favicon.ico`; // Use local favicon
    document.getElementsByTagName('head')[0].appendChild(link);
  }, []);

  // Handles user inactivity
  useEffect(() => {
    if (isLoggedIn) {
      const events = ['mousemove', 'keydown', 'wheel', 'DOMMouseScroll', 'mouseWheel', 'mousedown', 'touchstart', 'touchmove', 'MSPointerDown', 'MSPointerMove'];
      const resetTimeout = () => {
        clearTimeout(inactivityTimeoutId);
        inactivityTimeoutId = setTimeout(() => {
          handleLogout('You have been logged out due to inactivity. Please log back in.');
        }, 60 * 15 * 1000);
      };
      for (let i in events) {
        window.addEventListener(events[i], resetTimeout);
      }
      resetTimeout();
      return () => {
        for (let i in events) {
          window.removeEventListener(events[i], resetTimeout);
        }
        clearTimeout(inactivityTimeoutId);
      };
    }
  }, [isLoggedIn]);

  // Checks the login status and fetches playlists if login was successful
  useEffect(() => {
    const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const urlParams = new URLSearchParams(window.location.search);
    const loginStatus = urlParams.get('login');
    if (loginStatus === 'success') {
      // Call check_session endpoint
      fetch(`${baseUrl}/check_session`, {
        credentials: 'include',  // Include credentials in the request
      }).then(response => response.json()).then(data => {
        if (data.status === 'success') {
          console.log('Login succeeded');
          setIsLoggedIn(true);
          setIsLoading(false); 
          fetchPlaylists();
        } else {
          handleLogout('Please log in.')
          window.location.href = '/';
        }
      });
    }
  }, [fetchPlaylists]);

  // Hides the create playlist form when data is present
  useEffect(() => {
    if (data) {
      setShowCreatePlaylist(false);
    }
  }, [data]);

  // Resets data when loading starts
  useEffect(() => {
    if (isLoading) {
      setData(null);
    }
  }, [isLoading]);

  // Handles most click events and makes requests
  const handleClick = async (action, endpoint, method = 'GET') => {
    setShowCreatePlaylist(false)
    if (action === 'delete_daily'){
      if (!window.confirm("Are you sure you want to delete all daily playlists?")) {
        return;
      }
    }
    setIsLoading(true);
    try {
      const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/${endpoint}`, { 
        method,
        credentials: 'include',  // Include credentials in the request
        headers: {
          'Content-Type': 'application/json'
        }
      });
  
      if (!response.ok) { // Check if the response status is not OK
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      var data = await response.json();
      setIsLoading(false);
      setData(data.message);
      setLastAction(action);
    } catch (error) {
      setIsLoading(false);
      console.error('An error occurred:', error);
      setData(`Error: The operation could not be completed. ${error.message}`);
      setLastAction(action + "_failed");
    }
  };

  // Handles user login
  const handleLogin = async () => {
    try {
      setIsLoading(true);
      const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/health_check`);
  
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      window.location.href = `${baseUrl}/login`;
    } catch (error) {
      console.error('An error occurred:', error);
      setIsLoading(false);
      setLogoutMessage(`Login failed. ${error.message}`);
    }
  };
  
  // Handles user logout
  const handleLogout = async (logoutMessage = 'Successfully logged out.') => {
    try {
      setIsLoading(true);
      const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      const healthCheckResponse = await fetch(`${baseUrl}/health_check`); // Replace '/health-check' with an appropriate endpoint if needed
  
      if (!healthCheckResponse.ok) {
        throw new Error(`HTTP error! status: ${healthCheckResponse.status}`);
      }
  
      const logoutResponse = await fetch(`${baseUrl}/logout`);
  
      if (!logoutResponse.ok) {
        throw new Error(`HTTP error! status: ${logoutResponse.status}`);
      }
      setIsLoading(false)
      setIsLoggedIn(false);
      setData(null);
      setLogoutMessage(logoutMessage);
    } catch (error) {
      setIsLoading(false)
      console.error('An error occurred:', error);
      setData(`Logout failed. ${error.message}`);
    }
  };

  // Handles creating playlist from playlist feature
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
    try {
      const baseUrl = window._env_.REACT_APP_API_BASE_URL || 'http://localhost:8000';
      const options = {
        method: 'PUT',
        credentials: 'include',  // Include credentials in the request
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_playlist, target_playlist, num_songs }) // Send data as JSON in the body
      };
      const response = await fetch(`${baseUrl}/create_playlist`, options);
  
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      setData(""); // Reset the state
      const data = await response.json();
      setIsLoading(false);
      setData(data.message);
      setLastAction("create_playlist");
    } catch (error) {
      setIsLoading(false);
      console.error('An error occurred:', error);
      setData(`Error: The operation could not be completed. ${error.message}`);
      setLastAction("create_playlist_failed");
    }
    setShowCreatePlaylist(true);
  };

  // Handles using playlist from list as Create playlist input
  const handleSelectPlaylist = (playlist) => {
    setExistingPlaylist(playlist);
    setShowCreatePlaylist(true);
  };

  return (
    <div className="App">
      <div className="button-group">
        <div className={`login-section ${!isLoggedIn ? '' : 'hidden'}`}>
          {!isLoggedIn && (
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={handleLogin}>Login with Spotify</button>
          )}
          {logoutMessage &&
          <div className="logout-message">
            <p>{logoutMessage}</p>
          </div>
        }
        </div>
        <div className={`logout-section ${isLoggedIn ? '' : 'hidden'}`}>
          {isLoggedIn && (
            <button className="btn btn-moving-gradient btn-moving-gradient--blue logout-button" onClick={() => handleLogout()}>Logout</button>
          )}
        </div>
        {isLoggedIn && (
          <>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('get_all_playlists', 'get_all_playlists')}>Get All Playlists</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => setShowCreatePlaylist(prevState => !prevState)}>Create Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('add_daily', 'add_daily', 'PUT')}>Add Daily Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('add_weekly', 'add_weekly', 'PUT')}>Add/Update Weekly Playlist</button>
            <button className="btn btn-moving-gradient btn-moving-gradient--blue" onClick={() => handleClick('delete_daily', 'delete_daily', 'PUT')}>Delete All Daily Playlists</button>
          </>
        )}
      </div>
      {isLoggedIn && showCreatePlaylist && (
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
      {!showCreatePlaylist && isLoading && (
        <div className="spinner">
          <div className="double-bounce1"></div>
          <div className="double-bounce2"></div>
        </div>
      )}
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
                  autoFocus
                />
              )}
            </>
          )}
          {Array.isArray(data) ? data.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase())).map((item, index) => (
            <div key={index} className={`card ${activeCard === index ? 'active' : ''}`} onClick={() => toggleCard(index)}>
              <div className="card-front">
                <FontAwesomeIcon icon={faPlus} onClick={() => handleSelectPlaylist(item.name)} style={{ cursor: 'pointer' }} className="fa-plus" title="Create new playlist" />
                {item.image_url ? <img src={item.image_url} alt={item.name} className="card-image" /> : <div className="card-image-placeholder"></div>}
                <p>{item.name}</p>
              </div>
              {activeCard === index && (
                <div className="card-back">
                  {item.image_url ? <img src={item.image_url} alt={item.name} className="card-image" /> : <div className="card-image-placeholder"></div>}
                  <div className="card-text">
                    <p>{item.total_tracks} tracks</p>
                  </div>
                </div>
              )}
            </div>
          ))
            : <div className="card single-card"><p>{data}</p></div>
          }
        </div>
      }
      <div className="footer">created by parmati 😄</div>
    </div>
  );
}

export default App;