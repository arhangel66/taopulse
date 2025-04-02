import asyncio
import time
from typing import Dict, Any, Optional

from bittensor import Balance, AsyncSubtensor
from bittensor_wallet import Wallet

from app.common.logging import get_logger
from app.trade.schemas import TradeResult, ActionEnum

logger = get_logger(__name__)


class TradeService:
    def __init__(
        self,
        hotkey_ss58: str = "5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa",
        netuid: int = 18,
        wallet_name: str = "main",
        hotkey_name: str = "main",
        network: str = "test",
    ):
        self.hotkey_ss58 = hotkey_ss58
        self.netuid = netuid
        self.wallet_name = wallet_name
        self.hotkey_name = hotkey_name
        self.network = network
        self.wallet = None

    async def initialize(self, password: str) -> Dict[str, Any]:
        """Initialize wallet and connection to subtensor."""
        try:
            # Create wallet object
            self.wallet = Wallet(
                name=self.wallet_name, path="~/.bittensor/wallets/", hotkey=self.hotkey_name
            )

            # Save password to environment variable for coldkey
            try:
                self.wallet.coldkey_file.save_password_to_env(password=password)
            except Exception as e:
                return {"success": False, "message": f"Failed to save password to env: {e}"}

            # Unlock coldkey
            try:
                self.wallet.unlock_coldkey()
            except Exception as e:
                return {"success": False, "message": f"Failed to unlock coldkey: {e}"}

            logger.info("wallet init success.")
            return {"success": True}

        except Exception as e:
            return {"success": False, "message": f"Initialization error: {e}"}

    async def trade(self, netuid_for_trade: int, hotkey: str, sentiment: int) -> TradeResult:
        """
        Execute trade based on sentiment score.
        Positive sentiment adds stake, negative sentiment removes stake.

        Args:
            netuid_for_trade: Int indicating subnet ID for trade
            hotkey: Str indicating hotkey address for trade
            sentiment: Int indicating sentiment (-10 to 10)

        Returns:
            TradeResult containing success status and transaction details or error message
        """
        logger.info(f"Executing trade for netuid {netuid_for_trade} with sentiment {sentiment}")
        start_time = time.time()
        result = TradeResult(is_success=False)
        try:
            if self.wallet is None:
                raise ValueError("Wallet not initialized")

            if hotkey != self.wallet.hotkey.ss58_address:
                raise ValueError("Hotkey address does not match wallet hotkey")

            # Calculate amount for staking
            amount_tao = abs(0.01 * sentiment)
            amount = Balance.from_tao(amount_tao)
            result.amount = float(amount_tao)

            # Staking/unstaking logic
            if sentiment > 0:
                result = await self.add_stake(amount, amount_tao, hotkey, netuid_for_trade, result)

            elif sentiment < 0:
                result = await self.unstake(amount, amount_tao, hotkey, netuid_for_trade, result)

            else:
                result.is_success = True
                result.message = "Sentiment score is 0: No action taken"

        except Exception as e:
            result.message = f"Trade execution error: {e}"
            result.is_success = False
        finally:
            result.duration = time.time() - start_time
            return result

    async def unstake(self, amount, amount_tao, hotkey, netuid_for_trade, result):
        result.action = ActionEnum.unstake
        async with AsyncSubtensor(network=self.network) as subtensor:
            success = await subtensor.unstake(
                wallet=self.wallet,
                hotkey_ss58=hotkey,
                netuid=netuid_for_trade,
                amount=amount,
                wait_for_inclusion=True,
                wait_for_finalization=False,
            )
        if success:
            result.is_success = True
            result.message = f"Successfully unstaked {amount_tao} TAO"
        else:
            result.message = "Failed to unstake"
        return result

    async def add_stake(self, amount, amount_tao, hotkey, netuid_for_trade, result):
        result.action = ActionEnum.stake
        async with AsyncSubtensor(network=self.network) as subtensor:
            success = await subtensor.add_stake(
                wallet=self.wallet,
                hotkey_ss58=hotkey,
                netuid=netuid_for_trade,
                amount=amount,
                wait_for_inclusion=True,
                wait_for_finalization=False,
            )
        if success:
            result.is_success = True
            result.message = f"Successfully staked {amount_tao} TAO"
        else:
            result.message = "Failed to add stake"
        return result


if __name__ == "__main__":

    async def execute_trade(
        netuid_for_trade: int,
        hotkey: str,
        sentiment: int,
        password: str,
        hotkey_ss58: Optional[str] = None,
        netuid: Optional[int] = None,
        wallet_name: Optional[str] = None,
        hotkey_name: Optional[str] = None,
    ) -> TradeResult:
        """
        Main function to execute a trade based on sentiment score.

        Args:
            netuid_for_trade: Int indicating subnet ID for trade
            hotkey: Str indicating hotkey address for trade
            sentiment: Int indicating sentiment (-10 to 10)
            password: Password for coldkey
            hotkey_ss58: Optional hotkey address
            netuid: Optional subnet ID
            wallet_name: Optional wallet name
            hotkey_name: Optional hotkey name

        Returns:
            TradeResult containing success status and transaction details or error message
        """
        service = TradeService(
            hotkey_ss58=hotkey_ss58 or "5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa",
            netuid=netuid or 18,
            wallet_name=wallet_name or "main",
            hotkey_name=hotkey_name or "main",
        )

        try:
            # Initialize wallet
            init_result = await service.initialize(password)

            trade_result = await service.trade(netuid_for_trade, hotkey, sentiment)
            await service.close()
            return trade_result

        except Exception as e:
            await service.close()
            return TradeResult(success=False, message=f"Execution error: {e}", action="error")

    async def main():
        # Example usage
        result = await execute_trade(
            netuid_for_trade=18,
            hotkey="5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa",
            sentiment=5,
            password="Xi1nflYIT2L26iIf",
        )
        print(result)

    asyncio.run(main())
