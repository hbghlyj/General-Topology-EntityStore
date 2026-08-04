import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, BookOpen, Share2, Copy, Check, ExternalLink, ArrowRight, GitBranch } from 'lucide-react';
import SummaryGridTable from '../components/SummaryGridTable';
import MathRenderer from '../components/MathRenderer';

export default function EntityDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [entity, setEntity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`/api/entity/${encodeURIComponent(id)}`)
      .then(res => {
        if (!res.ok) throw new Error("Entity not found");
        return res.json();
      })
      .then(data => {
        setEntity(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Detail error:", err);
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-24 text-center">
        <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <span className="text-sm font-semibold text-slate-600">Loading entity summary table...</span>
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
          <h2 className="text-xl font-bold text-slate-900">Entity Not Found</h2>
          <p className="text-sm text-slate-600 mt-2">
            Could not find a topological concept or theorem matching ID "{id}".
          </p>
          <div className="mt-6 flex items-center justify-center space-x-4">
            <Link
              to="/explorer"
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-slate-900 text-white font-semibold text-sm hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Explorer</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const incoming = entity.incoming_relationships || [];
  const outgoing = entity.outgoing_relationships || [];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center space-x-2 text-xs font-semibold text-slate-500 mb-6">
        <Link to="/explorer" className="hover:text-slate-900 transition-colors flex items-center space-x-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Entity Explorer</span>
        </Link>
        <span>/</span>
        <span className="text-slate-700 font-bold uppercase">
          {entity.type === 'concept' ? 'Concept' : 'Theorem'}
        </span>
        <span>/</span>
        <span className="text-slate-900 font-mono truncate max-w-xs">{entity.id}</span>
      </nav>

      {/* Title & Action Banner */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start space-x-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 font-bold text-lg shadow-sm"
            style={{
              backgroundColor: entity.type === 'concept' ? '#B2FFB2' : '#FFFF80',
              color: '#1E293B',
              border: '1px solid #CBD5E1'
            }}
          >
            {entity.type === 'concept' ? 'C' : 'T'}
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <span
                className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider"
                style={{
                  backgroundColor: entity.type === 'concept' ? '#B2FFB2' : '#FFFF80',
                  color: '#1E293B',
                  border: '1px solid #CBD5E1'
                }}
              >
                {entity.type === 'concept' ? 'GeneralTopologyConcept' : 'GeneralTopologyTheorem'}
              </span>
              <span className="text-xs font-mono text-slate-400">ID: {entity.id}</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-2 tracking-tight">
              {entity.label || entity.id}
            </h1>
          </div>
        </div>

        {/* Toolbar buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopyLink}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold text-xs transition-colors shadow-xs"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4 text-slate-500" />}
            <span>{copied ? 'Copied URL!' : 'Copy Link'}</span>
          </button>
          <Link
            to={`/?search=${encodeURIComponent(entity.label)}`}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors shadow-xs"
          >
            <Share2 className="w-4 h-4" />
            <span>View in Graph</span>
          </Link>
        </div>
      </div>

      {/* Main Canonical Munkres Summary Grid Table */}
      <div className="mt-6">
        <SummaryGridTable entity={entity} />
      </div>

      {/* Bidirectional Relationships Row */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Outgoing Related Concepts & Theorems */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
              <GitBranch className="w-5 h-5 text-emerald-600" />
              <h3 className="font-bold text-slate-900 text-base">
                Referenced Concepts & Theorems ({outgoing.length})
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Topological objects and theorems directly cited or used by this entity.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              {outgoing.length === 0 ? (
                <span className="text-xs italic text-slate-400">No outgoing references recorded.</span>
              ) : (
                outgoing.map((rel, idx) => (
                  <Link
                    key={`${rel.id}-${idx}`}
                    to={`/entity/${encodeURIComponent(rel.id)}`}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-semibold shadow-xs transition-all hover:scale-105"
                    style={{
                      backgroundColor: rel.type === 'concept' ? '#B2FFB2' : '#FFFF80',
                      color: '#1E293B',
                      border: '1px solid #CBD5E1'
                    }}
                  >
                    <span>{rel.label || rel.id}</span>
                    <ArrowRight className="w-3 h-3 opacity-60" />
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Incoming Referenced By */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
              <GitBranch className="w-5 h-5 text-amber-600 transform rotate-180" />
              <h3 className="font-bold text-slate-900 text-base">
                Referenced By / Incoming Connections ({incoming.length})
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Other topological concepts and theorems in Munkres that link to or rely on this entity.
            </p>

            <div className="mt-4 flex flex-wrap gap-2 max-h-56 overflow-y-auto">
              {incoming.length === 0 ? (
                <span className="text-xs italic text-slate-400">No incoming references recorded.</span>
              ) : (
                incoming.map((rel, idx) => (
                  <Link
                    key={`${rel.id}-${idx}`}
                    to={`/entity/${encodeURIComponent(rel.id)}`}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-semibold shadow-xs transition-all hover:scale-105"
                    style={{
                      backgroundColor: rel.type === 'concept' ? '#B2FFB2' : '#FFFF80',
                      color: '#1E293B',
                      border: '1px solid #CBD5E1'
                    }}
                  >
                    <span>{rel.label || rel.id}</span>
                    <ArrowRight className="w-3 h-3 opacity-60" />
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
