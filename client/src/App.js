import React, { useState } from 'react';

function App() {
  const [data, setData] = useState(null);

  const handleClick = async (endpoint, method = 'GET') => {
    const response = await fetch(`http://localhost:8000/${endpoint}`, { method });
    
    if (response.ok) { // Check if the response status is 200
      var data = await response.json();
      setData(data.message);
    } else {
      setData("Error: The operation could not be completed.");
    }
  };

  return (
    <div className="App" style={{ backgroundColor: '#000000', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', height: '100vh', gap: '20px', paddingTop: '20px' }}>
      <div style={{ width: '100%', display: 'flex', justifyContent: 'space-around', marginBottom: '20px' }}>
        <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => handleClick('get_all_playlists')}>Get All Playlists</button>
        <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => handleClick('add_daily', 'PUT')}>Add Daily Playlist</button>
        <button style={{ padding: '10px', fontSize: '16px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => handleClick('delete_daily', 'PUT')}>Delete All Daily Playlists</button>
      </div>

      {data && 
        <div style={{ maxHeight: '600px', overflowY: 'scroll', width: '100%', backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '5px', textAlign: 'center' }}>
          {Array.isArray(data) ? data.map((item, index) => <p key={index} style={{ lineHeight: '1' }}>{item}</p>) : <p>{data}</p>}
        </div>
      }
    </div>
  );
}

export default App;