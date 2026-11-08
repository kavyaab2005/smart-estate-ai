import { Link, useNavigate } from 'react-router-dom';

function Navbar() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    navigate('/login');
  };

  const linkClass = "text-line hover:text-clay text-sm font-medium transition-colors";

  return (
    <nav className="flex justify-between items-center px-6 py-4 bg-ink">
      <Link to="/" className="font-serif font-semibold text-lg text-white no-underline">
        SmartEstate AI
      </Link>

      <div className="flex gap-5 items-center">
        <Link to="/search" className={linkClass}>Search</Link>
        <Link to="/map" className={linkClass}>Map</Link>

        {!token && (
          <>
            <Link to="/login" className={linkClass}>Login</Link>
            <Link to="/register" className={linkClass}>Register</Link>
          </>
        )}

        {token && role === 'buyer' && <Link to="/buyer" className={linkClass}>Dashboard</Link>}
        {token && role === 'agent' && <Link to="/agent" className={linkClass}>Dashboard</Link>}
        {token && role === 'admin' && <Link to="/admin" className={linkClass}>Dashboard</Link>}

        {token && (
          <>
            <Link to="/chat" className={linkClass}>Chat</Link>
            <Link to="/compare" className={linkClass}>Compare</Link>
            <Link to="/favorites" className={linkClass}>Favorites</Link>
            <Link to="/verify-documents" className={linkClass}>Verify Documents</Link>
          </>
        )}

        {token && (
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 text-sm font-medium text-ink bg-clay hover:bg-clay-dark rounded-md transition-colors"
          >
            Logout
          </button>
        )}
      </div>
    </nav>
  );
}

export default Navbar;