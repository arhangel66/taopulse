import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.dividends.bittensor_service import DividendService


@pytest.mark.asyncio
async def test_connect_and_warm_up(mock_substrate):
    """Test connecting to Bittensor and warming up the connection."""
    # Arrange
    with patch('app.dividends.bittensor_service.AsyncSubstrateInterface', return_value=mock_substrate):
        # Act
        service = DividendService("wss://test.endpoint")
        await service.connect(warm_up=True)
        
        # Assert
        assert service.substrate is not None
        assert service.is_warmed_up is True
        mock_substrate.get_chain_head.assert_called()
        mock_substrate.get_block_number.assert_called()
        mock_substrate.query.assert_called()


@pytest.mark.asyncio
async def test_close_connection(mock_substrate):
    """Test closing the Bittensor connection."""
    # Arrange
    with patch('app.dividends.bittensor_service.AsyncSubstrateInterface', return_value=mock_substrate):
        # Act
        service = DividendService()
        await service.connect(warm_up=False)
        await service.close()
        
        # Assert
        assert service.substrate is None
        assert service.is_warmed_up is False
        mock_substrate.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_dividends_specific_hotkey(mock_substrate):
    """Test getting dividends for a specific hotkey in a specific subnet."""
    # Arrange
    with patch('app.dividends.bittensor_service.AsyncSubstrateInterface', return_value=mock_substrate):
        # Act
        service = DividendService()
        await service.connect(warm_up=False)
        
        result = await service.get_dividends(
            netuid=18, 
            hotkey="5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa"
        )
        
        # Assert
        assert result == {"18": {"5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa": 1000}}
        mock_substrate.get_chain_head.assert_called()
        mock_substrate.query.assert_called_with(
            "SubtensorModule", 
            "TaoDividendsPerSubnet", 
            [18, "5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa"], 
            block_hash=mock_substrate.get_chain_head.return_value
        )


@pytest.mark.asyncio
async def test_get_dividends_all_hotkeys_in_subnet(mock_substrate):
    """Test getting dividends for all hotkeys in a specific subnet."""
    # Arrange
    with patch('app.dividends.bittensor_service.AsyncSubstrateInterface', return_value=mock_substrate), \
         patch('app.dividends.bittensor_service.decode_account_id', side_effect=["key1_ss58", "key2_ss58"]):
        
        # Act
        service = DividendService()
        await service.connect(warm_up=False)
        
        result = await service.get_dividends(netuid=18)
        
        # Assert
        assert result == {"18": {"key1_ss58": 100, "key2_ss58": 200}}
        mock_substrate.get_chain_head.assert_called()
        mock_substrate.query_map.assert_called_with(
            "SubtensorModule", 
            "TaoDividendsPerSubnet", 
            [18], 
            block_hash=mock_substrate.get_chain_head.return_value
        )


@pytest.mark.asyncio
async def test_get_dividends_multiple_subnets(mock_substrate):
    """Test getting dividends across multiple subnets."""
    # Arrange
    with patch('app.dividends.bittensor_service.AsyncSubstrateInterface', return_value=mock_substrate), \
         patch('app.dividends.bittensor_service.decode_account_id', side_effect=["key1_ss58", "key2_ss58"] * 50), \
         patch('app.dividends.bittensor_service.range', return_value=[1, 2]):  # Simulate 2 subnets for faster test
        
        # Act
        service = DividendService()
        await service.connect(warm_up=False)
        
        result = await service.get_dividends()
        
        # Assert
        assert "1" in result
        assert "2" in result
        assert result["1"] == {"key1_ss58": 100, "key2_ss58": 200}
        assert result["2"] == {"key1_ss58": 100, "key2_ss58": 200}


@pytest.mark.asyncio
async def test_query_error_handling(mock_substrate):
    """Test error handling during dividend queries."""
    # Arrange
    mock_substrate.query.side_effect = Exception("Test exception")
    
    with patch('app.dividends.bittensor_service.AsyncSubstrateInterface', return_value=mock_substrate):
        # Act
        service = DividendService()
        await service.connect(warm_up=False)
        
        # Assert
        with pytest.raises(Exception, match="Test exception"):
            await service.get_dividends(netuid=18, hotkey="test_hotkey")
