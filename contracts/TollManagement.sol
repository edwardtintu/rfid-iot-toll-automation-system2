// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TollManagement {
    struct TollTransaction {
        string tagUID;
        string vehicleType;
        uint256 amount;
        string decision;
        string reason;
        uint256 timestamp;
        string txHash;
        address registeredBy;
    }

    mapping(uint256 => TollTransaction) public tollTransactions;
    uint256 public transactionCount;
    
    event TollTransactionRecorded(
        uint256 indexed transactionId,
        string tagUID,
        string vehicleType,
        uint256 amount,
        string decision,
        string reason,
        uint256 timestamp,
        string txHash
    );

    constructor() {
        transactionCount = 0;
    }

    function recordTollTransaction(
        string memory _tagUID,
        string memory _vehicleType,
        uint256 _amount,
        string memory _decision,
        string memory _reason,
        string memory _txHash
    ) public returns (uint256) {
        uint256 transactionId = transactionCount;
        
        tollTransactions[transactionId] = TollTransaction({
            tagUID: _tagUID,
            vehicleType: _vehicleType,
            amount: _amount,
            decision: _decision,
            reason: _reason,
            timestamp: block.timestamp,
            txHash: _txHash,
            registeredBy: msg.sender
        });
        
        transactionCount++;
        
        emit TollTransactionRecorded(
            transactionId,
            _tagUID,
            _vehicleType,
            _amount,
            _decision,
            _reason,
            block.timestamp,
            _txHash
        );
        
        return transactionId;
    }

    function getTollTransaction(uint256 _transactionId) public view returns (
        string memory tagUID,
        string memory vehicleType,
        uint256 amount,
        string memory decision,
        string memory reason,
        uint256 timestamp,
        string memory txHash,
        address registeredBy
    ) {
        TollTransaction memory transaction = tollTransactions[_transactionId];
        return (
            transaction.tagUID,
            transaction.vehicleType,
            transaction.amount,
            transaction.decision,
            transaction.reason,
            transaction.timestamp,
            transaction.txHash,
            transaction.registeredBy
        );
    }

    function getAllTransactionCount() public view returns (uint256) {
        return transactionCount;
    }
}