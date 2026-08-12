import time

from backend.app.services.model_loader import model_loader
from backend.app.services.prediction import prediction_service

model_loader.load_and_validate_artifacts()

payload = {
    "Amount_Paid": 500.0,
    "Amount_Received": 500.0,
    "From_Account": "Acc_102",
    "To_Account": "Acc_994",
    "From_Bank": "Bank_A",
    "To_Bank": "Bank_B"
}

t0 = time.time()
df_feat = prediction_service.transform_transaction_to_features(payload)
t1 = time.time()
print(f"1. Feature Transform: {(t1 - t0)*1000:.2f} ms")

X_mat = df_feat.to_numpy()

t2 = time.time()
raw_prob = model_loader.model.predict_proba(df_feat)[0, 1]
t3 = time.time()
print(f"2. LightGBM Predict Proba: {(t3 - t2)*1000:.2f} ms")

t4 = time.time()
calib_prob = model_loader.calibrator.predict_proba(df_feat)[0, 1]
t5 = time.time()
print(f"3. Isotonic Calibrator Predict Proba: {(t5 - t4)*1000:.2f} ms")
