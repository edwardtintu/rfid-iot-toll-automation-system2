import json
import time
from web3 import Web3

def deploy_contract():
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
    
    # Get the first available account from Ganache (usually the first one)
    accounts = web3.eth.accounts
    if not accounts:
        print("Error: No accounts found in Ganache.")
        return None, None
    
    deployer_account = accounts[0]
    print(f"Using account {deployer_account} to deploy the contract")
    
    # Build the transaction
    construct_txn = contract.constructor().build_transaction({
        'from': deployer_account,
        'nonce': web3.eth.get_transaction_count(deployer_account),
        'gas': 3000000,  # Increased gas limit
        'gasPrice': web3.to_wei('20', 'gwei')  # Lower gas price
    })
    
    # Sign the transaction
    signed_txn = web3.eth.account.sign_transaction(construct_txn, 
        # Ganache default private key for first account - this is just a placeholder
        # In practice, you'd use the proper private key or a wallet connection
        private_key=input("Enter the private key for the deploying account: ")
    )
    
    print("Deploying contract...")
    
    # Send the transaction
    raw_tx = getattr(signed_txn, "rawTransaction", getattr(signed_txn, "raw", None))
    if raw_tx is None:
        print("Error: Could not get raw transaction from signed transaction")
        return None, None
    tx_hash = web3.eth.send_raw_transaction(raw_tx)
    
    # Wait for the transaction to be mined
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    print(f"Contract deployed successfully!")
    print(f"Contract address: {tx_receipt.contractAddress}")
    
    # Save contract address and ABI for use in the application
    deployment_info = {
        "contract_address": tx_receipt.contractAddress,
        "contract_abi": contract_abi,
        "deployer_account": deployer_account
    }
    
    with open("/Users/hariharansundaramoorthy/HTMS_Project/backend/blockchain_contracts/output/deployment_info.json", "w") as deploy_file:
        json.dump(deployment_info, deploy_file, indent=2)
    
    print("Deployment information saved!")
    
    return tx_receipt.contractAddress, contract_abi

def deploy_contract_with_manual_key():
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
    
    # Instructions for user
    print("\nTo deploy the contract, you need the private key for this account.")
    print("In Ganache UI:")
    print("1. Find the account", deployer_account, "in the accounts list")
    print("2. Click on the key icon next to it to reveal the private key")
    print("3. Copy the private key (it starts with '0x')")
    print("")
    
    # Get the private key from user input
    private_key = input(f"Enter the private key for account {deployer_account}: ").strip()
    
    # Validate the private key format
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    
    if len(private_key) != 66:  # 0x + 64 hex chars
        print(f"Error: Invalid private key format. Expected 64 hex characters (plus 0x prefix), got {len(private_key)-2}")
        return None, None
    
    # Build the transaction
    construct_txn = contract.constructor().build_transaction({
        'from': deployer_account,
        'nonce': web3.eth.get_transaction_count(deployer_account),
        'gas': 3000000,  # Increased gas limit
        'gasPrice': web3.to_wei('20', 'gwei')  # Lower gas price
    })
    
    # Sign the transaction
    signed_txn = web3.eth.account.sign_transaction(construct_txn, private_key=private_key)
    
    print("Deploying contract...")
    
    # Send the transaction
    raw_tx = getattr(signed_txn, "rawTransaction", getattr(signed_txn, "raw", None))
    if raw_tx is None:
        print("Error: Could not get raw transaction from signed transaction")
        return None, None
    tx_hash = web3.eth.send_raw_transaction(raw_tx)
    
    # Wait for the transaction to be mined
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    print(f"Contract deployed successfully!")
    print(f"Contract address: {tx_receipt.contractAddress}")
    
    # Save contract address and ABI for use in the application
    deployment_info = {
        "contract_address": tx_receipt.contractAddress,
        "contract_abi": contract_abi,
        "deployer_account": deployer_account
    }
    
    with open("/Users/hariharansundaramoorthy/HTMS_Project/backend/blockchain_contracts/output/deployment_info.json", "w") as deploy_file:
        json.dump(deployment_info, deploy_file, indent=2)
    
    print("Deployment information saved!")
    
    return tx_receipt.contractAddress, contract_abi

if __name__ == "__main__":
    contract_address, abi = deploy_contract_with_manual_key()