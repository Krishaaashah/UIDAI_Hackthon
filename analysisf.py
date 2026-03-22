import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ==========================================
# 1. ROBUST DATA LOADING (Recursive)
# ==========================================
def load_recursive(keyword):
    """
    Searches for files containing the keyword in any subfolder (deep search).
    """
    search_pattern = f"*{keyword}*/**/*.csv"
    files = sorted(glob.glob(search_pattern, recursive=True))
    
    # Fallback: Check current directory
    if not files:
        files = sorted(glob.glob(f"{keyword}*/**/*.csv", recursive=True))

    if not files:
        print(f"⚠️ ERROR: No files found for '{keyword}'. Check folder names.")
        return pd.DataFrame()

    print(f"Processing {len(files)} files for '{keyword}'...")
    df_list = []
    for f in files:
        try:
            df = pd.read_csv(f)
            # Standardize columns (lowercase, strip spaces)
            df.columns = [c.lower().strip() for c in df.columns]
            df_list.append(df)
        except Exception as e:
            print(f"Skipping corrupt file {f}")
            pass
    return pd.concat(df_list, ignore_index=True)

# ==========================================
# 2. LOAD DATASETS
# ==========================================
print("--- LOADING DATA ---")
df_bio = load_recursive("biometric")
df_enrol = load_recursive("enrolment")

if df_bio.empty or df_enrol.empty:
    print("❌ CRITICAL ERROR: Could not load datasets. Please check file paths.")
else:
    # ==========================================
    # 3. STANDARDIZE LOCATIONS (City Name Fixer)
    # ==========================================
    print("--- STANDARDIZING DISTRICT NAMES ---")
    locations = pd.concat([
        df_bio[['pincode', 'state', 'district']],
        df_enrol[['pincode', 'state', 'district']]
    ]).dropna()
    
    # Clean Strings
    locations['district'] = locations['district'].astype(str).str.title().str.strip()
    locations['state'] = locations['state'].astype(str).str.title().str.strip()

    # Consensus Logic: Use Pincode to fix "Bangalore" vs "Bengaluru"
    pincode_mapper = locations.groupby('pincode')[['state', 'district']].agg(
        lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0]
    ).reset_index()

    # Apply standardization
    df_bio = df_bio.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))
    df_enrol = df_enrol.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))

    # ==========================================
    # 4. CALCULATE "GHOST CHILD" RISK
    # ==========================================
    print("--- CALCULATING WELFARE METRICS ---")

    # METRIC A: Total Child Population (Stock)
    # We combine 0-5 and 5-17 to see the total "Serviceable Audience"
    df_enrol['child_stock'] = df_enrol['age_0_5'] + df_enrol['age_5_17']
    child_stock_agg = df_enrol.groupby(['state', 'district'])['child_stock'].sum().reset_index()

    # METRIC B: Mandatory Biometric Updates (Flow)
    # This checks if the 5-17 group is actually updating their biometrics
    df_bio['child_updates'] = df_bio['bio_age_5_17']
    child_compliance_agg = df_bio.groupby(['state', 'district'])['child_updates'].sum().reset_index()

    # MERGE metrics
    welfare_df = pd.merge(child_stock_agg, child_compliance_agg, on=['state', 'district'], how='inner').fillna(0)

    # FILTER: Remove small districts (< 1000 kids) to keep data relevant
    welfare_df = welfare_df[welfare_df['child_stock'] > 1000]

    # SCORE: Compliance Ratio (Updates per Enrolled Child)
    # Lower Score = Higher Risk of Exclusion
    welfare_df['compliance_ratio'] = welfare_df['child_updates'] / welfare_df['child_stock']

    # Sort to find the WORST districts (Bottom 15)
    at_risk_districts = welfare_df.sort_values('compliance_ratio', ascending=True).head(15)

    # ==========================================
    # 5. GENERATE THE WINNING GRAPH
    # ==========================================
    print("--- GENERATING FINAL GRAPH ---")
    plt.figure(figsize=(12, 7))
    sns.set_style("whitegrid")

    # Bar Chart
    sns.barplot(
        data=at_risk_districts, 
        x='compliance_ratio', 
        y='district', 
        hue='state', 
        dodge=False, 
        palette='Reds_r' # Darker Red = More Critical
    )

    plt.title('The "Ghost Child" Analysis: Districts with Critical Compliance Gaps', fontsize=14, weight='bold')
    plt.xlabel('Compliance Ratio (Mandatory Updates vs. Total Enrolled Children)', fontsize=12)
    plt.ylabel('District', fontsize=12)
    plt.legend(title='State', bbox_to_anchor=(1.02, 1), loc='upper left')

    # Insight Box
    msg = (
        "CRITICAL INSIGHT:\n"
        "These districts show High Child Enrolment\n"
        "but Near-Zero Mandatory Biometric Updates.\n"
        "RISK: Thousands of children may lose\n"
        "access to Scholarships/Mid-Day Meals."
    )
    plt.text(
        x=at_risk_districts['compliance_ratio'].max() * 0.6, 
        y=10, 
        s=msg, 
        bbox=dict(facecolor='mistyrose', edgecolor='red', boxstyle='round,pad=1'),
        fontsize=10
    )

    plt.tight_layout()
    plt.savefig('welfare_risk_shield_final.png', dpi=300)
    print("✅ SUCCESS! Graph saved as 'welfare_risk_shield_final.png'")
    
    # Save CSV for the PDF Report
    at_risk_districts.to_csv("welfare_risk_data.csv", index=False)
    print("✅ Data saved as 'welfare_risk_data.csv' (Include this in your report!)")
    
    print("\nTOP 5 CRITICAL DISTRICTS:")
    print(at_risk_districts[['state', 'district', 'compliance_ratio']].head())