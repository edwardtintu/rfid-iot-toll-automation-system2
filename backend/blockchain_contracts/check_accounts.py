import json
from web3 import Web3

def deploy_contract_with_provided_key():
    # Connect to Ganache
    ganache_url = "http://127.0.0.1:7545"
    web3 = Web3(Web3.HTTPProvider(ganache_url))
    
    # Check if connected to Ganache
    if not web3.is_connected():
        print("Error: Could not connect to Ganache. Please make sure Ganache is running.")
        return None, None
    
    print("Connected to Ganache successfully!")
    
    # Load contract ABI and bytecode
    with open("/Users/hariharansundaramoorthy/HTMS_Project/backend/blockchain_contracts/output/contract_abi.json", "r") as abi_file:
        contract_abi = json.load(abi_file)
    
    with open("/Users/hariharansundaramoorthy/HTMS_Project/backend/blockchain_contracts/output/contract_bytecode.txt", "r") as bytecode_file:
        contract_bytecode = bytecode_file.read()
    
    # Set up the contract instance
    contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    
    # Get the first available account from Ganache
    accounts = web3.eth.accounts
    if not accounts:
        print("Error: No accounts found in Ganache.")
        return None, None
    
    deployer_account = accounts[0]
    print(f"Using account {deployer_account} to deploy the contract")
    
    # Print all available accounts for reference
    print("Available accounts in Ganache:")
    for i, acc in enumerate(accounts):
        print(f"  Account {i}: {acc}")
    
    # IMPORTANT: You need to provide the private key for the account you want to use
    # This is just a placeholder - you'll need to get the actual private key from Ganache UI
    print("\n⚠️  IMPORTANT: This script cannot automatically determine the private key for your Ganache accounts.")
    print("Please get the private key for account 0 from your Ganache UI and update this script.")
    print("In Ganache UI, click on the key icon next to the account to reveal the private key.")
    print("")
    
    # For now, let's just list the accounts and exit with instructions
    print("Please update the deploy_contract.py file with the correct private key for your Ganache account.")
    return None, None

if __name__ == "__main__":
    deploy_contract_with_provided_key()