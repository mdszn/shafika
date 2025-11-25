"""
DEX (Decentralized Exchange) utility functions and constants
"""

# ==================== Event Signatures ====================

# Uniswap V2 / SushiSwap Swap Event
# event Swap(
#     address indexed sender,
#     uint amount0In,
#     uint amount1In,
#     uint amount0Out,
#     uint amount1Out,
#     address indexed to
# )
UNISWAP_V2_SWAP_SIGNATURE = (
    "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
)

# Uniswap V3 Swap Event
# event Swap(
#     address indexed sender,
#     address indexed recipient,
#     int256 amount0,
#     int256 amount1,
#     uint160 sqrtPriceX96,
#     uint128 liquidity,
#     int24 tick
# )
UNISWAP_V3_SWAP_SIGNATURE = (
    "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
)

# ==================== Factory Addresses (Ethereum Mainnet) ====================

UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNISWAP_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
SUSHISWAP_FACTORY = "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac"

# ==================== Popular Pools (for reference) ====================

# Uniswap V3 Pools
WETH_USDC_V3_005 = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # 0.05% fee
WETH_USDC_V3_030 = "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"  # 0.3% fee
WETH_USDT_V3_005 = "0x11b815efb8f581194ae79006d24e0d814b7697f6"  # 0.05% fee

# Uniswap V2 Pools
WETH_USDC_V2 = "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"
WETH_USDT_V2 = "0x0d4a11d5eeaac28ec3f61d100daf4d40471f1852"
WETH_DAI_V2 = "0xa478c2975ab1ea89e8196811f51a7b7ade33eb11"

def detect_dex_from_pool(pool_address: str, factory_cache: dict = None) -> str:
    """
    Detect which DEX a pool belongs to.

    Args:
        pool_address: The pool contract address
        factory_cache: Optional cache of pool->factory mappings

    Returns:
        DEX name: "uniswap_v2", "uniswap_v3", "sushiswap", or "unknown"
    """
    # This is a simplified version - in production you'd query the factory
    # or maintain a database of known pools
    pool_lower = pool_address.lower()

    # Check against known pools
    if pool_lower in [
        WETH_USDC_V3_005.lower(),
        WETH_USDC_V3_030.lower(),
        WETH_USDT_V3_005.lower(),
    ]:
        return "uniswap_v3"
    elif pool_lower in [
        WETH_USDC_V2.lower(),
        WETH_USDT_V2.lower(),
        WETH_DAI_V2.lower(),
    ]:
        return "uniswap_v2"

    # Default based on event signature (caller should pass this context)
    return "unknown"
