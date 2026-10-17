import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { config } from "./config.js";

// One small interface for the rest of the app, whichever login is in use:
// { isLoading, isAuthenticated, signIn, signOut, getToken }
const AuthContext = createContext(null);

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  if (config.devBypassSub) {
    return <DevAuth>{children}</DevAuth>;
  }
  return (
    <Auth0Provider
      domain={config.auth0Domain}
      clientId={config.auth0ClientId}
      authorizationParams={{ redirect_uri: window.location.origin, audience: config.auth0Audience }}
      // Refresh tokens in localStorage: Safari blocks the third-party cookies silent login would need.
      useRefreshTokens
      cacheLocation="localstorage"
    >
      <Auth0Bridge>{children}</Auth0Bridge>
    </Auth0Provider>
  );
}

function Auth0Bridge({ children }) {
  const { isLoading, isAuthenticated, loginWithRedirect, logout, getAccessTokenSilently } = useAuth0();
  const getToken = useCallback(() => getAccessTokenSilently(), [getAccessTokenSilently]);
  const value = useMemo(
    () => ({
      isLoading,
      isAuthenticated,
      signIn: () => loginWithRedirect(),
      signOut: () => logout({ logoutParams: { returnTo: window.location.origin } }),
      getToken,
    }),
    [isLoading, isAuthenticated, loginWithRedirect, logout, getToken],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Local demo without Auth0: sends "Bearer dev:<sub>", accepted only when the backend has DEV_AUTH_BYPASS=true.
function DevAuth({ children }) {
  const [signedIn, setSignedIn] = useState(true);
  const getToken = useCallback(async () => `dev:${config.devBypassSub}`, []);
  const value = useMemo(
    () => ({
      isLoading: false,
      isAuthenticated: signedIn,
      signIn: () => setSignedIn(true),
      signOut: () => setSignedIn(false),
      getToken,
    }),
    [signedIn, getToken],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
