import tkinter as tk
from tkinter import messagebox
from decimal import Decimal, InvalidOperation
import json
import time
import os
import logging
from dotenv import load_dotenv
from binance.client import Client
import ttkbootstrap as tb

# --- Logging setup ---
logging.basicConfig(
    filename="orders.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# --- Load .env ---
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
BASE_URL = os.getenv("BASE_URL", "https://testnet.binance.vision")

# --- Initialize Binance Client ---
client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = BASE_URL + "/api"

# --- Utility functions ---
def parse_decimal(value):
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError("Invalid number")

def get_symbol_info(symbol):
    info = client.get_symbol_info(symbol.upper())
    if not info:
        raise ValueError(f"Symbol {symbol} not found")
    lot_size = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
    price_filter = next(f for f in info['filters'] if f['filterType'] == 'PRICE_FILTER')
    return lot_size, price_filter

def adjust_quantity(qty, lot_size):
    step = Decimal(lot_size['stepSize'])
    return (qty // step) * step

def adjust_price(price, price_filter):
    tick = Decimal(price_filter['tickSize'])
    return (price // tick) * tick

def log_and_display(order, label="Order"):
    """Logs to file and displays in the output box"""
    output_text.delete("1.0", tk.END)
    formatted = json.dumps(order, indent=2)
    output_text.insert(tk.END, f"{label}:\n{formatted}\n")
    logging.info("%s placed: %s", label, formatted)

# --- Order functions ---
def place_market():
    symbol = symbol_var.get().upper()
    side = side_var.get().upper()
    qty = qty_var.get()
    try:
        qty = parse_decimal(qty)
        lot_size, _ = get_symbol_info(symbol)
        qty_adj = adjust_quantity(qty, lot_size)
        order = client.create_order(symbol=symbol, side=side, type="MARKET", quantity=float(qty_adj))
        log_and_display(order, "Market Order")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def place_limit():
    symbol = symbol_var.get().upper()
    side = side_var.get().upper()
    qty = qty_var.get()
    price = price_var.get()
    try:
        qty = parse_decimal(qty)
        price = parse_decimal(price)
        lot_size, price_filter = get_symbol_info(symbol)
        qty_adj = adjust_quantity(qty, lot_size)
        price_adj = adjust_price(price, price_filter)
        order = client.create_order(
            symbol=symbol, side=side, type="LIMIT", timeInForce="GTC",
            quantity=float(qty_adj), price=str(price_adj)
        )
        log_and_display(order, "Limit Order")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def place_twap():
    symbol = symbol_var.get().upper()
    side = side_var.get().upper()
    qty = qty_var.get()
    parts = parts_var.get()
    interval = interval_var.get()
    try:
        qty = parse_decimal(qty)
        parts = int(parts)
        interval = int(interval)
        lot_size, _ = get_symbol_info(symbol)
        piece = adjust_quantity(qty / parts, lot_size)
        results = []
        output_text.delete("1.0", tk.END)
        for i in range(parts):
            order = client.create_order(symbol=symbol, side=side, type="MARKET", quantity=float(piece))
            results.append(order)
            formatted = json.dumps(order, indent=2)
            output_text.insert(tk.END, f"TWAP step {i+1}:\n{formatted}\n\n")
            logging.info("TWAP step %d placed: %s", i+1, formatted)
            if i < parts - 1:
                root.update()
                time.sleep(interval)
        output_text.insert(tk.END, "✅ TWAP completed.\n")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# --- GUI Setup ---
root = tb.Window(themename="darkly")  # themes: darkly, flatly, journal, etc.
root.title("Binance Spot Testnet Bot")
root.geometry("900x650")
root.resizable(False, False)

# Frame for inputs
frame = tb.Labelframe(root, text="⚙️ Order Settings", bootstyle="info")
frame.pack(fill="x", padx=15, pady=15)

tb.Label(frame, text="Symbol:").grid(row=0, column=0, padx=5, pady=8, sticky="w")
symbol_var = tk.StringVar(value="BTCUSDT")
tb.Entry(frame, textvariable=symbol_var, width=15).grid(row=0, column=1, padx=5, pady=8)

tb.Label(frame, text="Side:").grid(row=0, column=2, padx=5, pady=8, sticky="w")
side_var = tk.StringVar(value="BUY")
tb.Combobox(frame, textvariable=side_var, values=["BUY", "SELL"], width=12).grid(row=0, column=3, padx=5, pady=8)

tb.Label(frame, text="Quantity:").grid(row=1, column=0, padx=5, pady=8, sticky="w")
qty_var = tk.StringVar(value="0.003")
tb.Entry(frame, textvariable=qty_var, width=15).grid(row=1, column=1, padx=5, pady=8)

tb.Label(frame, text="Price (Limit only):").grid(row=1, column=2, padx=5, pady=8, sticky="w")
price_var = tk.StringVar(value="25000")
tb.Entry(frame, textvariable=price_var, width=15).grid(row=1, column=3, padx=5, pady=8)

tb.Label(frame, text="TWAP Parts:").grid(row=2, column=0, padx=5, pady=8, sticky="w")
parts_var = tk.StringVar(value="3")
tb.Entry(frame, textvariable=parts_var, width=12).grid(row=2, column=1, padx=5, pady=8)

tb.Label(frame, text="TWAP Interval (s):").grid(row=2, column=2, padx=5, pady=8, sticky="w")
interval_var = tk.StringVar(value="5")
tb.Entry(frame, textvariable=interval_var, width=12).grid(row=2, column=3, padx=5, pady=8)

# Buttons
btn_frame = tb.Frame(root)
btn_frame.pack(fill="x", padx=15, pady=10)

tb.Button(btn_frame, text="📈 Market Order", bootstyle="success", command=place_market).pack(side="left", padx=10)
tb.Button(btn_frame, text="📊 Limit Order", bootstyle="warning", command=place_limit).pack(side="left", padx=10)
tb.Button(btn_frame, text="⏱️ TWAP Order", bootstyle="primary", command=place_twap).pack(side="left", padx=10)

# Output box
output_frame = tb.Labelframe(root, text="📜 Order Log", bootstyle="secondary")
output_frame.pack(fill="both", expand=True, padx=15, pady=15)

output_text = tk.Text(output_frame, wrap="word", height=20, bg="#1e1e1e", fg="#ffffff", insertbackground="white")
output_text.pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()
