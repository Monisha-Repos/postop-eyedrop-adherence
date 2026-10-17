export default function SetupNeeded() {
  return (
    <main className="center-screen">
      <h1>Setup needed</h1>
      <p>
        Copy <code>app/.env.example</code> to <code>app/.env.local</code>, fill in your Auth0 and backend
        details (or set <code>VITE_DEV_BYPASS_SUB</code> for a local demo), then restart <code>npm run dev</code>.
      </p>
    </main>
  );
}
