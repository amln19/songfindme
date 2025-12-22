import { Link } from "react-router";
import { useAuth } from "../context/AuthContext.jsx";

const Navbar = () => {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-base-content/20">
      <div className="mx-auto max-w-7xl p-4">
        <div className="flex items-center justify-between">
          {/* Logo / Title */}
          <Link to="/" className="text-3xl font-bold font-sans tracking-tight">
            SongFindMe
          </Link>

          <div className="flex items-center gap-4">
            {/* Add Song - Only visible to Admins */}
            {user && user.role === "admin" && (
              <Link
                to="/add-song"
                className="btn btn-ghost hidden sm:inline-flex"
              >
                Add Song
              </Link>
            )}

            {/* Identify Song */}
            <Link
              to="/identify-song"
              className="btn btn-ghost hidden sm:inline-flex"
            >
              Identify Song
            </Link>

            {/* Divider */}
            <div className="divider divider-horizontal mx-0"></div>

            {/* Login / Signup Buttons */}
            {user ? (
              <div className="flex items-center gap-5">
                {/* History Button (If Logged In) */}
                <Link to="/history" className="btn btn-ghost">
                  History
                </Link>

                <span className="text-sm font-medium hidden sm:block">
                  Hi, {user.username} ({user.role})
                </span>
                <button onClick={logout} className="btn btn-outline btn-sm">
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-5">
                <Link to="/login" className="btn btn-primary btn-sm">
                  Login
                </Link>
                <Link to="/signup" className="btn btn-secondary btn-sm">
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Navbar;