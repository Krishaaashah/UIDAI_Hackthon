import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ==========================================
# 1. LOAD EVERYTHING (Using your extracted folders)
# ==========================================
def load_recursive(keyword):
    files = sorted(glob.glob(f"*{keyword}*/**/*.csv", recursive=True))
    if not files: files = sorted(glob.glob(f"{keyword}*/**/*.csv", recursive=True)) # Fallback
    
    df_list = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = [c.lower().strip() for c in df.columns]
            df_list.append(df)
        except: pass
    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

print("Loading All Datasets...")
df_demo = load_recursive("demographic")
df_enrol = load_recursive("enrolment")
df_bio = load_recursive("biometric")

# Standardize Cities (The Pincode Consensus Trick)
all_locs = pd.concat([
    df_demo[['pincode', 'state', 'district']],
    df_enrol[['pincode', 'state', 'district']],
    df_bio[['pincode', 'state', 'district']]
]).dropna()

all_locs['district'] = all_locs['district'].astype(str).str.title().str.strip()
all_locs['state'] = all_locs['state'].astype(str).str.title().str.strip()

# Create Master Dictionary
pincode_mapper = all_locs.groupby('pincode')[['state', 'district']].agg(
    lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0]
).reset_index()

# Apply Dictionary to all 3 datasets
df_demo = df_demo.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))
df_enrol = df_enrol.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))
df_bio = df_bio.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))

# ==========================================
# 2. CALCULATE MIGRATION SCORE (X-AXIS)
# ==========================================
print("Calculating Migration Scores...")
df_demo['updates'] = df_demo['demo_age_5_17'] + df_demo['demo_age_17_']
df_enrol['enrolments'] = df_enrol['age_0_5'] + df_enrol['age_5_17'] + df_enrol['age_18_greater']

mig_agg = pd.merge(
    df_demo.groupby(['state', 'district'])['updates'].sum().reset_index(),
    df_enrol.groupby(['state', 'district'])['enrolments'].sum().reset_index(),
    on=['state', 'district']
).fillna(0)

mig_agg['migration_pressure'] = mig_agg['updates'] / (mig_agg['enrolments'] + 1)

# ==========================================
# 3. CALCULATE ANOMALY RISK (Y-AXIS)
# ==========================================
print("Detecting Anomalies...")
df_bio['total_updates'] = df_bio['bio_age_5_17'] + df_bio['bio_age_17_']
daily_stats = df_bio.groupby(['state', 'district', 'date'])['total_updates'].sum().reset_index()

# Calculate Mean & StdDev for each District
district_stats = daily_stats.groupby(['state', 'district'])['total_updates'].agg(['mean', 'std']).reset_index()
district_stats.columns = ['state', 'district', 'daily_avg', 'daily_std']

# Merge and Flag Anomalies
analysis = pd.merge(daily_stats, district_stats, on=['state', 'district'])
# Strict Rule: Anomaly if updates > Average + (3 * StdDev)
analysis['is_anomaly'] = analysis['total_updates'] > (analysis['daily_avg'] + (3 * analysis['daily_std']))

# Count Anomalies per District
anomaly_counts = analysis[analysis['is_anomaly'] == True].groupby(['state', 'district']).size().reset_index(name='anomaly_count')

# ==========================================
# 4. THE "NEXUS" MERGE (CORRELATION)
# ==========================================
final_df = pd.merge(mig_agg, anomaly_counts, on=['state', 'district'], how='left').fillna(0)

# Filter for meaningful districts (Ignore tiny villages)
final_df = final_df[final_df['updates'] > 5000] 

# Exclude conflict zones to keep it about "Systems"
exclude = ['Imphal', 'Thoubal', 'Bishnupur']
final_df = final_df[~final_df['district'].str.contains('|'.join(exclude), case=False)]

# ==========================================
# 5. GENERATE THE "WINNING" GRAPH
# ==========================================
print("Generating The Risk Nexus Graph...")
plt.figure(figsize=(12, 8))
sns.set_style("whitegrid")

# Scatter Plot: X=Migration, Y=Anomalies, Size=Volume
scatter = sns.scatterplot(
    data=final_df, 
    x='migration_pressure', 
    y='anomaly_count', 
    size='updates', 
    sizes=(50, 500), 
    hue='state', 
    palette='deep', 
    alpha=0.7,
    legend=False
)

# Label the "Quadrants of Concern"
# Quadrant 1: High Migration + High Anomalies (The Danger Zone)
danger_zone = final_df[
    (final_df['migration_pressure'] > final_df['migration_pressure'].quantile(0.8)) & 
    (final_df['anomaly_count'] > final_df['anomaly_count'].quantile(0.8))
]

# Annotate the Danger Cities
for line in range(0, danger_zone.shape[0]):
     plt.text(
         danger_zone.migration_pressure.iloc[line]+0.2, 
         danger_zone.anomaly_count.iloc[line], 
         danger_zone.district.iloc[line], 
         horizontalalignment='left', 
         size='small', 
         color='black', 
         weight='semibold'
     )

plt.title('The Risk Nexus: Do Migration Hubs Hide System Fraud?', fontsize=16, weight='bold')
plt.xlabel('Migration Pressure (Updates vs Births)', fontsize=12)
plt.ylabel('Number of Biometric Anomalies (Spikes)', fontsize=12)

# Insight Box
txt = (
    "KEY FINDING:\n"
    "Districts in the TOP RIGHT corner are\n"
    "your primary targets. They suffer from\n"
    "rapid population influx AND frequent\n"
    "suspicious system spikes."
)
plt.text(
    x=final_df['migration_pressure'].max() * 0.7, 
    y=final_df['anomaly_count'].max() * 0.1, 
    s=txt, 
    bbox=dict(facecolor='mistyrose', edgecolor='red', boxstyle='round,pad=1'),
    fontsize=10
)

plt.tight_layout()
plt.savefig('project_nexus_final.png', dpi=300)
print("✅ WINNING GRAPH SAVED: 'project_nexus_final.png'")

# Top 5 "Danger Zone" Districts
print("\nTOP 5 'DANGER ZONE' DISTRICTS (High Migration + High Anomalies):")
print(danger_zone[['state', 'district', 'migration_pressure', 'anomaly_count']].sort_values('anomaly_count', ascending=False).head(5))