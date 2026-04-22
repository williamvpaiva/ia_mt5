import time
import os
import pandas as pd
import importlib.metadata
import importlib
importlib.metadata = importlib.metadata
import pandas_ta as ta
import ccxt
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from dotenv import load_dotenv

load_dotenv()

class DirectionalDashboard:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.exchange.set_sandbox_mode(True)
        self.symbol = '1000PEPE/USDT'
        self.console = Console()
        self.initial_capital = 5000.0

    def get_data(self):
        try:
            # 1. Ticker e Indicadores
            ticker = self.exchange.fetch_ticker(self.symbol)
            candles = self.exchange.fetch_ohlcv(self.symbol, timeframe='15m', limit=50)
            df = pd.DataFrame(candles, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            
            # BB
            bb = ta.bbands(df['c'], length=20, std=2)
            last_bb = bb.iloc[-1]
            bbu = last_bb.filter(like='BBU').iloc[0]
            bbl = last_bb.filter(like='BBL').iloc[0]
            
            # RSI
            rsi = ta.rsi(df['c'], length=14).iloc[-1]
            
            # ADX
            adx_df = ta.adx(df['h'], df['l'], df['c'], length=14)
            adx = adx_df['ADX_14'].iloc[-1]

            # 2. Carteira e Posição
            balance = self.exchange.fetch_balance()
            wallet_balance = float(balance['total']['USDT'])
            
            positions = self.exchange.fetch_positions([self.symbol])
            pos = positions[0] if positions else None
            
            # 3. Histórico
            trades = self.exchange.fetch_my_trades(self.symbol, limit=8)
            
            return {
                'price': ticker['last'],
                'bbu': bbu,
                'bbl': bbl,
                'rsi': rsi,
                'adx': adx,
                'balance': wallet_balance,
                'pos': pos,
                'trades': trades
            }
        except Exception as e:
            return {"error": str(e)}

    def generate_layout(self, data):
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
        )
        layout["body"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="history", ratio=1),
        )

        # 1. HEADER
        if data and "error" not in data:
            total_profit = data['balance'] - self.initial_capital
            roi_pct = (total_profit / self.initial_capital) * 100
            style = "bold green" if total_profit >= 0 else "bold red"
            
            header_content = (
                f"[bold white]PREÇO:[/] [yellow]{data['price']:.8f}[/] | "
                f"[bold white]SALDO USDT:[/] [cyan]${data['balance']:.2f}[/] | "
                f"[bold white]PERFORMANCE SESSÃO:[/] [{style}]${total_profit:+.2f} ({roi_pct:+.2f}%)[/]"
            )
        else:
            header_content = "[bold red]CONECTANDO À BINANCE (SNIPER MODE)...[/]"
        
        layout["header"].update(Panel(header_content, title="SNIPER DIRECIONAL DASHBOARD", border_style="blue"))

        # 2. STATUS & INDICADORES
        stats_table = Table(title="Indicadores & Posição Ativa", expand=True)
        stats_table.add_column("DADO", style="cyan")
        stats_table.add_column("VALOR", style="white")

        if data and "error" not in data:
            # Indicadores
            rsi_style = "red" if data['rsi'] > 70 or data['rsi'] < 30 else "green"
            stats_table.add_row("RSI (14)", f"[{rsi_style}]{data['rsi']:.1f}[/]")
            stats_table.add_row("Bollinger Upper", f"{data['bbu']:.8f}")
            stats_table.add_row("Bollinger Lower", f"{data['bbl']:.8f}")
            stats_table.add_row("ADX Trend Força", f"{data['adx']:.1f}")
            stats_table.add_section()
            
            # Posição
            pos = data['pos']
            if pos and float(pos['contracts']) > 0:
                side = "LONG" if pos['side'] == 'long' else "SHORT"
                side_style = "bold green" if side == "LONG" else "bold red"
                pnl = float(pos['unrealizedPnl'])
                pnl_style = "green" if pnl >= 0 else "red"
                
                stats_table.add_row("Posição Atual", f"[{side_style}]{side}[/]")
                stats_table.add_row("Tamanho", f"{pos['contracts']} cont")
                stats_table.add_row("Preço Entrada", f"{float(pos['entryPrice']):.8f}")
                stats_table.add_row("PNL Flutuante", f"[{pnl_style}]${pnl:+.2f}[/]")
            else:
                stats_table.add_row("Posição", "[dim]AGUARDANDO SINAL...[/]")
        
        layout["stats"].update(Panel(stats_table, border_style="magenta"))

        # 3. HISTÓRICO
        hist_table = Table(title="Últimos Trades Encerrados", expand=True)
        hist_table.add_column("Data", style="dim")
        hist_table.add_column("Lado", style="bold")
        hist_table.add_column("Preço", style="yellow")
        hist_table.add_column("Lucro/Taxa", justify="right")

        if data and "error" not in data and data['trades']:
            # Filtramos para mostrar apenas trades que provavelmente são do Sniper (Valor > $50)
            sniper_trades = [t for t in data['trades'] if (float(t['amount']) * float(t['price'])) > 50]
            
            if not sniper_trades:
                hist_table.add_row("", "[dim]Sem trades do Sniper ainda[/]", "", "")
            
            for t in reversed(sniper_trades):
                side_style = "green" if t['side'] == 'buy' else "red"
                cost = float(t['amount']) * float(t['price'])
                hist_table.add_row(
                    time.strftime('%H:%M:%S', time.localtime(t['timestamp']/1000)),
                    f"[{side_style}]{t['side'].upper()}[/]",
                    f"{t['price']:.8f}",
                    f"${cost:.2f}"
                )

        layout["history"].update(Panel(hist_table, border_style="cyan"))

        return layout

    def start(self):
        with Live(screen=True, refresh_per_second=1) as live:
            while True:
                data = self.get_data()
                live.update(self.generate_layout(data))
                time.sleep(2)

if __name__ == "__main__":
    dash = DirectionalDashboard()
    try:
        dash.start()
    except KeyboardInterrupt:
        pass
