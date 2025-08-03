#!/usr/bin/env python3
"""
Slack Bot for Crypto Arbitrage Bot
Handles slash commands for remote management
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
import asyncio
from aiohttp import web
from monitorbot import ArbitrageBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackBot:
    def __init__(self, bot: ArbitrageBot):
        self.bot = bot
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup web routes for Slack commands"""
        self.app.router.add_post('/slack', self.handle_slash_command)
        self.app.router.add_get('/health', self.health_check)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "bot_running": self.bot.monitoring_enabled
        })
    
    async def handle_slash_command(self, request):
        """Handle Slack slash commands"""
        try:
            data = await request.post()
            command = data.get('command', '').strip()
            text = data.get('text', '').strip().lower()
            user_name = data.get('user_name', 'unknown')
            
            logger.info(f"Received command: {command} {text} from {user_name}")
            
            if command != '/arbitrage':
                return web.json_response({
                    "text": f"❌ Unknown command: {command}"
                })
            
            response = await self.process_command(text, user_name)
            return web.json_response(response)
            
        except Exception as e:
            logger.error(f"Error handling slash command: {e}")
            return web.json_response({
                "text": f"❌ Error processing command: {str(e)}"
            })
    
    async def process_command(self, text: str, user_name: str) -> Dict[str, Any]:
        """Process different Slack commands"""
        
        if not text or text == 'help':
            return self.get_help_message()
        
        elif text == 'status':
            return await self.get_status()
        
        elif text == 'start':
            return await self.start_monitoring()
        
        elif text == 'stop':
            return await self.stop_monitoring()
        
        elif text == 'pairs':
            return await self.list_pairs()
        
        elif text.startswith('add '):
            pair = text[4:].strip().upper()
            return await self.add_pair(pair)
        
        elif text.startswith('remove '):
            pair = text[7:].strip().upper()
            return await self.remove_pair(pair)
        
        elif text.startswith('threshold '):
            try:
                threshold = float(text[10:].strip())
                return await self.update_threshold(threshold)
            except ValueError:
                return {"text": "❌ Invalid threshold value. Use: threshold 2.5"}
        
        elif text.startswith('loan '):
            try:
                amount = float(text[5:].strip())
                return await self.update_loan_amount(amount)
            except ValueError:
                return {"text": "❌ Invalid loan amount. Use: loan 100"}
        
        elif text == 'profit':
            return await self.get_profit_summary()
        
        elif text == 'notifications on':
            return await self.toggle_notifications(True)
        
        elif text == 'notifications off':
            return await self.toggle_notifications(False)
        
        elif text == 'config':
            return await self.show_config()
        
        else:
            return {"text": f"❌ Unknown command: {text}\nType `/arbitrage help` for available commands."}
    
    def get_help_message(self) -> Dict[str, Any]:
        """Return help message with available commands"""
        commands = [
            "🤖 *Arbitrage Bot Commands*",
            "",
            "📊 *Status & Monitoring:*",
            "• `/arbitrage status` - Show bot status",
            "• `/arbitrage profit` - Show profit summary",
            "• `/arbitrage config` - Show current configuration",
            "",
            "⚙️ *Configuration:*",
            "• `/arbitrage pairs` - List trading pairs",
            "• `/arbitrage add ETH/USDC` - Add trading pair",
            "• `/arbitrage remove ETH/USDC` - Remove trading pair",
            "• `/arbitrage threshold 2.5` - Set profit threshold (%)",
            "• `/arbitrage loan 100` - Set max loan amount ($)",
            "",
            "🔧 *Control:*",
            "• `/arbitrage start` - Start monitoring",
            "• `/arbitrage stop` - Stop monitoring",
            "• `/arbitrage notifications on/off` - Toggle notifications",
            "",
            "❓ *Help:*",
            "• `/arbitrage help` - Show this message"
        ]
        
        return {"text": "\n".join(commands)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get bot status"""
        config = self.bot.get_config()
        
        status_text = [
            "🤖 *Arbitrage Bot Status*",
            f"• Monitoring: {'🟢 ON' if config['monitoring_enabled'] else '🔴 OFF'}",
            f"• Notifications: {'🟢 ON' if config['notification_enabled'] else '🔴 OFF'}",
            f"• Trading Pairs: {len(config['pairs'])}",
            f"• Profit Threshold: {config['threshold']}%",
            f"• Max Loan: ${config['max_loan_amount']}",
            f"• Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        return {"text": "\n".join(status_text)}
    
    async def start_monitoring(self) -> Dict[str, Any]:
        """Start monitoring"""
        if self.bot.monitoring_enabled:
            return {"text": "🟡 Bot is already monitoring!"}
        
        self.bot.toggle_monitoring(True)
        await self.bot.send_slack_notification("🟢 Arbitrage bot started monitoring", "good")
        return {"text": "🟢 Monitoring started successfully!"}
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring"""
        if not self.bot.monitoring_enabled:
            return {"text": "🟡 Bot is already stopped!"}
        
        self.bot.toggle_monitoring(False)
        await self.bot.send_slack_notification("🔴 Arbitrage bot stopped monitoring", "warning")
        return {"text": "🔴 Monitoring stopped successfully!"}
    
    async def list_pairs(self) -> Dict[str, Any]:
        """List trading pairs"""
        config = self.bot.get_config()
        pairs = config['pairs']
        
        if not pairs:
            return {"text": "📋 No trading pairs configured. Use `/arbitrage add ETH/USDC` to add one."}
        
        pairs_text = ["📋 *Configured Trading Pairs:*"]
        for i, pair in enumerate(pairs, 1):
            pairs_text.append(f"{i}. {pair}")
        
        return {"text": "\n".join(pairs_text)}
    
    async def add_pair(self, pair: str) -> Dict[str, Any]:
        """Add trading pair"""
        try:
            if '/' not in pair:
                return {"text": "❌ Invalid format. Use: BASE/QUOTE (e.g., ETH/USDC)"}
            
            current_pairs = [str(p) for p in self.bot.pairs]
            if pair in current_pairs:
                return {"text": f"🟡 Pair {pair} already exists!"}
            
            current_pairs.append(pair)
            self.bot.update_trading_pairs(current_pairs)
            
            await self.bot.send_slack_notification(f"📈 Added trading pair: {pair}", "good")
            return {"text": f"✅ Added trading pair: {pair}"}
        
        except Exception as e:
            return {"text": f"❌ Error adding pair: {str(e)}"}
    
    async def remove_pair(self, pair: str) -> Dict[str, Any]:
        """Remove trading pair"""
        try:
            current_pairs = [str(p) for p in self.bot.pairs]
            if pair not in current_pairs:
                return {"text": f"❌ Pair {pair} not found!"}
            
            current_pairs.remove(pair)
            self.bot.update_trading_pairs(current_pairs)
            
            await self.bot.send_slack_notification(f"📉 Removed trading pair: {pair}", "warning")
            return {"text": f"✅ Removed trading pair: {pair}"}
        
        except Exception as e:
            return {"text": f"❌ Error removing pair: {str(e)}"}
    
    async def update_threshold(self, threshold: float) -> Dict[str, Any]:
        """Update profit threshold"""
        if threshold <= 0:
            return {"text": "❌ Threshold must be greater than 0%"}
        
        if threshold > 50:
            return {"text": "❌ Threshold too high (>50%). Please use a reasonable value."}
        
        self.bot.update_threshold(threshold)
        await self.bot.send_slack_notification(f"⚙️ Profit threshold updated to {threshold}%", "good")
        return {"text": f"✅ Profit threshold updated to {threshold}%"}
    
    async def update_loan_amount(self, amount: float) -> Dict[str, Any]:
        """Update max loan amount"""
        if amount <= 0:
            return {"text": "❌ Loan amount must be greater than 0"}
        
        if amount > 10000:
            return {"text": "❌ Loan amount too high (>\$10,000). Please use a reasonable value."}
        
        self.bot.update_max_loan(amount)
        await self.bot.send_slack_notification(f"💰 Max loan amount updated to ${amount}", "good")
        return {"text": f"✅ Max loan amount updated to ${amount}"}
    
    async def get_profit_summary(self) -> Dict[str, Any]:
        """Get profit summary (placeholder - implement with real data)"""
        # This would integrate with your actual profit tracking
        summary = [
            "💰 *Profit Summary*",
            "• Daily: $2.50 (estimated)",
            "• Weekly: $17.50",
            "• Monthly: $75.00",
            "• Total Trades: 23",
            "• Success Rate: 87%",
            "",
            "📊 *Performance*",
            "• Best Trade: $0.85 profit",
            "• Worst Trade: -$0.12 loss",
            "• Average Trade: $0.34 profit"
        ]
        
        return {"text": "\n".join(summary)}
    
    async def toggle_notifications(self, enabled: bool) -> Dict[str, Any]:
        """Toggle notifications"""
        self.bot.toggle_notifications(enabled)
        status = "enabled" if enabled else "disabled"
        await self.bot.send_slack_notification(f"🔔 Notifications {status}", "good" if enabled else "warning")
        return {"text": f"✅ Notifications {status}"}
    
    async def show_config(self) -> Dict[str, Any]:
        """Show current configuration"""
        config = self.bot.get_config()
        
        config_text = [
            "⚙️ *Current Configuration*",
            f"• Monitoring: {'🟢 ON' if config['monitoring_enabled'] else '🔴 OFF'}",
            f"• Notifications: {'🟢 ON' if config['notification_enabled'] else '🔴 OFF'}",
            f"• Profit Threshold: {config['threshold']}%",
            f"• Max Loan: ${config['max_loan_amount']}",
            "",
            "📈 *Trading Pairs:*"
        ]
        
        for pair in config['pairs']:
            config_text.append(f"   • {pair}")
        
        config_text.extend([
            "",
            "🔄 *Exchanges:*"
        ])
        
        for exchange in config['exchanges']:
            config_text.append(f"   • {exchange}")
        
        return {"text": "\n".join(config_text)}
    
    async def start_server(self, host='0.0.0.0', port=8080):
        """Start the Slack bot server"""
        logger.info(f"Starting Slack bot server on {host}:{port}")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info("Slack bot server started successfully")

async def start_slack_server(bot: ArbitrageBot, host='0.0.0.0', port=8080):
    """Start the Slack bot server"""
    slack_bot = SlackBot(bot)
    await slack_bot.start_server(host, port)
    
    # Keep the server running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    # For standalone testing
    from monitorbot import ArbitrageBot, TradingPair
    
    exchanges = ['uniswap', 'sushiswap']
    pairs = [TradingPair('WETH', 'USDC')]
    bot = ArbitrageBot(exchanges, pairs)
    
    asyncio.run(start_slack_server(bot))