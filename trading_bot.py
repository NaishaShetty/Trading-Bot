#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot (CLI)
Supports: MARKET, LIMIT, and TWAP (split market) orders
"""

import os
import time
import json
import argparse
import logging
from decimal import Decimal, InvalidOperation
from dotenv import load_dotenv
from binance.client import Client

# Load env
load_dotenv()
LOGFILE = os.getenv("BOT_LOGFILE", "bot.log")

# Logging
logger = logging.getLogger("futuresbot")
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
fh = logging.FileHandler(LOGFILE)
fh.setFormatter(fmt)
logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setFormatter(fmt)
logger.addHandler(sh)

# Validators
def parse_decimal(value: str) -> Decimal:
    try:
        d = Decimal(value)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"Invalid number: {value}")
    if d <= 0:
        raise argparse.ArgumentTypeError("Value must be positive")
    return d

def validate_side(s: str) -> str:
    s2 = s.strip().upper()
    if s2 not in ("BUY", "SELL"):
        raise argparse.ArgumentTypeError("Side must be BUY or SELL")
    return s2

# Bot class
class FuturesBot:
    def __init__(self, api_key, api_secret, base_url):
        self.client = Client(api_key, api_secret, testnet=True)
        self.client.FUTURES_URL = base_url + "/fapi"
        logger.info(f"Initialized FuturesBot with {base_url}")

    def market(self, symbol, side, qty):
        try:
            resp = self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side,
                type="MARKET",
                quantity=float(qty),
            )
            logger.info(f"Market {side} {qty} {symbol}: {resp}")
            return resp
        except Exception as e:
            logger.error(f"Market order failed: {e}")
            return {"error": str(e)}

    def limit(self, symbol, side, qty, price):
        try:
            resp = self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side,
                type="LIMIT",
                timeInForce="GTC",
                quantity=float(qty),
                price=str(price),
            )
            logger.info(f"Limit {side} {qty}@{price} {symbol}: {resp}")
            return resp
        except Exception as e:
            logger.error(f"Limit order failed: {e}")
            return {"error": str(e)}

    def twap(self, symbol, side, total_qty, parts=3, interval=5):
        piece = total_qty / parts
        results = []
        for i in range(parts):
            resp = self.market(symbol, side, piece)
            results.append(resp)
            if i < parts - 1:
                time.sleep(interval)
        return {"twap_results": results}


# CLI
def main():
    parser = argparse.ArgumentParser(description="Binance Futures Testnet Bot CLI")
    parser.add_argument("--api-key", default=os.getenv("BINANCE_API_KEY"))
    parser.add_argument("--api-secret", default=os.getenv("BINANCE_API_SECRET"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL"))

    sub = parser.add_subparsers(dest="cmd", required=True)

    # Market
    pm = sub.add_parser("market")
    pm.add_argument("--symbol", required=True)
    pm.add_argument("--side", required=True, type=validate_side)
    pm.add_argument("--quantity", required=True, type=parse_decimal)

    # Limit
    pl = sub.add_parser("limit")
    pl.add_argument("--symbol", required=True)
    pl.add_argument("--side", required=True, type=validate_side)
    pl.add_argument("--quantity", required=True, type=parse_decimal)
    pl.add_argument("--price", required=True, type=parse_decimal)

    # TWAP
    pt = sub.add_parser("twap")
    pt.add_argument("--symbol", required=True)
    pt.add_argument("--side", required=True, type=validate_side)
    pt.add_argument("--quantity", required=True, type=parse_decimal)
    pt.add_argument("--parts", type=int, default=3)
    pt.add_argument("--interval", type=int, default=5)

    args = parser.parse_args()
    bot = FuturesBot(args.api_key, args.api_secret, args.base_url)

    if args.cmd == "market":
        print(json.dumps(bot.market(args.symbol, args.side, args.quantity), indent=2))
    elif args.cmd == "limit":
        print(json.dumps(bot.limit(args.symbol, args.side, args.quantity, args.price), indent=2))
    elif args.cmd == "twap":
        print(json.dumps(bot.twap(args.symbol, args.side, args.quantity, args.parts, args.interval), indent=2))


if __name__ == "__main__":
    main()
