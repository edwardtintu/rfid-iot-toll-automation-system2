import pandas as pd
import numpy as np
import random

# Generate synthetic toll transaction data with fraud labels
# Features will match those used by Model B: amount, speed, inter_arrival, sin_hour, cos_hour
np.random.seed(42)
random.seed(42)

# Generate a dataset similar to the credit card dataset but for toll transactions
n_samples = 100000

# Generate realistic toll transaction features
data = {
    'amount': [],
    'speed': [],
    'inter_arrival': [],
    'sin_hour': [],
    'cos_hour': [],
    'Class': []  # Fraud label (0 = legitimate, 1 = fraudulent)
}

for i in range(n_samples):
    # Generate legitimate transactions with higher probability
    is_fraud = np.random.choice([0, 1], p=[0.98, 0.02])  # 2% fraud rate (realistic for toll systems)
    
    # Generate time-based features
    hour = np.random.randint(0, 24)
    sin_hour = np.sin(2 * np.pi * hour / 24)
    cos_hour = np.cos(2 * np.pi * hour / 24)
    
    if is_fraud:
        # Fraudulent transactions - create anomalous patterns
        amount = np.random.uniform(0.5, 800)  # Could be very low (toll evasions) or high
        speed = np.random.uniform(0, 200)  # Could be very high or low speeds
        inter_arrival = np.random.exponential(0.1)  # Time between transactions - could be very low
    else:
        # Legitimate transactions - more realistic patterns
        amount = np.random.uniform(1, 15)  # Normal toll amounts
        speed = np.random.normal(65, 20)  # Typical highway speeds
        speed = max(0, min(120, speed))  # Clamp to reasonable range
        inter_arrival = np.random.exponential(5)  # Time between transactions - typically higher
    
    data['amount'].append(amount)
    data['speed'].append(speed)
    data['inter_arrival'].append(inter_arrival)
    data['sin_hour'].append(sin_hour)
    data['cos_hour'].append(cos_hour)
    data['Class'].append(is_fraud)

# Create DataFrame
df = pd.DataFrame(data)

# Add more sophisticated fraud patterns
# Multiple transactions in very short time (likely fraudulent)
n_mtf = 500  # Number of multi-transaction frauds
for i in range(n_mtf):
    idx = random.randint(0, n_samples - 1)
    df.iloc[idx, df.columns.get_loc('inter_arrival')] = np.random.uniform(0.01, 0.1)  # Very low
    df.iloc[idx, df.columns.get_loc('Class')] = 1

# Very high amounts (likely fraudulent)
n_hf = 300
for i in range(n_hf):
    idx = random.randint(0, n_samples - 1)
    df.iloc[idx, df.columns.get_loc('amount')] = np.random.uniform(100, 500)
    df.iloc[idx, df.columns.get_loc('Class')] = 1

# Very low amounts (possible toll evasion)
n_lf = 200
for i in range(n_lf):
    idx = random.randint(0, n_samples - 1)
    df.iloc[idx, df.columns.get_loc('amount')] = np.random.uniform(0.1, 0.5)
    df.iloc[idx, df.columns.get_loc('Class')] = 1

# Very high speeds (possible fraud through overspeeding)
n_sf = 200
for i in range(n_sf):
    idx = random.randint(0, n_samples - 1)
    df.iloc[idx, df.columns.get_loc('speed')] = np.random.uniform(120, 200)
    df.iloc[idx, df.columns.get_loc('Class')] = 1

print(f"Dataset shape: {df.shape}")
print(f"Fraud distribution:\n{df['Class'].value_counts()}")
print(f"Fraud percentage: {df['Class'].mean()*100:.2f}%")
print(f"Feature columns: {df.columns.tolist()}")

# Save the synthetic toll fraud dataset
df.to_csv('data/toll_fraud_dataset.csv', index=False)
print("\n✅ Synthetic toll fraud dataset saved to data/toll_fraud_dataset.csv")
print("Dataset contains 5 features matching Model B + 1 fraud label column")