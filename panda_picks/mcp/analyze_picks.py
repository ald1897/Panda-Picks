import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def analyze_pick_performance():
    """
    Analyze the performance of picks and generate insights.
    """
    conn = sqlite3.connect("../../database/nfl_data.db")

    # Calculate overall pick accuracy
    accuracy_query = """
    SELECT 
        COUNT(*) as total_picks,
        SUM(Correct_Pick) as correct_picks,
        ROUND(SUM(Correct_Pick) * 100.0 / COUNT(*), 2) as accuracy_percentage
    FROM picks_results
    """

    accuracy_df = pd.read_sql_query(accuracy_query, conn)
    print("\n🎯 Overall Pick Accuracy:")
    print(f"Correct picks: {accuracy_df['correct_picks'][0]} out of {accuracy_df['total_picks'][0]}")
    print(f"Accuracy rate: {accuracy_df['accuracy_percentage'][0]}%")

    # Analysis by team (which teams we predict best)
    team_query = """
    SELECT 
        Game_Pick as team, 
        COUNT(*) as total_picks,
        SUM(Correct_Pick) as correct_picks,
        ROUND(SUM(Correct_Pick) * 100.0 / COUNT(*), 2) as accuracy_percentage
    FROM picks_results
    GROUP BY Game_Pick
    ORDER BY accuracy_percentage DESC
    """

    team_accuracy_df = pd.read_sql_query(team_query, conn)
    print("\n🏈 Pick Accuracy by Team (Top 5):")
    print(team_accuracy_df.head(5))

    # Analysis by advantage significance
    significance_query = """
    SELECT 
        Overall_Adv_Sig as significance, 
        COUNT(*) as total_picks,
        SUM(Correct_Pick) as correct_picks,
        ROUND(SUM(Correct_Pick) * 100.0 / COUNT(*), 2) as accuracy_percentage
    FROM picks_results
    GROUP BY Overall_Adv_Sig
    ORDER BY accuracy_percentage DESC
    """

    significance_df = pd.read_sql_query(significance_query, conn)
    print("\n📊 Pick Accuracy by Advantage Significance:")
    print(significance_df)

    # Weekly performance trend
    weekly_query = """
    SELECT 
        WEEK,
        COUNT(*) as total_picks,
        SUM(Correct_Pick) as correct_picks,
        ROUND(SUM(Correct_Pick) * 100.0 / COUNT(*), 2) as accuracy_percentage
    FROM picks_results
    GROUP BY WEEK
    ORDER BY WEEK
    """

    weekly_df = pd.read_sql_query(weekly_query, conn)
    print("\n📈 Weekly Performance Trend:")
    print(weekly_df)

    # Correlation between advantage metrics and correct picks
    correlation_query = """
    SELECT 
        Overall_Adv,
        Offense_Adv,
        Defense_Adv,
        Correct_Pick
    FROM picks_results
    """

    correlation_df = pd.read_sql_query(correlation_query, conn)
    correlation = correlation_df.corr()
    print("\n🔄 Correlation between Advantage Metrics and Correct Picks:")
    print(correlation['Correct_Pick'].sort_values(ascending=False))

    conn.close()

    # You could also generate visualizations here
    # For example:
    # plt.figure(figsize=(10, 6))
    # plt.bar(weekly_df['WEEK'], weekly_df['accuracy_percentage'])
    # plt.title('Pick Accuracy by Week')
    # plt.xlabel('Week')
    # plt.ylabel('Accuracy %')
    # plt.savefig('weekly_accuracy.png')

    return {
        'overall_accuracy': accuracy_df['accuracy_percentage'][0],
        'best_team': team_accuracy_df.iloc[0]['team'],
        'best_team_accuracy': team_accuracy_df.iloc[0]['accuracy_percentage'],
        'best_significance': significance_df.iloc[0]['significance'],
        'best_significance_accuracy': significance_df.iloc[0]['accuracy_percentage'],
        'top_correlated_factor': correlation['Correct_Pick'].idxmax()
    }

if __name__ == "__main__":
    results = analyze_pick_performance()
    print("\n🏆 Summary:")
    print(f"Overall accuracy: {results['overall_accuracy']}%")
    print(f"Best team to pick: {results['best_team']} ({results['best_team_accuracy']}% accuracy)")
    print(f"Best indicator: {results['best_significance']} ({results['best_significance_accuracy']}% accuracy)")
    print(f"Top correlated factor: {results['top_correlated_factor']}")
