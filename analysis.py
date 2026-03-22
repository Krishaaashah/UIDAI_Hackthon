import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ==========================================
# 1. SMART DATA LOADING (Recursive Search)
# ==========================================
def load_recursive(folder_keywords):
    """
    Finds CSV files inside any folder that matches the keyword.
    Example: keyword 'demographic' will find files in 'api_data_aadhar_demographic'
    """
    # This pattern looks for any folder (*) containing the keyword, and then any CSV inside it (recursive)
    search_pattern = f"*{folder_keywords}*/**/*.csv"
    files = sorted(glob.glob(search_pattern, recursive=True))
    
    if not files:
        # Fallback: Try looking in the current directory if folders are right here
        search_pattern = f"{folder_keywords}*/**/*.csv"
        files = sorted(glob.glob(search_pattern, recursive=True))

    if not files:
        print(f"⚠️ ERROR: No files found for keyword '{folder_keywords}'. Check folder names.")
        return pd.DataFrame()
        
    print(f"Found {len(files)} files for '{folder_keywords}'...")
    
    df_list = []
    for f in files:
        try:
            df = pd.read_csv(f)
            # Standardize columns: remove spaces, make lowercase
            df.columns = [c.lower().strip() for c in df.columns]
            df_list.append(df)
        except Exception as e:
            print(f"Skipping corrupt file {f}")
            
    return pd.concat(df_list, ignore_index=True)

print("--- STEP 1: LOADING EXTRACTED DATA ---")
# We look for folders containing 'demographic' and 'enrolment'
df_demo = load_recursive("demographic") 
df_enrol = load_recursive("enrolment")

if df_demo.empty or df_enrol.empty:
    print("❌ STOPPING: Could not load data. Please ensure folders are in the same directory as this script.")
else:
    print(f"✅ Loaded: {len(df_demo):,} Demo Rows | {len(df_enrol):,} Enrolment Rows")

    # ==========================================
    # 2. THE "CITY NAME FIXER" (Pincode Consensus)
    # ==========================================
    print("\n--- STEP 2: STANDARDIZING CITY NAMES ---")
    
    # Stack simple location data from both sets
    locations = pd.concat([
        df_demo[['pincode', 'state', 'district']],
        df_enrol[['pincode', 'state', 'district']]
    ]).dropna()

    # Clean Text
    locations['district'] = locations['district'].astype(str).str.title().str.strip()
    locations['state'] = locations['state'].astype(str).str.title().str.strip()

    # Find "Mode" (Most frequent name) for each Pincode
    # This fixes "Bangalore" vs "Bengaluru" automatically
    pincode_mapper = locations.groupby('pincode')[['state', 'district']].agg(
        lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0]
    ).reset_index()

    # Apply Fixes
    df_demo = df_demo.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))
    df_enrol = df_enrol.merge(pincode_mapper, on='pincode', how='left', suffixes=('_old', ''))

    # ==========================================
    # 3. CALCULATE "MIGRATION SCORE"
    # ==========================================
    print("\n--- STEP 3: CALCULATING SCORES ---")

    # Define Columns to Sum
    df_demo['updates'] = df_demo['demo_age_5_17'] + df_demo['demo_age_17_']
    df_enrol['enrolments'] = df_enrol['age_0_5'] + df_enrol['age_5_17'] + df_enrol['age_18_greater']

    # Aggregate
    demo_agg = df_demo.groupby(['state', 'district'])['updates'].sum().reset_index()
    enrol_agg = df_enrol.groupby(['state', 'district'])['enrolments'].sum().reset_index()

    # Merge
    migration_df = pd.merge(demo_agg, enrol_agg, on=['state', 'district'], how='outer').fillna(0)

    # Filter Noise (< 1000 updates) & Conflict Zones
    migration_df = migration_df[migration_df['updates'] > 1000]
    exclude = ['Imphal', 'Thoubal', 'Bishnupur', 'Mohla-Manpur']
    migration_df = migration_df[~migration_df['district'].str.contains('|'.join(exclude), case=False)]

    # SCORE FORMULA
    migration_df['migration_score'] = migration_df['updates'] / (migration_df['enrolments'] + 1)
    top_hubs = migration_df.sort_values('migration_score', ascending=False).head(15)

    # ==========================================
    # 4. GENERATE GRAPH (With Info Box)
    # ==========================================
    print("\n--- STEP 4: GENERATING GRAPH ---")
    plt.figure(figsize=(12, 7))
    sns.set_style("whitegrid")

    # Bar Plot
    sns.barplot(data=top_hubs, x='migration_score', y='district', hue='state', dodge=False, palette='magma')

    # Labels
    plt.title('Top 15 Economic Migration Hubs (Identified by Update/Enrolment Ratio)', fontsize=14, weight='bold')
    plt.xlabel('Migration Pressure Score (Updates per New Birth)', fontsize=11)
    plt.ylabel(None)
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', title='State')

    # INFO BOX (Explains the graph automatically)
    explanation = (
        "INSIGHT:\n"
        "• These districts have massive 'Update' volume\n"
        "  but very low 'New Enrolment' (Births).\n"
        "• This indicates a heavy influx of working-age\n"
        "  population migrating for jobs."
    )
    plt.text(
        x=top_hubs['migration_score'].max() * 0.65, 
        y=10, 
        s=explanation, 
        bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=1', alpha=0.9),
        fontsize=9
    )

    plt.tight_layout()
    plt.savefig('migration_radar_final.png', dpi=300)
    print("✅ Graph saved: 'migration_radar_final.png'")

    # ==========================================
    # 5. SAVE MAP DATA
    # ==========================================
    migration_df.to_csv("INDIA_MIGRATION_MAP_DATA.csv", index=False)
    print("✅ Map Data saved: 'INDIA_MIGRATION_MAP_DATA.csv'")
    print("\nTop 5 Districts:")
    print(top_hubs[['state', 'district', 'migration_score']].head())