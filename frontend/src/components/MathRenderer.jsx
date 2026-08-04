import React, { useEffect, useRef, useState } from 'react';

/**
 * MathRenderer
 * ------------
 * Rendering/layout only — no mathematical-semantic guessing happens here.
 *
 * In `flow` mode the backend supplies an explicit token structure
 * (entity.statement_tokens): a list of lines, each line a list of
 *   { t: 'text',  v }          wrappable prose
 *   { t: 'math',  v }          atomic inline-math chunk (LaTeX)
 *   { t: 'space', thin?:bool } explicit wrappable separator
 * and this component merely lays those tokens out so long statements wrap
 * over several lines instead of overflowing as one unbreakable formula.
 */
export default function MathRenderer({ math, inline = false, flow = false, tokens = null, className = "" }) {
  const containerRef = useRef(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    const typeset = () => {
      if (window.MathJax && window.MathJax.typesetPromise) {
        // Clear previous typeset attributes to allow re-render
        window.MathJax.typesetClear && window.MathJax.typesetClear([containerRef.current]);
        window.MathJax.typesetPromise([containerRef.current])
          .then(() => setRendered(true))
          .catch((err) => console.error("MathJax typeset error:", err));
      }
    };

    if (window.MathJax && window.MathJax.typesetPromise) {
      typeset();
    } else {
      // Check periodically until MathJax script finishes loading from CDN
      const interval = setInterval(() => {
        if (window.MathJax && window.MathJax.typesetPromise) {
          clearInterval(interval);
          typeset();
        }
      }, 150);
      return () => clearInterval(interval);
    }
  }, [math, inline, flow, tokens]);

  if (!math && !tokens) return null;

  // Flowing mode: lay out the backend-provided prose/math/space tokens.
  if (flow) {
    let lines = Array.isArray(tokens) ? tokens : null;
    if (!lines || lines.length === 0) {
      // No token structure available: fall back to one atomic formula per
      // explicit line (no semantic parsing in the rendering layer).
      lines = String(math || '')
        .split(/\\\\/)
        .map((l) => l.trim())
        .filter(Boolean)
        .map((l) => [{ t: 'math', v: l }]);
    }

    const renderTokens = (toks) =>
      toks.map((t, idx) => {
        if (t.t === 'text') {
          return <span key={idx} className="flow-text">{t.v}</span>;
        }
        if (t.t === 'space') {
          return <span key={idx}>{t.thin ? '\u2009' : ' '}</span>;
        }
        return <span key={idx} className="flow-math">{`$${t.v}$`}</span>;
      });

    return (
      <div ref={containerRef} className={`math-flow text-slate-800 ${className}`}>
        {lines.map((line, i) => (
          <div key={i} className="flow-line">{renderTokens(line)}</div>
        ))}
      </div>
    );
  }

  // Split multiple lines if separated by '\\' (from Restrictions / multi-item tables)
  const lines = typeof math === 'string'
    ? math.split(/\\\\/).map(l => l.trim()).filter(Boolean)
    : [String(math)];

  if (lines.length > 1) {
    return (
      <div ref={containerRef} className={`space-y-2 mathjax-container ${className}`}>
        {lines.map((line, idx) => (
          <div key={idx} className="flex items-center space-x-2 py-1 border-b border-slate-100 last:border-0">
            <span className="text-xs font-semibold text-slate-400 select-none">({idx + 1})</span>
            <span className="text-slate-800 text-base font-serif">
              {inline ? `$${line}$` : `\\[${line}\\]`}
            </span>
          </div>
        ))}
      </div>
    );
  }

  const singleLine = lines[0] || "";

  return (
    <span
      ref={containerRef}
      className={`mathjax-container inline-block ${className}`}
    >
      <span className="text-slate-800 text-base font-serif">
        {inline ? `$${singleLine}$` : `\\[${singleLine}\\]`}
      </span>
    </span>
  );
}
