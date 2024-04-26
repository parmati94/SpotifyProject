import React, { useState, useEffect, useCallback } from 'react';

function App() {
  const [data, setData] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [existingPlaylist, setExistingPlaylist] = useState('');
  const [newPlaylist, setNewPlaylist] = useState('');
  const [playlists, setPlaylists] = useState([]);
  const [showCreatePlaylist, setShowCreatePlaylist] = useState(false);

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
    <div className="App" style={{ backgroundColor: '#000000', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', height: '100vh', gap: '20px', paddingTop: '20px' }}>
      <div style={{ width: '100%', display: 'flex', justifyContent: 'space-around', marginBottom: '20px' }}>
        <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={handleLogin}>Login with Spotify</button>
        {isLoggedIn && (
          <>
          <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => handleClick('get_all_playlists')}>Get All Playlists</button>
          <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => handleClick('add_daily', 'PUT')}>Add Daily Playlist</button>
          <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => handleClick('add_weekly', 'PUT')}>Add/Update Weekly Playlist</button>
          <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => handleClick('delete_daily', 'PUT')}>Delete All Daily Playlists</button>
          <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => setShowCreatePlaylist(prevState => !prevState)}>Create Playlist</button>
          {showCreatePlaylist && (
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
              <h2 style={{ color: '#fff', marginBottom: '20px' }}>Create a Playlist Based on an Existing One 😮</h2>
              <select style={{ display: 'block', margin: '20px 0', padding: '10px', fontSize: '16px', fontFamily: 'Arial, sans-serif', width: '100%', boxSizing: 'border-box' }} value={existingPlaylist} onChange={(e) => setExistingPlaylist(e.target.value)}>
                {playlists.map((playlist) => (
                  <option key={playlist} value={playlist}>
                    {playlist}
                  </option>
                ))}
              </select>
              <input style={{ display: 'block', margin: '20px 0', padding: '10px', fontSize: '16px', fontFamily: 'Arial, sans-serif', width: '100%', boxSizing: 'border-box' }} type="text" value={newPlaylist} onChange={(e) => setNewPlaylist(e.target.value)} placeholder="Enter new playlist name" />
              <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => handleCreatePlaylist(existingPlaylist, newPlaylist)}>Submit</button>
            </div>
          )}
          </>
        )}
      </div>
      {!showCreatePlaylist && data && 
        <div style={{ maxHeight: '600px', overflowY: 'scroll', width: '100%', backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '5px', textAlign: 'center' }}>
          {Array.isArray(data) ? data.map((item, index) => <p key={index} style={{ lineHeight: '1' }}>{item}</p>) : <p>{data}</p>}
        </div>
      }
    </div>
  );
}

export default App;