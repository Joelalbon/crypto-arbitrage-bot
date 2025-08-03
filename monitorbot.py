#!/usr/bin/env python3
"""
Crypto Arbitrage Bot - Main Monitor
Monitors price differences across DEXes and executes profitable trades
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiohttp
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbitrage_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Exchange APIs
from exchanges.uniswap import UniswapAPI
from exchanges.sushiswap import SushiSwapAPI
from exchanges.pancakeswap import PancakeSwapAPI
from exchanges.quickswap import QuickSwapAPI
from exchanges.traderjoe import TraderJoeAPI
from exchanges.pangolin import PangolinAPI
from exchanges.biswap import BiswapAPI
from exchanges.apeswap import ApeSwapAPI
from exchanges.curve import CurveAPI
from exchanges.balancer import BalancerAPI

class TradingPair:
    def __init__(self, base: str, quote: str, amount: float = 1.0):
        self.base = base
        self.quote = quote
        self.amount = amount
    
    def __str__(self):
        return f"{self.base}/{self.quote}"

class ArbitrageBot:
    def __init__(self, exchanges: List[str], pairs: List[TradingPair], threshold: float = 1.0):
        self.exchanges = exchanges
        self.pairs = pairs
        self.threshold = threshold  # Minimum profit percentage
        self.max_loan_amount = float(os.getenv('MAX_LOAN_AMOUNT', 1000))
        self.monitoring_enabled = True
        self.notification_enabled = True
        self.config_file = 'bot_config.json'
        
        # Load configuration
        self.load_config()
        
        # Initialize exchange APIs
        self.exchange_apis = {
            'uniswap': UniswapAPI(),
            'sushiswap': SushiSwapAPI(),
            'pancakeswap': PancakeSwapAPI(),
            'quickswap': QuickSwapAPI(),
            'traderjoe': TraderJoeAPI(),
            'pangolin': PangolinAPI(),
            'biswap': BiswapAPI(),
            'apeswap': ApeSwapAPI(),
            'curve': CurveAPI(),
            'balancer': BalancerAPI()
        }
        
        # Slack webhook
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        
        logger.info(f"Arbitrage bot initialized with threshold: {self.threshold}%")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.pairs = [TradingPair(p['base'], p['quote'], p.get('amount', 1.0)) 
                                 for p in config.get('pairs', [])]
                    self.threshold = config.get('threshold', self.threshold)
                    self.max_loan_amount = config.get('max_loan_amount', self.max_loan_amount)
                    self.monitoring_enabled = config.get('monitoring_enabled', True)
                    self.notification_enabled = config.get('notification_enabled', True)
                    logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                'pairs': [{'base': p.base, 'quote': p.quote, 'amount': p.amount} for p in self.pairs],
                'threshold': self.threshold,
                'max_loan_amount': self.max_loan_amount,
                'monitoring_enabled': self.monitoring_enabled,
                'notification_enabled': self.notification_enabled,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    async def send_slack_notification(self, message: str, color: str = "good"):
        """Send notification to Slack"""
        if not self.slack_webhook or not self.notification_enabled:
            return
        
        try:
            payload = {
                "text": "🤖 Arbitrage Bot Alert",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {
                                "title": "Message",
                                "value": message,
                                "short": False
                            },
                            {
                                "title": "Time",
                                "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True
                            }
                        ]
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent successfully")
                    else:
                        logger.error(f"Failed to send Slack notification: {response.status}")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    async def get_prices(self, pair: TradingPair) -> Dict[str, float]:
        """Get prices from all configured exchanges for a trading pair"""
        prices = {}
        
        for exchange_name in self.exchanges:
            if exchange_name in self.exchange_apis:
                try:
                    api = self.exchange_apis[exchange_name]
                    price = await api.get_price(pair.base, pair.quote)
                    if price and price > 0:
                        prices[exchange_name] = price
                        logger.debug(f"{exchange_name}: {pair} = ${price:.4f}")
                except Exception as e:
                    logger.error(f"Error getting price from {exchange_name}: {e}")
        
        return prices
    
    def find_arbitrage_opportunities(self, prices: Dict[str, float], pair: TradingPair) -> List[Dict]:
        """Find arbitrage opportunities from price data"""
        if len(prices) < 2:
            return []
        
        opportunities = []
        exchanges = list(prices.keys())
        
        for buy_exchange in exchanges:
            for sell_exchange in exchanges:
                if buy_exchange != sell_exchange:
                    buy_price = prices[buy_exchange]
                    sell_price = prices[sell_exchange]
                    
                    if buy_price > 0 and sell_price > 0:
                        profit_percentage = ((sell_price - buy_price) / buy_price) * 100
                        
                        if profit_percentage >= self.threshold:
                            opportunities.append({
                                'pair': str(pair),
                                'buy_exchange': buy_exchange,
                                'sell_exchange': sell_exchange,
                                'buy_price': buy_price,
                                'sell_price': sell_price,
                                'profit_percentage': profit_percentage,
                                'timestamp': datetime.now().isoformat()
                            })
        
        return sorted(opportunities, key=lambda x: x['profit_percentage'], reverse=True)
    
    async def monitor_pairs(self):
        """Main monitoring loop"""
        logger.info("Starting arbitrage monitoring...")
        
        while self.monitoring_enabled:
            try:
                for pair in self.pairs:
                    logger.info(f"Checking {pair}...")
                    
                    prices = await self.get_prices(pair)
                    if prices:
                        opportunities = self.find_arbitrage_opportunities(prices, pair)
                        
                        if opportunities:
                            best_opportunity = opportunities[0]
                            message = f"🎯 Arbitrage opportunity found!\n"
                            message += f"Pair: {best_opportunity['pair']}\n"
                            message += f"Buy: {best_opportunity['buy_exchange']} at ${best_opportunity['buy_price']:.4f}\n"
                            message += f"Sell: {best_opportunity['sell_exchange']} at ${best_opportunity['sell_price']:.4f}\n"
                            message += f"Profit: {best_opportunity['profit_percentage']:.2f}%\n"
                            message += f"Loan amount: ${self.max_loan_amount}"
                            
                            logger.info(message)
                            await self.send_slack_notification(message, "good")
                        else:
                            logger.info(f"No arbitrage opportunities found for {pair}")
                    else:
                        logger.warning(f"No prices available for {pair}")
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await self.send_slack_notification(f"❌ Monitoring error: {str(e)}", "danger")
                await asyncio.sleep(30)  # Wait 30 seconds on error
    
    def update_trading_pairs(self, new_pairs: List[str]):
        """Update trading pairs"""
        self.pairs = [TradingPair(*pair.split('/')) for pair in new_pairs]
        self.save_config()
        logger.info(f"Trading pairs updated: {[str(p) for p in self.pairs]}")
    
    def update_threshold(self, new_threshold: float):
        """Update profit threshold"""
        self.threshold = new_threshold
        self.save_config()
        logger.info(f"Profit threshold updated to: {self.threshold}%")
    
    def update_max_loan(self, new_amount: float):
        """Update maximum loan amount"""
        self.max_loan_amount = new_amount
        self.save_config()
        logger.info(f"Max loan amount updated to: ${self.max_loan_amount}")
    
    def toggle_monitoring(self, enabled: bool):
        """Toggle monitoring on/off"""
        self.monitoring_enabled = enabled
        self.save_config()
        status = "enabled" if enabled else "disabled"
        logger.info(f"Monitoring {status}")
    
    def toggle_notifications(self, enabled: bool):
        """Toggle notifications on/off"""
        self.notification_enabled = enabled
        self.save_config()
        status = "enabled" if enabled else "disabled"
        logger.info(f"Notifications {status}")
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return {
            'pairs': [str(p) for p in self.pairs],
            'threshold': self.threshold,
            'max_loan_amount': self.max_loan_amount,
            'monitoring_enabled': self.monitoring_enabled,
            'notification_enabled': self.notification_enabled,
            'exchanges': self.exchanges
        }

async def main():
    """Main function"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Crypto Arbitrage Bot')
    parser.add_argument('--pairs', nargs='+', default=['WETH/USDC'], help='Trading pairs to monitor')
    parser.add_argument('--threshold', type=float, default=1.0, help='Minimum profit threshold (%)')
    parser.add_argument('--with-slack-commands', action='store_true', help='Run with Slack command server')
    parser.add_argument('--dry-run', action='store_true', help='Run without executing trades')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode')
    
    args = parser.parse_args()
    
    # Initialize bot
    exchanges = ['uniswap', 'sushiswap', 'pancakeswap', 'quickswap', 'traderjoe', 'pangolin', 'biswap', 'apeswap', 'curve', 'balancer']
    pairs = [TradingPair(*pair.split('/')) for pair in args.pairs]
    
    bot = ArbitrageBot(exchanges, pairs, args.threshold)
    
    if args.test_mode:
        logger.info("Running in test mode...")
        await bot.send_slack_notification("🧪 Arbitrage bot started in test mode")
    
    if args.with_slack_commands:
        # Import and start Slack bot server
        from slack_bot_server import start_slack_server
        
        # Start both the monitoring bot and Slack server
        tasks = [
            asyncio.create_task(bot.monitor_pairs()),
            asyncio.create_task(start_slack_server(bot))
        ]
        
        await asyncio.gather(*tasks)
    else:
        await bot.monitor_pairs()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)