import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import warnings
warnings.filterwarnings("ignore")

def train_model_a():
    """
    Train a new ModelA using the toll fraud dataset for fraud detection.
    This model will work on toll-specific features (amount, speed, inter_arrival, sin_hour, cos_hour)
    """
    print("Loading Toll Fraud Dataset...")
    df = pd.read_csv('data/toll_fraud_dataset.csv')
    
    print(f"Dataset shape: {df.shape}")
    print(f"Fraud distribution:\n{df['Class'].value_counts()}")
    
    # Features are the toll-specific features
    feature_columns = [col for col in df.columns if col not in ['Class']]
    X = df[feature_columns]
    y = df['Class']
    
    print(f"Feature columns: {X.columns.tolist()}")
    print(f"Number of features: {X.shape[1]}")
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Scale the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train the model
    print("Training Random Forest Classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate the model
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    print("\nModel Evaluation:")
    print(classification_report(y_test, y_pred))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Calculate additional metrics
    from sklearn.metrics import roc_auc_score, precision_recall_curve, auc
    auc_score = roc_auc_score(y_test, y_pred_proba)
    print(f"\nAUC Score: {auc_score:.4f}")
    
    # Save the model and scaler
    print("\nSaving model and scaler...")
    joblib.dump(model, 'models/modelA_toll_rf.joblib')  # Updated filename
    joblib.dump(scaler, 'models/toll_scaler_v2.joblib')  # Updated filename
    
    print("✅ ModelA training completed successfully!")
    print(f"✅ Model saved to models/modelA_toll_rf.joblib")
    print(f"✅ Scaler saved to models/toll_scaler_v2.joblib")
    
    return model, scaler

def test_model_a():
    """
    Test the new ModelA with sample data
    """
    print("\n" + "="*50)
    print("TESTING MODEL A")
    print("="*50)
    
    try:
        # Load the new model and scaler (updated names)
        model = joblib.load("models/modelA_toll_rf.joblib")
        scaler = joblib.load("models/toll_scaler_v2.joblib")
        print("✅ Model and scaler loaded successfully")
        
        # Load a sample from the toll fraud dataset to test
        df = pd.read_csv('data/toll_fraud_dataset.csv')
        sample_features = [col for col in df.columns if col not in ['Class']]
        
        # Get a few test samples
        test_sample = df[sample_features].iloc[0:5]  # First 5 rows
        print(f"Testing with sample data shape: {test_sample.shape}")
        
        # Scale the test data
        test_scaled = scaler.transform(test_sample)
        
        # Make predictions
        probas = model.predict_proba(test_scaled)
        predictions = model.predict(test_scaled)
        
        print("\nSample Predictions:")
        for i in range(len(test_sample)):
            fraud_proba = probas[i][1]
            pred = predictions[i]
            actual_class = df.iloc[i]['Class']
            print(f"Sample {i+1}: Fraud Probability = {fraud_proba:.4f}, Prediction = {pred}, Actual = {actual_class}")
        
        print("\n✅ ModelA testing completed successfully")
        
        # Also test with zeros (what the current detection.py uses)
        print("\nTesting with zeros (current usage in detection.py):")
        dummy_input = np.zeros((1, len(sample_features)))  # 1 sample, all features (5)
        dummy_scaled = scaler.transform(dummy_input)
        dummy_proba = model.predict_proba(dummy_scaled)[0][1]
        dummy_pred = model.predict(dummy_scaled)[0]
        print(f"Zeros input - Fraud Probability = {dummy_proba:.4f}, Prediction = {dummy_pred}")
        
        # Test with more realistic toll data
        print("\nTesting with realistic toll data:")
        realistic_sample = np.array([[5.0, 65.0, 3.0, 0.0, 1.0]])  # [amount, speed, inter_arrival, sin_hour, cos_hour]
        realistic_scaled = scaler.transform(realistic_sample)
        realistic_proba = model.predict_proba(realistic_scaled)[0][1]
        realistic_pred = model.predict(realistic_scaled)[0]
        print(f"Realistic toll data - Fraud Probability = {realistic_proba:.4f}, Prediction = {realistic_pred}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing ModelA: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting ModelA retraining process with toll fraud dataset...")
    model, scaler = train_model_a()
    test_model_a()
    print("\n🎉 ModelA retraining and testing completed!")