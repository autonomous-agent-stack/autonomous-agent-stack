import React, { useState, useEffect, useRef } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import {
  Activity, ShieldAlert, Cpu, Database, Fingerprint, Layers, Zap, CheckCircle2
} from 'lucide-react';

const SuperAgentDashboardV2 = () => {
  const [wsStatus, setWsStatus] = useState('connecting');
  const [telemetry, setTelemetry] = useState([]);
  const [agents, setAgents] = useState([]);
  const [lockStatus, setLockStatus] = useState('secure'); // secure, pending, unlocked
  const wsRef = useRef(null);

  // 模拟 WebSocket 连接与数据接收 (实际接入时替换为真实的 ws:// URL)
  useEffect(() => {
    // 模拟数据初始化
    const initialData = Array.from({ length: 20 }, (_, i) => ({
      time: i, cpu: 20 + Math.random() * 10, memory: 40 + Math.random() * 5
    }));
    setTelemetry(initialData);
    setWsStatus('connected');

    const mockAgents = [
      { id: 'codex', name: '架构总师', role: 'Redis/PG 维护', status: 'idle', ops: 0 },
      { id: 'glm5-sec', name: '首席安全官', role: 'WebAuthn 监控', status: 'monitoring', ops: 12 },
      { id: 'glm5-evo', name: '演化专家', role: 'Skill 沙盒', status: 'standby', ops: 0 },
      { id: 'glm4-hub', name: '通信网关', role: 'WS 广播', status: 'active', ops: 450 },
    ];
    setAgents(mockAgents);

    // 模拟 100ms 的实时遥测推流
    const interval = setInterval(() => {
      setTelemetry(prev => {
        const newData = [...prev.slice(1), {
          time: prev[prev.length - 1].time + 1,
          cpu: 20 + Math.random() * 30,
          memory: 40 + Math.random() * 10
        }];
        return newData;
      });

      // 随机闪烁通信网关的 OPS
      setAgents(prev => prev.map(a =>
        a.id === 'glm4-hub' ? { ...a, ops: Math.floor(400 + Math.random() * 200) } : a
      ));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleWebAuthnRequest = () => {
    setLockStatus('pending');
    // 模拟调用 WebAuthn API
    setTimeout(() => setLockStatus('unlocked'), 2000);
    setTimeout(() => setLockStatus('secure'), 5000);
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-slate-800 font-sans p-8">
      {/* 顶部状态栏 */}
      <header className="max-w-7xl mx-auto flex justify-between items-end mb-8 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-slate-900 mb-1">
            Universal <span className="font-medium text-slate-600">Matrix</span> V2.0
          </h1>
          <p className="text-[10px] uppercase tracking-widest text-slate-400">
            Distributed Core • Redis Bus • FIDO2 Secured
          </p>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <div className="flex flex-col items-end">
            <span className="text-[9px] uppercase tracking-widest text-slate-400 mb-1">Telemetry WS</span>
            <div className="flex items-center gap-2 font-medium">
              <div className={`w-1.5 h-1.5 rounded-full ${wsStatus === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-amber-500'}`} />
              <span className="text-slate-600 text-xs">100ms Duplex</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* 左侧：物理性能与安全锁 (4列) */}
        <div className="lg:col-span-4 space-y-6">
          {/* 安全隔离区 */}
          <section className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
            <div className="flex justify-between items-center mb-6 relative z-10">
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2"><Fingerprint size={14} /> FIDO2 物理锁
              </h3>
              <span className={`text-[9px] px-2 py-0.5 rounded uppercase font-bold tracking-widest ${
                lockStatus === 'secure' ? 'bg-green-50 text-green-600' :
                lockStatus === 'pending' ? 'bg-amber-50 text-amber-600 animate-pulse' : 'bg-red-50 text-red-600'
              }`}>
                {lockStatus === 'secure' ? 'LOCKED' : lockStatus === 'pending' ? 'VERIFYING...' : 'UNLOCKED'}
              </span>
            </div>

            <div className="relative z-10 p-4 border border-slate-100 rounded-xl bg-slate-50 flex flex-col items-center justify-center text-center space-y-3">
              <ShieldAlert size={24} className={lockStatus === 'secure' ? 'text-slate-300' : 'text-amber-500'} />
              <p className="text-xs text-slate-500 font-light">拦截高危指令，挂起等待授权</p>
              <button
                onClick={handleWebAuthnRequest}
                disabled={lockStatus !== 'secure'}
                className="w-full mt-2 bg-white border border-slate-200 hover:border-slate-300 text-slate-600 text-xs py-2 rounded-lg transition-all"
              >
                模拟触控 ID 签名
              </button>
            </div>
          </section>

          {/* 实时系统消耗波形 */}
          <section className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2">
              <Activity size={14} /> 宿主机负载 (Real-time)
            </h3>
            <div className="h-32 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={telemetry} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#94a3b8" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" hide />
                  <YAxis hide domain={[0, 100]} />
                  <Tooltip contentStyle={{ fontSize: '10px', borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}/>
                  <Area type="monotone" dataKey="cpu" stroke="#64748b" fillOpacity={1} fill="url(#colorCpu)" strokeWidth={2} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-between mt-4 text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1"><Cpu size={12}/> CPU: {telemetry[telemetry.length-1]?.cpu.toFixed(1)}%</span>
              <span className="flex items-center gap-1"><Database size={12}/> RAM: {telemetry[telemetry.length-1]?.memory.toFixed(1)}%</span>
            </div>
          </section>
        </div>

        {/* 右侧：分布式算力矩阵 (8列) */}
        <div className="lg:col-span-8 space-y-6">
          <section className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <Layers size={14} /> 异构算力节点矩阵 (6 Agents)
              </h3>
              <div className="flex items-center gap-2 text-[10px] uppercase font-bold text-slate-400">
                <Zap size={12} className="text-amber-400"/> Event Bus: Redis Pub/Sub
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-grow">
              {agents.map((agent) => (
                <div key={agent.id} className="p-5 border border-slate-100 rounded-xl bg-slate-50 flex flex-col justify-between hover:border-slate-300 transition-all">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="font-medium text-slate-700 block text-sm">{agent.name}</span>
                      <span className="text-[10px] text-slate-400">{agent.role}</span>
                    </div>
                    <span className={`text-[9px] px-2 py-0.5 rounded uppercase font-bold tracking-wider
                      ${agent.status === 'active' || agent.status === 'monitoring' ? 'bg-slate-200 text-slate-600' :
                      agent.status === 'standby' ? 'bg-slate-100 text-slate-400' : 'bg-slate-100 text-slate-400'}`}>
                      {agent.status}
                    </span>
                  </div>
                  <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between items-center text-xs text-slate-500 font-mono">
                    <span>Node ID: {agent.id.toUpperCase()}</span>
                    <span className={agent.ops > 0 ? 'text-slate-700 font-bold' : ''}>{agent.ops} OPS</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default SuperAgentDashboardV2;
