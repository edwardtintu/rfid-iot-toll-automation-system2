import json
import os
from solcx import compile_standard, install_solc

# Install specific version of Solidity compiler (more compatible version)
install_solc("0.8.17")

def compile_solidity():
    # Read the Solidity contract file
    with open("/Users/hariharansundaramoorthy/HTMS_Project/contracts/TollManagement.sol", "r") as file:
        contract_source_code = file.read()

    # Compile the contract
    compiled_sol = compile_standard({
        "language": "Solidity",
        "sources": {
            "TollManagement.sol": {
                "content": contract_source_code
            }
        },
        "settings": {
            "outputSelection": {
                "*": {
                    "*": [
                        "abi",
                        "evm.bytecode.object",
                        "evm.bytecode.opcodes"
                    ]
                }
            }
        }
    })

    # Extract contract information
    contract_info = compiled_sol["contracts"]["TollManagement.sol"]["TollManagement"]
    
    # Save the ABI and bytecode to files for later use
    contract_abi = contract_info["abi"]
    contract_bytecode = contract_info["evm"]["bytecode"]["object"]
    
    # Create output directory if it doesn't exist
    os.makedirs("/Users/hariharansundaramoorthy/HTMS_Project/backend/blockchain_contracts/output", exist_ok=True)
    
    # Write ABI to file
    with open("/Users/hariharansundaramoorthy/HTMS_Project/backend/blockchain_contracts/output/contract_abi.json", "w") as abi_file:
        json.dump(contract_abi, abi_file)
    
    # Write bytecode to file
    with open("/Users/hariharansundaramoorthy/HTMS_Project/backend/blockchain_contracts/output/contract_bytecode.txt", "w") as bytecode_file:
        bytecode_file.write(contract_bytecode)
    
    print("Contract compiled successfully!")
    print(f"ABI and bytecode saved to /Users/hariharansundaramoorthy/HTMS_Project/backend/blockchain_contracts/output/")
    
    return contract_abi, contract_bytecode

if __name__ == "__main__":
    abi, bytecode = compile_solidity()