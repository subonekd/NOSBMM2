import matplotlib.pyplot as plt
import numpy as np
from ipywidgets import interact, IntSlider, FloatSlider, Checkbox
import random

# --- Skill brackets ---
skill_brackets = {
    'Bottom 10% (≤0.35)': 0.10,
    'Next 10% (0.36–0.55)': 0.10,
    'Middle 50% (0.56–0.92)': 0.50,
    'Top 20% (1.15–2.08)': 0.19,
    'Top 1% (2.08–3.57)': 0.009,
    'Top 0.1% (≥3.57)': 0.001
}
bracket_names = list(skill_brackets.keys())
bracket_default_props = np.array(list(skill_brackets.values()))
rep_kds = [0.25, 0.45, 0.75, 1.5, 2.5, 4.0]
NUM_LOBBY = 150

def kd_to_sweatyness_combo(median, top_mean):
    α = 0.33
    β = 0.67
    composite = α * median + β * top_mean
    # Revised, more realistic mapping to assign "ultra sweaty" only for stacked lobbies
    if composite < 0.8:
        sweat = 1 + (composite-0.1) / 0.7 * 2
    elif composite < 1.1:
        sweat = 3 + (composite-0.8)/0.3*3
    elif composite < 1.5:
        sweat = 6 + (composite-1.1)/0.4*2
    elif composite < 2.0:
        sweat = 8 + (composite-1.5)/0.5*2
    else:
        sweat = 10
    sweat = float(np.clip(round(sweat, 1), 1, 10))
    return sweat, composite

def sweat_rating_emoji(sweat):
    if sweat < 4:
        return "😎 Chill"
    elif sweat < 7:
        return "🙂 Normal"
    elif sweat < 9:
        return "😰 Sweaty"
    else:
        return "🔥 Ultra Sweaty!"

def get_sweat_score(all_kds, top_n=10):
    kds = np.array(all_kds)
    if len(kds) == 0:
        return 1, 0, 0, 0  # No players
    median = np.median(kds)
    topk = np.sort(kds)[-top_n:] if len(kds) >= top_n else kds
    top_mean = np.mean(topk)
    sweat, composite = kd_to_sweatyness_combo(median, top_mean)
    return sweat, composite, median, top_mean

def simulate_lobby(
    num_bots=0, 
    churn_level=0, 
    advanced_churn=False, 
    kd_churn_cutoff=0.85
):
    random.seed(42)
    np.random.seed(42)
    num_humans = NUM_LOBBY - num_bots

    # --- Apply chosen churn logic ---
    if advanced_churn:
        # Remove all brackets with median K/D < cutoff
        keep_mask = np.array([k >= kd_churn_cutoff for k in rep_kds])
        prop_used = bracket_default_props * keep_mask
        total_prop = prop_used.sum()
        if total_prop == 0:
            # Failsafe: if all are churned, put everyone in the hardest bracket
            prop_used = np.zeros_like(bracket_default_props)
            prop_used[-1] = 1.0
        else:
            prop_used /= total_prop
        churn_desc = f"Churn ALL under {kd_churn_cutoff:.2f} K/D"
    else:
        prop_used = bracket_default_props.copy()
        prop_used[0] *= (1 - churn_level)
        prop_used[1] *= (1 - churn_level)
        prop_used /= prop_used.sum()
        churn_desc = f"Churn {churn_level*100:.0f}% of lowest 20%"

    # --- Proper multinomial sampling for humans ---
    humans_per_bracket = np.random.multinomial(num_humans, prop_used)

    # --- Generate K/Ds ---
    human_kds = []
    for count, med_kd in zip(humans_per_bracket, rep_kds):
        kd_samples = np.random.normal(loc=med_kd, scale=0.05, size=count)
        human_kds += list(np.clip(kd_samples, 0.05, None))
    bot_kds = [random.uniform(0.1, 0.6) for _ in range(num_bots)]

    # --- Compute new SWEAT score ---
    all_kds = human_kds + bot_kds
    sweat, composite, median_all_kd, top10_all_kd = get_sweat_score(all_kds, top_n=10)
    sweat_visual = sweat_rating_emoji(sweat)

    # --- Plot bar chart of humans per bracket ---
    bracket_colors = ['powderblue', 'cyan', 'gray', 'red', 'purple', 'black']
    fig, ax = plt.subplots(figsize=(10,5))
    bars = ax.bar(range(len(bracket_names)), humans_per_bracket, color=bracket_colors, width=0.7)
    plt.xticks(range(len(bracket_names)), bracket_names, rotation=30, ha='right')
    ax.set_ylabel("Players in Bracket (per Lobby)")
    ax.set_title(
        f"Bots: {num_bots}, Humans: {num_humans} ({churn_desc})"
    )
    plt.subplots_adjust(bottom=0.38)
    plt.show()

    # --- Print summary below plot ---
    expected_counts = num_humans * prop_used  # For stat reporting only
    pct = humans_per_bracket / num_humans * 100 if num_humans>0 else np.zeros(len(humans_per_bracket))
    lines = []
    for k, exp, actual, p in zip(bracket_names, expected_counts, humans_per_bracket, pct):
        lines.append(f"{k:<25}: {exp:5.2f} exp, {actual:3d} actual ({p:4.1f}%)")
    lines.append("")
    lines.append(f"Top 1% humans per lobby : ~{expected_counts[-2]:.2f}")
    lines.append(f"Top 0.1% humans per lobby: ~{expected_counts[-1]:.2f}")
    lines.append("")
    lines.append(f"SWEATYNESS (1-10): {sweat:.1f}   |   Sweat Rating: {sweat_visual}")
    lines.append(f"Composite (weighted): {composite:.2f}")
    lines.append(f"Median K/D (all): {median_all_kd:.2f}")
    lines.append(f"Mean K/D (top 10): {top10_all_kd:.2f}")
    if human_kds:
        median_human_kd = np.median(human_kds)
        lines.append(f"  (Median K/D, humans only): {median_human_kd:.2f}")
    lines.append(f"Bots: {num_bots} (K/D 0.1–0.6)")
    lines.append(f"Humans: {num_humans}")
    print('\n'.join(lines))

# ---------- Interactive widget ----------
interact(
    simulate_lobby,
    num_bots=IntSlider(min=0, max=140, step=10, value=0, description="Number of Bots"),
    churn_level=FloatSlider(min=0, max=1, step=0.05, value=0, description="% Churn Low Skill"),
    advanced_churn=Checkbox(value=False, description="Churn all < K/D"),
    kd_churn_cutoff=FloatSlider(min=0.1, max=2.0, step=0.05, value=0.85, description="K/D Churn Cutoff"),
);