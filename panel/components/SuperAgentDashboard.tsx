import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  ShieldCheck, 
  Cpu, 
  Zap, 
  Layers, 
  Eye, 
  Terminal, 
  HardDrive,
  RefreshCw,
  AlertTriangle
} from 'lucide-react';

const SuperAgentDashboard = () => {
  const [activeTab, setActiveTab] = useState('matrix');
  const [stats, setStats] = useState({
    cleanupCount: 0,
    astBlocks: 0,
    uptime: '0h 0m',
    memoryUsage: '0GB'
  });
  const [agents, setAgents] = useState([]);
  const [recentLogs, setRecentLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  // 获取实时数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/v1/system/health');
        const data = await response.json();
        
        setStats({
          cleanupCount: data.cleanup_count,
          astBlocks: data.ast_blocks,
          uptime: data.uptime,
          memoryUsage: data.memory_usage
        });
        setAgents(data.agents);
        setRecentLogs(data.recent_logs);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch system health:', error);
        setLoading(false);
      }
    };

    fetchData();
    // 每 30 秒刷新一次
    const interval = setInterval(fetchData, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans p-6 lg:p-12">
      {/* Header */}
      <header className="max-w-6xl mx-auto flex flex-col md:flex-row md:items-center justify-between mb-12 border-b border-slate-200 pb-8">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-slate-900 mb-2">
            Super Agent Stack <span className="font-semibold text-blue-600">Base</span>
          </h1>
          <p className="text-slate-500 font-light italic">现代化、去工厂化的多智能体执行底座</p>
        </div>
        <div className="flex items-center gap-6 mt-6 md:mt-0">
          <div className="flex flex-col items-end">
            <span className="text-xs uppercase tracking-widest text-slate-400">Host Status</span>
            <span className="text-sm font-medium flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" /> M1 Pro / Tailscale
            </span>
          </div>
          <button className="p-2 hover:bg-white rounded-full transition-all border border-transparent hover:border-slate-200">
            <RefreshCw size={20} className="text-slate-400" />
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Physical Metrics */}
        <div className="lg:col-span-1 space-y-8">
          <section className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="text-xs uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
              <ShieldCheck size={14} /> 物理防御层
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-slate-50 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">AppleDouble 清理</p>
                <p className="text-2xl font-light">{stats.cleanupCount}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">AST 拦截次数</p>
                <p className="text-2xl font-light text-red-500">{stats.astBlocks}</p>
              </div>
            </div>
            <div className="mt-6 flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1"><HardDrive size={12} /> /Volumes/PS1008</span>
              <span className="flex items-center gap-1"><Cpu size={12} /> Sandbox: Docker</span>
            </div>
          </section>

          <section className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="text-xs uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
              <Terminal size={14} /> 实时审计流
            </h3>
            <div className="space-y-4">
              {recentLogs.map(log => (
                <div key={log.id} className="text-sm border-l-2 border-slate-100 pl-4 py-1">
                  <p className="font-light text-slate-600 leading-relaxed">{log.msg}</p>
                  <span className="text-[10px] text-slate-400 mt-1 block uppercase">{log.time}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right Column: Agent Matrix & Vibe Graph */}
        <div className="lg:col-span-2 space-y-8">
          <section className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-xs uppercase tracking-widest text-slate-400 flex items-center gap-2">
                <Layers size={14} /> 智能体算力矩阵
              </h3>
              <div className="px-3 py-1 bg-blue-50 text-blue-600 text-[10px] font-bold rounded-full uppercase tracking-tighter">
                P4 Autonomous Active
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {agents.map(agent => (
                <div key={agent.id} className="group p-5 border border-slate-100 rounded-xl hover:border-blue-100 hover:bg-blue-50/30 transition-all cursor-pointer relative overflow-hidden">
                  <div className="flex items-center justify-between mb-3 relative z-10">
                    <span className="font-medium text-slate-700">{agent.name}</span>
                    <div className={`w-2 h-2 rounded-full ${agent.status === 'working' ? 'bg-green-500 animate-pulse' : 'bg-slate-300'}`} />
                  </div>
                  <p className="text-sm text-slate-500 font-light relative z-10">{agent.work}</p>
                  <div className={`absolute bottom-0 right-0 w-16 h-16 bg-${agent.color}-500/5 -mb-6 -mr-6 rounded-full group-hover:scale-150 transition-transform`} />
                </div>
              ))}
            </div>
          </section>

          {/* Vibe Graphing Visualization Placeholder */}
          <section className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-10">
              <h3 className="text-xs uppercase tracking-widest text-slate-400 flex items-center gap-2">
                <Zap size={14} /> MASFactory 编排拓扑 (Vibe Graph)
              </h3>
              <span className="text-xs text-slate-400">4 Nodes / 3 Channels</span>
            </div>
            
            <div className="relative h-48 flex items-center justify-center">
              {/* Simplified SVG DAG Illustration */}
              <svg width="100%" height="100%" viewBox="0 0 400 120">
                <defs>
                  <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                    <path d="M0,0 L0,6 L9,3 z" fill="#CBD5E1" />
                  </marker>
                </defs>
                <circle cx="50" cy="60" r="25" fill="#F8FAFC" stroke="#E2E8F0" />
                <text x="50" y="65" fontSize="10" textAnchor="middle" fill="#64748B">Input</text>
                
                <line x1="75" y1="60" x2="125" y2="60" stroke="#E2E8F0" strokeWidth="2" markerEnd="url(#arrow)" />
                
                <rect x="150" y="35" width="100" height="50" rx="8" fill="#F8FAFC" stroke="#E2E8F0" />
                <text x="200" y="65" fontSize="10" textAnchor="middle" fill="#64748B" fontWeight="600">PLANNER</text>
                
                <line x1="250" y1="60" x2="300" y2="60" stroke="#E2E8F0" strokeWidth="2" markerEnd="url(#arrow)" />
                
                <circle cx="350" cy="60" r="25" fill="#EFF6FF" stroke="#BFDBFE" />
                <text x="350" y="65" fontSize="10" textAnchor="middle" fill="#2563EB">MATRIX</text>
              </svg>
            </div>
          </section>
        </div>
      </main>

      <footer className="max-w-6xl mx-auto mt-16 text-center">
        <p className="text-[10px] text-slate-400 uppercase tracking-[0.2em]">
          End-to-End Encrypted | Audit Logs Persistence: 90 Days
        </p>
      </footer>
    </div>
  );
};

export default SuperAgentDashboard;
