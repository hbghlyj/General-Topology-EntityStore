import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Database, Code2, Share2, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 animate-fade-in">
      <div className="bg-white rounded-3xl p-8 sm:p-12 shadow-sm border border-slate-200">
        {/* Title */}
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-600 to-amber-500 flex items-center justify-center text-white shadow-md">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
              About the General Topology EntityStore
            </h1>
            <p className="text-sm font-semibold text-slate-500 mt-1">
              An interactive topological knowledge graph and textbook explorer based on James Munkres' <span className="italic">Topology</span>.
            </p>
          </div>
        </div>

        {/* Overview Section */}
        <div className="mt-8 prose prose-slate max-w-none text-slate-700 space-y-4 text-base leading-relaxed">
          <p>
            The <strong>General Topology EntityStore</strong> web application is built on the Wolfram Language data repository resource <code>"General Topology EntityStore"</code>, which systematically encodes definitions, qualifying objects, mathematical statements, restrictions, and inter-concept relationships from James Munkres' classical textbook, <em>Topology</em> (2nd Edition, Prentice Hall, 2000).
          </p>
          <p>
            The database contains two primary entity types:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-6 not-prose">
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200">
              <div className="flex items-center space-x-2">
                <span className="w-4 h-4 rounded-full inline-block shadow-xs" style={{ backgroundColor: '#B2FFB2', border: '1px solid #16A34A' }}></span>
                <h3 className="font-bold text-slate-900 text-base">216 Topological Concepts</h3>
              </div>
              <p className="text-xs text-slate-600 mt-2 leading-normal">
                Includes foundational definitions such as <code>IsTopologicalSpace</code>, <code>IsConnected</code>, <code>IsHausdorff</code>, <code>IsCompact</code>, <code>IsNormal</code>, <code>IsParacompact</code>, and relational structures like <code>IsReflexiveRelationOn</code>.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200">
              <div className="flex items-center space-x-2">
                <span className="w-4 h-4 rounded-md inline-block shadow-xs" style={{ backgroundColor: '#FFFF80', border: '1px solid #CA8A04' }}></span>
                <h3 className="font-bold text-slate-900 text-base">225 Topological Theorems</h3>
              </div>
              <p className="text-xs text-slate-600 mt-2 leading-normal">
                Encodes major theorems from Munkres including Urysohn's Lemma, Tychonoff's Theorem, Baire Category Theorem, Ascoli's Theorem, Nagata-Smirnov Metrization Theorem, and fundamental connectivity & compactness criteria.
              </p>
            </div>
          </div>
        </div>

        {/* Technical Highlights */}
        <div className="mt-10 border-t border-slate-200 pt-8">
          <h2 className="text-xl font-bold text-slate-900">
            System Architecture & Features
          </h2>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-5 rounded-2xl border border-slate-200 bg-white">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold mb-3">
                <Database className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-sm">Relational & Graph Database</h3>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                All Wolfram Language entities are parsed into a normalized SQLite database (<code>topology.db</code>) with dedicated relational tables for <code>entities</code> and <code>relationships</code> (1,659 edges).
              </p>
            </div>

            <div className="p-5 rounded-2xl border border-slate-200 bg-white">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold mb-3">
                <Code2 className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-sm">Traditional Math Form LaTeX</h3>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                Wolfram Language syntax and custom box expressions (<code>SummaryGrid</code>) are recursively converted into standard textbook LaTeX and rendered dynamically on the frontend using <strong>MathJax 3</strong>.
              </p>
            </div>

            <div className="p-5 rounded-2xl border border-slate-200 bg-white">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold mb-3">
                <Share2 className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-sm">Interactive Cytoscape.js Graph</h3>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                A full-screen interactive node-link graph with D3-style force-directed CoSE layout, search highlighting, and node inspector popup for seamless exploration.
              </p>
            </div>
          </div>
        </div>

        {/* Munkres Summary Grid Explanation */}
        <div className="mt-10 border-t border-slate-200 pt-8">
          <h2 className="text-xl font-bold text-slate-900">
            Summary Grid Documentation Structure
          </h2>
          <p className="text-sm text-slate-600 mt-2">
            Each concept and theorem detail page replicates the structured Munkres properties table format:
          </p>

          <div className="mt-4 space-y-2 text-sm text-slate-700">
            <div className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span><strong>Theorem / Math:</strong> The canonical Wolfram symbol identifier (e.g. <code>EquivalenceClassesFormPartition</code>).</span>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span><strong>Label & AlternateNames:</strong> Standard textbook names and alternative terminology.</span>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span><strong>QualifyingObjects &amp; Arguments:</strong> Foundational sets, topologies, relations, or functions {'($X, \\tau, R, A$)'}.</span>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span><strong>Restrictions:</strong> Mathematical hypotheses and constraints {'(e.g. $X \\neq \\emptyset$, $R \\text{ is an equivalence relation}$)'}.</span>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span><strong>Statement / Expression / Output:</strong> The core mathematical formula or theorem conclusion in Traditional Math Form.</span>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span><strong>References & RelatedConcepts:</strong> Precise page citations to Munkres (2000) and clickable color-coded links to related concepts and theorems.</span>
            </div>
          </div>
        </div>

        {/* Footer CTA */}
        <div className="mt-10 border-t border-slate-200 pt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="text-xs text-slate-500 font-mono">
            Data Source: Wolfram Language Data Repository • James Munkres' Topology (2nd Ed)
          </div>

          <div className="flex items-center space-x-3">
            <Link
              to="/explorer"
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs shadow-xs transition-colors"
            >
              <span>Browse Explorer</span>
            </Link>
            <Link
              to="/"
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs shadow-xs transition-colors"
            >
              <span>Explore Interactive Graph</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
