// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@aave/core-v3/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
import "@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title FlashLoanArbitrage
 * @dev Flash loan arbitrage contract for DEX trading
 */
contract FlashLoanArbitrage is FlashLoanSimpleReceiverBase, ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;

    struct ArbitrageParams {
        address tokenA;
        address tokenB;
        uint256 amount;
        address dexRouter1;
        address dexRouter2;
        uint256 minProfit;
    }

    struct DexRouter {
        address router;
        bytes data;
    }

    mapping(address => bool) public authorizedBots;
    mapping(address => bool) public whitelistedTokens;
    mapping(address => DexRouter) public dexRouters;

    event ArbitrageExecuted(
        address indexed tokenA,
        address indexed tokenB,
        uint256 amount,
        uint256 profit,
        address indexed executor
    );

    event BotAuthorized(address indexed bot, bool authorized);
    event TokenWhitelisted(address indexed token, bool whitelisted);
    event RouterAdded(address indexed router, address indexed dex);

    constructor(
        address _addressProvider
    ) FlashLoanSimpleReceiverBase(IPoolAddressesProvider(_addressProvider)) {}

    modifier onlyAuthorized() {
        require(authorizedBots[msg.sender] || msg.sender == owner(), "Not authorized");
        _;
    }

    /**
     * @dev Execute flash loan arbitrage
     * @param params Arbitrage parameters
     */
    function executeArbitrage(ArbitrageParams calldata params) external onlyAuthorized nonReentrant {
        require(whitelistedTokens[params.tokenA], "Token A not whitelisted");
        require(whitelistedTokens[params.tokenB], "Token B not whitelisted");
        require(params.amount > 0, "Invalid amount");
        require(params.minProfit > 0, "Invalid min profit");

        address[] memory assets = new address[](1);
        assets[0] = params.tokenA;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = params.amount;
        uint256[] memory modes = new uint256[](1);
        modes[0] = 0;

        bytes memory data = abi.encode(params);
        POOL.flashLoanSimple(address(this), params.tokenA, params.amount, data, 0);
    }

    /**
     * @dev Flash loan callback
     */
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        require(msg.sender == address(POOL), "Invalid caller");
        require(initiator == address(this), "Invalid initiator");

        ArbitrageParams memory arbParams = abi.decode(params, (ArbitrageParams));
        
        // Execute arbitrage trades
        uint256 finalAmount = _executeArbitrageTrades(arbParams);
        
        uint256 amountOwing = amount + premium;
        require(finalAmount >= amountOwing + arbParams.minProfit, "Insufficient profit");

        // Repay flash loan
        IERC20(asset).safeApprove(address(POOL), amountOwing);

        uint256 profit = finalAmount - amountOwing;
        
        // Send profit to owner
        if (profit > 0) {
            IERC20(asset).safeTransfer(owner(), profit);
        }

        emit ArbitrageExecuted(
            arbParams.tokenA,
            arbParams.tokenB,
            arbParams.amount,
            profit,
            tx.origin
        );

        return true;
    }

    /**
     * @dev Internal function to execute arbitrage trades
     */
    function _executeArbitrageTrades(ArbitrageParams memory params) internal returns (uint256) {
        // Trade on first DEX
        uint256 amountB = _tradeOnDex(params.dexRouter1, params.tokenA, params.tokenB, params.amount);
        
        // Trade back on second DEX
        uint256 finalAmount = _tradeOnDex(params.dexRouter2, params.tokenB, params.tokenA, amountB);
        
        return finalAmount;
    }

    /**
     * @dev Trade on specific DEX
     */
    function _tradeOnDex(address router, address tokenIn, address tokenOut, uint256 amountIn) internal returns (uint256) {
        require(dexRouters[router].router != address(0), "Router not configured");
        
        // Approve token spending
        IERC20(tokenIn).safeApprove(router, amountIn);
        
        // Execute trade based on router type
        // This is a simplified version - implement specific DEX logic
        if (router == dexRouters[router].router) {
            // Implement specific DEX trading logic here
            return _executeUniswapTrade(router, tokenIn, tokenOut, amountIn);
        }
        
        revert("Unsupported DEX");
    }

    /**
     * @dev Execute Uniswap V2 trade
     */
    function _executeUniswapTrade(address router, address tokenIn, address tokenOut, uint256 amountIn) internal returns (uint256) {
        // Simplified Uniswap V2 trade implementation
        // In practice, you'd use the router's swapExactTokensForTokens function
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;
        
        // This is a placeholder - implement actual DEX integration
        return amountIn; // Simplified for demo
    }

    /**
     * @dev Emergency withdrawal
     */
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }

    /**
     * @dev Authorize bot address
     */
    function authorizeBot(address bot, bool authorized) external onlyOwner {
        authorizedBots[bot] = authorized;
        emit BotAuthorized(bot, authorized);
    }

    /**
     * @dev Whitelist token
     */
    function whitelistToken(address token, bool whitelisted) external onlyOwner {
        whitelistedTokens[token] = whitelisted;
        emit TokenWhitelisted(token, whitelisted);
    }

    /**
     * @dev Add DEX router
     */
    function addDexRouter(address router, address dex) external onlyOwner {
        dexRouters[router] = DexRouter(router, "");
        emit RouterAdded(router, dex);
    }

    /**
     * @dev Get contract balance
     */
    function getBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
}