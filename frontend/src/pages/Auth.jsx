import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Auth({ mode }) {
  const isSignUp = mode === "signup";
  const { user, loading, signIn, signUp } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (loading) return <p className="p-8 text-center text-muted">Checking your session…</p>;
  if (user) return <Navigate to="/" replace />;

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isSignUp) await signUp(username, email, password);
      else await signIn(email, password);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-story">
        <Link to="/signin" className="auth-brand">
          <span className="auth-brand-icon" aria-hidden="true">M</span>
          <span>Meetwise</span>
        </Link>
        <div className="auth-story-copy">
          <p className="auth-story-eyebrow">MAKE EVERY MEETING COUNT</p>
          <h1>Good ideas deserve to be <em>remembered.</em></h1>
          <p>Bring your conversations together. Find the decisions, people, and next steps hiding in your meeting notes.</p>
          <div className="auth-quote">
            <span aria-hidden="true">“</span>
            <p>One place for the details that move your work forward.</p>
          </div>
        </div>
        <div className="auth-story-art" aria-hidden="true">
          <span className="auth-art-ring auth-art-ring-one" />
          <span className="auth-art-ring auth-art-ring-two" />
          <span className="auth-art-card auth-art-card-back" />
          <span className="auth-art-card auth-art-card-front">
            <i /><i /><i /><b>✓</b><i /><i />
          </span>
          <span className="auth-art-spark">✦</span>
        </div>
        <p className="auth-story-foot">PRIVATE BY DESIGN <span>·</span> YOUR MEETINGS, YOUR WORKSPACE</p>
      </section>

      <section className="auth-form-side">
        <div className="auth-form-wrap">
          <p className="auth-mobile-brand">MEETWISE <span>·</span> TRANSCRIPT INTELLIGENCE</p>
          <p className="auth-form-eyebrow">{isSignUp ? "GET STARTED" : "YOUR WORKSPACE AWAITS"}</p>
          <h2>{isSignUp ? "Create your account" : "Welcome back"}</h2>
          <p className="auth-form-description">
            {isSignUp ? "A clearer view of every conversation starts here." : "Sign in to pick up where your team left off."}
          </p>

          <form onSubmit={submit} className="auth-form">
            {isSignUp && (
              <div className="auth-field">
                <label htmlFor="username">Username</label>
                <input
                  id="username"
                  type="text"
                  className="field"
                  autoComplete="nickname"
                  placeholder="Your name"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  required
                  maxLength={80}
                />
              </div>
            )}
            <div className="auth-field">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                className="field"
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                maxLength={255}
              />
            </div>
            <div className="auth-field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                className="field"
                autoComplete={isSignUp ? "new-password" : "current-password"}
                placeholder={isSignUp ? "At least 10 characters" : "Enter your password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={isSignUp ? 10 : 1}
                maxLength={128}
              />
            </div>

            {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}

            <button type="submit" className="auth-submit" disabled={busy}>
              {busy ? "Please wait…" : isSignUp ? "Create account" : "Sign in"}
              {!busy && <span aria-hidden="true">→</span>}
            </button>
          </form>

          <p className="auth-switch">
            {isSignUp ? "Already have an account?" : "New to Meetwise?"}{" "}
            <Link to={isSignUp ? "/signin" : "/signup"}>
              {isSignUp ? "Sign in" : "Create an account"}
            </Link>
          </p>
          <p className="auth-security"><span aria-hidden="true">◈</span> Your transcripts are private to your account.</p>
        </div>
      </section>
    </main>
  );
}
