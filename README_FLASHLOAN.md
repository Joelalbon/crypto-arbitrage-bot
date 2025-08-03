# FlashLoan Integration Guide

This guide covers the complete flashloan arbitrage integration for the crypto arbitrage bot.

## Overview

The flashloan integration adds true arbitrage execution capabilities to the monitoring bot by leveraging Aave V3 flashloans across multiple networks (Polygon, BSC, Avalanche).

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Monitor Bot   │    │  FlashLoan Bot   │    │  Smart Contract │
│                 │    │                  │    │                 │
│ • Price feeds   │───→│ • Opportunity    │───→│ • Flashloan     │
│ • Opportunity   │    │   detection      │    │   execution     │
│   detection     │    │ • Profit calc    │    │ • DEX trading   │
│ • Notifications │    │ • Risk mgmt      │    │ • Profit calc   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Components

### 1. Smart Contract (`contracts/flashloan_contract.sol`)
- **Purpose**: Handles flashloan execution and arbitrage trades
- **Features**:
  - Aave V3 flashloan integration
  - Token/DEX router whitelisting
  - Profit threshold enforcement
  - Emergency withdrawal functions
  - Owner controls and bot authorization

### 2. Contract Integration (`src/contract_integration.py`)
- **Purpose**: Python interface for smart contract interaction
- **Features**:
  - Multi-network support (Polygon, BSC, Avalanche)
  - Transaction execution
  - Balance queries
  - Status monitoring

### 3. FlashLoan Bot (`src/flashloan_bot.py`)
- **Purpose**: Enhanced arbitrage bot with flashloan capabilities
- **Features**:
  - Opportunity filtering for flashloan suitability
  - Profit calculation including fees
  - Automated execution
  - Performance tracking

## Setup Instructions

### Prerequisites

1. **Node.js and npm** (for contract compilation)
2. **Python packages**:
   ```bash
   pip install web3 eth-account aiohttp python-dotenv
   ```
3. **Hardhat** (for contract development):
   ```bash
   npm install --save-dev hardhat
   npm install @aave/core-v3
   ```

### Environment Variables

Create a `.env` file with the following:

```bash
# Network RPC URLs
POLYGON_RPC=https://polygon-rpc.com
BSC_RPC=https://bsc-dataseed.binance.org
AVALANCHE_RPC=https://api.avax.network/ext/bc/C/rpc

# Private keys (DO NOT commit to git)
POLYGON_PRIVATE_KEY=your_polygon_private_key
BSC_PRIVATE_KEY=your_bsc_private_key
AVALANCHE_PRIVATE_KEY=your_avalanche_private_key

# Contract addresses (after deployment)
FLASHLOAN_CONTRACT_POLYGON=0x...
FLASHLOAN_CONTRACT_BSC=0x...
FLASHLOAN_CONTRACT_AVALANCHE=0x...

# Slack integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_BOT_TOKEN=xoxb-your-bot-token
```

### Contract Deployment

#### Option 1: Using Hardhat

1. **Initialize Hardhat**:
   ```bash
   npm init -y
   npm install --save-dev hardhat @aave/core-v3 @openzeppelin/contracts
   npx hardhat
   ```

2. **Configure Hardhat** (`hardhat.config.js`):
   ```javascript
   require("@nomicfoundation/hardhat-toolbox");
   
   module.exports = {
     solidity: "0.8.19",
     networks: {
       polygon: {
         url: process.env.POLYGON_RPC,
         accounts: [process.env.POLYGON_PRIVATE_KEY]
       },
       bsc: {
         url: process.env.BSC_RPC,
         accounts: [process.env.BSC_PRIVATE_KEY]
       },
       avalanche: {
         url: process.env.AVALANCHE_RPC,
         accounts: [process.env.AVALANCHE_PRIVATE_KEY]
       }
     }
   };
   ```

3. **Deploy contract**:
   ```bash
   npx hardhat run scripts/deploy.js --network polygon
   ```

#### Option 2: Using Python Script

1. **Compile contract** first (see Hardhat method above)
2. **Update bytecode** in `scripts/deploy_flashloan.py`
3. **Run deployment**:
   ```bash
   python scripts/deploy_flashloan.py --network polygon
   ```

## Usage

### Basic Flashloan Bot

```python
from src.flashloan_bot import FlashLoanBot
import asyncio

async def main():
    bot = FlashLoanBot()
    await bot.initialize()
    
    # Initialize flashloan
    await bot.initialize_flashloan(
        network="polygon",
        contract_address="0x...",  # Your deployed contract
        private_key="your_private_key"
    )
    
    # Start monitoring
    await bot.monitor_and_execute()

if __name__ == "__main__":
    asyncio.run(main())
```

### Manual Contract Interaction

```python
from src.contract_integration import ContractIntegration
import asyncio

async def interact():
    integration = ContractIntegration("polygon")
    await integration.initialize(
        contract_address="0x...",
        private_key="your_private_key"
    )
    
    # Check contract balance
    balance = await integration.get_contract_balance(
        "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"  # WETH
    )
    print(f"Contract WETH balance: {balance}")

asyncio.run(interact())
```

## Configuration

### Token Whitelisting

Before executing arbitrage, whitelist tokens in the contract:

```python
# Example token addresses for Polygon
TOKENS = {
    "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
    "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
}

DEX_ROUTERS = {
    "QuickSwap": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
    "SushiSwap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
    "UniswapV3": "0xE592427A0AEce92De3Edee1F18E0157C05861564"
}
```

### Risk Management

Configure risk parameters:

```python
# In flashloan_bot.py
bot.min_profit_threshold = Decimal("0.01")  # Minimum 0.01 ETH profit
bot.max_loan_amount = Decimal("1000")       # Maximum 1000 tokens
```

## Testing

### Testnet Deployment

1. **Get testnet tokens**:
   - Polygon Mumbai: https://faucet.polygon.technology/
   - BSC Testnet: https://testnet.binance.org/faucet-smart
   - Avalanche Fuji: https://faucet.avax.network/

2. **Deploy to testnet**:
   ```bash
   npx hardhat run scripts/deploy.js --network mumbai
   ```

3. **Run tests**:
   ```bash
   python -m pytest tests/test_flashloan.py -v
   ```

### Integration Testing

```bash
# Test contract integration
python -c "
from src.contract_integration import ContractIntegration
import asyncio
async def test():
    integration = ContractIntegration('polygon')
    await integration.initialize('0x...', 'your_key')
    print(await integration.get_contract_status())
asyncio.run(test())
"
```

## Monitoring and Alerts

### Slack Integration

The bot automatically sends notifications for:
- Successful arbitrage executions
- Contract deployment confirmations
- Error alerts
- Performance summaries

### Performance Metrics

Track performance using:

```bash
# View execution logs
tail -f flashloan_results.jsonl

# Get performance summary
python -c "
from src.flashloan_bot import FlashLoanBot
import asyncio
async def stats():
    bot = FlashLoanBot()
    print(await bot.get_performance_metrics())
asyncio.run(stats())
"
```

## Security Considerations

### Private Key Management
- Never commit private keys to git
- Use environment variables or secure key management
- Consider using hardware wallets for production

### Contract Security
- The contract includes:
  - Owner controls for critical functions
  - Token/DEX router whitelisting
  - Profit threshold enforcement
  - Emergency withdrawal functions

### Rate Limiting
- Implement cooldown periods between executions
- Monitor gas prices to avoid high-fee transactions
- Set maximum loan amounts per transaction

## Troubleshooting

### Common Issues

1. **"Insufficient funds" error**:
   - Ensure wallet has enough native tokens for gas
   - Check network configuration

2. **"Contract not whitelisted" error**:
   - Add tokens and DEX routers to contract whitelist
   - Verify contract ownership

3. **"Transaction failed"**:
   - Check gas limits and prices
   - Verify token approvals
   - Check for sufficient liquidity

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "src.flashloan_bot"]
```

### Systemd Service

Create `/etc/systemd/system/flashloan-bot.service`:

```ini
[Unit]
Description=Flashloan Arbitrage Bot
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/crypto-arbitrage-bot
Environment=PATH=/opt/crypto-arbitrage-bot/venv/bin
ExecStart=/opt/crypto-arbitrage-bot/venv/bin/python -m src.flashloan_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Health Checks

```bash
# Check bot status
curl -f http://localhost:8080/health || exit 1

# Check contract balance
python -c "
from src.contract_integration import ContractIntegration
import asyncio
async def check():
    integration = ContractIntegration('polygon')
    await integration.initialize('0x...', 'key')
    print(await integration.get_contract_status())
asyncio.run(check())
"
```

## Support and Updates

For updates and support:
- Check GitHub repository for latest changes
- Monitor Aave documentation for protocol updates
- Join community discussions on Discord/Telegram
- Review security advisories regularly

## Next Steps

1. **Implement actual DEX trading logic** in the smart contract
2. **Add more sophisticated risk management**
3. **Implement multi-path arbitrage**
4. **Add MEV protection**
5. **Integrate with flashloan aggregators**
6. **Add advanced analytics dashboard**