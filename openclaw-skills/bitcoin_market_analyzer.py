#!/usr/bin/env python3
"""
OpenClaw Skill: Bitcoin Market Analyzer

This skill integrates with Falconer API to provide Bitcoin market analysis
and blockchain information to OpenClaw users.

Integration Pattern:
- OpenClaw executes this skill as a Python script
- Skill makes HTTP requests to Falconer API
- Results are returned to OpenClaw for user display
"""

import os
import requests
from typing import Dict, Any, Optional
from datetime import datetime

class BitcoinMarketAnalyzer:
    """Bitcoin Market Analyzer skill for OpenClaw."""
    
    def __init__(self):
        """Initialize the Bitcoin Market Analyzer skill."""
        self.api_url = os.environ.get("FALCONER_API_URL", "http://falconer-api:8000")
        self.api_key = os.environ.get("FALCONER_API_KEY", "")
        
    def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a request to the Falconer API with proper error handling."""
        url = f"{self.api_url}{endpoint}"
        headers = {
            "X-API-Key": self.api_key,
            "User-Agent": "OpenClaw-BitcoinMarketAnalyzer/1.0",
            "Accept": "application/json"
        } if self.api_key else {
            "User-Agent": "OpenClaw-BitcoinMarketAnalyzer/1.0",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=10,
                verify=True  # Verify SSL in production
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            return {
                "error": error_msg,
                "endpoint": endpoint,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error"
            }
    
    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get current Bitcoin blockchain information."""
        return self._make_api_request("/api/bitcoin/blockchain-info")
    
    def get_mempool_info(self) -> Dict[str, Any]:
        """Get current mempool information."""
        return self._make_api_request("/api/bitcoin/mempool-info")
    
    def get_fee_estimates(self) -> Dict[str, Any]:
        """Get current fee estimates."""
        return self._make_api_request("/api/bitcoin/fee-estimates")
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get Bitcoin network statistics."""
        return self._make_api_request("/api/bitcoin/network-stats")
    
    def get_market_analysis(self) -> Dict[str, Any]:
        """Get AI-powered market analysis."""
        return self._make_api_request("/api/bitcoin/market-analysis")
    
    def get_address_info(self, address: str) -> Dict[str, Any]:
        """Get information about a Bitcoin address."""
        return self._make_api_request("/api/bitcoin/address-info", {"address": address})
    
    def get_transaction_info(self, tx_id: str) -> Dict[str, Any]:
        """Get information about a Bitcoin transaction."""
        return self._make_api_request("/api/bitcoin/transaction", {"tx_id": tx_id})
    
    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive Bitcoin market analysis."""
        analysis = {
            "blockchain": self.get_blockchain_info(),
            "mempool": self.get_mempool_info(),
            "fees": self.get_fee_estimates(),
            "network": self.get_network_stats(),
            "market": self.get_market_analysis(),
        }
        return analysis

# OpenClaw Skill Interface
def openclaw_skill_main(command: str = "analysis", **kwargs) -> Dict[str, Any]:
    """
    Main entry point for OpenClaw skill execution.
    
    Args:
        command: The command to execute (analysis, blockchain, mempool, fees, etc.)
        **kwargs: Additional parameters for the command
        
    Returns:
        Dictionary with skill execution results
    """
    analyzer = BitcoinMarketAnalyzer()
    
    try:
        if command == "blockchain":
            return {"status": "success", "data": analyzer.get_blockchain_info()}
        
        elif command == "mempool":
            return {"status": "success", "data": analyzer.get_mempool_info()}
        
        elif command == "fees":
            return {"status": "success", "data": analyzer.get_fee_estimates()}
        
        elif command == "network":
            return {"status": "success", "data": analyzer.get_network_stats()}
        
        elif command == "market":
            return {"status": "success", "data": analyzer.get_market_analysis()}
        
        elif command == "address":
            address = kwargs.get("address", "")
            if not address:
                return {"status": "error", "error": "Address parameter required"}
            return {"status": "success", "data": analyzer.get_address_info(address)}
        
        elif command == "transaction":
            tx_id = kwargs.get("tx_id", "")
            if not tx_id:
                return {"status": "error", "error": "tx_id parameter required"}
            return {"status": "success", "data": analyzer.get_transaction_info(tx_id)}
        
        elif command == "analysis" or command == "full":
            return {"status": "success", "data": analyzer.get_comprehensive_analysis()}
        
        else:
            return {"status": "error", "error": f"Unknown command: {command}"}
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Example usage and testing
if __name__ == "__main__":
    print("🔍 Bitcoin Market Analyzer - OpenClaw Skill")
    print("=" * 50)
    
    # Test the OpenClaw interface
    result = openclaw_skill_main("analysis")
    
    if result["status"] == "success":
        analysis = result["data"]
        
        # Display blockchain info
        blockchain = analysis["blockchain"]
        print(f"📊 Blockchain: {blockchain.get('blocks', 'N/A')} blocks")
        print(f"🔗 Chain: {blockchain.get('chain', 'N/A')}")
        print(f"💪 Difficulty: {blockchain.get('difficulty', 'N/A')}")
        
        # Display mempool info
        mempool = analysis["mempool"]
        print(f"📦 Mempool: {mempool.get('size', 'N/A')} transactions")
        print(f"💾 Size: {mempool.get('bytes', 'N/A')} bytes")
        
        # Display fee estimates
        fees = analysis["fees"]
        print(f"⚡ Fast fee: {fees.get('fast', 'N/A')} sats/vbyte")
        print(f"🐢 Slow fee: {fees.get('slow', 'N/A')} sats/vbyte")
        
        # Display market analysis
        market = analysis["market"]
        print(f"📈 Opportunity score: {market.get('opportunity_score', 'N/A')}")
        print(f"⚠️  Risk level: {market.get('risk_level', 'N/A')}")
        print(f"💡 Recommendation: {market.get('recommendation', 'N/A')}")
        
        print("\n✅ Skill execution successful!")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")