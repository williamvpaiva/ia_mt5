import React, { useEffect, useState } from 'react';
import { X, CheckCircle, AlertCircle } from 'lucide-react';

interface SystemEvent {
  id: number;
  type: string;
  message: string;
  timestamp: string;
  data: any;
}

export const NotificationOverlay: React.FC = () => {
  const [events, setEvents] = useState<SystemEvent[]>([]);

  const fetchEvents = async () => {
    try {
      const response = await fetch('http://localhost:8000/events/');
      const data = await response.json();
      setEvents(data);
    } catch (error) {
      console.error("Erro ao buscar notificações:", error);
    }
  };

  const dismissEvent = async (id: number) => {
    try {
      await fetch(`http://localhost:8000/events/${id}/dismiss`, { method: 'POST' });
      setEvents(prev => prev.filter(e => e.id !== id));
    } catch (error) {
      console.error("Erro ao descartar evento:", error);
    }
  };

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 30000); // Poll a cada 30s
    return () => clearInterval(interval);
  }, []);

  if (events.length === 0) return null;

  return (
    <div className="fixed top-6 right-6 z-[9999] flex flex-col gap-4 max-w-sm w-full animate-in slide-in-from-right duration-500">
      {events.map((evt) => (
        <div 
          key={evt.id} 
          className="bg-[#161a23]/95 backdrop-blur-xl border border-white/10 p-5 rounded-[24px] shadow-2xl flex items-start gap-4 group hover:border-[#00FFB2]/30 transition-all cursor-pointer overflow-hidden relative"
          onClick={() => dismissEvent(evt.id)}
        >
          {/* Progress bar inferior simulada ou indicador de sucesso */}
          <div className="absolute bottom-0 left-0 h-1 bg-[#00FFB2]/20 w-full" />
          
          <div className={`p-2 rounded-xl flex-shrink-0 ${
            evt.type.includes('SUCCESS') ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'
          }`}>
            {evt.type.includes('SUCCESS') ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
          </div>

          <div className="flex-1">
            <div className="flex justify-between items-start mb-1">
              <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">
                Sistema Autônomo
              </span>
              <span className="text-[10px] font-mono text-gray-600">
                {new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <p className="text-xs font-bold text-gray-200 leading-relaxed pr-6">
              {evt.message}
            </p>
          </div>

          <button 
            className="absolute top-4 right-4 text-gray-600 hover:text-white transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      ))}
      
      {events.length > 1 && (
        <button 
          onClick={async (e) => {
            e.stopPropagation();
            await fetch('http://localhost:8000/events/clear-all', { method: 'DELETE' });
            setEvents([]);
          }}
          className="text-center text-[10px] font-black text-gray-500 uppercase hover:text-white transition-colors"
        >
          Limpar todas as notificações
        </button>
      )}
    </div>
  );
};
