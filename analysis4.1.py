import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. SMART DATA LOADING
# ==========================================
def load_recursive(keyword):
    """
    Searches for files containing the keyword in any subfolder.
    """
    # Pattern to find files deep inside extracted folders
    search_pattern = f"*{keyword}*/**/*.csv"
    files = sorted(glob.glob(search_pattern, recursive=True))
    
    # Fallback: Check current directory if folders are not nested
    if not files:
        files = sorted(glob.glob(f"{keyword}*/**/*.csv", recursive=True))

    if not files:
        print(f"⚠️ ERROR: No files found for '{keyword}'. Check your folder names.")
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

# Load Biometric Data
print("--- LOADING DATA ---")
df_bio = load_recursive("biometric")

if df_bio.empty:
    print("❌ STOPPING: No data loaded.")
else:
    # ==========================================
    # 2. DATA PROCESSING
    # ==========================================
    print("--- CALCULATING TRENDS ---")
    
    # Convert 'date' column to datetime objects
    df_bio['date'] = pd.to_datetime(df_bio['date'], dayfirst=True, errors='coerce')
    
    # Drop rows with invalid dates
    df_bio = df_bio.dropna(subset=['date'])

    # Calculate Total Daily Volume (Age 5-17 + Age 17+)
    df_bio['total_volume'] = df_bio['bio_age_5_17'] + df_bio['bio_age_17_']

    # Aggregate by Date
    daily_trend = df_bio.groupby('date')['total_volume'].sum().reset_index()
    daily_trend = daily_trend.sort_values('date')

    # Calculate 7-Day Moving Average (Trend Line)
    # This smooths out the "Weekend Dip" to show the real growth
    daily_trend['7_day_avg'] = daily_trend['total_volume'].rolling(window=7).mean()

    # ==========================================
    # 3. GENERATE THE GRAPH
    # ==========================================
    print("--- GENERATING GRAPH ---")
    plt.figure(figsize=(14, 7))
    sns.set_style("whitegrid")

    # Plot 1: Raw Daily Data (Light Grey) - Shows the noise/volatility
    plt.plot(daily_trend['date'], daily_trend['total_volume'], 
             color='lightgray', label='Daily Volume (Raw)', alpha=0.6)

    # Plot 2: Trend Line (Navy Blue) - Shows the true direction
    plt.plot(daily_trend['date'], daily_trend['7_day_avg'], 
             color='navy', linewidth=2.5, label='7-Day Trend (Moving Average)')

    # Chart Styling
    plt.title('The "Pulse" of Digital India: Biometric Update Traffic (2025)', fontsize=16, weight='bold')
    plt.xlabel('Timeline', fontsize=12)
    plt.ylabel('Daily Biometric Updates', fontsize=12)
    plt.legend(loc='upper left')

    # AUTOMATIC ANNOTATION: Find and Label the Peak Day
    peak_row = daily_trend.loc[daily_trend['total_volume'].idxmax()]
    peak_date = peak_row['date']
    peak_val = int(peak_row['total_volume'])
    
    # Add an arrow pointing to the highest spike
    plt.annotate(f"PEAK LOAD\n{peak_val:,} Updates", 
                 xy=(peak_date, peak_val), 
                 xytext=(peak_date, peak_val + (peak_val * 0.1)), # Position text slightly above
                 arrowprops=dict(facecolor='red', shrink=0.05),
                 fontsize=10, weight='bold', color='red', ha='center')

    # Save the file
    plt.tight_layout()
    plt.savefig('project_pulse_trend.png', dpi=300)
    
    print(f"✅ SUCCESS! Graph saved as 'project_pulse_trend.png'")
    print(f"📊 Stats: Processed {daily_trend['total_volume'].sum():,} total updates.")
    print(f"🚀 Peak Day: {peak_date.date()} with {peak_val:,} updates.")