import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.trade.trade_service import TradeService
from app.trade.schemas import TradeResult, ActionEnum
from bittensor import Balance


@pytest.mark.asyncio
async def test_initialize_wallet(mock_wallet):
    """Test initializing the wallet."""
    # Arrange
    with patch('app.trade.trade_service.Wallet', return_value=mock_wallet):
        # Act
        service = TradeService()
        result = await service.initialize("test_password")
        
        # Assert
        assert result["success"] is True
        mock_wallet.coldkey_file.save_password_to_env.assert_called_once()
        mock_wallet.unlock_coldkey.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_wallet_failure(mock_wallet):
    """Test wallet initialization failure."""
    # Arrange
    mock_wallet.unlock_coldkey.side_effect = Exception("Test error")
    
    with patch('app.trade.trade_service.Wallet', return_value=mock_wallet):
        # Act
        service = TradeService()
        result = await service.initialize("test_password")
        
        # Assert
        assert result["success"] is False
        assert "Failed to unlock coldkey" in result["message"]


@pytest.mark.asyncio
async def test_trade_positive_sentiment(mock_wallet, mock_subtensor):
    """Test trade with positive sentiment (add stake)."""
    # Arrange
    with patch('app.trade.trade_service.Wallet', return_value=mock_wallet), \
         patch('app.trade.trade_service.AsyncSubtensor', return_value=mock_subtensor), \
         patch('app.trade.trade_service.Balance.from_tao', return_value=0.05):
        
        # Act
        service = TradeService()
        service.wallet = mock_wallet  # Skip initialization
        
        result = await service.trade(
            netuid_for_trade=18, 
            hotkey="5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa", 
            sentiment=5
        )
        
        # Assert
        assert result.is_success is True
        assert result.action == ActionEnum.stake
        assert result.amount == 0.05  # 0.01 * 5
        mock_subtensor.add_stake.assert_called_once()


@pytest.mark.asyncio
async def test_trade_negative_sentiment(mock_wallet, mock_subtensor):
    """Test trade with negative sentiment (unstake)."""
    # Arrange
    with patch('app.trade.trade_service.Wallet', return_value=mock_wallet), \
         patch('app.trade.trade_service.AsyncSubtensor', return_value=mock_subtensor), \
         patch('app.trade.trade_service.Balance.from_tao', return_value=0.05):
        
        # Act
        service = TradeService()
        service.wallet = mock_wallet  # Skip initialization
        
        result = await service.trade(
            netuid_for_trade=18, 
            hotkey="5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa", 
            sentiment=-5
        )
        
        # Assert
        assert result.is_success is True
        assert result.action == ActionEnum.unstake
        assert result.amount == 0.05  # 0.01 * 5
        mock_subtensor.unstake.assert_called_once()


@pytest.mark.asyncio
async def test_trade_zero_sentiment(mock_wallet):
    """Test trade with zero sentiment (no action)."""
    # Arrange
    with patch('app.trade.trade_service.Wallet', return_value=mock_wallet):
        # Act
        service = TradeService()
        service.wallet = mock_wallet  # Skip initialization
        
        result = await service.trade(
            netuid_for_trade=18, 
            hotkey="5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa", 
            sentiment=0
        )
        
        # Assert
        assert result.is_success is True
        assert result.message == "Sentiment score is 0: No action taken"
        assert result.action is None


@pytest.mark.asyncio
async def test_trade_wallet_not_initialized():
    """Test trade with uninitialized wallet."""
    # Act
    service = TradeService()
    
    result = await service.trade(
        netuid_for_trade=18, 
        hotkey="5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa", 
        sentiment=5
    )
    
    # Assert
    assert result.is_success is False
    assert "Wallet not initialized" in result.message


@pytest.mark.asyncio
async def test_trade_hotkey_mismatch(mock_wallet):
    """Test trade with hotkey that doesn't match wallet."""
    # Arrange
    with patch('app.trade.trade_service.Wallet', return_value=mock_wallet):
        # Act
        service = TradeService()
        service.wallet = mock_wallet  # Skip initialization
        
        result = await service.trade(
            netuid_for_trade=18, 
            hotkey="different_hotkey", 
            sentiment=5
        )
        
        # Assert
        assert result.is_success is False
        assert "Hotkey address does not match wallet hotkey" in result.message
