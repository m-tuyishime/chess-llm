import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D  
import matplotlib.colors as mcolors
import colorsys

from .database_manager import DatabaseManager

# ---------------------------
# Module: Création de rapports
# ---------------------------
class ReportGenerator:
    def __init__(self, db_manager=DatabaseManager()):
        self.db_manager = db_manager

    def rating_trends(self):
        """
        Generate a line plot showing the trend of model ratings over evaluations.
        Each model's x-axis is now based on the evaluation index.
        """
        df = self.db_manager.get_benchmark_data()
        if df.empty:
            print("No benchmark data available.")
            return

        plt.figure(figsize=(10, 6))
        for agent_name, data in df.groupby("agent_name"):
            data = data.sort_values("evaluation_index").copy()
            plt.plot(data['evaluation_index'], data['agent_rating'], label=agent_name)

        plt.xlabel("Evaluation Index")
        plt.ylabel("Model Rating")
        plt.title("Model Rating Trends Over Evaluations")
        plt.legend()
        plt.show()

    def rating_deviation_trends(self):
        """
        Generate a line plot showing the trend of model's rating deviations over evaluations.
        Each model's x-axis is now based on the evaluation index.
        """
        df = self.db_manager.get_benchmark_data()
        if df.empty:
            print("No benchmark data available.")
            return

        plt.figure(figsize=(10, 6))
        for agent_name, data in df.groupby("agent_name"):
            data = data.sort_values("evaluation_index").copy()
            plt.plot(data['evaluation_index'], data['agent_deviation'], label=agent_name)

        plt.xlabel("Evaluation Index")
        plt.ylabel("Model Rating Deviation")
        plt.title("Model Rating Deviation Trends Over Evaluations")
        plt.legend()
        plt.show()

    def puzzle_outcome(self):
        """
        Generate a single bar chart showing successes vs. failures by puzzle type overall.
        (Existing implementation kept for reusability.)
        """
        df = self.db_manager.get_puzzle_outcome_data()
        if df.empty:
            print("No game data available.")
            return

        x = df["type"]
        x_pos = range(len(x))
        width = 0.35

        plt.figure(figsize=(10, 6))
        plt.bar(x_pos, df["successes"], width=width, label="Successes")
        plt.bar([p + width for p in x_pos], df["failures"], width=width, label="Failures")
        plt.xticks([p + width / 2 for p in x_pos], x)
        plt.xlabel("Puzzle Type")
        plt.ylabel("Count")
        plt.title("Puzzle Outcomes by Type")
        plt.legend()
        plt.show()

    def puzzle_outcomes_by_agent(self):
        """
        Generate subplots of puzzle outcomes by type for each model.
        For each model, display a bar chart with successes and failures per puzzle type.
        """
        df = self.db_manager.get_puzzle_outcomes_by_agent_data()
        if df.empty:
            print("No game data available.")
            return

        models = df["agent_name"].unique()
        num_models = len(models)
        
        # Create subplots (arranged in one row or multiple rows if many models)
        cols = min(num_models, 3)  # up to 3 columns
        rows = (num_models + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4), squeeze=False)
        axes = axes.flatten()
        
        for idx, model in enumerate(models):
            ax = axes[idx]
            data = df[df["agent_name"] == model]
            
            types = data["type"].tolist()
            successes = data["successes"].tolist()
            failures = data["failures"].tolist()
            x = range(len(types))
            width = 0.35
            
            ax.bar(x, successes, width=width, label='Successes')
            ax.bar([p + width for p in x], failures, width=width, label='Failures')
            ax.set_xticks([p + width / 2 for p in x])
            ax.set_xticklabels(types, rotation=45)
            
            ax.set_xlabel("Puzzle Type")
            ax.set_ylabel("Count")
            ax.set_title(model)
            ax.legend()
        
        # Hide any unused subplots
        for jdx in range(idx + 1, len(axes)):
            fig.delaxes(axes[jdx])
            
        plt.tight_layout()
        plt.show()

    def illegal_moves_distribution(self): 
        """
        Generate a bar chart showing the percentage of illegal moves by model.
        The percentage is computed as (illegal_moves_count / total_moves) * 100 for each model.
        """ 
        df = self.db_manager.get_illegal_moves_data()
        if df.empty:
            print("No illegal moves data available.")
            return

        # Calculate illegal moves percentage for all models
        df["illegal_percentage"] = (df["illegal_moves_count"] / df["total_moves"]) * 100
        
        # Sort by percentage for better visualization
        df = df.sort_values("illegal_percentage", ascending=False)

        plt.figure(figsize=(10, 6))
        bars = plt.bar(df["agent_name"], df["illegal_percentage"], color="coral")
        
        # Add percentage labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.3,
                    f'{height:.1f}%',
                    ha='center', va='bottom', rotation=0)
            
        plt.xlabel("Model Name")
        plt.ylabel("Illegal Moves (%)")
        plt.title("Percentage of Illegal Moves by Model")
        plt.xticks(rotation=45, ha="right")
        plt.ylim(0, max(df["illegal_percentage"]) * 1.1)  # Add some space for labels
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()
        plt.show()

    def final_ratings_intervals(self):
        """
        Generate a plot showing each model's final rating with a 95% confidence
        interval calculated as rating ± (2 × rating_deviation) and the weighted puzzle rating spread.
        Splits the "Model Final Rating" entry into separate entries for the marker and the error bar.
        """
        df = self.db_manager.get_final_ratings_data()
        if df.empty:
            print("No ratings data available.")
            return

        # Calculate error as 2 × RD
        df['error'] = df['agent_deviation'] * 2

        plt.figure(figsize=(8, 6))
        # Remove label from errorbar call
        plt.errorbar(
            df['agent_name'], 
            df['agent_rating'], 
            yerr=df['error'], 
            fmt='o', 
            ecolor='red', 
            capsize=5, 
            markersize=8
        )

        # Plot weighted puzzle rating spread 
        weighted_rating, weighted_rd = self.db_manager.get_weighted_puzzle_rating()
        if weighted_rating is not None:
            puzzle_error = weighted_rd * 2
            plt.axhline(weighted_rating, color='green', linestyle='--')
            x_min, x_max = plt.xlim()
            plt.fill_between([x_min, x_max], weighted_rating - puzzle_error, weighted_rating + puzzle_error, 
                             color='green', alpha=0.2)

        # Create custom proxy handles for legend entries.
        # Proxies for model's final rating (blue dot) and its error bar (red line)
        marker_proxy = Line2D([], [], marker='o', color='blue', linestyle='None', markersize=8, label='Model Final Rating')
        spread_proxy = Line2D([], [], color='red', linestyle='-', linewidth=1, label='Model Rating Spread')
        
        handles = [marker_proxy, spread_proxy]
        
        # If weighted puzzle rating exists, create proxies for them as well.
        if weighted_rating is not None:
            weighted_proxy = Line2D([], [], color='green', linestyle='--', label='Weighted Puzzle Rating')
            # For the filled spread, using a thicker line to mimic the filled band.
            weighted_spread_proxy = Line2D([], [], color='green', linestyle='-', linewidth=10, alpha=0.2, label='Puzzle Rating Spread')
            handles.extend([weighted_proxy, weighted_spread_proxy])
        
        plt.xlabel("Model Name")
        plt.ylabel("Model Rating")
        plt.title("Final Model Ratings with 95% Confidence Intervals")
        plt.xticks(rotation=45, ha="right")
        plt.grid(True)
        plt.legend(handles=handles)
        plt.show()

    def correct_moves_percentage(self):
        """
        Generate a bar chart showing the average percentage of correct moves by model.
        The percentage is calculated as:
            (number of moves in game.agent_solution / number of moves in puzzles.moves) * 100.
        """
        df = self.db_manager.get_solutionary_agent_moves()
        if df.empty:
            print("No moves data available.")
            return

        results = []
        for idx, row in df.iterrows():
            expected = row["moves"]
            # Split moves into lists (ignoring extra whitespace)
            expected_moves = expected.strip().split() if isinstance(expected, str) and expected.strip() else []
            num_expected = len(expected_moves)
            if num_expected == 0:
                raise ValueError(f"Expected moves for puzzle {idx} are empty or invalid.")

            agent_solution = row["agent_moves"]
            agent_moves = agent_solution.strip().split() if isinstance(agent_solution, str) and agent_solution.strip() else []
            # Calculate percentage of moves provided
            if len(agent_moves) > num_expected:
                raise ValueError(f"Model moves for puzzle {idx} exceed expected moves.")
            correct_pct = (len(agent_moves) / num_expected) * 100

            results.append({"agent_name": row["agent_name"], "correct_pct": correct_pct})

        if not results:
            print("No valid moves to evaluate.")
            return

        df_pct = pd.DataFrame(results)
        avg_pct = df_pct.groupby("agent_name")["correct_pct"].mean().reset_index()

        plt.figure(figsize=(10, 6))
        plt.bar(avg_pct["agent_name"], avg_pct["correct_pct"], color="skyblue")
        plt.xlabel("Model Name")
        plt.ylabel("Average % of Correct Moves")
        plt.title("Average Percentage of Correct Moves by Model")
        plt.xticks(rotation=45, ha="right")
        plt.ylim(0, 100)
        plt.grid(axis="y")
        plt.show()
        
    def token_usage_per_move(self):
        """
        Generate subplots showing average token usage per move for each model.
        One subplot for prompt tokens and another for completion tokens.
        Uses a logarithmic y-axis to better show models with lower token counts.
        """
        df = self.db_manager.get_token_usage_per_move_data()
        if df.empty:
            print("No token usage data available per move.")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Sort by token usage for better visualization
        df_prompt = df.sort_values('avg_prompt_tokens', ascending=False)
        df_completion = df.sort_values('avg_completion_tokens', ascending=False)
        
        # Plot prompt tokens with log y-axis
        ax1.bar(df_prompt['agent_name'], df_prompt['avg_prompt_tokens'], color='blue')
        ax1.set_title('Average Prompt Tokens per Move (Log Scale)')
        ax1.set_xlabel('Model')
        ax1.set_ylabel('Tokens')
        ax1.set_xticks(df_prompt['agent_name'])
        ax1.set_xticklabels(
            ax1.get_xticklabels(),
            rotation=45,         
            ha="right"         
        )
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        ax1.set_yscale('log')
        
        # Plot completion tokens with log y-axis
        ax2.bar(df_completion['agent_name'], df_completion['avg_completion_tokens'], color='green')
        ax2.set_title('Average Completion Tokens per Move (Log Scale)')
        ax2.set_xlabel('Model')
        ax2.set_ylabel('Tokens')
        ax2.set_xticks(df_completion['agent_name'])
        ax2.set_xticklabels(
            ax2.get_xticklabels(),
            rotation=45,         
            ha="right"         
        )
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        ax2.set_yscale('log')
        
        plt.tight_layout()
        plt.show()

    def token_usage_per_puzzle(self):
        """
        Generate subplots showing average token usage per puzzle for each model.
        One subplot for prompt tokens and another for completion tokens.
        Uses a logarithmic y-axis so that models with lower token counts are still visible.
        """
        df = self.db_manager.get_token_usage_per_puzzle_data()
        if df.empty:
            print("No token usage data available per puzzle.")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Sort by token usage for better visualization
        df_prompt = df.sort_values('avg_puzzle_prompt_tokens', ascending=False)
        df_completion = df.sort_values('avg_puzzle_completion_tokens', ascending=False)
        
        # Plot prompt tokens with log y-axis
        ax1.bar(df_prompt['agent_name'], df_prompt['avg_puzzle_prompt_tokens'], color='purple')
        ax1.set_title('Average Prompt Tokens per Puzzle (Log Scale)')
        ax1.set_xlabel('Model')
        ax1.set_ylabel('Tokens')
        ax1.set_xticks(df_prompt['agent_name'])
        ax1.set_xticklabels(
            ax1.get_xticklabels(),
            rotation=45,         
            ha="right"         
        )
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        ax1.set_yscale('log')
        
        # Plot completion tokens with log y-axis
        ax2.bar(df_completion['agent_name'], df_completion['avg_puzzle_completion_tokens'], color='orange')
        ax2.set_title('Average Completion Tokens per Puzzle (Log Scale)')
        ax2.set_xlabel('Model')
        ax2.set_ylabel('Tokens')
        ax2.set_xticks(df_completion['agent_name'])
        ax2.set_xticklabels(
            ax2.get_xticklabels(),
            rotation=45,         
            ha="right"         
        )
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        ax2.set_yscale('log')
        
        plt.tight_layout()
        plt.show()

    def success_percentage_by_theme_rating_bins(self, num_bins: int = 5):
        """
        Generate subplots (one per puzzle type) showing the percentage of successful puzzles 
        by model within puzzle rating bins. For each bin, the displayed value is:
            (success_count / (success_count + failure_count)) * 100.
        Bins are generated using quantile-based binning.
        """
        df = self.db_manager.get_solutionary_moves_data()
        if df.empty:
            print("No moves data available.")
            return

        # Determine success: a puzzle is successful if agent_moves count ≥ expected moves count.
        def is_success(row):
            if pd.isna(row["moves"]) or pd.isna(row["agent_moves"]):
                return False
            expected = row["moves"].strip().split()
            agent_solution = row["agent_moves"].strip().split()
            return len(agent_solution) >= len(expected)
        
        df["success"] = df.apply(is_success, axis=1)

        # Define bins using quantiles from the puzzle ratings.
        ratings = df["puzzle_rating"]
        bin_edges = np.quantile(ratings, np.linspace(0, 1, num_bins + 1))
        bin_edges = np.round(bin_edges).astype(int)
        bins_info = []
        for i in range(num_bins):
            low = bin_edges[i]
            high = bin_edges[i+1]
            label = f"{low}-{high-1}"
            bins_info.append((low, high, label))
        
        # For every puzzle (success or failure), create a record for each bin where its rating ± deviation overlaps.
        records = []
        for _, row in df.iterrows():
            r = row["puzzle_rating"]
            d = row["puzzle_deviation"] if pd.notnull(row["puzzle_deviation"]) else 0
            rmin = r - d
            rmax = r + d
            outcome = "success" if row["success"] else "failure"
            for bin_low, bin_high, label in bins_info:
                if rmin <= bin_high and rmax >= bin_low:
                    records.append({
                        "type": row["type"],
                        "agent_name": row["agent_name"],
                        "bin_label": label,
                        "outcome": outcome
                    })
        
        if not records:
            print("No bin overlaps were found for puzzles.")
            return

        agg_df = pd.DataFrame(records)
        # Group by type, bin, model, and outcome.
        grouped = agg_df.groupby(["type", "bin_label", "agent_name", "outcome"]).size().unstack(fill_value=0).reset_index()
        # Compute success percentage.
        # Sometimes a bin may have only successes or only failures.
        grouped["total"] = grouped.get("success", 0) + grouped.get("failure", 0)
        grouped["success_pct"] = grouped.get("success", 0) / grouped["total"] * 100

        # Create a consistent color mapping for models.
        all_models = sorted(grouped["agent_name"].unique())
        colormap = plt.get_cmap("tab10")
        agent_colors = {model: colormap(i % 10) for i, model in enumerate(all_models)}

        types = grouped["type"].unique()
        num_types = len(types)
        fig, axes = plt.subplots(1, num_types, figsize=(6 * num_types, 5), squeeze=False)
        axes = axes.flatten()

        # Determine bin order based on the numeric lower bound.
        bin_order = sorted(grouped["bin_label"].unique(), key=lambda x: int(x.split("-")[0]))

        # Pivot the data so that rows are bins and columns are models.
        for idx, t in enumerate(types):
            ax = axes[idx]
            type_data = grouped[grouped["type"] == t]
            pivot = type_data.pivot(index="bin_label", columns="agent_name", values="success_pct").reindex(bin_order)
            x = np.arange(len(pivot.index))
            total_width = 0.8
            num_models = len(all_models)
            bar_width = total_width / num_models

            for j, model in enumerate(all_models):
                # Get success percentage for this model; if missing, assume 0.
                percentages = [pivot.at[bin_label, model] if bin_label in pivot.index and model in pivot.columns else 0 for bin_label in bin_order]
                positions = x - total_width/2 + j * bar_width + bar_width/2
                ax.bar(positions, percentages, width=bar_width, label=model if idx == 0 else "", color=agent_colors.get(model))
            
            ax.set_xticks(x)
            ax.set_xticklabels(bin_order, rotation=0)
            ax.set_xlabel("Puzzle Rating Bins")
            ax.set_ylabel("Success Percentage (%)")
            ax.set_title(f"Puzzle Type: {t}")
            ax.set_ylim(0, 100)
            ax.grid(True)
            if idx == 0:
                ax.legend()

        plt.tight_layout()
        plt.show()