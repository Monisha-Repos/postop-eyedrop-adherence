
import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import { config } from "./config.js";

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
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: config.auth0Audience,
      }}
      useRefreshTokens
      cacheLocation="localstorage"
    >
      <Auth0Bridge>{children}</Auth0Bridge>
    </Auth0Provider>
  );
}

function Auth0Bridge({ children }) {
  const {
    isLoading,
    isAuthenticated,
    loginWithRedirect,
    logout,
    getAccessTokenSilently,
  } = useAuth0();

  const getToken = useCallback(
    () => getAccessTokenSilently(),
    [getAccessTokenSilently]
  );

  const value = useMemo(
    () => ({
      isLoading,
      isAuthenticated,
      signIn: () => loginWithRedirect(),
      signOut: () =>
        logout({
          logoutParams: {
            returnTo: window.location.origin,
          },
        }),
      getToken,
    }),
    [
      isLoading,
      isAuthenticated,
      loginWithRedirect,
      logout,
      getToken,
    ]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Local demo authentication only.
// Never enable DEV_AUTH_BYPASS in a public deployment.
function DevAuth({ children }) {
  const [demoSub, setDemoSub] = useState(null);

  const signIn = useCallback((role = "patient") => {
    const sub =
      role === "doctor"
        ? "auth0|demo-provider"
        : "auth0|demo-patient";

    setDemoSub(sub);
  }, []);

  const signOut = useCallback(() => {
    setDemoSub(null);
  }, []);

  const getToken = useCallback(async () => {
    if (!demoSub) {
      throw new Error("Not signed in");
    }

    return `dev:${demoSub}`;
  }, [demoSub]);

  const value = useMemo(
    () => ({
      isLoading: false,
      isAuthenticated: Boolean(demoSub),
      signIn,
      signOut,
      getToken,
    }),
    [demoSub, signIn, signOut, getToken]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
