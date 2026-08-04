import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Search, Filter, ArrowRight, BookOpen, ChevronLeft, ChevronRight, Grid, List } from 'lucide-react';
import MathRenderer from '../components/MathRenderer';

export default function ExplorerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const qParam = searchParams.get('q') || '';
  const typeParam = searchParams.get('type') || 'all';
  const sortParam = searchParams.get('sort') || 'label';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);

  const [q, setQ] = useState(qParam);
  const [typeFilter, setTypeFilter] = useState(typeParam);
  const [sortBy, setSortBy] = useState(sortParam);
  const [page, setPage] = useState(pageParam);

  const [data, setData] = useState({ items: [], total_count: 0, total_pages: 1 });
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'table'

  useEffect(() => {
    setLoading(true);
    fetch(`/api/entities?q=${encodeURIComponent(q)}&type_filter=${typeFilter}&sort_by=${sortBy}&page=${page}&limit=24`)
      .then(res => res.json())
      .then(res => {
        setData(res);
        setLoading(false);
      })
      .catch(err => {
        console.error("Explorer fetch error:", err);
        setLoading(false);
      });

    // Update URL params
    const params = {};
    if (q) params.q = q;
    if (typeFilter !== 'all') params.type = typeFilter;
    if (sortBy !== 'label') params.sort = sortBy;
    if (page > 1) params.page = String(page);
    setSearchParams(params, { replace: true });
  }, [q, typeFilter, sortBy, page]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top Title Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Topological Concepts & Theorems Explorer
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Browse, search, and filter all 216 concepts and 225 theorems from James Munkres' <span className="italic">Topology</span>.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200 self-start md:self-center">
          <button
            onClick={() => setViewMode('grid')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              viewMode === 'grid' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Grid Cards</span>
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              viewMode === 'table' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <List className="w-3.5 h-3.5" />
            <span>Table View</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="mt-6 bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center space-x-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search by name, ID, statement formula, restriction, or citation..."
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            className="w-full bg-transparent border-0 text-sm text-slate-900 placeholder-slate-400 focus:outline-hidden"
          />
          {q && (
            <button
              type="button"
              onClick={() => {
                setQ('');
                setPage(1);
              }}
              className="text-xs text-slate-400 hover:text-slate-600 font-medium"
            >
              Clear
            </button>
          )}
        </form>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Type Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-500">Type:</span>
            <div className="flex bg-slate-100 p-0.5 rounded-lg text-xs font-medium">
              {[
                { id: 'all', label: 'All (441)' },
                { id: 'concept', label: 'Concepts (216)' },
                { id: 'theorem', label: 'Theorems (225)' }
              ].map(t => (
                <button
                  key={t.id}
                  onClick={() => {
                    setTypeFilter(t.id);
                    setPage(1);
                  }}
                  className={`px-2.5 py-1 rounded-md transition-colors ${
                    typeFilter === t.id
                      ? 'bg-white text-slate-900 font-semibold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Sort Selector */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-500">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="text-xs bg-slate-100 border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-hidden"
            >
              <option value="label">Label (A-Z)</option>
              <option value="id">Identifier (A-Z)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Count & Status */}
      <div className="mt-4 flex items-center justify-between text-xs text-slate-500 px-1">
        <span>
          Showing <strong>{data.items.length}</strong> of <strong>{data.total_count}</strong> entities
          {q && <span> matching <strong>"{q}"</strong></span>}
        </span>
        <span>Page {data.page} of {data.total_pages}</span>
      </div>

      {/* Loading State */}
      {loading ? (
        <div className="py-24 text-center">
          <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <span className="text-sm font-medium text-slate-600">Loading topological entities...</span>
        </div>
      ) : data.items.length === 0 ? (
        <div className="py-16 text-center bg-white rounded-2xl border border-slate-200 mt-4">
          <div className="text-slate-400 mb-2">No concepts or theorems match your filters.</div>
          <button
            onClick={() => {
              setQ('');
              setTypeFilter('all');
              setPage(1);
            }}
            className="text-xs font-semibold text-emerald-600 hover:underline"
          >
            Reset all search filters
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid Cards View */
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {data.items.map((item) => (
            <Link
              key={item.id}
              to={`/entity/${encodeURIComponent(item.id)}`}
              className="group bg-white rounded-2xl p-5 border border-slate-200 hover:border-slate-300 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <span
                    className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider shrink-0"
                    style={{
                      backgroundColor: item.type === 'concept' ? '#B2FFB2' : '#FFFF80',
                      color: '#1E293B',
                      border: '1px solid #CBD5E1'
                    }}
                  >
                    {item.type === 'concept' ? 'Concept' : 'Theorem'}
                  </span>
                  <span className="text-xs font-mono text-slate-400 truncate max-w-[140px]">
                    {item.id}
                  </span>
                </div>

                <h3 className="mt-3 font-bold text-slate-900 text-base group-hover:text-emerald-700 transition-colors line-clamp-2">
                  {item.label || item.id}
                </h3>

                {/* MathJax Statement Snippet */}
                {item.statement && (
                  <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-100 text-sm overflow-x-auto max-h-24">
                    <MathRenderer math={item.statement} inline={true} />
                  </div>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-slate-500 group-hover:text-emerald-700">
                <span>View summary grid</span>
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
              </div>
            </Link>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="mt-4 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-xs uppercase font-bold text-slate-600">
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Label & Identifier</th>
                  <th className="py-3 px-4">Statement / Definition</th>
                  <th className="py-3 px-4">References</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-sm">
                {data.items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span
                        className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider inline-block"
                        style={{
                          backgroundColor: item.type === 'concept' ? '#B2FFB2' : '#FFFF80',
                          color: '#1E293B',
                          border: '1px solid #CBD5E1'
                        }}
                      >
                        {item.type === 'concept' ? 'Concept' : 'Theorem'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 min-w-[200px]">
                      <Link
                        to={`/entity/${encodeURIComponent(item.id)}`}
                        className="font-bold text-slate-900 hover:text-emerald-700 block"
                      >
                        {item.label || item.id}
                      </Link>
                      <span className="text-xs font-mono text-slate-400">{item.id}</span>
                    </td>
                    <td className="py-3.5 px-4 max-w-md">
                      {item.statement ? (
                        <div className="py-1">
                          <MathRenderer math={item.statement} inline={true} />
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-600 font-serif max-w-xs">
                      {item.references_text ? (
                        item.references_text.replace(/\\text\{([^}]*)\}/g, '$1').replace(/\$/g, '')
                      ) : (
                        <span className="text-slate-400 italic">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <Link
                        to={`/entity/${encodeURIComponent(item.id)}`}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-colors"
                      >
                        <span>View</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination Controls */}
      {data.total_pages > 1 && (
        <div className="mt-8 flex items-center justify-between border-t border-slate-200 pt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={data.page === 1}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-semibold text-slate-700 transition-colors shadow-xs"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          <div className="flex items-center space-x-1">
            {Array.from({ length: Math.min(5, data.total_pages) }, (_, i) => {
              let pageNum;
              if (data.total_pages <= 5) {
                pageNum = i + 1;
              } else if (data.page <= 3) {
                pageNum = i + 1;
              } else if (data.page >= data.total_pages - 2) {
                pageNum = data.total_pages - 4 + i;
              } else {
                pageNum = data.page - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`w-9 h-9 rounded-xl text-sm font-semibold transition-colors ${
                    data.page === pageNum
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
            disabled={data.page === data.total_pages}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-semibold text-slate-700 transition-colors shadow-xs"
          >
            <span>Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
