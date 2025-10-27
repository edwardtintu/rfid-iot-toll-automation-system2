from web3 import Web3

# Connect to Ganache or placeholder
ganache_url = "http://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(ganache_url))

def send_to_chain(tx_hash, decision, reason):
    """
    Placeholder for blockchain transaction logging.
    Replace this with actual contract interaction later.
    """
    print(f"[CHAIN LOG] TxHash={tx_hash[:10]}... Decision={decision} | Reason={reason or 'None'}")
