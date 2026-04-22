import { LayoutDashboard, Bot, Brain, FlaskConical, Settings, LogOut, History } from 'lucide-react';
import { clsx } from 'clsx';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'bots', label: 'Meus Bots', icon: Bot },
  { id: 'trades', label: 'Operações', icon: History },
  { id: 'news', label: 'IA & Notícias', icon: Brain },
  { id: 'backtesting', label: 'Backtesting', icon: FlaskConical },
  { id: 'settings', label: 'Configurações', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  return (
    <div className="w-64 bg-bg-card border-r border-border-card flex flex-col h-screen">
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 bg-brand-primary rounded-lg flex items-center justify-center text-bg-dark font-bold text-xl">
          IA
        </div>
        <h1 className="text-xl font-bold bg-gradient-to-r from-brand-primary to-brand-secondary bg-clip-text text-transparent">
          MT5 Controller
        </h1>
      </div>
      
      <nav className="flex-1 px-4 space-y-2 mt-4">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={clsx(
              "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
              activeTab === item.id 
                ? "bg-brand-primary/10 text-brand-primary" 
                : "text-gray-400 hover:bg-gray-800/50 hover:text-white"
            )}
          >
            <item.icon size={20} />
            <span className="font-medium">{item.label}</span>
          </button>
        ))}
      </nav>
      
      <div className="p-4 border-t border-border-card">
        <div className="bg-gray-800/30 rounded-2xl p-4 mb-4">
          <p className="text-xs text-gray-500 mb-1">Status do Sistema</p>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-brand-primary rounded-full animate-pulse" />
            <span className="text-sm font-medium">SINCRO OK</span>
          </div>
        </div>
        
        <button className="w-full flex items-center gap-3 px-4 py-3 text-red-400 hover:bg-red-400/10 rounded-xl transition-colors">
          <LogOut size={20} />
          <span className="font-medium">Sair</span>
        </button>
      </div>
    </div>
  );
};
