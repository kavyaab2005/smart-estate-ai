import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "data", "bangalore_properties.csv")

df = pd.read_csv(DATA)
df = df[df["listing_type"] == "sale"].copy()

cat_cols = ["property_type", "furnishing", "city"]
num_cols = ["area_sqft", "bhk", "bedrooms", "floor", "total_floors",
            "property_age_years", "parking"]

encoders = {}
for col in cat_cols:
    le = LabelEncoder()
    df[col + "_enc"] = le.fit_transform(df[col])
    encoders[col] = le

df["amenity_count"] = df["amenities"].apply(
    lambda x: len(str(x).split("|")) if pd.notnull(x) else 0
)

feat_cols = [c + "_enc" for c in cat_cols] + num_cols + ["amenity_count"]
X = df[feat_cols]
y = df["price"]

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr)
X_te_s  = scaler.transform(X_te)

models = {
    "LinearRegression":  LinearRegression(),
    "RandomForest":      RandomForestRegressor(n_estimators=100, random_state=42),
    "GradientBoosting":  GradientBoostingRegressor(n_estimators=100, random_state=42),
    "XGBoost":           XGBRegressor(n_estimators=100, random_state=42, verbosity=0),
}

print(f"\n{'Model':<25} {'MAE':>15} {'RMSE':>15} {'R2':>8}")
print("-" * 68)

best_model, best_r2, best_name = None, -999, ""
for name, m in models.items():
    m.fit(X_tr_s, y_tr)
    p    = m.predict(X_te_s)
    mae  = mean_absolute_error(y_te, p)
    rmse = np.sqrt(mean_squared_error(y_te, p))
    r2   = r2_score(y_te, p)
    print(f"{name:<25} Rs.{mae:>12,.0f} Rs.{rmse:>12,.0f} {r2:>8.4f}")
    if r2 > best_r2:
        best_r2, best_model, best_name = r2, m, name

print(f"\nBest model: {best_name}  (R2 = {best_r2:.4f})")

model_dir = os.path.join(BASE, "models")
os.makedirs(model_dir, exist_ok=True)
out = os.path.join(model_dir, "price_model.pkl")
joblib.dump({
    "model": best_model, "scaler": scaler,
    "encoders": encoders, "feature_cols": feat_cols,
    "model_name": best_name
}, out)
print(f"Model saved to {out}")