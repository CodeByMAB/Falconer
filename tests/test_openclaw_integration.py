"""Integration tests for OpenClaw + Falconer API."""

import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from falconer.api.test_endpoints import create_api_app
from falconer.config import Config


class TestOpenClawAPIIntegration:
    """Test OpenClaw API integration."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test configuration
        self.config = Config(
            openclaw_enabled=True,
            openclaw_api_key="test-api-key-123",
            env="test",
        )
        
        # Create test API app
        self.app = create_api_app(self.config)
        self.client = TestClient(self.app)

    def test_health_check_no_auth(self):
        """Test that health check works without authentication."""
        response = self.client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "falconer-api"

    def test_echo_endpoint_no_auth(self):
        """Test that echo endpoint works without authentication."""
        test_data = {"message": "hello", "test": True}
        response = self.client.post("/api/test/echo", json=test_data)
        assert response.status_code == 200
        data = response.json()
        assert data["echo"] == test_data

    def test_bitcoin_endpoints_require_api_key(self):
        """Test that Bitcoin endpoints require API key when OpenClaw is enabled."""
        # Test without API key
        response = self.client.get("/api/bitcoin/blockchain-info")
        assert response.status_code == 401
        assert response.json()["error"] == "API key required"
        
        # Test with invalid API key
        response = self.client.get("/api/bitcoin/blockchain-info", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        assert response.json()["error"] == "Invalid API key"

    def test_bitcoin_endpoints_with_valid_api_key(self):
        """Test that Bitcoin endpoints work with valid API key."""
        # Mock the Bitcoin adapter
        with patch("falconer.api.test_endpoints.BitcoinAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.get_blockchain_info.return_value = {
                "blocks": 800000,
                "headers": 800000,
                "chain": "main",
                "difficulty": 123456789,
                "size_on_disk": 1000000000,
                "pruned": False,
            }
            mock_adapter.close.return_value = None
            mock_adapter_class.return_value = mock_adapter
            
            # Test blockchain info endpoint
            response = self.client.get(
                "/api/bitcoin/blockchain-info", 
                headers={"X-API-Key": "test-api-key-123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["blocks"] == 800000
            assert data["chain"] == "main"
            assert data["difficulty"] == 123456789
            assert "timestamp" in data

    def test_mempool_info_endpoint(self):
        """Test mempool info endpoint."""
        with patch("falconer.api.test_endpoints.BitcoinAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.get_mempool_info.return_value = {
                "loaded": True,
                "size": 5000,
                "bytes": 1000000,
                "usage": 500000,
                "maxmempool": 300000000,
                "mempoolminfee": 0.00001,
            }
            mock_adapter.close.return_value = None
            mock_adapter_class.return_value = mock_adapter
            
            response = self.client.get(
                "/api/bitcoin/mempool-info", 
                headers={"X-API-Key": "test-api-key-123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["size"] == 5000
            assert data["bytes"] == 1000000

    def test_fee_estimates_endpoint(self):
        """Test fee estimates endpoint."""
        with patch("falconer.api.test_endpoints.BitcoinAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.estimate_fee_rates.return_value = {
                "fast": 20,
                "medium": 10,
                "slow": 5,
                "economical": 2,
                "minimum": 1,
            }
            mock_adapter.close.return_value = None
            mock_adapter_class.return_value = mock_adapter
            
            response = self.client.get(
                "/api/bitcoin/fee-estimates", 
                headers={"X-API-Key": "test-api-key-123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["fast"] == 20
            assert data["slow"] == 5

    def test_network_stats_endpoint(self):
        """Test network stats endpoint."""
        with patch("falconer.api.test_endpoints.BitcoinAdapter") as mock_bitcoin_class, \
             patch("falconer.api.test_endpoints.ElectrsAdapter") as mock_electrs_class:
            
            mock_bitcoin = Mock()
            mock_bitcoin.get_blockchain_info.return_value = {
                "blocks": 800000,
                "headers": 800000,
                "chain": "main",
                "difficulty": 123456789,
            }
            mock_bitcoin.get_mempool_info.return_value = {
                "size": 5000,
                "bytes": 1000000,
            }
            mock_bitcoin.close.return_value = None
            mock_bitcoin_class.return_value = mock_bitcoin
            
            mock_electrs = Mock()
            mock_electrs.get_tip_height.return_value = 800000
            mock_electrs.close.return_value = None
            mock_electrs_class.return_value = mock_electrs
            
            response = self.client.get(
                "/api/bitcoin/network-stats", 
                headers={"X-API-Key": "test-api-key-123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["network"] == "main"
            assert data["block_height"] == 800000
            assert data["electrs_tip_height"] == 800000
            assert data["is_synced"] == True

    def test_market_analysis_endpoint(self):
        """Test market analysis endpoint (mock data)."""
        response = self.client.get(
            "/api/bitcoin/market-analysis", 
            headers={"X-API-Key": "test-api-key-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "opportunity_score" in data
        assert "risk_level" in data
        assert "recommendation" in data
        assert "timestamp" in data

    def test_address_info_endpoint(self):
        """Test address info endpoint."""
        with patch("falconer.api.test_endpoints.ElectrsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.get_address_info.return_value = {
                "balance": 1000000,
                "tx_count": 10,
                "unconfirmed_balance": 50000,
            }
            mock_adapter.close.return_value = None
            mock_adapter_class.return_value = mock_adapter
            
            response = self.client.get(
                "/api/bitcoin/address-info?address=bc1qtest123", 
                headers={"X-API-Key": "test-api-key-123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["address"] == "bc1qtest123"
            assert data["balance_sats"] == 1000000
            assert data["tx_count"] == 10

    def test_transaction_info_endpoint(self):
        """Test transaction info endpoint."""
        with patch("falconer.api.test_endpoints.BitcoinAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.get_transaction.return_value = {
                "confirmations": 6,
                "size": 225,
                "weight": 500,
                "fee": 1000,
                "fee_rate": 4.44,
            }
            mock_adapter.close.return_value = None
            mock_adapter_class.return_value = mock_adapter
            
            response = self.client.get(
                "/api/bitcoin/transaction?tx_id=abc123", 
                headers={"X-API-Key": "test-api-key-123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["txid"] == "abc123"
            assert data["confirmations"] == 6
            assert data["fee"] == 1000

    def test_error_handling(self):
        """Test error handling in API endpoints."""
        with patch("falconer.api.test_endpoints.BitcoinAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.get_blockchain_info.side_effect = Exception("Connection failed")
            mock_adapter_class.return_value = mock_adapter
            
            response = self.client.get(
                "/api/bitcoin/blockchain-info", 
                headers={"X-API-Key": "test-api-key-123"}
            )
            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "Failed to get blockchain info"
            assert data["status_code"] == 500
            assert "timestamp" in data

    def test_openclaw_disabled_allows_access(self):
        """Test that when OpenClaw is disabled, endpoints are accessible without API key."""
        # Create config with OpenClaw disabled
        disabled_config = Config(
            openclaw_enabled=False,
            openclaw_api_key="test-api-key-123",
            env="test",
        )
        
        disabled_app = create_api_app(disabled_config)
        disabled_client = TestClient(disabled_app)
        
        # Should work without API key when OpenClaw is disabled
        response = disabled_client.get("/api/bitcoin/blockchain-info")
        assert response.status_code == 400  # Will fail due to missing Bitcoin adapter, but not 401

    def test_security_headers(self):
        """Test that security headers are present in responses."""
        response = self.client.get("/api/health")
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "Content-Security-Policy" in response.headers

    def test_cors_headers(self):
        """Test that CORS headers are properly configured."""
        response = self.client.get("/api/health")
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"


class TestBitcoinMarketAnalyzerSkill:
    """Test the Bitcoin Market Analyzer skill for OpenClaw."""

    def setup_method(self):
        """Set up test fixtures."""
        import sys
        import os
        
        # Add the openclaw-skills directory to the path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "openclaw-skills"))
        
        from bitcoin_market_analyzer import BitcoinMarketAnalyzer
        
        self.analyzer = BitcoinMarketAnalyzer()
        
        # Mock environment variables
        os.environ["FALCONER_API_URL"] = "http://test-api:8000"
        os.environ["FALCONER_API_KEY"] = "test-key"

    def test_skill_initialization(self):
        """Test skill initialization."""
        assert self.analyzer.api_url == "http://test-api:8000"
        assert self.analyzer.api_key == "test-key"

    def test_api_request_success(self):
        """Test successful API request."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"test": "data"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = self.analyzer._make_api_request("/test-endpoint")
            assert result == {"test": "data"}
            
            # Verify headers were set correctly
            call_args = mock_get.call_args
            assert call_args[1]["headers"]["X-API-Key"] == "test-key"

    def test_api_request_failure(self):
        """Test failed API request."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")
            
            result = self.analyzer._make_api_request("/test-endpoint")
            assert "error" in result
            assert "Connection error" in result["error"]

    def test_get_blockchain_info(self):
        """Test get_blockchain_info method."""
        with patch.object(self.analyzer, "_make_api_request") as mock_request:
            mock_request.return_value = {"blocks": 800000}
            
            result = self.analyzer.get_blockchain_info()
            assert result == {"blocks": 800000}
            mock_request.assert_called_once_with("/api/bitcoin/blockchain-info")

    def test_get_comprehensive_analysis(self):
        """Test comprehensive analysis method."""
        with patch.multiple(
            self.analyzer,
            get_blockchain_info=Mock(return_value={"blocks": 800000}),
            get_mempool_info=Mock(return_value={"size": 5000}),
            get_fee_estimates=Mock(return_value={"fast": 20}),
            get_network_stats=Mock(return_value={"network": "main"}),
            get_market_analysis=Mock(return_value={"opportunity_score": 0.8}),
        ):
            result = self.analyzer.get_comprehensive_analysis()
            
            assert "blockchain" in result
            assert "mempool" in result
            assert "fees" in result
            assert "network" in result
            assert "market" in result
            assert result["blockchain"]["blocks"] == 800000
            assert result["market"]["opportunity_score"] == 0.8


@pytest.mark.asyncio
async def test_api_performance():
    """Test API performance under load."""
    config = Config(
        openclaw_enabled=True,
        openclaw_api_key="test-key",
        env="test",
    )
    
    app = create_api_app(config)
    client = TestClient(app)
    
    # Test multiple concurrent requests
    async def make_request():
        response = client.get("/api/health")
        return response.status_code
    
    tasks = [make_request() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    # All requests should succeed
    assert all(status == 200 for status in results)


def test_api_version_consistency():
    """Test that API version is consistent."""
    config = Config(env="test")
    app = create_api_app(config)
    client = TestClient(app)
    
    response = client.get("/api/health")
    data = response.json()
    
    # Version should match package version
    from falconer import __version__
    assert data["version"] == __version__