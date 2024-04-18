export default function Button( { label, handler } ) {
  return (
    <div>
      <button onClick={handler}>{label}</button>
    </div>
  );
}
