# Hybrid Toll Management System - Blockchain Integration

## Overview
This document describes the blockchain integration for the Hybrid Toll Management System (HTMS). The system uses Ethereum blockchain via Ganache for secure, immutable logging of toll transactions.

## Architecture

### Smart Contract: TollManagement.sol
The system uses a Solidity smart contract deployed on the Ethereum blockchain (Ganache) to store toll transaction records.

#### Contract Functions:
- `recordTollTransaction()`: Records a new toll transaction on the blockchain
- `getTollTransaction()`: Retrieves a specific toll transaction
- `getAllTransactionCount()`: Returns the total number of transactions

#### Data Stored on Blockchain:
- `tagUID`: RFID tag identifier
- `vehicleType`: Type of vehicle (CAR, BUS, TRUCK)
- `amount`: Toll amount (in cents to avoid floating point issues)
- `decision`: Transaction decision (ALLOW/BLOCK)
- `reason`: Reason for the decision
- `timestamp`: When the transaction occurred
- `txHash`: Unique transaction hash
- `registeredBy`: Address that recorded the transaction

## Implementation Details

### Backend Integration
The blockchain integration is handled in `backend/blockchain.py` with the following functions:

1. `send_to_chain()` - Sends toll transaction data to the blockchain
2. `get_transaction_from_chain()` - Retrieves transaction data from blockchain

### Fallback Mechanism
If the blockchain is unavailable, the system will:
- Log the transaction locally
- Continue processing normally
- Return a fallback indicator

### Deployment Process

1. Compile the smart contract:
   ```bash
   python backend/blockchain_contracts/compile_sol.py
   ```

2. Deploy the smart contract to Ganache:
   ```bash
   python backend/blockchain_contracts/deploy_contract.py
   ```

3. The deployment information will be saved to `backend/blockchain_contracts/output/deployment_info.json`

## Setup for Frontend Development

### Prerequisites
- Ganache (for blockchain network)
- Metamask (or other Web3 wallet for frontend integration)

### Ganache Setup
1. Download and install Ganache from https://www.trufflesuite.com/ganache
2. Start Ganache, which will provide:
   - RPC Server: http://127.0.0.1:7545
   - Test accounts with ETH for transactions

### Successful Deployment Information
- **Contract Address**: `0x982E07677e8d0F1c9e54fcbfdF22a052feF79e48`
- **Deployed Functions**: 
  - `recordTollTransaction()` - Records toll transactions on blockchain
  - `getTollTransaction()` - Retrieves specific transaction
  - `getAllTransactionCount()` - Gets total transaction count
- **Deployed Events**: 
  - `TollTransactionRecorded` - Emitted when transactions are recorded

### API Endpoints for Frontend
- `GET /` - Health check
- `GET /api/card/{uid}` - Get card details
- `POST /api/toll` - Process toll transaction

### Testing the Integration
Run the test script to verify blockchain functionality:
```bash
python test_blockchain_integration.py
```

## Security Considerations
- Using Ganache default private key is only for development/testing
- In production, proper wallet integration should be used
- Transactions are stored immutably on the blockchain
- All toll transactions are verifiable

## Future Enhancements
- Add user wallet integration for frontend
- Implement transaction verification UI
- Add blockchain explorer links
- Gas optimization for transaction costs