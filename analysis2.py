import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. LOAD BIOMETRIC DATA
# ==========================================
def load_biometric_recursive(folder_keyword):
    search_pattern = f"*{folder_keyword}*/**/*.csv"
    files = sorted(glob.glob(search_pattern, recursive=True))
    
    # Fallback for current directory
    if not files:
        files = sorted(glob.glob(f"{folder_keyword}*/**/*.csv", recursive=True))

    if not files:
        print("⚠️ No biometric files found!")
        return pd.DataFrame()

    print(f"Scanning {len(files)} Biometric files...")
    df_list = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = [c.lower().strip() for c in df.columns]
            df_list.append(df)
        except:
            pass
    return pd.concat(df_list, ignore_index=True)

print("--- LOADING BIOMETRIC DATA ---")
df_bio = load_biometric_recursive("biometric")

# ==========================================
# 2. DETECT ANOMALIES (The "Spike" Logic)
# ==========================================
print("--- HUNTING FOR ANOMALIES ---")

# Convert Date
df_bio['date'] = pd.to_datetime(df_bio['date'], dayfirst=True, errors='coerce')

# Total Daily Updates per Pincode
df_bio['total_updates'] = df_bio['bio_age_5_17'] + df_bio['bio_age_17_']

# Group: Pincode + Date
daily_activity = df_bio.groupby(['state', 'district', 'pincode', 'date'])['total_updates'].sum().reset_index()

# Calculate Statistics per Pincode (Mean & Standard Deviation)
stats = daily_activity.groupby('pincode')['total_updates'].agg(['mean', 'std']).reset_index()
stats.columns = ['pincode', 'avg_daily', 'std_dev']

# Merge stats back to main data
analysis = pd.merge(daily_activity, stats, on='pincode')

# DEFINE ANOMALY: Activity > (Average + 4 * StdDev)
# This finds "Extreme Rare Events" (99.9% outlier)
analysis['is_anomaly'] = analysis['total_updates'] > (analysis['avg_daily'] + (4 * analysis['std_dev']))

# Filter only the anomalies
anomalies = analysis[analysis['is_anomaly'] == True].sort_values('total_updates', ascending=False)

# Get Top 5 "Suspicious" Pincodes to visualize
top_suspicious = anomalies.drop_duplicates('pincode').head(5)
suspicious_pincodes = top_suspicious['pincode'].tolist()

print(f"\nFound {len(anomalies)} suspicious spikes across India.")
print("Top 5 Extreme Events Detected:")
print(top_suspicious[['date', 'state', 'district', 'pincode', 'total_updates', 'avg_daily']])

# ==========================================
# 3. VISUALIZE THE "HEARTBEAT" (Time Series)
# ==========================================
print("\n--- GENERATING FORENSIC CHART ---")

# Filter data for only the top 3 suspicious pincodes
plot_data = daily_activity[daily_activity['pincode'].isin(suspicious_pincodes[:3])]

plt.figure(figsize=(14, 6))
sns.lineplot(data=plot_data, x='date', y='total_updates', hue='pincode', palette='bright', marker='o')

plt.title('Forensic Analysis: Suspicious Biometric Spikes (Potential Camps or Fraud)', fontsize=14, weight='bold')
plt.xlabel('Timeline')
plt.ylabel('Daily Biometric Updates')
plt.legend(title='Pincode')

# Add Threshold Line (Visual Guide)
plt.axhline(y=100, color='red', linestyle='--', alpha=0.5, label='Normal Threshold')

plt.tight_layout()
plt.savefig('biometric_anomaly_detection.png', dpi=300)
print("✅ Graph saved: 'biometric_anomaly_detection.png'")