import React from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, BookOpen, Tag, ArrowRight } from 'lucide-react';
import MathRenderer from './MathRenderer';

export default function SummaryGridTable({ entity }) {
  if (!entity) return null;

  const isTheorem = entity.type === 'theorem';
  const rawRows = entity.raw_rows || [];

  // Helper to find raw row value by header
  const getRowValue = (headers) => {
    const list = Array.isArray(headers) ? headers : [headers];
    for (const r of rawRows) {
      const hClean = r[0].replace(/^"|"$/g, '').trim();
      if (list.includes(hClean)) {
        return r[1];
      }
    }
    return '';
  };

  // Determine row order according to Munkres topology documentation
  const rowConfig = isTheorem
    ? [
        { header: 'Theorem', value: entity.id, type: 'title' },
        { header: 'Label', value: entity.label, type: 'label' },
        { header: 'AlternateNames', value: getRowValue(['AlternateNames', 'AlternateNames']), type: 'text' },
        { header: 'QualifyingObjects', value: getRowValue(['QualifyingObjects', 'Arguments']), type: 'math' },
        { header: 'Notation', value: getRowValue('Notation'), type: 'math' },
        { header: 'Restrictions', value: getRowValue('Restrictions'), type: 'math_multi' },
        { header: 'Statement', value: getRowValue(['Statement', 'Output', 'Expression']), type: 'math_multi' },
        { header: 'References', value: getRowValue('References'), type: 'references' },
        { header: 'RelatedConcepts', value: '', type: 'related' }
      ]
    : [
        { header: 'Math', value: entity.id, type: 'title' },
        { header: 'Label', value: entity.label, type: 'label' },
        { header: 'AlternateNames', value: getRowValue('AlternateNames'), type: 'text' },
        { header: 'Arguments', value: getRowValue(['Arguments', 'QualifyingObjects']), type: 'math' },
        { header: 'Notation', value: getRowValue('Notation'), type: 'math' },
        { header: 'Restrictions', value: getRowValue('Restrictions'), type: 'math_multi' },
        { header: 'Expression', value: getRowValue(['Expression', 'Output', 'Statement']), type: 'math_multi' },
        { header: 'References', value: getRowValue('References'), type: 'references' },
        { header: 'RelatedConcepts', value: '', type: 'related' },
        { header: 'RelatedTheorems', value: '', type: 'related_theorems' }
      ];

  const outgoing = entity.outgoing_relationships || [];

  const renderCellContent = (row) => {
    if (row.type === 'title') {
      return (
        <div className="font-mono text-base font-bold text-slate-900 flex items-center space-x-2">
          <span>{row.value}</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-sans border border-slate-200">
            {entity.type === 'concept' ? 'GeneralTopologyConcept' : 'GeneralTopologyTheorem'}
          </span>
        </div>
      );
    }

    if (row.type === 'label') {
      return (
        <div className="text-base font-medium text-slate-800">
          "{row.value}"
        </div>
      );
    }

    if (row.type === 'math' || row.type === 'math_multi') {
      if (!row.value) return <span className="text-slate-400 italic text-sm">None</span>;
      return (
        <div className="py-0.5">
          <MathRenderer math={row.value} inline={true} />
        </div>
      );
    }

    if (row.type === 'references') {
      if (!row.value) return <span className="text-slate-400 italic text-sm">None</span>;
      // Clean citation text
      const cleanRef = row.value.replace(/\\text\{([^}]*)\}/g, '$1').replace(/\$/g, '');
      return (
        <div className="flex items-start space-x-2 text-sm text-slate-700 font-serif">
          <BookOpen className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <span>{cleanRef}</span>
        </div>
      );
    }

    if (row.type === 'related' || row.type === 'related_theorems') {
      const filterType = row.type === 'related' ? 'RelatedConcepts' : 'RelatedTheorems';
      const items = outgoing.filter(o => o.rel_type === filterType || (row.type === 'related' && !o.rel_type));

      if (items.length === 0) {
        return <span className="text-slate-400 italic text-sm">No related {row.type === 'related' ? 'concepts' : 'theorems'} listed</span>;
      }

      return (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <Link
              key={`${item.rel_type}-${item.id}`}
              to={`/entity/${encodeURIComponent(item.id)}`}
              className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold shadow-xs transition-all hover:scale-105 hover:shadow-sm"
              style={{
                backgroundColor: item.type === 'concept' ? '#B2FFB2' : '#FFFF80',
                color: '#1E293B',
                border: '1px solid #CBD5E1'
              }}
            >
              <span>{item.label}</span>
              <ArrowRight className="w-3 h-3 opacity-60" />
            </Link>
          ))}
        </div>
      );
    }

    return <div className="text-sm text-slate-700">{row.value || <span className="text-slate-400 italic">None</span>}</div>;
  };

  return (
    <div className="bg-white rounded-xl shadow-md border border-slate-300 overflow-hidden">
      <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: entity.type === 'concept' ? '#B2FFB2' : '#FFFF80', border: '1px solid #94A3B8' }}></span>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Wolfram Language Summary Grid — {entity.type === 'concept' ? 'GeneralTopologyConcept' : 'GeneralTopologyTheorem'}
          </span>
        </div>
        <span className="text-xs font-mono text-slate-400">ID: {entity.id}</span>
      </div>

      <div className="overflow-x-auto">
        <table className="summary-grid-table">
          <tbody>
            {rowConfig.map((row, idx) => {
              // Skip empty optional rows
              if (!row.value && (row.header === 'AlternateNames' || row.header === 'Notation')) {
                return null;
              }
              return (
                <tr key={`${row.header}-${idx}`}>
                  <th scope="row" className="align-top">
                    <span className="font-semibold text-slate-800 text-sm">{row.header}</span>
                  </th>
                  <td className="align-top">
                    {renderCellContent(row)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
