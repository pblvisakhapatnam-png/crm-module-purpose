import { FormEvent, useState } from "react";

import { SHOW_DEMO_CREDENTIALS } from "../config/buildFlags";
import { signInRefusal } from "../components/signInMessages";
import { signOut, useSession } from "../components/useSession";

const API_BASE = "";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const VIEWED_ACCOUNT_IDS_KEY = "pbl_viewed_account_ids_this_session";
const VIEWED_OPPORTUNITY_IDS_KEY = "pbl_viewed_opportunity_ids_this_session";

function notifySessionChanged() {
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

type LoginResponse = {
  access_token: string;
  token_type: string;
  user: {
    public_id: string;
    username: string;
    display_name: string;
    roles: string[];
    role_codes: string[];
  };
};

type SignInState = { kind: "idle" } | { kind: "signing-in" } | { kind: "failed"; message: string };

export default function LoginPage() {
  // Development builds prefill a demo user so local checks can sign in with one click. The hosted
  // pilot's build removes both the prefill and the list below (src/config/buildFlags.ts).
  const [username, setUsername] = useState(SHOW_DEMO_CREDENTIALS ? "admin1" : "");
  const [password, setPassword] = useState(SHOW_DEMO_CREDENTIALS ? "password" : "");
  const [signIn, setSignIn] = useState<SignInState>({ kind: "idle" });
  // The name the sign-in answer gave, kept with its token, so the page names the person at once - before the
  // session's own lookup answers - and never names them under another session.
  const [answered, setAnswered] = useState<{ token: string; name: string } | null>(null);
  const session = useSession();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSignIn({ kind: "signing-in" });

    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      // A wrong password, or a username stopped after repeated ones (TB-1 TB1-204 part a): said beside the button.
      setSignIn({ kind: "failed", message: await signInRefusal(response) });
      return;
    }

    const data = (await response.json()) as LoginResponse;
    localStorage.setItem("pbl_auth_token", data.access_token);
    sessionStorage.removeItem(VIEWED_ACCOUNT_IDS_KEY);
    sessionStorage.removeItem(VIEWED_OPPORTUNITY_IDS_KEY);
    setAnswered({ token: data.access_token, name: data.user.display_name || data.user.username });
    setSignIn({ kind: "idle" });
    notifySessionChanged();
  }

  // Signed in: the page says who, points to the Dashboard and offers Sign out in place of the form; signing in
  // as someone else is sign out, then sign in (owner, 27 September 2026).
  const name = session.user?.display_name ?? (answered && answered.token === session.token ? answered.name : null);

  return (
    <section>
      <h2>Sign in</h2>

      {!session.mounted ? (
        <p className="helper-text">Checking the session...</p>
      ) : session.token !== null ? (
        <div className="form-card form-card-narrow">
          <p className="action-feedback">
            {name ? (
              <>
                You are signed in as <strong>{name}</strong>.
              </>
            ) : (
              "You are signed in."
            )}{" "}
            Click <a href="/">here</a> to view the Dashboard.
          </p>
          <div className="form-actions">
            <button type="button" onClick={signOut}>
              Sign out
            </button>
          </div>
        </div>
      ) : (
        <>
          <p>
            {SHOW_DEMO_CREDENTIALS
              ? "Sign in with one of the test users listed below."
              : "Sign in with the username and password you were given."}
          </p>

          <form onSubmit={handleSubmit} className="form-card form-card-narrow">
            <label className="field-stack">
              Username
              <input value={username} onChange={(event) => setUsername(event.target.value)} />
            </label>

            <label className="field-stack">
              Password
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>

            <div className="form-actions">
              <button type="submit">Sign in</button>
            </div>

            {signIn.kind === "signing-in" && <p className="action-feedback helper-text">Signing in...</p>}
            {signIn.kind === "failed" && <p className="action-feedback text-danger">{signIn.message}</p>}
          </form>

          {SHOW_DEMO_CREDENTIALS && (
            <div className="content-card">
              <h3>Test users</h3>
              <ul>
                <li>admin1 / password</li>
                <li>sales1 / password</li>
                <li>manager1 / password</li>
                <li>finance1 / password</li>
                <li>ops1 / password</li>
                <li>readonly1 / password</li>
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
