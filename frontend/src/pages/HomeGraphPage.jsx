import React from 'react';
import CytoscapeGraph from '../components/CytoscapeGraph';

export default function HomeGraphPage() {
  return (
    <div className="w-full h-[calc(100vh-4rem)] flex flex-col bg-slate-900">
      <CytoscapeGraph />
    </div>
  );
}
