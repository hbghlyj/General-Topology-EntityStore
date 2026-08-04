import React, { useEffect, useRef, useState } from 'react';

/**
 * Tokenize a LaTeX-ish statement string into a sequence of flow tokens so the
 * statement can be typeset as flowing, wrappable content (like a textbook
 * sentence) instead of one long unbreakable formula line:
 *   { type: 'text',  value }        -> plain wrappable prose (from \text{...})
 *   { type: 'math',  value }        -> atomic inline-math chunk
 *   { type: 'space', thin?: bool }  -> wrappable space between chunks
 */
function tokenizeFlow(src) {
  const s = String(src)
    // thin / en / hair spaces used as separators in the source LaTeX -> normal spaces
    .replace(/[\u2009\u200A\u2002\u2003\u205F]/g, ' ')
    .replace(/\\ /g, ' ');

  const tokens = [];

  const isPlainish = (chunk) => {
    const t = chunk.trim();
    if (!t) return false;
    // pure punctuation runs are plain text
    if (/^[.,;:!?]+$/.test(t)) return true;
    // word runs: every "word" longer than one character -> plain prose
    // (single-letter identifiers such as F, d, n stay math italic)
    if (/^[A-Za-z][A-Za-z'’-]*(\s+[A-Za-z][A-Za-z'’-]*)*$/.test(t)) {
      return t.split(/\s+/).every((w) => w.length > 1);
    }
    return false;
  };

  // relational / operator chunks get regular spaces around them
  const isRel = (chunk) =>
    /^\\(iff|implies|impliedby|subseteq|supseteq|in|ni|equiv|leq|geq|neq|prec|succ|to|longrightarrow|longmapsto|mapsto|rightarrow|leftarrow|land|lor)\b/.test(chunk.trim()) ||
    /^[=<>]|\\(eq|ne|le|ge)/.test(chunk.trim());

  // find the index just past a \text{...} group starting at position j (the '{')
  const matchTextGroup = (str, j) => {
    let depth = 0;
    for (let k = j; k < str.length; k++) {
      if (str[k] === '\\') { k++; continue; }
      if (str[k] === '{') depth++;
      else if (str[k] === '}') { depth--; if (depth === 0) return k + 1; }
    }
    return -1;
  };

  const pushMathBuf = (buf) => {
    if (!buf.trim()) return;
    // split at top-level spaces (outside {} and () groups, and outside \text{...})
    const chunks = [];
    let cur = '';
    let brace = 0;
    let paren = 0;
    for (let i = 0; i < buf.length; i++) {
      const c = buf[i];
      if (c === '\\') {
        if (buf.startsWith('text{', i + 1)) {
          const end = matchTextGroup(buf, i + 5);
          if (end > 0) { cur += buf.slice(i, end); i = end - 1; continue; }
        }
        cur += c + (buf[i + 1] ?? '');
        i++;
        continue;
      }
      if (c === '{') brace++;
      else if (c === '}') brace = Math.max(0, brace - 1);
      else if (c === '(') paren++;
      else if (c === ')') paren = Math.max(0, paren - 1);

      if (c === ' ' && brace === 0 && paren === 0) {
        if (cur.trim()) chunks.push(cur.trim());
        cur = '';
      } else {
        cur += c;
      }
    }
    if (cur.trim()) chunks.push(cur.trim());

    chunks.forEach((chunk, idx) => {
      if (idx > 0) {
        const prev = chunks[idx - 1];
        tokens.push({ type: 'space', thin: !isRel(prev) && !isRel(chunk) });
      }
      if (isPlainish(chunk)) tokens.push({ type: 'text', value: chunk });
      else tokens.push({ type: 'math', value: chunk });
    });
  };

  let i = 0;
  let buf = '';
  let brace = 0;
  let paren = 0;
  while (i < s.length) {
    const c = s[i];
    if (c === '\\') {
      if (s.startsWith('\\text', i) && s[i + 5] === '{') {
        const end = matchTextGroup(s, i + 5);
        if (end > 0) {
          const nextCh = s[end];
          if (paren === 0 && brace === 0 && nextCh !== '_' && nextCh !== '^') {
            // top-level \text{...} -> wrappable prose run
            pushMathBuf(buf);
            buf = '';
            tokens.push({ type: 'space' });
            tokens.push({ type: 'text', value: s.slice(i + 6, end - 1) });
            tokens.push({ type: 'space' });
          } else {
            // nested inside a paren group or carrying a sub/superscript
            // (e.g. \text{Hom}_{...}): keep it inside the math chunk
            buf += s.slice(i, end);
          }
          i = end;
          continue;
        }
      }
      buf += c + (s[i + 1] ?? '');
      i += 2;
      continue;
    }
    if (c === '{') brace++;
    else if (c === '}') brace = Math.max(0, brace - 1);
    else if (c === '(') paren++;
    else if (c === ')') paren = Math.max(0, paren - 1);
    buf += c;
    i++;
  }
  pushMathBuf(buf);

  // collapse duplicate / leading / trailing spaces
  const out = [];
  for (const t of tokens) {
    if (t.type === 'space') {
      if (out.length === 0) continue;
      if (out[out.length - 1].type === 'space') continue;
    }
    out.push(t);
  }
  while (out.length && out[out.length - 1].type === 'space') out.pop();

  // glue bare sub/superscript chunks (e.g. "_{A \\times A}") onto the previous
  // math chunk so they never render as a dangling script
  const glued = [];
  for (const t of out) {
    const prev = glued[glued.length - 1];
    const before = glued[glued.length - 2];
    if (
      t.type === 'math' && /^[_^]/.test(t.value) &&
      prev && prev.type === 'space' && before && before.type === 'math'
    ) {
      glued.pop(); // drop the separator
      before.value += t.value;
      continue;
    }
    glued.push(t);
  }
  return glued;
}

export default function MathRenderer({ math, inline = false, flow = false, className = "" }) {
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
  }, [math, inline, flow]);

  if (!math) return null;

  // Flowing mode: interleave wrappable prose with atomic inline math chunks so
  // long statements wrap over several lines instead of overflowing.
  if (flow) {
    const renderTokens = (toks) =>
      toks.map((t, idx) => {
        if (t.type === 'text') {
          return <span key={idx} className="flow-text">{t.value}</span>;
        }
        if (t.type === 'space') {
          return <span key={idx}>{t.thin ? '\u2009' : ' '}</span>;
        }
        return <span key={idx} className="flow-math">{`$${t.value}$`}</span>;
      });

    // explicit line separators ('\\') become their own wrapped flow lines
    const parts = String(math).split(/\\\\/).map(p => p.trim()).filter(Boolean);
    return (
      <div ref={containerRef} className={`math-flow text-slate-800 ${className}`}>
        {parts.map((part, i) => (
          <div key={i} className="flow-line">{renderTokens(tokenizeFlow(part))}</div>
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
