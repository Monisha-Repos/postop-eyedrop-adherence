export default function Login({ onSignIn, onSignOut, error }) {
  return (
    <main className="center-screen login">
      <div className="logo" aria-hidden="true">👁</div>
      <h1>Eye Spy</h1>
      <p className="subtitle">Your eye-drop helper</p>
      {error ? (
        <>
          <p className="error" role="alert">{error}</p>
          <button className="big-button" onClick={onSignOut}>Sign out</button>
        </>
      ) : (
        <button className="big-button" onClick={onSignIn}>Sign in</button>
      )}
    </main>
  );
}
