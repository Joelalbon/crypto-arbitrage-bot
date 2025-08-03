#!/usr/bin/env python3
"""
FlashLoan Contract Deployment Script
"""

import os
import json
import asyncio
from web3 import Web3
from eth_account import Account

async def deploy_contract():
    """Deploy flashloan contract"""
    print("Flashloan deployment script ready")
    print("Please compile contracts first using:")
    print("npm install")
    print("npx hardhat compile")
    print("npx hardhat run scripts/deploy.js --network polygon")

if __name__ == "__main__":
    asyncio.run(deploy_contract())