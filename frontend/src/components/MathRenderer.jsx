import React, { useEffect, useRef, useState } from 'react';

export default function MathRenderer({ math, inline = false, className = "" }) {
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
  }, [math, inline]);

  if (!math) return null;

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
