import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. LOAD & PREP DATA (Standard Logic)
# ==========================================
# (We reuse the previous cleaning logic to ensure consistency)
def load_recursive(keyword):
    search_pattern = f"*{keyword}*/**/*.csv"
    files = sorted(glob.glob(search_pattern, recursive=True))
    if not files: files = sorted(glob.glob(f"{keyword}*/**/*.csv", recursive=True))
    df_list = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = [c.lower().strip() for c in df.columns]
            df_list.append(df)
        except: pass
    return pd.concat(df_list, ignore_index=True)

df_bio = load_recursive("biometric")
df_enrol = load_recursive("enrolment")

# Standardize Locations
locations = pd.concat([df_bio[['pincode', 'state', 'district']], df_enrol[['pincode', 'state', 'district']]]).dropna()
locations['state'] = locations['state'].astype(str).str.title().str.strip()
pincode_mapper = locations.groupby('pincode')['state'].agg(lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0]).reset_index()

df_bio = df_bio.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))
df_enrol = df_enrol.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))

# ==========================================
# 2. STATE-LEVEL AGGREGATION
# ==========================================
print("--- CALCULATING STATE LEADERS & LAGGARDS ---")

# Metric A: Stock (Total Children 0-17)
df_enrol['child_stock'] = df_enrol['age_0_5'] + df_enrol['age_5_17']
state_stock = df_enrol.groupby('state')['child_stock'].sum()

# Metric B: Flow (Updates 5-17)
df_bio['child_updates'] = df_bio['bio_age_5_17']
state_updates = df_bio.groupby('state')['child_updates'].sum()

# Merge & Calculate Ratio
state_df = pd.concat([state_stock, state_updates], axis=1).fillna(0)
state_df = state_df[state_df['child_stock'] > 5000] # Filter small territories for fairness
state_df['compliance_ratio'] = state_df['child_updates'] / state_df['child_stock']

# Identify Top 5 and Bottom 5
state_df = state_df.sort_values('compliance_ratio', ascending=False)
top_5 = state_df.head(5).copy()
top_5['type'] = 'Best Performing States'
bottom_5 = state_df.tail(5).copy()
bottom_5['type'] = 'Critical Attention Needed'

# Combine for Plotting
plot_data = pd.concat([top_5, bottom_5])

# ==========================================
# 3. GENERATE THE "POLICY VIEW" GRAPH
# ==========================================
plt.figure(figsize=(12, 7))
sns.set_style("whitegrid")

# Create a Diverging Bar Chart
colors = ['green' if x == 'Best Performing States' else 'red' for x in plot_data['type']]
ax = sns.barplot(
    data=plot_data,
    x='compliance_ratio',
    y=plot_data.index,
    palette=colors
)

plt.title('National Policy Audit: The Compliance Divide', fontsize=16, weight='bold')
plt.xlabel('Compliance Ratio (Mandatory Updates per Child)', fontsize=12)
plt.ylabel('State', fontsize=12)

# Add Value Labels
for i, v in enumerate(plot_data['compliance_ratio']):
    ax.text(v + 0.01, i, f"{v:.2f}", color='black', va='center', weight='bold')

# Insight Text
plt.text(
    x=plot_data['compliance_ratio'].max() * 0.7, 
    y=6, 
    s="INSIGHT:\nThe 'Green' states show that high compliance\nis achievable. The 'Red' states require\nimmediate policy intervention.",
    bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=1'),
    fontsize=10
)

plt.tight_layout()
plt.savefig('state_policy_audit.png', dpi=300)
print("✅ State Leaderboard Saved: 'state_policy_audit.png'")