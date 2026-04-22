import React from 'react';
import { 
  Database, 
  Zap, 
  ShieldCheck, 
  Activity,
  History,
  Download,
  BrainCircuit,
  Newspaper,
  Terminal,
  Layers,
  RefreshCcw,
  LineChart as LineChartIcon
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer
} from 'recharts';

// Dados simulados de evolução da qualidade
const qualitySeries = [
  { time: '01/04', loss: 0.082, acc: 71 },
  { time: '05/04', loss: 0.075, acc: 74 },
  { time: '10/04', loss: 0.061, acc: 79 },
  { time: '15/04', loss: 0.054, acc: 82 },
  { time: '19/04', loss: 0.042, acc: 85 },
];

export const NewsAI: React.FC = () => {
  const [isValidating, setIsValidating] = React.useState(false);

  const handleValidate = async () => {
    setIsValidating(true);
    try {
      const res = await fetch('http://localhost:8000/events/trigger', { method: 'POST' });
      if (res.ok) {
        // O próprio backend vai gerar um SystemEvent que aparecerá no NotificationOverlay
        console.log("Validação concluída");
      }
    } catch (error) {
      console.error("Erro ao validar integridade:", error);
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <div className="p-4 space-y-8 text-white min-h-screen">
      
      {/* Header com Timestamps principais */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div>
          <h2 className="text-3xl font-black flex items-center gap-3">
            <BrainCircuit className="text-[#00FFB2]" size={32} />
            Métricas de IA & Dados
          </h2>
          <p className="text-gray-500 font-medium">Relatório Detalhado de Performance e Integridade</p>
        </div>
        
        <div className="flex flex-wrap gap-4">
          <div className="bg-[#161a23] px-6 py-3 rounded-2xl border border-white/5 flex items-center gap-4">
             <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
                <History size={18} />
             </div>
             <div>
                <p className="text-[10px] text-gray-500 font-black uppercase">Último Treinamento</p>
                <p className="text-sm font-bold">19 Abr 2026 - 10:45</p>
             </div>
          </div>
          <div className="bg-[#161a23] px-6 py-3 rounded-2xl border border-white/5 flex items-center gap-4">
             <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
                <Download size={18} />
             </div>
             <div>
                <p className="text-[10px] text-gray-500 font-black uppercase">Último Download</p>
                <p className="text-sm font-bold">Hoje - 11:22</p>
             </div>
          </div>
        </div>
      </div>

      {/* Grid de Métricas de Volume e Qualidade */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Quantidade de Dados */}
        <div className="bg-[#161a23] border border-white/5 p-6 rounded-[24px]">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 rounded-xl bg-orange-500/10 text-orange-500">
               <Layers size={20} />
            </div>
            <span className="text-[10px] font-black text-gray-500 uppercase">Volume Total</span>
          </div>
          <h3 className="text-2xl font-black">2.45M</h3>
          <p className="text-[10px] text-gray-500 font-bold uppercase mt-1">Velas & Ticks Processados</p>
          <div className="mt-4 pt-4 border-t border-white/5 flex justify-between">
             <span className="text-[10px] font-bold text-gray-400">WIN (1.2M)</span>
             <span className="text-[10px] font-bold text-gray-400">WDO (1.25M)</span>
          </div>
        </div>

        {/* Qualidade do Treinamento */}
        <div className="bg-[#161a23] border border-white/5 p-6 rounded-[24px]">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 rounded-xl bg-[#00FFB2]/10 text-[#00FFB2]">
               <Activity size={20} />
            </div>
            <span className="text-[10px] font-black text-gray-500 uppercase">Precisão Atual</span>
          </div>
          <h3 className="text-2xl font-black">85.4%</h3>
          <p className="text-[10px] text-gray-500 font-bold uppercase mt-1">Nível de Confiança da IA</p>
          <div className="mt-4 pt-4 border-t border-white/5 flex justify-between">
             <span className="text-[10px] font-bold text-emerald-500">+2.4% vs last week</span>
          </div>
        </div>

        {/* Loss Rate (Qualidade Técnica) */}
        <div className="bg-[#161a23] border border-white/5 p-6 rounded-[24px]">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 rounded-xl bg-red-500/10 text-red-500">
               <LineChartIcon size={20} />
            </div>
            <span className="text-[10px] font-black text-gray-500 uppercase">Loss (Erro)</span>
          </div>
          <h3 className="text-2xl font-black">0.042</h3>
          <p className="text-[10px] text-gray-500 font-bold uppercase mt-1">Taxa de Convergência</p>
          <div className="mt-4 pt-4 border-t border-white/5 flex justify-between">
             <span className="text-[10px] font-bold text-red-400">Optimal Range: {'<'} 0.05</span>
          </div>
        </div>

        {/* Status Infra */}
        <div className="bg-[#161a23] border border-white/5 p-6 rounded-[24px]">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500">
               <Database size={20} />
            </div>
            <span className="text-[10px] font-black text-gray-500 uppercase">Banco Local</span>
          </div>
          <h3 className="text-2xl font-black">4.2 GB</h3>
          <p className="text-[10px] text-gray-500 font-bold uppercase mt-1">Espaço em Disco IA</p>
          <div className="mt-4 pt-4 border-t border-white/5 flex justify-between">
             <span className="text-[10px] font-bold text-gray-400">Status: Optimized</span>
          </div>
        </div>

      </div>

      {/* Gráfico de Qualidade (Evolução) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-[#161a23] border border-white/5 rounded-[32px] p-8">
           <div className="flex justify-between items-center mb-8">
              <h3 className="text-xl font-black flex items-center gap-2">
                <Zap className="text-yellow-500" size={20} />
                Evolução da Qualidade (Treinamento)
              </h3>
              <div className="flex gap-4">
                 <div className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-[#00FFB2]" />
                    <span className="text-[10px] font-black text-gray-500 uppercase">Accuracy</span>
                 </div>
              </div>
           </div>
           {/* Fix: Container com height mínimo para evitar width -1 */}
           <div className="h-[250px] min-h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={qualitySeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D2D2D" vertical={false} />
                <XAxis dataKey="time" stroke="#525252" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#525252" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1A1A1A', border: '1px solid #333', borderRadius: '12px' }}
                />
                <Area type="monotone" dataKey="acc" stroke="#00FFB2" strokeWidth={3} fill="#00FFB2" fillOpacity={0.1} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sidebar de Integridade */}
        <div className="bg-[#161a23] border border-white/5 rounded-[32px] p-8">
           <h3 className="text-xl font-black mb-6 flex items-center gap-2">
            <ShieldCheck className="text-emerald-500" size={20} />
            Metadados de Integridade
          </h3>
          <div className="space-y-4">
             {[
               { l: 'Consistência do Sync', v: '99.98%' },
               { l: 'Modelo Ativo', v: 'Llama 3.2' },
               { l: 'Hardware (Local GPU)', v: 'NVIDIA RTX' },
               { l: 'Conformidade Reg.', v: 'Auditada' },
             ].map((m, i) => (
               <div key={i} className="flex justify-between items-center p-4 bg-black/10 rounded-2xl border border-white/5">
                 <span className="text-[11px] font-bold text-gray-500 uppercase tracking-tighter">{m.l}</span>
                 <span className="text-xs font-black text-white">{m.v}</span>
               </div>
             ))}
          </div>
          <button 
            onClick={handleValidate}
            disabled={isValidating}
            className={`w-full mt-6 py-4 bg-white/5 hover:bg-white/10 text-white font-black text-[10px] uppercase tracking-widest rounded-2xl transition-all border border-white/5 flex items-center justify-center gap-2 ${isValidating ? 'opacity-50 cursor-wait' : ''}`}
          >
            <RefreshCcw size={14} className={isValidating ? 'animate-spin' : ''} />
            {isValidating ? 'Processando Integridade...' : 'Validar Integridade Agora'}
          </button>
        </div>
      </div>

      {/* Logs de Treinamento e Notícias */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-[#161a23] border border-white/5 rounded-[32px] p-8">
          <h3 className="text-xl font-black mb-6 flex items-center gap-3">
             <Newspaper className="text-[#00FFB2]" size={20} />
             Live Economic Feed
          </h3>
          <div className="space-y-3">
             {[
               { time: '11:15', msg: 'Payroll USA Data Received', impact: 'CRITICAL', c: 'text-red-500' },
               { time: '11:00', msg: 'MT5 Tick Data Synchronized', impact: 'SUCCESS', c: 'text-emerald-500' },
               { time: '10:45', msg: 'Bot Sniper Optimized (Training #42)', impact: 'IA', c: 'text-[#00FFB2]' },
               { time: '09:00', msg: 'Market Opening Audit Log', impact: 'INFO', c: 'text-gray-400' },
             ].map((log, i) => (
               <div key={i} className="flex items-center gap-4 p-3 bg-black/10 border border-white/5 rounded-2xl">
                  <span className="text-[10px] font-mono text-gray-700">{log.time}</span>
                  <p className="text-[11px] font-bold flex-1">{log.msg}</p>
                  <span className={`text-[9px] font-black ${log.c}`}>{log.impact}</span>
               </div>
             ))}
          </div>
        </div>

        <div className="bg-[#161a23] border border-white/5 rounded-[32px] p-8">
          <h3 className="text-xl font-black mb-6 flex items-center gap-3">
             <Terminal className="text-emerald-500" size={20} />
             IA Training Execution Console
          </h3>
          <div className="bg-black/40 rounded-2xl p-6 font-mono text-[10px] tracking-tight relative overflow-hidden h-[180px]">
             <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500/30" />
             <div className="space-y-1">
                <p className="text-emerald-500">$ training --bot-id sniper-m5 --cycles latest</p>
                <p className="text-gray-600">[2026-04-19 10:45:01] Processing cluster WIN$ (1.2M rows)</p>
                <p className="text-gray-600">[2026-04-19 10:45:15] Validating weight distribution...</p>
                <p className="text-gray-300">[2026-04-19 11:29:45] Loss: 0.042 | Epoch: 45/50</p>
                <p className="text-emerald-500 animate-pulse underline decoration-emerald-800 underline-offset-4">[RUNNING] Fine-tuning Llama-3.2 Context...</p>
                <p className="text-blue-400 mt-2">TOTAL_DATASET_SCORE: 0.9852</p>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};
