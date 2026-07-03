import os
import numpy as np
import pandas as pd

def process_cricket_stats(csv_path: str, output_path: str, scout_output_path: str):
    print(f"📖 Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Clean column names (strip any accidental trailing whitespaces)
    df.columns = df.columns.str.strip()

    # Define all expected numeric columns from your dataset structure
    numeric_cols = [
        'Year', 'Matches_Batted', 'Not_Outs', 'Runs_Scored', 'Highest_Score',
        'Batting_Average', 'Balls_Faced', 'Batting_Strike_Rate', 'Centuries',
        'Half_Centuries', 'Fours', 'Sixes', 'Catches_Taken', 'Stumpings',
        'Matches_Bowled', 'Balls_Bowled', 'Runs_Conceded', 'Wickets_Taken',
        'Bowling_Average', 'Economy_Rate', 'Bowling_Strike_Rate',
        'Four_Wicket_Hauls', 'Five_Wicket_Hauls'
    ]

    # --- AGGRESIVE SANITIZATION LAYER ---
    # Force every single numeric column to numbers. Any string text turns into NaN.
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Ensure Player_Name is treated as a clean string and fill empty values
    df['Player_Name'] = df['Player_Name'].astype(str).str.strip()
    
    # Drop rows where critical components like Year or Player Name are completely missing
    df = df.dropna(subset=['Year', 'Player_Name'])
    # Convert Year to integer now that it's perfectly clean
    df['Year'] = df['Year'].astype(int)
    # ------------------------------------

    # 1. IDENTIFY NEW SCOUTS / PLAYERS WITH NO DATA
    # Group by player and find who has zero activity across their entire career record
    total_perf_per_player = df.groupby('Player_Name')[['Runs_Scored', 'Balls_Bowled']].sum()
    new_scout_names = total_perf_per_player[
        (total_perf_per_player['Runs_Scored'] == 0) & (total_perf_per_player['Balls_Bowled'] == 0)
    ].index.tolist()

    print(f"✨ Found {len(new_scout_names)} players with no history. Exporting as scouts...")
    df_scouts = pd.DataFrame({'Player_Name': new_scout_names, 'Status': 'No old stats, new scout!'})
    df_scouts.to_csv(scout_output_path, index=False)

    # Remove scout players from the core calculation matrix
    df_filtered = df[~df['Player_Name'].isin(new_scout_names)].copy()

    # 2. EXTRACT PRE-2018 EXPERIENCE FLAGS
    print("⏳ Extracting pre-2018 career experience flags...")
    pre_2018_players = set(df_filtered[df_filtered['Year'] < 2018]['Player_Name'].unique())

    # 3. DROP ROWS PRIOR TO 2018 FOR RECENT STATS
    df_filtered = df_filtered[df_filtered['Year'] >= 2018].copy()

    if df_filtered.empty:
        print("⚠️ Warning: No data left after filtering for years >= 2018!")
        return

    # 4. ASSIGN TIME-DECAY WEIGHTS
    # 2018-2021 -> 1x multiplier | 2022-2025 -> 3x multiplier
    df_filtered['Weight'] = np.where(df_filtered['Year'] >= 2022, 3, 1)

    # 5. EXECUTE TIME-WEIGHTED AGGREGATIONS
    print("🧮 Computing time-weighted statistical profiles...")
    columns_to_weight = [
        'Matches_Batted', 'Not_Outs', 'Runs_Scored', 'Balls_Faced', 
        'Centuries', 'Half_Centuries', 'Fours', 'Sixes', 'Catches_Taken', 'Stumpings',
        'Matches_Bowled', 'Balls_Bowled', 'Runs_Conceded', 'Wickets_Taken', 
        'Four_Wicket_Hauls', 'Five_Wicket_Hauls'
    ]

    # Multiply counts by weight factor
    for col in columns_to_weight:
        if col in df_filtered.columns:
            df_filtered[f'{col}_weighted'] = df_filtered[col].fillna(0) * df_filtered['Weight']

    # Group by player and sum up weighted values and weight denominators
    group_cols = [f'{col}_weighted' for col in columns_to_weight] + ['Weight']
    aggregated = df_filtered.groupby('Player_Name')[group_cols].sum()

    # Normalize back by total weight to get true weighted averages per season
    final_players = pd.DataFrame(index=aggregated.index)
    for col in columns_to_weight:
        final_players[col] = aggregated[f'{col}_weighted'] / aggregated['Weight']

    # Handle highest score maximums separately (not a weighted average)
    if 'Highest_Score' in df_filtered.columns:
        final_players['Highest_Score_Max'] = df_filtered.groupby('Player_Name')['Highest_Score'].max().fillna(0)

    # 6. FEATURE ENGINEERING ADVANCED RATIOS
    print("🚀 Engineering advanced efficiency metrics...")
    
    # Boundary Percentage = (Fours + Sixes) / Balls Faced
    final_players['Boundary_Percentage'] = (final_players['Fours'] + final_players['Sixes']) / final_players['Balls_Faced'].replace(0, np.nan)
    final_players['Boundary_Percentage'] = final_players['Boundary_Percentage'].fillna(0)

    # Career Batting Strike Rate = (Runs Scored / Balls Faced) * 100
    final_players['Batting_Strike_Rate'] = (final_players['Runs_Scored'] / final_players['Balls_Faced'].replace(0, np.nan)) * 100
    final_players['Batting_Strike_Rate'] = final_players['Batting_Strike_Rate'].fillna(0)

    # Career Batting Average = Runs Scored / Dismissals (Innings - Not Outs)
    dismissals = final_players['Matches_Batted'] - final_players['Not_Outs']
    final_players['Batting_Average'] = final_players['Runs_Scored'] / dismissals.replace(0, 1)
    
    # Career Bowling Strike Rate = Balls Bowled / Wickets Taken
    final_players['Bowling_Strike_Rate'] = final_players['Balls_Bowled'] / final_players['Wickets_Taken'].replace(0, np.nan)
    final_players['Bowling_Strike_Rate'] = final_players['Bowling_Strike_Rate'].fillna(99.9)

    # Career Economy Rate = (Runs Conceded / Balls Bowled) * 6
    final_players['Economy_Rate'] = (final_players['Runs_Conceded'] / final_players['Balls_Bowled'].replace(0, np.nan)) * 6
    final_players['Economy_Rate'] = final_players['Economy_Rate'].fillna(0)

    # 7. INJECT EXPERIENCE POINT FLAG
    final_players = final_players.reset_index()
    final_players['has_old_experience'] = final_players['Player_Name'].apply(lambda x: 1 if x in pre_2018_players else 0)

    # Save to final cleaned CSV file
    final_players.to_csv(output_path, index=False)
    print(f"✅ Success! Cleaned player tracking profiles saved to: {output_path}")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INPUT_CSV = os.path.join(BASE_DIR, "stats.csv")
    OUTPUT_CSV = os.path.join(BASE_DIR, "cleaned_auction_profiles.csv")
    SCOUT_CSV = os.path.join(BASE_DIR, "new_scouts.csv")

    process_cricket_stats(INPUT_CSV, OUTPUT_CSV, SCOUT_CSV)