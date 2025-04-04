import asyncio
from async_substrate_interface.async_substrate import AsyncSubstrateInterface
from bittensor.core.chain_data import decode_account_id
from bittensor.core.settings import SS58_FORMAT
import time
import warnings
import logging
from typing import Optional
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Ignore deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


class DividendServiceNoWarmUp:
    """
    Client for interacting with the Bittensor blockchain.
    Creates a new connection for each query.
    """

    def __init__(self, endpoint: str = "wss://entrypoint-finney.opentensor.ai:443"):
        """
        Initialize the client with the blockchain endpoint.
        """
        self.endpoint = endpoint

    async def connect(self, warm_up: bool = True):
        """
        Establish connection to the Bittensor blockchain and optionally warm it up.

        Args:
            warm_up: If True, performs a lightweight query to fully initialize the connection
        """
        logger.info(f"fake connect")

    async def _warm_up(self):
        pass

    async def close(self):
        pass

    async def get_dividends(
        self, netuid: Optional[int] = None, hotkey: Optional[str] = None
    ) -> dict[str, dict[str, int]]:
        """
        Query TAO dividends from the blockchain.

        Args:
            netuid: Optional subnet ID (1-50). If None, query all subnets.
            hotkey: Optional hotkey to filter results. If None, query all hotkeys.

        Returns:
            dictionary mapping netuids to hotkey-dividend mappings
        """
        # Log query details
        query_type = "single hotkey" if hotkey else "all hotkeys"
        subnet_desc = f"subnet {netuid}" if netuid is not None else "all subnets"
        logger.info(f"Querying {query_type} in {subnet_desc}...")

        # Timing the actual query
        start = time.time()
        results = {}

        try:
            # Create a new connection for each query
            async with AsyncSubstrateInterface(self.endpoint, ss58_format=SS58_FORMAT) as substrate:
                # Get the latest block hash
                block_hash = await substrate.get_chain_head()
                block_hash_time = time.time() - start

                # Determine which netuids to query
                netuids = [netuid] if netuid is not None else range(1, 51)

                # Create tasks for parallel execution
                tasks = []
                for net_id in netuids:
                    if hotkey:
                        # Query single hotkey
                        tasks.append(self._query_single(substrate, net_id, hotkey, block_hash))
                    else:
                        # Query all hotkeys in subnet
                        tasks.append(self._query_subnet(substrate, net_id, block_hash))

                # Run all queries in parallel
                subnet_results = await asyncio.gather(*tasks)

                # Organize results by netuid
                results = {str(net_id): result for net_id, result in zip(netuids, subnet_results)}

                elapsed = time.time() - start
                logger.info(
                    f"Query completed in {elapsed:.2f}s (block hash took {block_hash_time:.2f}s)"
                )

        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise

        return results

    async def _query_single(
        self, substrate, net_id: int, hotkey: str, block_hash: str
    ) -> dict[str, int]:
        """
        Query dividends for a specific hotkey in a subnet.
        """
        result = {}
        value = await substrate.query(
            "SubtensorModule", "TaoDividendsPerSubnet", [net_id, hotkey], block_hash=block_hash
        )
        result[hotkey] = value.value if value else 0
        return result

    async def _query_subnet(self, substrate, net_id: int, block_hash: str) -> dict[str, int]:
        """
        Query dividends for all hotkeys in a subnet.
        """
        result = {}
        query_result = await substrate.query_map(
            "SubtensorModule", "TaoDividendsPerSubnet", [net_id], block_hash=block_hash
        )

        async for key, value in query_result:
            account_id = decode_account_id(key)
            result[account_id] = value.value

        return result


async def main():
    """
    Example of how to use the BittensorClient class.
    """
    logger.info("Starting main loop...")

    # Create client and maintain persistent connection
    logger.info("Creating Bittensor client...")
    dividend_service = DividendServiceNoWarmUp()
    t1 = time.time()
    try:
        # Connect once with warm-up
        await dividend_service.connect(warm_up=True)

        # Example 1: Query specific hotkey in a specific subnet
        hotkey = "5F2CsUDVbRbVMXTh9fAzF9GacjVX7UapvRxidrxe7z8BYckQ"
        results1 = await dividend_service.get_dividends(hotkey=hotkey, netuid=1)
        logger.info(json.dumps(results1, indent=2))

        # Example 2: Query the same hotkey in a different subnet
        results2 = await dividend_service.get_dividends(hotkey=hotkey, netuid=2)
        logger.info(json.dumps(results2, indent=2))  # Fixed to print results2

        results3 = await dividend_service.get_dividends(hotkey=hotkey, netuid=3)
        logger.info(json.dumps(results3, indent=3))  # Fixed to print results2

        logger.info(f"Time taken: {time.time() - t1:.2f}s")

        # Example 3: Query all hotkeys in a subnet (potentially slow)
        # Uncomment if needed:
        # subnet_results = await client.query_tao_dividends(netuid=1)
        # logger.info(f"Found {sum(len(data) for data in subnet_results.values())} entries")

    finally:
        # Close connection when completely done
        await dividend_service.close()


if __name__ == "__main__":
    logger.info("Starting...")
    asyncio.run(main())
