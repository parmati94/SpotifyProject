import React, { useState, useEffect } from "react";
import Header from "./Components/Header.js";
import Button from "./Components/Button.js";

function App() {
  const [data, setData] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const loginStatus = urlParams.get("login");
    if (loginStatus === "success") {
      setIsLoggedIn(true);
    }
  }, []);

  const handleClick = async (endpoint, method = "GET") => {
    const response = await fetch(`http://localhost:8000/${endpoint}`, {
      method,
    });

    if (response.ok) {
      // Check if the response status is 200
      var data = await response.json();
      setData(data.message);
    } else {
      setData("Error: The operation could not be completed.");
    }
  };

  function handleLogin() {
    window.location.href = "http://localhost:8000/login";
  }

  return (
    <>
      <Header handleFn={() => handleLogin()} loggedIn={isLoggedIn} />
      <div>
        {isLoggedIn && (
          <container className="center">
            <Button
              label="Get All Playlists"
              handler={() => handleClick("get_all_playlists")}
            />
            <Button
              label="Add Daily Playlist"
              handler={() => handleClick("add_daily", "PUT")}
            />
            <Button
              label="Delete All Daily Playlists"
              handler={() => handleClick("delete_daily", "PUT")}
            />
          </container>
        )}
      </div>

      {data && (
        <div className="center">
          {Array.isArray(data) ? (
            data.map((item, index) => (
              <p key={index} style={{ lineHeight: "1" }}>
                {item}
              </p>
            ))
          ) : (
            <p id="datalist">{data}</p>
          )}
        </div>
      )}
    </>
  );
}

export default App;
