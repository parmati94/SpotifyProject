import Button from "./Button";
export default function Header({ handleFn, loggedIn}) {
    
  return (
    <header>
      <div>
        <h1>Playlist Generator</h1>
        {!loggedIn && <Button handler={handleFn} label="Login with Spotify"/> }
      </div>
    </header>
  );
}
