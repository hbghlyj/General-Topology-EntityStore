import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Search, Share2, Table, BookOpen, X, ChevronRight, ExternalLink } from 'lucide-react';
import MathRenderer from './MathRenderer';

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [stats, setStats] = useState({ concepts: 216, theorems: 225, relationships: 1659 });
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('/api/stats')
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error("Failed to load stats:", err));
  }, []);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    const timer = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(query)}&limit=12`)
        .then(res => res.json())
        .then(data => {
          setResults(data.items || []);
          setLoading(false);
        })
        .catch(err => {
          console.error("Search error:", err);
          setLoading(false);
        });
    }, 180);
    return () => clearTimeout(timer);
  }, [query]);

  // Handle keyboard shortcut (Cmd/Ctrl + K) to open search
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      } else if (e.key === 'Escape' && searchOpen) {
        setSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [searchOpen]);

  const handleSelectResult = (id) => {
    setSearchOpen(false);
    setQuery('');
    navigate(`/entity/${encodeURIComponent(id)}`);
  };

  const navItemClass = (path) => {
    const active = location.pathname === path || (path !== '/' && location.pathname.startsWith(path));
    return `flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      active
        ? 'bg-slate-900 text-white shadow-sm'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
    }`;
  };

  return (
    <>
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Brand Logo */}
            <div className="flex items-center space-x-3">
              <Link to="/" className="flex items-center space-x-3 group">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-amber-500 flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform">
                  <Share2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900 text-lg tracking-tight">
                      General Topology EntityStore
                    </span>
                    <span className="hidden sm:inline-block text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                      James Munkres' Topology
                    </span>
                  </div>
                  <div className="flex items-center space-x-3 text-xs text-slate-500">
                    <span className="flex items-center space-x-1">
                      <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: '#B2FFB2', border: '1px solid #16A34A' }}></span>
                      <span><strong>{stats.concepts}</strong> Concepts</span>
                    </span>
                    <span>·</span>
                    <span className="flex items-center space-x-1">
                      <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: '#FFFF80', border: '1px solid #CA8A04' }}></span>
                      <span><strong>{stats.theorems}</strong> Theorems</span>
                    </span>
                    <span>·</span>
                    <span><strong>{stats.relationships}</strong> Connections</span>
                  </div>
                </div>
              </Link>
            </div>

            {/* Navigation Tabs */}
            <nav className="hidden md:flex items-center space-x-1">
              <Link to="/" className={navItemClass('/')}>
                <Share2 className="w-4 h-4" />
                <span>Relationship Graph</span>
              </Link>
              <Link to="/explorer" className={navItemClass('/explorer')}>
                <Table className="w-4 h-4" />
                <span>Entity Explorer</span>
              </Link>
              <Link to="/about" className={navItemClass('/about')}>
                <BookOpen className="w-4 h-4" />
                <span>About Dataset</span>
              </Link>
            </nav>

            {/* Search Trigger */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setSearchOpen(true)}
                className="flex items-center space-x-2 px-3 py-1.5 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-900 text-sm transition-colors shadow-xs"
              >
                <Search className="w-4 h-4 text-slate-500" />
                <span className="hidden sm:inline">Search topology...</span>
                <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-xs font-mono bg-white border border-slate-200 rounded text-slate-400">
                  ⌘K
                </kbd>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Instant Search Modal */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-200 flex items-center space-x-3 bg-slate-50/50">
              <Search className="w-5 h-5 text-slate-400" />
              <input
                type="text"
                autoFocus
                placeholder="Search concepts or theorems (e.g. Hausdorff, compact, partition, connected)..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full bg-transparent border-0 focus:outline-hidden text-slate-900 placeholder-slate-400 text-base font-medium"
              />
              <button
                onClick={() => setSearchOpen(false)}
                className="p-1 rounded-lg hover:bg-slate-200 text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="max-h-96 overflow-y-auto divide-y divide-slate-100">
              {loading && (
                <div className="p-6 text-center text-slate-500 text-sm">
                  Searching topology entities...
                </div>
              )}

              {!loading && query.trim() && results.length === 0 && (
                <div className="p-6 text-center text-slate-500 text-sm">
                  No concepts or theorems found for "{query}".
                </div>
              )}

              {!loading && results.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleSelectResult(item.id)}
                  className="p-3.5 hover:bg-slate-50 cursor-pointer flex items-center justify-between group transition-colors"
                >
                  <div className="flex items-start space-x-3 min-w-0">
                    <span
                      className="mt-0.5 px-2 py-0.5 rounded-full text-xs font-semibold shrink-0"
                      style={{
                        backgroundColor: item.type === 'concept' ? '#B2FFB2' : '#FFFF80',
                        color: '#1E293B',
                        border: '1px solid #CBD5E1'
                      }}
                    >
                      {item.type === 'concept' ? 'Concept' : 'Theorem'}
                    </span>
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-900 text-sm group-hover:text-emerald-700 truncate">
                        {item.label}
                      </div>
                      <div className="text-xs text-slate-500 truncate font-mono">
                        {item.id}
                      </div>
                      {item.statement && (
                        <div className="mt-1 text-xs text-slate-600 line-clamp-1 overflow-hidden">
                          <MathRenderer math={item.statement} inline={true} />
                        </div>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-slate-600 shrink-0" />
                </div>
              ))}

              {!query.trim() && (
                <div className="p-6 text-center text-slate-500 text-sm">
                  Type to search across 216 concepts and 225 theorems from Munkres' Topology.
                </div>
              )}
            </div>

            <div className="p-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 px-4">
              <span>Press <strong>ESC</strong> to close</span>
              <span>Showing results from Munkres' Topology</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
