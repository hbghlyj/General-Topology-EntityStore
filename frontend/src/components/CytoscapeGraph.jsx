import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import cytoscape from 'cytoscape';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw, Filter, Search, ArrowRight, X, ExternalLink } from 'lucide-react';
import MathRenderer from './MathRenderer';

export default function CytoscapeGraph({ onNodeSelect }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('all'); // 'all', 'concept', 'theorem'
  const [searchQuery, setSearchQuery] = useState('');
  const [layoutName, setLayoutName] = useState('cose');
  const [selectedNode, setSelectedNode] = useState(null);
  const [graphStats, setGraphStats] = useState({ nodes: 0, edges: 0 });

  // Fetch graph data and initialize Cytoscape
  useEffect(() => {
    setLoading(true);
    fetch(`/api/graph?filter_type=${filterType}&limit=450`)
      .then(res => res.json())
      .then(data => {
        if (!containerRef.current) return;

        setGraphStats({
          nodes: data.nodes.length,
          edges: data.edges.length
        });

        const elements = [
          ...data.nodes.map(n => ({
            data: {
              id: n.id,
              label: n.label,
              type: n.type,
              color: n.color,
              statement: n.statement || ''
            }
          })),
          ...data.edges.map(e => ({
            data: {
              id: e.id,
              source: e.source,
              target: e.target,
              rel_type: e.rel_type
            }
          }))
        ];

        if (cyRef.current) {
          cyRef.current.destroy();
        }

        const cy = cytoscape({
          container: containerRef.current,
          elements: elements,
          style: [
            {
              selector: 'node',
              style: {
                'label': 'data(label)',
                'background-color': 'data(color)',
                'color': '#1e293b',
                'font-size': '10px',
                'font-weight': 'bold',
                'font-family': 'sans-serif',
                'text-valign': 'center',
                'text-halign': 'center',
                'text-wrap': 'wrap',
                'text-max-width': '90px',
                'width': '52px',
                'height': '52px',
                'border-width': 1.5,
                'border-color': '#64748b',
                'shape': 'round-rectangle',
                'transition-property': 'background-color, border-color, border-width, opacity',
                'transition-duration': '150ms'
              }
            },
            {
              selector: 'node[type = "concept"]',
              style: {
                'shape': 'ellipse',
                'border-color': '#16a34a'
              }
            },
            {
              selector: 'node[type = "theorem"]',
              style: {
                'shape': 'round-rectangle',
                'border-color': '#ca8a04'
              }
            },
            {
              selector: 'node:selected',
              style: {
                'border-width': 3.5,
                'border-color': '#0f172a',
                'box-shadow': '0 0 12px rgba(15, 23, 42, 0.4)'
              }
            },
            {
              selector: 'edge',
              style: {
                'width': 1.2,
                'line-color': '#cbd5e1',
                'target-arrow-color': '#cbd5e1',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'opacity': 0.7
              }
            },
            {
              selector: '.highlighted',
              style: {
                'border-width': 3,
                'border-color': '#0284c7',
                'opacity': 1
              }
            },
            {
              selector: '.dimmed',
              style: {
                'opacity': 0.15
              }
            }
          ],
          layout: {
            name: layoutName,
            animate: false,
            padding: 30,
            nodeDimensionsIncludeLabels: true,
            randomize: false,
            idealEdgeLength: 100,
            nodeOverlap: 20,
            refresh: 20,
            fit: true
          },
          minZoom: 0.2,
          maxZoom: 3.5,
          wheelSensitivity: 0.25
        });

        cyRef.current = cy;

        // Click event on nodes
        cy.on('tap', 'node', (evt) => {
          const nodeData = evt.target.data();
          setSelectedNode(nodeData);
          if (onNodeSelect) {
            onNodeSelect(nodeData);
          }
        });

        // Double click to navigate
        cy.on('dbltap', 'node', (evt) => {
          const nodeData = evt.target.data();
          navigate(`/entity/${encodeURIComponent(nodeData.id)}`);
        });

        // Click background to deselect
        cy.on('tap', (evt) => {
          if (evt.target === cy) {
            setSelectedNode(null);
          }
        });

        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load graph:", err);
        setLoading(false);
      });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [filterType]);

  // Handle Search & Highlighting
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;

    if (!searchQuery.trim()) {
      cy.elements().removeClass('highlighted dimmed');
      return;
    }

    const q = searchQuery.toLowerCase().trim();
    cy.batch(() => {
      cy.elements().removeClass('highlighted dimmed');
      const matched = cy.nodes().filter(node => {
        const d = node.data();
        return (
          d.label.toLowerCase().includes(q) ||
          d.id.toLowerCase().includes(q) ||
          (d.statement && d.statement.toLowerCase().includes(q))
        );
      });

      if (matched.length > 0) {
        cy.elements().addClass('dimmed');
        matched.removeClass('dimmed').addClass('highlighted');
        matched.connectedEdges().removeClass('dimmed');
        matched.neighborhood().removeClass('dimmed');
      }
    });
  }, [searchQuery]);

  const handleZoomIn = () => cyRef.current && cyRef.current.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current && cyRef.current.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current && cyRef.current.fit(cyRef.current.elements(), 40);

  const handleRelayout = (name) => {
    setLayoutName(name);
    if (cyRef.current) {
      cyRef.current.layout({
        name: name,
        animate: true,
        animationDuration: 400,
        padding: 30
      }).run();
    }
  };

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] bg-slate-900 overflow-hidden flex flex-col">
      {/* Top Floating Control Bar */}
      <div className="absolute top-4 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
        {/* Left: Filter by Type & Layout */}
        <div className="flex items-center space-x-2 bg-white/95 backdrop-blur-md px-3 py-2 rounded-xl shadow-lg border border-slate-200 pointer-events-auto">
          <Filter className="w-4 h-4 text-slate-500 shrink-0" />
          <span className="text-xs font-semibold text-slate-600">View:</span>
          <div className="flex bg-slate-100 p-0.5 rounded-lg text-xs font-medium">
            {[
              { id: 'all', label: 'All (441)' },
              { id: 'concept', label: 'Concepts (216)' },
              { id: 'theorem', label: 'Theorems (225)' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilterType(tab.id)}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  filterType === tab.id
                    ? 'bg-white text-slate-900 font-semibold shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <span className="text-slate-300">|</span>

          {/* Layout Selector */}
          <span className="text-xs font-semibold text-slate-600">Layout:</span>
          <select
            value={layoutName}
            onChange={(e) => handleRelayout(e.target.value)}
            className="text-xs bg-slate-100 border border-slate-200 rounded-md px-2 py-1 font-medium text-slate-700 focus:outline-hidden"
          >
            <option value="cose">Force Directed (CoSE)</option>
            <option value="grid">Grid Layout</option>
            <option value="circle">Circle Layout</option>
            <option value="concentric">Concentric</option>
          </select>
        </div>

        {/* Right: Search Highlight Input */}
        <div className="flex items-center space-x-2 bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-xl shadow-lg border border-slate-200 pointer-events-auto w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Highlight on graph (e.g. Hausdorff)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-transparent border-0 text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="text-slate-400 hover:text-slate-600">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Bottom Floating Toolbar & Legend */}
      <div className="absolute bottom-6 left-4 right-4 z-20 flex flex-wrap items-end justify-between gap-4 pointer-events-none">
        {/* Color Legend */}
        <div className="flex items-center space-x-4 bg-white/95 backdrop-blur-md px-4 py-2.5 rounded-xl shadow-lg border border-slate-200 pointer-events-auto text-xs font-medium text-slate-700">
          <div className="flex items-center space-x-2">
            <span className="w-3.5 h-3.5 rounded-full inline-block shadow-xs" style={{ backgroundColor: '#B2FFB2', border: '1.5px solid #16A34A' }}></span>
            <span>Concept (Green)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3.5 h-3.5 rounded-md inline-block shadow-xs" style={{ backgroundColor: '#FFFF80', border: '1.5px solid #CA8A04' }}></span>
            <span>Theorem (Yellow)</span>
          </div>
          <span className="text-slate-400">|</span>
          <span className="text-slate-500 font-mono">{graphStats.nodes} nodes · {graphStats.edges} edges</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-500 italic">Click node to inspect · Double-click to visit page</span>
        </div>

        {/* Zoom & Fit Toolbar */}
        <div className="flex items-center space-x-1.5 bg-white/95 backdrop-blur-md p-1.5 rounded-xl shadow-lg border border-slate-200 pointer-events-auto">
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleFit}
            title="Fit to Screen"
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleRelayout(layoutName)}
            title="Re-layout Graph"
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Selected Node Inspector Popup Panel */}
      {selectedNode && (
        <div className="absolute top-20 right-4 z-30 w-80 bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-200 p-4 transition-all animate-fade-in">
          <div className="flex items-start justify-between border-b border-slate-200 pb-2.5">
            <div className="flex items-center space-x-2">
              <span
                className="px-2 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider"
                style={{
                  backgroundColor: selectedNode.type === 'concept' ? '#B2FFB2' : '#FFFF80',
                  color: '#1E293B',
                  border: '1px solid #CBD5E1'
                }}
              >
                {selectedNode.type === 'concept' ? 'Concept' : 'Theorem'}
              </span>
              <span className="text-xs font-mono text-slate-400 truncate max-w-[140px]">
                {selectedNode.id}
              </span>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-slate-600 rounded-lg p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-3">
            <h3 className="font-bold text-slate-900 text-base leading-snug">
              {selectedNode.label}
            </h3>
            {selectedNode.statement ? (
              <div className="mt-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200 max-h-40 overflow-y-auto">
                <MathRenderer math={selectedNode.statement} inline={true} />
              </div>
            ) : (
              <div className="mt-2.5 text-xs italic text-slate-400">
                No statement preview available
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
            <button
              onClick={() => navigate(`/entity/${encodeURIComponent(selectedNode.id)}`)}
              className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs shadow-md transition-colors"
            >
              <span>View Full Summary Page</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Cytoscape Container */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-40">
          <div className="bg-white px-6 py-4 rounded-2xl shadow-2xl flex items-center space-x-3">
            <div className="w-5 h-5 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm font-semibold text-slate-700">Loading interactive topology graph...</span>
          </div>
        </div>
      )}
    </div>
  );
}
