import os
import time
import ccxt
import pandas as pd
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()

class ProfessionalDashboard:
    def __init__(self):
        self.symbol = '1000PEPE/USDT'
        self.console = Console()
        self.exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
            'timeout': 7000 
        })
        self.exchange.set_sandbox_mode(True)
        self.initial_capital = 5000.0

    def get_data(self):
        try:
            # Coleta de dados com tratamento individual para evitar travamentos
            ticker = self.exchange.fetch_ticker(self.symbol)
            
            try:
                balance = self.exchange.fetch_balance()
                wallet_balance = float(balance['total']['USDT'])
            except:
                wallet_balance = self.initial_capital # Fallback se falhar
                
            try:
                positions = self.exchange.fetch_positions([self.symbol])
                pos = positions[0] if positions else None
            except:
                pos = None
                
            try:
                orders = self.exchange.fetch_open_orders(self.symbol)
            except:
                orders = []
                
            try:
                trades = self.exchange.fetch_my_trades(self.symbol, limit=5)
            except:
                trades = []
            
            return {
                'price': ticker['last'],
                'balance': wallet_balance,
                'pos': pos,
                'orders': sorted(orders, key=lambda x: x['price'], reverse=True),
                'trades': trades
            }
        except Exception as e:
            # Se o ticker falhar, o mercado caiu ou a conexão morreu
            return {"error": str(e)}

    def generate_layout(self, data):
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=10)
        )
        
        # HEADER (PERFORMANCE TOTAL)
        if data and "error" not in data:
            # PnL Flutuante (Aberto)
            unrealized_pnl = 0.0
            if data['pos'] and float(data['pos']['contracts']) > 0:
                unrealized_pnl = float(data['pos']['unrealizedPnl'])
            
            # Lucro Total (Saldo atual - Inicial)
            total_profit = data['balance'] - self.initial_capital
            # Lucro Realizado (Total - Flutuante)
            realized_profit = total_profit - unrealized_pnl
            
            retorno_pct = (total_profit / self.initial_capital) * 100
            retorno_style = "bold green" if total_profit >= 0 else "bold red"
            realized_style = "green" if realized_profit >= 0 else "red"
            
            header_content = (
                f"[bold white]PREÇO:[/] [yellow]{data['price']:.8f}[/] | "
                f"[bold white]SALDO:[/] [cyan]${data['balance']:.2f}[/] | "
                f"[bold white]RETORNO TOTAL:[/] [{retorno_style}]${total_profit:+.2f} ({retorno_pct:+.3f}%)[/] | "
                f"[bold white]REALIZADO:[/] [{realized_style}]${realized_profit:+.2f}[/]"
            )
        elif data and "error" in data:
            header_content = f"[bold red]ERRO DE CONEXÃO: {data['error'][:30]}...[/]"
        else:
            header_content = "[bold red]AGUARDANDO BINANCE (TESTNET)...[/]"
            
        layout["header"].update(Panel(header_content, style="blue"))

        # COLUNAS PRINCIPAIS
        main_table = Table.grid(expand=True)
        main_table.add_column(ratio=1)
        main_table.add_column(ratio=1)

        # TABELA DE ORDENS
        order_table = Table(title="Grade Ativa (Livro)", title_style="bold magenta", expand=True)
        order_table.add_column("Lado", justify="center")
        order_table.add_column("Preço", justify="right")
        order_table.add_column("Qtd", justify="right")

        if data and data['orders']:
            for o in data['orders'][:8]:
                color = "green" if o['side'] == 'buy' else "red"
                order_table.add_row(o['side'].upper(), f"{o['price']:.8f}", f"{o['amount']}", style=color)

        # TABELA DE POSIÇÃO
        pos_table = Table(title="Posição Em Aberto", title_style="bold yellow", expand=True)
        pos_table.add_column("Métrica", style="cyan")
        pos_table.add_column("Valor", justify="right")

        if data and data['pos'] and float(data['pos']['contracts']) > 0:
            p = data['pos']
            pos_table.add_row("Tamanho", f"{float(p['contracts'])}")
            pos_table.add_row("Entrada", f"{float(p['entryPrice']):.7f}")
            pnl = float(p['unrealizedPnl'])
            pnl_style = "bold green" if pnl >= 0 else "bold red"
            
            # Cálculo de PnL % em relação ao preço médio para o Reequilíbrio
            entry_price = float(p['entryPrice'])
            pnl_pos_pct = (data['price'] / entry_price - 1) * 100 if p['side'] == 'long' else (1 - data['price'] / entry_price) * 100
            
            pos_table.add_row("PnL Reequilíbrio", f"[{pnl_style}]{pnl_pos_pct:+.3f}%[/] / 0.350%")
            pos_table.add_row("PnL Flutuante", f"${pnl:+.4f}", style=pnl_style)
            
            # Lucro Realizado acumulado na banca
            realized_pnl_acc = (data['balance'] - self.initial_capital) - pnl
            realized_style = "green" if realized_pnl_acc >= 0 else "red"
            pos_table.add_row("Total Realizado", f"${realized_pnl_acc:+.4f}", style=realized_style)
        else:
            pos_table.add_row("Status", "Aguardando Entrada")
            if data:
                realized_pnl_acc = data['balance'] - self.initial_capital
                realized_style = "green" if realized_pnl_acc >= 0 else "red"
                pos_table.add_row("Total Realizado", f"${realized_pnl_acc:+.4f}", style=realized_style)

        main_table.add_row(Panel(order_table, border_style="magenta"), Panel(pos_table, border_style="yellow"))
        layout["main"].update(main_table)

        # FOOTER (ÚLTIMAS REALIZADAS)
        history_table = Table(title="Últimas Realizações (Profit/Loss)", title_style="bold green", expand=True)
        history_table.add_column("ID", style="dim")
        history_table.add_column("Lado")
        history_table.add_column("Preço")
        history_table.add_column("Qtd")
        history_table.add_column("Custo Comissão")

        if data and data['trades']:
            for t in reversed(data['trades']):
                history_table.add_row(
                    str(t['id'])[-6:],
                    t['side'].upper(),
                    f"{t['price']:.7f}",
                    str(t['amount']),
                    f"${float(t['fee']['cost']):.4f}" if t.get('fee') else "$0.00"
                )
        
        layout["footer"].update(Panel(history_table, border_style="green"))
        
        return layout

    def run(self):
        with Live(self.generate_layout(None), refresh_per_second=1, screen=True) as live:
            while True:
                data = self.get_data()
                live.update(self.generate_layout(data))
                time.sleep(1.5)

if __name__ == "__main__":
    dash = ProfessionalDashboard()
    dash.run()
