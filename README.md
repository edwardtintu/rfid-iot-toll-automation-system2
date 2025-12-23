# Hybrid Toll Management System (HTMS)

A comprehensive toll management system with fraud detection and blockchain integration.

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [Frontend Usage](#frontend-usage)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

## 🌟 Overview
The Hybrid Toll Management System (HTMS) is a secure toll collection system that combines traditional toll processing with machine learning-based fraud detection and blockchain technology for immutable transaction records.

## 🚀 Features
- **RFID-based toll processing**
- **Real-time fraud detection** using ML models
- **Blockchain integration** for secure transaction logging
- **Web dashboard** for monitoring and management
- **Card lookup functionality**
- **Transaction history tracking**

## 💻 Prerequisites
Before running the project, ensure you have the following installed:

### Required Software
- **Python 3.8+** (with pip)
- **Node.js** (for frontend development, optional)
- **Ganache** (for blockchain network)
- **Git**

### Python Packages
The project requires the following Python packages:
- fastapi
- uvicorn
- pandas
- numpy
- scikit-learn
- joblib
- web3
- sqlalchemy

## 📦 Installation

### 1. Clone the Repository
```bash
git clone [repository-url]
cd HTMS_Project
```

### 2. Set up Python Environment
```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# Install required packages
pip install -r backend/requirements.txt
```

### 3. Install Additional Requirements
```bash
# Install Solidity compiler (for blockchain)
pip install py-solc-x

# Install additional packages if needed
pip install solcx
```

## 🏃‍♂️ Running the Project

### 1. Start Ganache (Blockchain Network)
- Download and install Ganache from https://www.trufflesuite.com/ganache
- Launch Ganache and create a new workspace
- Make sure it's running on default port `7545`

### 2. Deploy Smart Contract (One-time setup)
```bash
cd /path/to/HTMS_Project

# Compile the smart contract
python backend/blockchain_contracts/compile_sol.py

# Deploy the smart contract to Ganache
python backend/blockchain_contracts/deploy_contract_cli.py 0xbc24a6d338d60d7ebdb87a16f65e40f22bfb32f4ba7e68b16496d725000db13e
```
**Note:** Use the private key shown in your Ganache account details for the deployment account.

### 3. Initialize Database
```bash
cd /path/to/HTMS_Project
python backend/seed_db.py
```

### 4. Start the Backend Server
```bash
cd /path/to/HTMS_Project
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the Frontend
- Open the simple frontend: Open `/path/to/HTMS_Project/simple-frontend/index.html` in your browser
- Or run a local HTTP server:
  ```bash
  # Using Python (if you have Python installed)
  cd /path/to/HTMS_Project/simple-frontend
  python -m http.server 8080
  # Then open http://localhost:8080 in your browser
  ```

## 🖥️ Frontend Usage

### Dashboard Features
1. **Dashboard Tab**: Overview of system stats and recent transactions
2. **Process Toll Tab**: Process new toll transactions
3. **Card Lookup Tab**: Search for card details by RFID UID
4. **History Tab**: View transaction history with filters
5. **Blockchain Tab**: View blockchain transaction records

### Sample UIDs for Testing
- `5B88F75` - CAR type
- `9C981B6` - TRUCK type  
- `BE9E1E33` - BUS type

## 🌐 API Endpoints

### Backend API
- `GET /` - Health check: Returns `{"message": "HTMS API running"}`
- `GET /api/card/{uid}` - Get card details
- `POST /api/toll` - Process toll transaction

### Example API Request
```bash
curl -X POST http://localhost:8000/api/toll \
  -H "Content-Type: application/json" \
  -d '{"tagUID": "9C981B6", "speed": 60}'
```

## 🔧 Troubleshooting

### Common Issues

#### Issue: "ModuleNotFoundError: No module named 'backend'"
**Solution:** Run the backend from the project root directory:
```bash
cd /path/to/HTMS_Project
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

#### Issue: "Connection refused" when accessing API
**Solution:** 
1. Ensure the backend server is running
2. Check that the port is correct (default: 8000)
3. Verify firewall settings aren't blocking the connection

#### Issue: "Ganache not connecting" 
**Solution:**
1. Ensure Ganache is running before starting the backend
2. Check that Ganache is running on port 7545
3. Verify that the contract is properly deployed

#### Issue: "Database not initialized"
**Solution:** Run the seed script to initialize the database:
```bash
cd /path/to/HTMS_Project
python backend/seed_db.py
```

#### Issue: "Blockchain deployment fails"
**Solution:**
1. Make sure Ganache is running
2. Use the correct private key from your Ganache account
3. Ensure py-solc-x is installed

### Backend Server Not Starting
- Check that port 8000 is not in use by another application
- Ensure all required Python packages are installed
- Verify that the database files are writable

### Frontend Not Loading Styles
- Make sure to open the HTML file directly in browser, or serve it through a local server
- Check browser console for any error messages

## 🛠️ Project Structure
```
HTMS_Project/
├── backend/                  # Backend server files
│   ├── app.py               # Main FastAPI application
│   ├── blockchain.py        # Blockchain integration
│   ├── database.py          # Database models
│   ├── detection.py         # Fraud detection logic
│   ├── requirements.txt     # Python dependencies
│   └── seed_db.py          # Database initialization
├── simple-frontend/         # Simple HTML/CSS/JS frontend
│   └── index.html          # Main frontend file
├── models/                  # ML models
│   ├── modelA_credit_rf.joblib
│   ├── modelB_toll_rf.joblib
│   ├── modelB_toll_iso.joblib
│   ├── credit_scaler.joblib
│   └── toll_scaler.joblib
└── README.md               # This file
```

## 📈 System Components
- **Backend**: FastAPI server handling requests and business logic
- **Database**: SQLite for persistent storage
- **Blockchain**: Ethereum-based (Ganache) for immutable records
- **ML Models**: Pre-trained models for fraud detection
- **Frontend**: Simple HTML/CSS/JS interface

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.