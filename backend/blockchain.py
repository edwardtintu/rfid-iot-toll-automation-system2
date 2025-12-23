import json
from web3 import Web3

# Connect to Ganache
ganache_url = "http://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(ganache_url))

# Load contract information
def load_contract_info():
    try:
        with open("backend/blockchain_contracts/output/deployment_info.json", "r") as deploy_file:
            deployment_info = json.load(deploy_file)
        return deployment_info
    except FileNotFoundError:
        # If deployment info doesn't exist, return None
        # This allows the system to work in offline mode
        print("[BLOCKCHAIN] Warning: Deployment info not found. Contract interaction disabled.")
        return None

def send_to_chain(tx_hash, decision, reason, tagUID="N/A", vehicle_type="CAR", amount=0.0):
    """
    Send toll transaction data to the blockchain.
    
    Args:
        tx_hash: Transaction hash
        decision: Decision (allow/block)
        reason: Reason for decision
        tagUID: RFID tag UID
        vehicle_type: Vehicle type
        amount: Toll amount
    """
    deployment_info = load_contract_info()
    
    if not deployment_info or not web3.is_connected():
        # Fallback to local logging if blockchain is not available
        print(f"[CHAIN LOG] TxHash={tx_hash[:10]}... Decision={decision} | Reason={reason or 'None'}")
        return {"success": False, "error": "Blockchain not available", "fallback_used": True}
    
    try:
        # Get the contract instance
        contract_address = deployment_info["contract_address"]
        contract_abi = deployment_info["contract_abi"]
        
        toll_contract = web3.eth.contract(address=contract_address, abi=contract_abi)
        
        # Get the account to send the transaction (first account in Ganache)
        accounts = web3.eth.accounts
        if not accounts:
            return {"success": False, "error": "No accounts available", "fallback_used": True}
        
        sender_account = accounts[0]
        
        # Prepare the transaction to call the smart contract
        transaction = toll_contract.functions.recordTollTransaction(
            tagUID,
            vehicle_type,
            int(amount * 100),  # Convert to cents to avoid floating point issues
            decision,
            reason or "None",
            tx_hash
        ).build_transaction({
            'from': sender_account,
            'nonce': web3.eth.get_transaction_count(sender_account),
            'gas': 3000000,  # Increased gas limit
            'gasPrice': web3.to_wei('20', 'gwei')  # Lower gas price
        })
        
        # Use your specific account and private key
        # This is the account you provided
        your_account = "0xfe427f1B10FD82bc654316058e0c2eed511f0Bb9"
        your_private_key = "0x7715ec38c0aa2248b358292ed969c8146bfc6d5886acfc819fb4203ed8a512a4"

        # Check if the current account matches your account
        if sender_account.lower() != your_account.lower():
            print(f"[BLOCKCHAIN] Warning: Current account {sender_account} doesn't match expected account {your_account}")
            # Try to use your account directly if it's available in the Ganache instance
            if your_account.lower() in [acc.lower() for acc in accounts]:
                sender_account = your_account
            else:
                print(f"[BLOCKCHAIN] Error: Your account {your_account} is not available in this Ganache instance")
                print(f"[CHAIN LOG] TxHash={tx_hash[:10]}... Decision={decision} | Reason={reason or 'None'} [FALLBACK]")
                return {"success": False, "error": "Account mismatch", "fallback_used": True}

        selected_private_key = your_private_key
        
        if not selected_private_key:
            print(f"[BLOCKCHAIN] Error: Could not find private key for account {sender_account}")
            print(f"[CHAIN LOG] TxHash={tx_hash[:10]}... Decision={decision} | Reason={reason or 'None'} [FALLBACK]")
            return {"success": False, "error": "Could not find private key for account", "fallback_used": True}
        
        # Sign and send the transaction
        signed_txn = web3.eth.account.sign_transaction(transaction, private_key=selected_private_key)
        
        # Handle different attribute names for the raw transaction
        raw_tx = getattr(signed_txn, "raw_transaction", getattr(signed_txn, "rawTransaction", getattr(signed_txn, "raw", None)))
        if raw_tx is None:
            print(f"[BLOCKCHAIN] Error: Could not get raw transaction from signed transaction")
            print(f"[CHAIN LOG] TxHash={tx_hash[:10]}... Decision={decision} | Reason={reason or 'None'} [FALLBACK]")
            return {"success": False, "error": "Could not get raw transaction", "fallback_used": True}
            
        tx_hash_on_chain = web3.eth.send_raw_transaction(raw_tx)
        
        # Wait for the transaction to be mined
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash_on_chain)
        
        print(f"[BLOCKCHAIN] Tx recorded on chain: {receipt.transactionHash.hex()}")
        print(f"[BLOCKCHAIN] Gas used: {receipt.gasUsed}")
        
        return {
            "success": True, 
            "transaction_hash": receipt.transactionHash.hex(),
            "contract_address": contract_address,
            "fallback_used": False
        }
        
    except Exception as e:
        # If blockchain recording fails, log it but continue operation
        print(f"[BLOCKCHAIN ERROR] {str(e)}")
        print(f"[CHAIN LOG] TxHash={tx_hash[:10]}... Decision={decision} | Reason={reason or 'None'} [FALLBACK]")
        return {"success": False, "error": str(e), "fallback_used": True}

def get_transaction_from_chain(transaction_id):
    """
    Get toll transaction data from the blockchain.
    
    Args:
        transaction_id: The ID of the transaction to retrieve
    
    Returns:
        Transaction data from the blockchain
    """
    deployment_info = load_contract_info()
    
    if not deployment_info or not web3.is_connected():
        return {"error": "Blockchain not available"}
    
    try:
        contract_address = deployment_info["contract_address"]
        contract_abi = deployment_info["contract_abi"]
        
        toll_contract = web3.eth.contract(address=contract_address, abi=contract_abi)
        
        # Get the transaction data from the blockchain
        transaction_data = toll_contract.functions.getTollTransaction(transaction_id).call()
        
        return {
            "tagUID": transaction_data[0],
            "vehicleType": transaction_data[1],
            "amount": transaction_data[2],
            "decision": transaction_data[3],
            "reason": transaction_data[4],
            "timestamp": transaction_data[5],
            "txHash": transaction_data[6],
            "registeredBy": transaction_data[7]
        }
    except Exception as e:
        return {"error": str(e)}