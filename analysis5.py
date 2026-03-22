# ... (Previous loading code remains the same)

# ==========================================
# 3. CALCULATE THE "EXCLUSION RISK"
# ==========================================
print("Calculating Child Welfare Risks...")

# Metric 1: The "New Generation" (Enrolment of 0-5 and 5-17)
df_enrol['child_stock'] = df_enrol['age_0_5'] + df_enrol['age_5_17']
child_stock_agg = df_enrol.groupby(['state', 'district'])['child_stock'].sum().reset_index()

# Metric 2: The "Compliance" (Biometric Updates for 5-17)
df_bio['child_updates'] = df_bio['bio_age_5_17']
child_compliance_agg = df_bio.groupby(['state', 'district'])['child_updates'].sum().reset_index()

# MERGE (FIXED LINE)
# We use on=['state', 'district'] with an equals sign
welfare_df = pd.merge(child_stock_agg, child_compliance_agg, on=['state', 'district'], how='inner').fillna(0)

# FILTER: Ignore tiny districts (< 1000 kids) to avoid noise
welfare_df = welfare_df[welfare_df['child_stock'] > 1000]

# SCORE: The Compliance Ratio
welfare_df['compliance_ratio'] = welfare_df['child_updates'] / welfare_df['child_stock']

# FIND THE WORST PERFORMERS (Bottom 15)
at_risk_districts = welfare_df.sort_values('compliance_ratio', ascending=True).head(15)

# ==========================================
# 4. VISUALIZE THE "DANGER ZONES"
# ==========================================
plt.figure(figsize=(12, 7))
sns.set_style("whitegrid")

# Bar Plot
ax = sns.barplot(
    data=at_risk_districts, 
    x='compliance_ratio', 
    y='district', 
    hue='state', 
    dodge=False, 
    palette='Reds_r' # Dark Red = Worst
)

plt.title('The "Ghost Child" Risk: Districts with Lowest Mandatory Biometric Compliance', fontsize=14, weight='bold')
plt.xlabel('Compliance Ratio (Biometric Updates per Enrolled Child)', fontsize=12)
plt.ylabel(None)
plt.legend(title='State', bbox_to_anchor=(1.02, 1), loc='upper left')

# Add Explainer Text
msg = (
    "URGENT ACTION REQUIRED:\n"
    "In these districts, children are enrolling (Stock)\n"
    "but NOT updating Biometrics (Flow).\n"
    "Risk: Massive loss of Scholarships/Benefits."
)
plt.text(
    x=at_risk_districts['compliance_ratio'].max() * 0.5, 
    y=12, 
    s=msg, 
    bbox=dict(facecolor='mistyrose', edgecolor='red', boxstyle='round,pad=1'),
    fontsize=10
)

plt.tight_layout()
plt.savefig('welfare_risk_shield.png', dpi=300)
print("✅ Welfare Graph Saved: 'welfare_risk_shield.png'")

print("\nTOP 5 HIGH-RISK DISTRICTS (Lowest Compliance):")
print(at_risk_districts[['state', 'district', 'child_stock', 'child_updates', 'compliance_ratio']].head(5))