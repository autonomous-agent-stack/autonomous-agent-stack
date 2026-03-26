import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  ShieldCheck, 
  Cpu, 
  Zap, 
  Layers, 
  Terminal, 
  HardDrive,
  RefreshCw,
  Lock,
  Unlock,
  Wifi,
  WifiOff
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const RealtimeTelemetryDashboard = () => {
  const [stats, setStats] = useState({
    apple_double_cleaned: 0,
    ast_blocks: 0,
    matrix_active: false,
    cpu_load: 0,
    memory_usage: 0,
    heartbeat: 0
  });
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [webAuthnLocked, setWebAuthnLocked] = useState(true);
  const [cpuHistory, setCpuHistory] = useState([]);
  const [heartbeatHistory, setHeartbeatHistory] = useState([]);
  
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);

  // WebSocket 连接
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const wsUrl = `ws://${window.location.hostname}:8001/api/v1/telemetry/stream`;
        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          console.log('✅ WebSocket 连接成功');
          setWsConnected(true);
          reconnectAttempts.current = 0;
        };

        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            // 更新统计数据
            setStats({
              apple_double_cleaned: data.system_audit?.apple_double_cleaned || 0,
              ast_blocks: data.system_audit?.ast_blocks || 0,
              matrix_active: data.matrix_active || false,
              cpu_load: data.cpu_load || 0,
              memory_usage: data.memory_usage || 0,
              heartbeat: data.heartbeat || Date.now()
            });
            
            setAgents(data.agents || []);
            
            // 更新 CPU 历史记录
            setCpuHistory(prev => {
              const newHistory = [...prev, {
                time: new Date().toLocaleTimeString(),
                cpu: data.cpu_load || 0
              }];
              return newHistory.slice(-50); // 保留最近 50 个数据点
            });
            
            // 更新心跳历史记录
            setHeartbeatHistory(prev => {
              const newHistory = [...prev, {
                time: new Date().toLocaleTimeString(),
                heartbeat: data.heartbeat || 0
              }];
              return newHistory.slice(-50);
            });
            
            setLoading(false);
          } catch (error) {
            console.error('解析 WebSocket 消息失败:', error);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error('WebSocket 错误:', error);
          setWsConnected(false);
        };

        wsRef.current.onclose = () => {
          console.log('WebSocket 连接关闭');
          setWsConnected(false);
          
          // 自动重连（最多 5 次）
          if (reconnectAttempts.current < 5) {
            reconnectAttempts.current++;
            setTimeout(connectWebSocket, 3000);
          }
        };
      } catch (error) {
        console.error('WebSocket 连接失败:', error);
        setWsConnected(false);
      }
    };

    connectWebSocket();

    // 清理
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // WebAuthn 解锁
  const handleWebAuthnUnlock = async () => {
    try {
      // 调用 WebAuthn API
      const credential = await navigator.credentials.get({
        publicKey: {
          challenge: new Uint8Array(32),
          allowCredentials: [{
            type: 'public-key',
            id: new Uint8Array(32)
          }],
          userVerification: 'required'
        }
      });

      if (credential) {
        setWebAuthnLocked(false);
        console.log('✅ WebAuthn 验证成功');
      }
    } catch (error) {
      console.error('WebAuthn 验证失败:', error);
      alert('生物识别验证失败，请重试');
    }
  };

  // WebAuthn 锁定
  const handleWebAuthnLock = () => {
    setWebAuthnLocked(true);
    console.log('🔒 系统已锁定');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-slate-500">连接中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans p-6 lg:p-12">
      {/* Header */}
      <header className="max-w-6xl mx-auto flex flex-col md:flex-row md:items-center justify-between mb-12 border-b border-slate-200 pb-8">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-slate-900 mb-2">
            Super Agent Stack <span className="font-semibold text-blue-600">Telemetry</span>
          </h1>
          <p className="text-slate-500 font-light italic">实时遥测看板 (100ms 级别)</p>
        </div>
        <div className="flex items-center gap-6 mt-6 md:mt-0">
          {/* WebSocket 状态 */}
          <div className="flex flex-col items-end">
            <span className="text-xs uppercase tracking-widest text-slate-400">WebSocket</span>
            <span className="text-sm font-medium flex items-center gap-2">
              {wsConnected ? (
                <>
                  <Wifi size={16} className="text-green-500" />
                  <span className="text-green-600">Connected</span>
                </>
              ) : (
                <>
                  <WifiOff size={16} className="text-red-500" />
                  <span className="text-red-600">Disconnected</span>
                </>
              )}
            </span>
          </div>

          {/* WebAuthn 锁 */}
          <button
            onClick={webAuthnLocked ? handleWebAuthnUnlock : handleWebAuthnLock}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
              webAuthnLocked 
                ? 'bg-red-100 text-red-700 hover:bg-red-200' 
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            }`}
          >
            {webAuthnLocked ? (
              <>
                <Lock size={16} />
                <span>已锁定</span>
              </>
            ) : (
              <>
                <Unlock size={16} />
                <span>已解锁</span>
              </>
            )}
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
                <p className="text-2xl font-light">{stats.apple_double_cleaned}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">AST 拦截次数</p>
                <p className="text-2xl font-light text-red-500">{stats.ast_blocks}</p>
              </div>
            </div>
            <div className="mt-6 flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1"><HardDrive size={12} /> /Volumes/PS1008</span>
              <span className="flex items-center gap-1"><Cpu size={12} /> Sandbox: Docker</span>
            </div>
          </section>

          {/* 心跳监控 */}
          <section className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="text-xs uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
              <Activity size={14} /> 心跳监控
            </h3>
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={heartbeatHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="time" stroke="#94A3B8" fontSize={10} />
                  <YAxis stroke="#94A3B8" fontSize={10} />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="heartbeat" 
                    stroke="#3B82F6" 
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        </div>

        {/* Right Column: Agent Matrix */}
        <div className="lg:col-span-2 space-y-8">
          <section className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-xs uppercase tracking-widest text-slate-400 flex items-center gap-2">
                <Layers size={14} /> 智能体算力矩阵
              </h3>
              <div className="px-3 py-1 bg-blue-50 text-blue-600 text-[10px] font-bold rounded-full uppercase tracking-tighter">
                Real-time (100ms)
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {agents.map((agent, index) => (
                <div key={index} className="group p-5 border border-slate-100 rounded-xl hover:border-blue-100 hover:bg-blue-50/30 transition-all cursor-pointer relative overflow-hidden">
                  <div className="flex items-center justify-between mb-3 relative z-10">
                    <span className="font-medium text-slate-700">{agent.name}</span>
                    <div className={`w-2 h-2 rounded-full ${
                      agent.status === 'active' || agent.status === 'working' || agent.status === 'evolving' 
                        ? 'bg-green-500 animate-pulse' 
                        : 'bg-slate-300'
                    }`} />
                  </div>
                  <p className="text-sm text-slate-500 font-light relative z-10">{agent.task || agent.status}</p>
                </div>
              ))}
            </div>
          </section>

          {/* CPU 实时波形图 */}
          <section className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xs uppercase tracking-widest text-slate-400 flex items-center gap-2">
                <Cpu size={14} /> CPU 实时波形
              </h3>
              <span className="text-sm text-slate-600">{stats.cpu_load.toFixed(1)}%</span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={cpuHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="time" stroke="#94A3B8" fontSize={10} />
                  <YAxis stroke="#94A3B8" fontSize={10} domain={[0, 100]} />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="cpu" 
                    stroke="#64748B" 
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* Memory Usage */}
          <section className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xs uppercase tracking-widest text-slate-400 flex items-center gap-2">
                <HardDrive size={14} /> 内存使用
              </h3>
              <span className="text-sm text-slate-600">{stats.memory_usage.toFixed(1)} GB / 8.0 GB</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-4">
              <div 
                className="bg-blue-500 h-4 rounded-full transition-all duration-100"
                style={{ width: `${(stats.memory_usage / 8) * 100}%` }}
              />
            </div>
          </section>
        </div>
      </main>

      <footer className="max-w-6xl mx-auto mt-16 text-center">
        <p className="text-[10px] text-slate-400 uppercase tracking-[0.2em]">
          Real-time Telemetry | WebSocket: 100ms | WebAuthn: {webAuthnLocked ? 'Locked' : 'Unlocked'}
        </p>
      </footer>
    </div>
  );
};

export default RealtimeTelemetryDashboard;
