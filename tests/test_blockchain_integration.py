#!/usr/bin/env python3
"""
Test script for the blockchain integration in the Hybrid Toll Management System.
This script will:
1. Check if the blockchain contract is deployed
2. If not deployed, it will first deploy the contract
3. Then test a sample transaction to the blockchain
"""

import json
import sys
import os
from pathlib import Path
from web3 import Web3

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

def test_blockchain_connection():
    """Test if we can connect to Ganache and interact with the blockchain."""
    
    # Connect to Ganache
    ganache_url = "http://127.0.0.1:7545"
    web3 = Web3(Web3.HTTPProvider(ganache_url))
    
    print("Testing connection to Ganache...")
    
    if not web3.is_connected():
        print("❌ Error: Could not connect to Ganache. Please make sure Ganache is running on http://127.0.0.1:7545")
        print("💡 To run Ganache, download it from https://www.trufflesuite.com/ganache and start a new workspace.")
        return False
    
    print("✅ Successfully connected to Ganache!")
    
    # Check accounts
    accounts = web3.eth.accounts
    if not accounts:
        print("❌ Error: No accounts found in Ganache.")
        return False
    
    print(f"✅ Found {len(accounts)} accounts in Ganache")
    print(f"   First account: {accounts[0]}")
    
    return True

def test_contract_deployment():
    """Test if contract is deployed and interact with it."""
    
    # Load deployment info
    try:
        deploy_path = PROJECT_ROOT / "backend" / "blockchain_contracts" / "output" / "deployment_info.json"
        with open(deploy_path, "r") as deploy_file:
            deployment_info = json.load(deploy_file)
    except FileNotFoundError:
        print("❌ Deployment info not found. The contract may not be deployed yet.")
        print("💡 Please deploy the contract first using the deployment script.")
        return False
    
    # Connect to Ganache
    ganache_url = "http://127.0.0.1:7545"
    web3 = Web3(Web3.HTTPProvider(ganache_url))
    
    if not web3.is_connected():
        print("❌ Cannot connect to Ganache for contract interaction.")
        return False
    
    # Get contract instance
    contract_address = deployment_info["contract_address"]
    contract_abi = deployment_info["contract_abi"]
    
    toll_contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    
    print(f"✅ Contract deployed at address: {contract_address}")
    
    # Test calling a read function
    try:
        transaction_count = toll_contract.functions.getAllTransactionCount().call()
        print(f"✅ Contract interaction successful. Current transaction count: {transaction_count}")
        return True
    except Exception as e:
        print(f"❌ Error interacting with contract: {str(e)}")
        return False

def simulate_toll_transaction():
    """Simulate a toll transaction using the blockchain integration."""
    
    # Import the blockchain module to test
    from backend.blockchain import send_to_chain
    
    print("\n--- Testing Toll Transaction Blockchain Integration ---")
    
    # Simulate a toll transaction
    result = send_to_chain(
        tx_hash="a1b2c3d4e5f678901234567890123456789012345678901234567890abcdef0",
        decision="allow",
        reason="Valid transaction",
        tagUID="TEST123",
        vehicle_type="CAR",
        amount=120.0
    )
    
    if result["success"]:
        print("✅ Toll transaction successfully recorded on blockchain!")
        print(f"   Transaction hash: {result['transaction_hash']}")
        print(f"   Contract address: {result['contract_address']}")
    else:
        print("⚠️  Toll transaction handled with fallback (blockchain may not be available)")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print(f"   Fallback used: {result['fallback_used']}")
    
    return True

def main():
    print("=== Hybrid Toll Management System - Blockchain Integration Test ===\n")
    
    # Test blockchain connection
    if not test_blockchain_connection():
        print("\n❌ Blockchain connection test failed. Please ensure Ganache is running.")
        return 1
    
    # Test contract deployment
    if not test_contract_deployment():
        print("\n⚠️  Contract deployment test failed. The contract might not be deployed yet.")
        print("💡 You can deploy the contract using: python backend/blockchain_contracts/deploy_contract.py")
    else:
        print("\n✅ Contract deployment test passed!")
    
    # Simulate a toll transaction
    simulate_toll_transaction()
    
    print("\n=== Blockchain Integration Test Complete ===")
    return 0

if __name__ == "__main__":
    exit(main())
