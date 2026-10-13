import { signedInRolesText } from "./sessionUser";
import { signOut, useSession } from "./useSession";

// The menu's Session panel: who is signed in, with their roles, and Sign out; or Sign in when nobody is.

export default function SessionActions() {
  const { mounted, token, user } = useSession();

  function handleSignOut() {
    signOut();
    window.location.replace("/login");
  }

  return (
    <div className="session-panel">
      <div className="session-label">Session</div>

      {!mounted ? (
        <div className="session-status">Checking session...</div>
      ) : token !== null ? (
        <>
          {user ? (
            <div className="session-status">
              Signed in as <strong>{user.display_name}</strong>
              {user.roles.length ? <div className="session-role">{signedInRolesText(user)}</div> : null}
            </div>
          ) : (
            <div className="session-status">Signed in</div>
          )}
          <button
            type="button"
            onClick={handleSignOut}
            suppressHydrationWarning
            className="session-button"
          >
            Sign out
          </button>
        </>
      ) : (
        <>
          <div className="session-status">Not signed in</div>
          <a className="session-link" href="/login">
            Sign in
          </a>
        </>
      )}
    </div>
  );
}
