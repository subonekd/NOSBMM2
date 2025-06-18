import matplotlib.pyplot as plt
import numpy as np
from ipywidgets import interact, IntSlider, FloatSlider, Checkbox
import random

# Skill buckets with more granular middle and high splits
skill_brackets = {
    'Bottom 10% (≤0.35)': 0.10,
    'Next 10% (0.36–0.74)': 0.10,
    'Lower Middle 35% (0.75–0.92)': 0.35,
    'Upper Middle 15% (0.93–1.14)': 0.15,
    'High 13% (1.15–1.49)': 0.13,
    'Very High 6% (1.50–2.08)': 0.06,
    'Top 1% (2.08–3.57)': 0.009,
    'Top 0.1% (≥3.57)': 0.001
}
rep_kds = [0.25, 0.45, 0.7, 0.88, 1.3, 1.7, 2.5, 4.0]
bracket_names = list(skill_brackets.keys())
bracket_default_props = np.array(list(skill_brackets.values()))
NUM_LOBBY = 150

def sweat_rating_emoji(sweat):
    if sweat < 4:
        return "😎 Chill"
    elif sweat < 6.5:
        return "🙂 Normal"
    elif sweat < 7:
        return "😰 Sweaty"
    else:
        return "🔥 Ultra Sweaty!"

def kd_to_sweatyness_combo(median_ignore, composite, *args):
    kd = float(composite)
    # Mapping: Center a typical lobby around sweat=6, with headroom above
    breakpoints = [0.3, 0.84, 1.0, 1.2, 1.5, 3.0]
    sweats      = [  3,   4,   4, 4.25,   6,  10]
    sweat = np.interp(kd, breakpoints, sweats)
    return float(np.clip(round(sweat, 1), 1, 10)), composite

def get_sweat_score(all_kds, top_n=5):
    kds = np.array(all_kds)
    if len(kds) == 0:
        return 1, 0, 0, 0
    median = np.median(kds)
    topk = np.sort(kds)[-top_n:] if len(kds) >= top_n else kds
    top_mean = np.mean(topk)
    composite = 0.25 * median + 0.75 * top_mean
    sweat, _ = kd_to_sweatyness_combo(0, composite, 0)
    return sweat, composite, median, top_mean

def simulate_lobby(
    num_bots=0,
    churn_level=0,
    advanced_churn=False,
    kd_churn_cutoff=0.85,
    num_repeats=20
):
    sweat_scores = []
    composites = []
    medians = []
    top_means = []
    all_humans_per_bracket = []
    all_medians_humans = []

    for repeat in range(num_repeats):
        np.random.seed()
        random.seed()
        num_humans = NUM_LOBBY - num_bots

        if advanced_churn:
            # Hard cutoff: only keep brackets with rep_kds >= cutoff
            keep_mask = np.array([k >= kd_churn_cutoff for k in rep_kds])
            prop_used = bracket_default_props * keep_mask
            total_prop = prop_used.sum()
            if total_prop == 0:
                prop_used = np.zeros_like(bracket_default_props)
                prop_used[-1] = 1.0
            else:
                prop_used /= total_prop
            churn_desc = f"Churn ALL under {kd_churn_cutoff:.2f} K/D"
        else:
            # Soft churn: remove % of each bracket with rep_kd below or equal to cutoff
            prop_used = bracket_default_props.copy()
            for i, bk in enumerate(rep_kds):
                if bk <= kd_churn_cutoff:
                    prop_used[i] *= (1 - churn_level)
            prop_used /= prop_used.sum()
            churn_desc = (
                f"Churn {churn_level*100:.0f}% of brackets with K/D ≤ {kd_churn_cutoff:.2f}"
            )

        humans_per_bracket = np.random.multinomial(num_humans, prop_used)
        human_kds = []
        for count, med_kd in zip(humans_per_bracket, rep_kds):
            kd_samples = np.random.normal(loc=med_kd, scale=0.05, size=count)
            human_kds += list(np.clip(kd_samples, 0.05, None))
        bot_kds = [random.uniform(0.1, 0.6) for _ in range(num_bots)]
        all_kds = human_kds + bot_kds
        sweat, composite, median_all_kd, topN_all_kd = get_sweat_score(all_kds, top_n=5)
        sweat_scores.append(sweat)
        composites.append(composite)
        medians.append(median_all_kd)
        top_means.append(topN_all_kd)
        all_humans_per_bracket.append(humans_per_bracket)
        if human_kds:
            all_medians_humans.append(np.median(human_kds))

    # Show mean ± std
    avg_humans_per_bracket = np.mean(np.stack(all_humans_per_bracket), axis=0)
    avg_exp_counts = num_humans * prop_used
    pct = avg_humans_per_bracket / num_humans * 100 if num_humans > 0 else np.zeros(len(avg_humans_per_bracket))
    composite_avg = np.mean(composites)
    sweat_avg, _ = kd_to_sweatyness_combo(0, composite_avg, 0)
    sweat_visual = sweat_rating_emoji(sweat_avg)
    composite_std = np.std(composites)
    median_avg = np.mean(medians)
    topN_mean_avg = np.mean(top_means)
    median_human_avg = np.mean(all_medians_humans) if all_medians_humans else 0

       # Define bracket colors list if not defined already
    bracket_colors = ['powderblue', 'cyan', 'lightgray', 'gray', 'gold', 'salmon', 'red', 'black']

    # All bots go into the lowest skill bracket (or customize as needed)
    bot_bracket_counts = np.zeros(len(bracket_names), dtype=int)
    share_0 = int(num_bots * 0.5)
    share_1 = num_bots - share_0
    bot_bracket_counts[0] = share_0
    bot_bracket_counts[1] = share_1

    fig, ax = plt.subplots(figsize=(13,5))
    bars_humans = ax.bar(
        range(len(bracket_names)), avg_humans_per_bracket, 
        color=bracket_colors, width=0.7, label="Humans"
    )
    bars_bots = ax.bar(
        range(len(bracket_names)), bot_bracket_counts, 
        color="limegreen", width=0.7,
        bottom=avg_humans_per_bracket, label="Bots"
    )
    ax.legend()
    plt.xticks(range(len(bracket_names)), bracket_names, rotation=30, ha='right')
    ax.set_ylabel(f"Avg Players in Bracket (mean of {num_repeats} runs)")
    ax.set_title(
        f"Bots: {num_bots}, Humans: {num_humans} ({churn_desc})"
    )
    plt.subplots_adjust(bottom=0.42)
    plt.show()

    lines = []
    for k, exp, actual, p in zip(bracket_names, avg_exp_counts, avg_humans_per_bracket, pct):
        lines.append(f"{k:<30}: {exp:5.2f} exp, {actual:5.2f} avg ({p:4.1f}%)")
    lines.append("")
    lines.append(f"Top 1% humans per lobby : ~{avg_exp_counts[-2]:.2f}")
    lines.append(f"Top 0.1% humans per lobby: ~{avg_exp_counts[-1]:.2f}")
    lines.append("")
    lines.append(f"SWEATYNESS (1-10): {sweat_avg:.2f}   |   Sweat Rating: {sweat_visual}")
    lines.append(f"Composite (weighted):   {composite_avg:.2f} ± {composite_std:.2f}")
    lines.append(f"Median K/D (all):       {median_avg:.2f}")
    lines.append(f"Mean K/D (top 5):       {topN_mean_avg:.2f}")
    if all_medians_humans:
        lines.append(f"Median K/D, humans only: {median_human_avg:.2f}")
    lines.append(f"Bots: {num_bots} (K/D 0.1–0.6)")
    lines.append(f"Humans: {num_humans}")
    print('\n'.join(lines))

interact(
    simulate_lobby,
    num_bots=IntSlider(min=0, max=140, step=10, value=0, description="Number of Bots"),
    churn_level=FloatSlider(min=0, max=1, step=0.05, value=0, description="% Churn Low Skill"),
    advanced_churn=Checkbox(value=False, description="Churn all < K/D"),
    kd_churn_cutoff=FloatSlider(min=0.1, max=2.0, step=0.05, value=0.85, description="K/D Churn Cutoff"),
    num_repeats=IntSlider(min=1, max=100, step=1, value=20, description="Runs to Avg")
)
