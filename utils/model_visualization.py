import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc, precision_recall_curve
from sklearn.ensemble import IsolationForest
import warnings
warnings.filterwarnings('ignore')

# Set style for better-looking plots
plt.style.use('default')
sns.set_palette("husl")

def load_models_and_data():
    """
    Load the trained models and test data
    """
    try:
        modelA = joblib.load('../models/modelA_toll_rf.joblib')
        modelB = joblib.load('../models/modelB_toll_rf.joblib')
        isoB = joblib.load('../models/modelB_toll_iso.joblib')
        toll_scaler = joblib.load('../models/toll_scaler.joblib')
        toll_scaler_v2 = joblib.load('../models/toll_scaler_v2.joblib')
        
        print("✅ Models loaded successfully")
        return modelA, modelB, isoB, toll_scaler, toll_scaler_v2
    except FileNotFoundError:
        print("❌ Model files not found. Please ensure models are trained first.")
        return None, None, None, None, None

def create_sample_data():
    """
    Create sample toll transaction data for testing and visualization
    """
    np.random.seed(42)
    n_samples = 1000
    
    # Create realistic toll features
    amounts = np.random.uniform(50, 500, n_samples)  # Toll amounts between 50-500
    speeds = np.random.uniform(30, 120, n_samples)    # Vehicle speeds 30-120 km/h
    inter_arrivals = np.random.exponential(10, n_samples)  # Inter-arrival times
    hours = np.random.randint(0, 24, n_samples)      # Time of day
    
    # Create features matrix
    X = pd.DataFrame({
        'amount': amounts,
        'speed': speeds,
        'inter_arrival': inter_arrivals,
        'sin_hour': np.sin(2 * np.pi * hours / 24),
        'cos_hour': np.cos(2 * np.pi * hours / 24)
    })
    
    # Create synthetic labels (0 for normal, 1 for fraud) - more fraud during unusual hours
    fraud_mask = (
        (X['amount'] > 400) | 
        (X['speed'] > 100) | 
        (X['inter_arrival'] < 0.1) |
        (X['amount'] < 50) & (X['speed'] > 80)  # Very low toll with high speed = suspicious
    )
    y = fraud_mask.astype(int)
    
    print(f"✅ Created sample dataset with {n_samples} samples")
    print(f"   Fraudulent transactions: {y.sum()} ({y.mean()*100:.1f}%)")
    
    return X, y

def visualize_model_performance(modelA, modelB, isoB, toll_scaler, toll_scaler_v2, X, y):
    """
    Create comprehensive visualizations for model performance
    """
    # Prepare test data
    X_scaled_B = toll_scaler.transform(X)
    X_scaled_A = toll_scaler_v2.transform(X)
    
    # Get predictions
    if modelA:
        y_pred_A = modelA.predict(X_scaled_A)
        y_proba_A = modelA.predict_proba(X_scaled_A)[:, 1]
    else:
        y_pred_A, y_proba_A = np.zeros(len(X)), np.zeros(len(X))
    
    if modelB:
        y_pred_B = modelB.predict(X_scaled_B)
        y_proba_B = modelB.predict_proba(X_scaled_B)[:, 1]
    else:
        y_pred_B, y_proba_B = np.zeros(len(X)), np.zeros(len(X))
    
    if isoB:
        y_iso_pred = isoB.predict(X_scaled_B)
        y_iso_scores = isoB.decision_function(X_scaled_B)
    else:
        y_iso_pred = np.zeros(len(X))
        y_iso_scores = np.zeros(len(X))
    
    # Create comprehensive visualization
    fig = plt.figure(figsize=(20, 15))
    
    # Subplot 1: Feature distributions
    plt.subplot(3, 4, 1)
    plt.hist(X['amount'], bins=50, alpha=0.7, label='Amount', color='skyblue')
    plt.title('Distribution of Toll Amounts')
    plt.xlabel('Amount')
    plt.ylabel('Frequency')
    
    plt.subplot(3, 4, 2)
    plt.hist(X['speed'], bins=50, alpha=0.7, label='Speed', color='lightgreen')
    plt.title('Distribution of Vehicle Speeds')
    plt.xlabel('Speed (km/h)')
    plt.ylabel('Frequency')
    
    plt.subplot(3, 4, 3)
    plt.scatter(X['amount'], X['speed'], c=y, cmap='viridis', alpha=0.6)
    plt.title('Amount vs Speed (Colored by Fraud Label)')
    plt.xlabel('Amount')
    plt.ylabel('Speed')
    
    # Subplot 2: Model A Performance
    if modelA:
        plt.subplot(3, 4, 4)
        plt.hist(y_proba_A[y == 0], bins=30, alpha=0.5, label='Legitimate', color='green', density=True)
        plt.hist(y_proba_A[y == 1], bins=30, alpha=0.5, label='Fraud', color='red', density=True)
        plt.title('Model A: Fraud Probability Distribution')
        plt.xlabel('Fraud Probability')
        plt.ylabel('Density')
        plt.legend()
    
    # Subplot 3: Model B Performance
    if modelB:
        plt.subplot(3, 4, 5)
        plt.hist(y_proba_B[y == 0], bins=30, alpha=0.5, label='Legitimate', color='green', density=True)
        plt.hist(y_proba_B[y == 1], bins=30, alpha=0.5, label='Fraud', color='red', density=True)
        plt.title('Model B: Fraud Probability Distribution')
        plt.xlabel('Fraud Probability')
        plt.ylabel('Density')
        plt.legend()
    
    # Subplot 4: ROC Curves
    plt.subplot(3, 4, 6)
    if modelA:
        fpr_A, tpr_A, _ = roc_curve(y, y_proba_A)
        roc_auc_A = auc(fpr_A, tpr_A)
        plt.plot(fpr_A, tpr_A, label=f'Model A (AUC = {roc_auc_A:.3f})', linewidth=2)
    
    if modelB:
        fpr_B, tpr_B, _ = roc_curve(y, y_proba_B)
        roc_auc_B = auc(fpr_B, tpr_B)
        plt.plot(fpr_B, tpr_B, label=f'Model B (AUC = {roc_auc_B:.3f})', linewidth=2)
    
    plt.plot([0, 1], [0, 1], 'k--', label='Random', alpha=0.5)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curves')
    plt.legend()
    
    # Subplot 5: Precision-Recall Curves
    plt.subplot(3, 4, 7)
    if modelA:
        precision_A, recall_A, _ = precision_recall_curve(y, y_proba_A)
        pr_auc_A = auc(recall_A, precision_A)
        plt.plot(recall_A, precision_A, label=f'Model A (AUC = {pr_auc_A:.3f})', linewidth=2)
    
    if modelB:
        precision_B, recall_B, _ = precision_recall_curve(y, y_proba_B)
        pr_auc_B = auc(recall_B, precision_B)
        plt.plot(recall_B, precision_B, label=f'Model B (AUC = {pr_auc_B:.3f})', linewidth=2)
    
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curves')
    plt.legend()
    
    # Subplot 6: Feature Importance (for Model B)
    if modelB:
        plt.subplot(3, 4, 8)
        feature_names = ['Amount', 'Speed', 'Inter-Arrival', 'Sin(Hour)', 'Cos(Hour)']
        importances = modelB.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        plt.bar(range(len(importances)), importances[indices])
        plt.title('Model B Feature Importance')
        plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=45)
        plt.ylabel('Importance')
    
    # Subplot 7: Confusion Matrix for Model A
    if modelA:
        plt.subplot(3, 4, 9)
        cm_A = confusion_matrix(y, y_pred_A)
        sns.heatmap(cm_A, annot=True, fmt='d', cmap='Blues')
        plt.title('Model A Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
    
    # Subplot 8: Confusion Matrix for Model B
    if modelB:
        plt.subplot(3, 4, 10)
        cm_B = confusion_matrix(y, y_pred_B)
        sns.heatmap(cm_B, annot=True, fmt='d', cmap='Blues')
        plt.title('Model B Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
    
    # Subplot 9: Isolation Forest Scores
    plt.subplot(3, 4, 11)
    plt.scatter(y_iso_scores[y == 0], np.zeros_like(y_iso_scores[y == 0]), 
               alpha=0.5, label='Legitimate', color='green')
    plt.scatter(y_iso_scores[y == 1], np.ones_like(y_iso_scores[y == 1]), 
               alpha=0.5, label='Fraud', color='red')
    plt.title('Isolation Forest Scores')
    plt.xlabel('Anomaly Score')
    plt.ylabel('Fraud Class')
    plt.legend()
    
    # Subplot 10: Combined Detection Performance
    plt.subplot(3, 4, 12)
    if modelA and modelB:
        # Create hybrid detection
        combined_pred = ((y_proba_A > 0.5) | (y_proba_B > 0.5) | (y_iso_pred == -1)).astype(int)
        cm_combined = confusion_matrix(y, combined_pred)
        sns.heatmap(cm_combined, annot=True, fmt='d', cmap='Blues')
        plt.title('Combined Detection Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
    
    plt.tight_layout()
    plt.savefig('model_visualization.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return y_proba_A, y_proba_B, y_iso_scores

def print_model_metrics(y_true, y_pred_A, y_pred_B, y_proba_A, y_proba_B):
    """
    Print comprehensive model metrics
    """
    print("\n" + "="*60)
    print("MODEL PERFORMANCE METRICS")
    print("="*60)
    
    if len(y_pred_A) > 0:
        print("\n📊 Model A (Credit-based Fraud Detection) Performance:")
        print(classification_report(y_true, y_pred_A, target_names=['Legitimate', 'Fraud']))
    
    if len(y_pred_B) > 0:
        print("\n📊 Model B (Toll-specific Fraud Detection) Performance:")
        print(classification_report(y_true, y_pred_B, target_names=['Legitimate', 'Fraud']))
    
    if len(y_proba_A) > 0:
        from sklearn.metrics import roc_auc_score
        auc_A = roc_auc_score(y_true, y_proba_A)
        print(f"\n📈 Model A AUC-ROC Score: {auc_A:.4f}")
    
    if len(y_proba_B) > 0:
        auc_B = roc_auc_score(y_true, y_proba_B)
        print(f"📈 Model B AUC-ROC Score: {auc_B:.4f}")

def main():
    """
    Main function to run the visualization
    """
    print("🔍 Starting Model Performance Visualization for HTMS Project")
    
    # Load models
    modelA, modelB, isoB, toll_scaler, toll_scaler_v2 = load_models_and_data()
    
    if modelA is None:
        print("❌ Could not load models. Please run train_model_a.py and train_model_b.py first.")
        return
    
    # Create sample data
    X, y = create_sample_data()
    
    # Visualize model performance
    y_proba_A, y_proba_B, y_iso_scores = visualize_model_performance(
        modelA, modelB, isoB, toll_scaler, toll_scaler_v2, X, y
    )
    
    # Make predictions for metrics
    X_scaled_A = toll_scaler_v2.transform(X) if toll_scaler_v2 is not None else X
    X_scaled_B = toll_scaler.transform(X) if toll_scaler is not None else X
    
    y_pred_A = modelA.predict(X_scaled_A) if modelA else np.zeros(len(X))
    y_pred_B = modelB.predict(X_scaled_B) if modelB else np.zeros(len(X))
    
    # Print metrics
    print_model_metrics(y, y_pred_A, y_pred_B, 
                       modelA.predict_proba(X_scaled_A)[:, 1] if modelA else np.zeros(len(X)),
                       modelB.predict_proba(X_scaled_B)[:, 1] if modelB else np.zeros(len(X)))
    
    print("\n✅ Visualization complete! Check 'model_visualization.png' for detailed plots.")
    print("The visualization shows:")
    print("  • Feature distributions in the dataset")
    print("  • Fraud probability distributions for each model")
    print("  • ROC and Precision-Recall curves")
    print("  • Feature importance for Model B")
    print("  • Confusion matrices for individual and combined models")

if __name__ == "__main__":
    main()