# 🚀 FlashLoan Arbitrage Integration Guide

## Overview
This guide covers the integration of flashloan smart contracts with the crypto arbitrage bot for automated DEX arbitrage execution.

## 📋 Components Added

### 1. Smart Contract (`contracts/FlashLoanArbitrage.sol`)
- **Purpose**: Executes flashloan-based arbitrage across DEXes
- **Features**:
  - Aave V3 flashloan integration
  - Multi-DEX support (Uniswap, SushiSwap, PancakeSwap, etc.)
  - Profit threshold enforcement
  - Emergency withdrawal functions
  - Bot authorization system

### 2. Deployment Script (`scripts/deploy_contract.py`)
- **Purpose**: Deploy contracts to multiple networks
- **Networks**: Polygon, BSC, Avalanche
- **Features**: Automated deployment with verification

### 3. Contract Integration (`contract_integration.py`)
- **Purpose**: Python interface for smart contract interaction
- **Features**: Web3 integration, transaction management, balance queries

### 4. FlashLoan Bot (`flashloan_bot.py`)
- **Purpose**: Enhanced bot with flashloan execution
- **Features**: Real arbitrage execution, profit calculation, risk management

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
# Install Solidity compiler
npm install -g solc

# Install Web3 and related packages
pip install web3 eth-account python-dotenv

# Install Hardhat (optional, for advanced compilation)
npm install --save-dev hardhat
```

### 2. Environment Configuration
Add to your `.env` file:
```bash
# Network RPC URLs
POLYGON_RPC=https://polygon-rpc.com
BSC_RPC=https://bsc-dataseed.binance.org
AVALANCHE_RPC=https://api.avax.network/ext/bc/C/rpc

# Private Keys (keep secure!)
POLYGON_PRIVATE_KEY=your_polygon_private_key
BSC_PRIVATE_KEY=your_bsc_private_key
AVALANCHE_PRIVATE_KEY=your_avalanche_private_key

# Infura/Alchemy (optional)
INFURA_PROJECT_ID=your_infura_project_id
```

### 3. Deploy Smart Contracts
```bash
# Deploy to all configured networks
python scripts/deploy_contract.py

# Deploy to specific network
python scripts/deploy_contract.py --network polygon
```

### 4. Configure Bot for Flashloans
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

## 🔧 Usage Examples

### Basic Flashloan Arbitrage
```python
from flashloan_bot import FlashLoanArbitrageBot

# Initialize bot
bot = FlashLoanArbitrageBot(exchanges, pairs, threshold=2.0)
await bot.initialize_apis()

# Start monitoring with flashloan execution
await bot.enhanced_monitoring_loop()
```

### Manual Contract Interaction
```python
from contract_integration import FlashLoanManager

manager = FlashLoanManager()

# Execute arbitrage
result = await manager.execute_profitable_arbitrage(
    token_a="0x7ceB23fd6bc0add59e62ac25578270cFF1B9f619",  # WETH
    token_b="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC
    amount=1000000000000000000,  # 1 ETH
    profit_threshold=50,  # $50 minimum profit
    network="polygon",
    private_key="your_private_key"
)
```

## 🎯 Token Addresses by Network

### Polygon (Mainnet)
- WETH: `0x7ceB23fd6bc0add59e62ac25578270cFF1B9f619`
- USDC: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
- USDT: `0xc2132D05D31c914a87C6611C10748AEb04B58e8F`
- DAI: `0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063`
- WBTC: `0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6`

### BSC (Mainnet)
- WETH: `0x2170ed0880ac9a755fd29b2688956bd959f933f8`
- USDC: `0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d`
- USDT: `0x55d398326f99059ff775485246999027b3197955`
- DAI: `0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3`
- WBTC: `0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c`

### Avalanche (Mainnet)
- WETH: `0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB`
- USDC: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- USDT: `0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7`
- DAI: `0xd586E7F844cEa2F87f50152665BCbc2C279D8d70`
- WBTC: `0x50b7545627a5162F82A992c33b87aDc75187B218`

## ⚡ Aave Pool Providers

- **Polygon**: `0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb`
- **BSC**: `0xff75B6da14FfbbFD88561a135b3B5E5c9D2aE99d`
- **Avalanche**: `0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb`

## 🛡️ Security Considerations

### 1. Private Key Management
- Never commit private keys to git
- Use environment variables or secure key management
- Consider hardware wallets for production

### 2. Contract Security
- Audit smart contracts before mainnet deployment
- Test thoroughly on testnets
- Implement emergency pause mechanisms

### 3. Risk Management
- Set appropriate profit thresholds
- Monitor gas prices and adjust accordingly
- Implement position sizing limits

## 🧪 Testing

### Testnet Deployment
```bash
# Deploy to Polygon Mumbai testnet
export POLYGON_RPC=https://rpc-mumbai.maticvigil.com
export POLYGON_PRIVATE_KEY=your_testnet_key
python scripts/deploy_contract.py --network polygon --testnet
```

### Integration Testing
```bash
# Run flashloan bot tests
python test_flashloan.py

# Test contract interactions
python test_contract_integration.py
```

## 📊 Monitoring and Alerts

### Contract Events
The smart contract emits these events:
- `ArbitrageExecuted`: When arbitrage is successful
- `BotAuthorized`: When new bots are authorized
- `TokenWhitelisted`: When tokens are added/removed

### Slack Integration
Flashloan executions are automatically reported to Slack:
```
🚀 Flashloan Arbitrage Executed!
Pair: WETH/USDC
Buy: Uniswap @ $1800.50
Sell: SushiSwap @ $1815.25
Amount: 1.0 ETH
Profit: $14.75
Network: Polygon
Tx: 0xabc123...
```

## 🔗 Quick Start

1. **Deploy Contracts**:
   ```bash
   python scripts/deploy_contract.py
   ```

2. **Configure Bot**:
   ```bash
   python flashloan_bot.py
   ```

3. **Monitor via Slack**:
   - Use `/arbitrage status` to check bot status
   - Use `/arbitrage profit` to see profit summary

## 📈 Profit Calculation

### Formula
```
Profit = (Sell_Price - Buy_Price) * Amount - Gas_Fees - Flashloan_Fee
```

### Example
- Buy WETH at $1800 on Uniswap
- Sell WETH at $1820 on SushiSwap
- Amount: 1 ETH
- Gas: $15
- Flashloan fee: $2
- **Net Profit**: $20 - $15 - $2 = $3

## 🚨 Troubleshooting

### Common Issues
1. **"Contract not deployed"**: Run deployment script first
2. **"Insufficient liquidity"**: Check DEX liquidity pools
3. **"Gas estimation failed"**: Increase gas limit or check network congestion

### Debug Commands
```bash
# Check contract deployment
python scripts/deploy_contract.py --verify-only

# Test contract balance
python -c "from contract_integration import FlashLoanManager; import asyncio; asyncio.run(FlashLoanManager().contract_integration.get_contract_balance('polygon', '0x...'))"
```

## 🎉 Next Steps

1. Deploy contracts to mainnet
2. Fund contracts with small amounts for gas
3. Start with small position sizes
4. Monitor and scale based on performance
5. Implement additional DEX integrations as needed

For support, check the GitHub repository issues or use Slack commands for real-time assistance.