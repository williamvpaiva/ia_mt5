import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { clsx } from 'clsx';

interface MetricCardProps {
  label: string;
  value: string;
  delta?: string;
  isPositive?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, delta, isPositive }) => {
  return (
    <div className="bg-bg-card border border-border-card p-6 rounded-2xl hover:border-brand-primary/30 transition-colors group">
      <p className="text-gray-400 text-sm font-medium mb-1">{label}</p>
      <div className="flex items-end justify-between">
        <h3 className="text-2xl font-bold text-white group-hover:text-brand-primary transition-colors">{value}</h3>
        {delta && (
          <div className={clsx(
            "flex items-center gap-1 text-sm font-bold px-2 py-1 rounded-lg",
            isPositive ? "text-emerald-400 bg-emerald-400/10" : "text-red-400 bg-red-400/10"
          )}>
            {isPositive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            {delta}
          </div>
        )}
      </div>
    </div>
  );
};
