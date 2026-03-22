import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import calendar

# ==========================================
# 1. LOAD DATA
# ==========================================
def load_recursive(keyword):
    # Searches for files containing the keyword in any subfolder
    files = sorted(glob.glob(f"*{keyword}*/**/*.csv", recursive=True))
    if not files: files = sorted(glob.glob(f"{keyword}*/**/*.csv", recursive=True))
    
    df_list = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = [c.lower().strip() for c in df.columns]
            df_list.append(df)
        except: pass
    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

print("Loading Biometric Data (The Pulse)...")
df_bio = load_recursive("biometric")

# ==========================================
# 2. PREPARE THE CALENDAR DATA
# ==========================================
# Convert Date
df_bio['date'] = pd.to_datetime(df_bio['date'], dayfirst=True, errors='coerce')

# Filter for 2025 (or your main year) to keep the calendar clean
df_bio = df_bio[df_bio['date'].dt.year == 2025]

# Calculate Daily Total Volume
df_bio['total_volume'] = df_bio['bio_age_5_17'] + df_bio['bio_age_17_']
daily_vol = df_bio.groupby('date')['total_volume'].sum().reset_index()

# Extract Day and Month for the Heatmap
daily_vol['day'] = daily_vol['date'].dt.day
daily_vol['month'] = daily_vol['date'].dt.month
daily_vol['month_name'] = daily_vol['date'].dt.month_name()

# Pivot the data: Rows=Month, Cols=Day, Values=Volume
heatmap_data = daily_vol.pivot_table(index='month', columns='day', values='total_volume', aggfunc='sum')

# Sort index to ensure Jan is top, Dec is bottom
heatmap_data = heatmap_data.sort_index(ascending=True)
# Rename index to Month Names
heatmap_data.index = [calendar.month_abbr[i] for i in heatmap_data.index]

# ==========================================
# 3. GENERATE THE "RHYTHM" CHART
# ==========================================
plt.figure(figsize=(20, 8))
sns.set(font_scale=1.1)

# The Heatmap
ax = sns.heatmap(
    heatmap_data, 
    cmap="RdYlGn_r", # Red = High Traffic (Busy), Green = Low Traffic
    linewidths=1, 
    linecolor='white',
    cbar_kws={'label': 'Daily Aadhaar Interactions'}
)

plt.title("The Rhythm of India: When Does the Nation Update?", fontsize=24, weight='bold', pad=20)
plt.xlabel("Day of the Month", fontsize=14)
plt.ylabel("Month", fontsize=14)

# ADD CREATIVE ANNOTATIONS (The Storytelling Part)
# You can manually adjust these coordinates based on your graph
# Example: "School Rush" in May/June
plt.text(15, 5.5, "SCHOOL ADMISSION RUSH?\n(Mandatory Age 5/15 Updates)", 
         horizontalalignment='center', color='black', weight='bold', fontsize=10,
         bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))

# Example: "Year End Rush"
plt.text(25, 11.5, "FINANCIAL YEAR END\nDEADLINES?", 
         horizontalalignment='center', color='black', weight='bold', fontsize=10,
         bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))

plt.tight_layout()
plt.savefig('creative_rhythm_calendar.png', dpi=300)
print("✅ Creative Visual Saved: 'creative_rhythm_calendar.png'")