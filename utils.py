import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import ast
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Circle, Rectangle, Arc

# ==========================================
#      FONCTIONS UTILITAIRES
# ==========================================
def parse_time(gt_str):
    """Convertit le temps de jeu 'MM:SS' en secondes."""
    try:
        m, s = map(int, gt_str.split(':'))
        return m * 60 + s
    except:
        return 0

def get_date_from_filename(filename):
    """Extrait la date du nom de fichier pour trier chronologiquement."""
    MOIS_FR = {
        'janv': 1, 'févr': 2, 'mars': 3, 'avr': 4, 'mai': 5, 'juin': 6,
        'juil': 7, 'août': 8, 'sept': 9, 'oct': 10, 'nov': 11, 'déc': 12
    }
    parts = filename.replace('.json', '').split('_')
    try:
        day = int(parts[0])
        month = MOIS_FR.get(parts[1].lower(), 1)
        year = int(parts[2])
        return pd.Timestamp(year=year, month=month, day=day)
    except:
        return pd.Timestamp('1900-01-01')

# ==========================================
#      FONCTIONS DE TRAITEMENT DES TIRS
# ==========================================
def draw_fiba_half_court_light(ax=None, color='#333333', lw=1.5, bg_color='#FFFFFF'):
    if ax is None:
        ax = plt.gca()
        
    ax.set_facecolor(bg_color)
    hoop = Circle((0, 1.575), radius=0.225, linewidth=lw, color='#FF5722', fill=False, zorder=3)
    ax.plot([-0.9, 0.9], [1.2, 1.2], color=color, linewidth=lw)
    paint = Rectangle((-2.45, 0), 4.9, 5.8, linewidth=lw, color=color, fill=False)

    free_throw_top = Arc((0, 5.8), 3.6, 3.6, theta1=0, theta2=180, linewidth=lw, color=color)
    free_throw_bottom = Arc((0, 5.8), 3.6, 3.6, theta1=180, theta2=360, linewidth=lw, color=color, linestyle='dashed')

    restricted_area_arc = Arc((0, 1.575), 2.5, 2.5, theta1=0, theta2=180, linewidth=lw, color=color)
    ax.plot([-1.25, -1.25], [1.2, 1.575], color=color, linewidth=lw)
    ax.plot([1.25, 1.25], [1.2, 1.575], color=color, linewidth=lw)

    ax.plot([-6.6, -6.6], [0, 2.99], color=color, linewidth=lw)
    ax.plot([6.6, 6.6], [0, 2.99], color=color, linewidth=lw)
    three_arc = Arc((0, 1.575), 13.5, 13.5, theta1=12.06, theta2=167.94, linewidth=lw, color=color)

    ax.plot([-7.5, 7.5], [14, 14], color=color, linewidth=lw)
    center_circle = Arc((0, 14), 3.6, 3.6, theta1=180, theta2=360, linewidth=lw, color=color)

    ax.plot([-7.5, 7.5], [0, 0], color=color, linewidth=lw)      
    ax.plot([-7.5, -7.5], [0, 14], color=color, linewidth=lw)    
    ax.plot([7.5, 7.5], [0, 14], color=color, linewidth=lw)      

    court_elements = [hoop, paint, free_throw_top, free_throw_bottom, restricted_area_arc, three_arc, center_circle]
    for element in court_elements:
        ax.add_patch(element)

    ax.set_aspect('equal') 
    ax.set_xlim(-8, 8)
    ax.set_ylim(-1, 15)
    ax.axis('off')
    return ax

def convert_to_metric(row):
    x_json, y_json = row['x'], row['y']
    if x_json > 50:
        x_json = 100 - x_json
        y_json = 100 - y_json 
    y_metric = x_json * 0.28 
    x_metric = (y_json - 50) * 0.15 
    return pd.Series([x_metric, y_metric])

def get_zone(row):
    x = row['x_metric']
    y = row['y_metric']
    dist_hoop = np.sqrt(x**2 + (y - 1.575)**2)
    is_3pt = dist_hoop >= 6.75 or (abs(x) >= 6.6 and y <= 2.99)
    is_paint = abs(x) <= 2.45 and y <= 5.8
    
    if is_3pt:
        if y < 2.99: return '3PT Corner Gauche' if x < 0 else '3PT Corner Droit'
        elif x < -2.5: return '3PT Aile Gauche'
        elif x > 2.5: return '3PT Aile Droite'
        else: return '3PT Axe'
    elif is_paint:
        if y < 2.5: return 'Raquette Bas'
        else: return 'Raquette Haut'
    else: 
        if x < -2.45: return 'Mi-dist Gauche'
        elif x > 2.45: return 'Mi-dist Droit'
        else: return 'Mi-dist Axe'

# --- NOUVELLES RÈGLES DE COULEURS ---
def get_color(pct, zone_name):
    """Retourne une couleur en fonction du pourcentage et de la zone (2pts ou 3pts)."""
    if '3PT' in zone_name.upper():
        if pct > 33: return '#c8e6c9' # Vert
        elif pct >= 27: return '#fff9c4' # Jaune
        else: return '#ffcdd2' # Rouge
    else:
        if pct > 49: return '#c8e6c9' # Vert
        elif pct >= 40: return '#fff9c4' # Jaune
        else: return '#ffcdd2' # Rouge

def plot_zone_repartition(df_pbp):
    total_tirs = len(df_pbp)
    if total_tirs == 0:
        fig, ax = plt.subplots()
        ax.axis('off')
        return fig
        
    zone_stats = df_pbp.groupby('Zone_Macro').agg(
        Tirs_Pris=('Action', 'count'), 
        Tirs_Reussis=('Success', 'sum')
    ).reset_index()
    zone_stats['Pourcentage_Repartition'] = (zone_stats['Tirs_Pris'] / total_tirs * 100).round(1)

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('#FFFFFF')
    
    order = ['Raquette (Peinture)', 'Mi-distance', '3 Points']
    order = [z for z in order if z in zone_stats['Zone_Macro'].values]
    
    sns.barplot(data=zone_stats, x='Zone_Macro', y='Tirs_Pris', color='lightgrey', label='Tirs Pris', order=order, ax=ax)
    sns.barplot(data=zone_stats, x='Zone_Macro', y='Tirs_Reussis', color='royalblue', label='Tirs Réussis', order=order, ax=ax)

    ax.set_title("Répartition des Tirs par Zone", fontsize=13, fontweight='bold')
    ax.set_ylabel("Nombre de Tirs")
    ax.set_xlabel("")
    
    for index, row in zone_stats.iterrows():
        x_pos = order.index(row['Zone_Macro'])
        ax.text(x_pos, row['Tirs_Pris'] + max(zone_stats['Tirs_Pris'], default=0)*0.03, 
                 f"{row['Tirs_Reussis']}/{row['Tirs_Pris']}\n({row['Pourcentage_Repartition']}%)", 
                 ha='center', fontsize=10, fontweight='bold')

    ax.legend()
    plt.tight_layout()
    return fig

def plot_zone_ppp(df_pbp):
    if len(df_pbp) == 0:
        fig, ax = plt.subplots()
        ax.axis('off')
        return fig
        
    ppp_stats = df_pbp.groupby('Zone_Macro').agg(
        Tirs_Pris=('Action', 'count'), 
        Points_Totaux=('Points', 'sum')
    ).reset_index()
    
    ppp_stats['PPP'] = (ppp_stats['Points_Totaux'] / ppp_stats['Tirs_Pris']).round(2)

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('#FFFFFF')
    
    order = ['Raquette (Peinture)', 'Mi-distance', '3 Points']
    order = [z for z in order if z in ppp_stats['Zone_Macro'].values]
    
    sns.barplot(data=ppp_stats, x='Zone_Macro', y='PPP', hue='Zone_Macro', palette='viridis', order=order, ax=ax)
    
    ax.set_title("Points par Possession (PPP) par Zone", fontsize=13, fontweight='bold')
    ax.set_ylabel("Points par Possession (PPP)")
    ax.set_xlabel("")
    ax.set_ylim(0, max(ppp_stats['PPP'], default=0) + 0.4)

    for index, row in ppp_stats.iterrows():
        x_pos = order.index(row['Zone_Macro'])
        ax.text(x_pos, row['PPP'] + 0.05, 
                 f"{row['PPP']} PPP\n({row['Points_Totaux']} pts)", 
                 ha='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    return fig

# ==========================================
#      FONCTION DE GRAPHIQUE TEMPO (DONUT)
# ==========================================
def plot_tempo_donut(df_pbp):
    pts_tempo = df_pbp.groupby('Tempo')['Points'].sum().reset_index()
    total_pts = pts_tempo['Points'].sum()
    
    if total_pts == 0:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Aucun point marqué", ha='center', va='center')
        ax.axis('off')
        return fig

    labels = pts_tempo['Tempo']
    sizes = pts_tempo['Points']
    
    colors_dict = {'Demi-terrain': '#2A52BE', 'Transition': '#FF8C00'}
    colors = [colors_dict.get(label, '#999999') for label in labels]
    
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor('#FFFFFF')
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%', startangle=140, 
        colors=colors, wedgeprops=dict(width=0.4, edgecolor='w', linewidth=2),
        textprops=dict(fontsize=12, fontweight='bold', color='#333333')
    )
    
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontsize(11)
    
    ax.text(0, 0, f"Total\n{total_pts} pts", ha='center', va='center', 
            fontsize=16, fontweight='bold', color='#1A1A1A')
    
    plt.title("Répartition des Points : Transition vs Demi-terrain", fontsize=15, fontweight='bold', color='#1A1A1A', pad=15)
    plt.tight_layout()
    
    return fig

# ==========================================
#      FONCTION DE CHARGEMENT DES DONNÉES
# ==========================================
@st.cache_data
def charger_donnees_json(dossier_data, mot_cle_equipe):
    joueurs_data = []
    equipe_data = []
    tous_tirs_cible = [] 
    tous_tirs_pbp = [] 
    global_lineup_stats = {} 
    late_shots_raw = [] 
    shot_clock_raw = []
    
    if not os.path.exists(dossier_data):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    mot_cle_equipe = mot_cle_equipe.upper()
    fichiers = [f for f in os.listdir(dossier_data) if f.endswith('.json')]
    fichiers.sort(key=get_date_from_filename)

    for filename in fichiers:
        filepath = os.path.join(dossier_data, filename)
        match_name = filename.replace('.json', '').replace('_', ' ').title()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        team_cible = None
        team_opp = None
        id_cible = None
        id_opp = None
        
        for t_id, t_data in data['tm'].items():
            if mot_cle_equipe in t_data['name'].upper() or mot_cle_equipe in t_data.get('shortName', '').upper():
                team_cible = t_data
                id_cible = str(t_id)
            else:
                team_opp = t_data
                id_opp = str(t_id)
                
        if not team_cible or not team_opp:
            continue
            
        # 1. Extraction JOUEURS
        for p_id, p_data in team_cible['pl'].items():
            if p_data.get('sMinutes', '0:00') == '0:00':
                continue
            fga = p_data.get('sFieldGoalsAttempted', 0)
            fta = p_data.get('sFreeThrowsAttempted', 0)
            pts = p_data.get('sPoints', 0)
            ts_denom = 2 * (fga + 0.44 * fta)
            ts_pct = (pts / ts_denom * 100) if ts_denom > 0 else 0
            
            joueurs_data.append({
                'Joueur': p_data.get('scoreboardName', p_data.get('name', 'Inconnu')),
                'Pts': pts, '2pt%': p_data.get('sTwoPointersPercentage', 0),
                '2ptA': p_data.get('sTwoPointersAttempted', 0), '3pt%': p_data.get('sThreePointersPercentage', 0),
                '3ptA': p_data.get('sThreePointersAttempted', 0), 'FT%': p_data.get('sFreeThrowsPercentage', 0),
                'FTA': fta, 'Ts%': round(ts_pct, 2), 'Ast': p_data.get('sAssists', 0),
                'Orb': p_data.get('sReboundsOffensive', 0), 'Stl': p_data.get('sSteals', 0),
                'Tov': p_data.get('sTurnovers', 0), 'Eval': p_data.get('eff_1', 0) 
            })
            
        # 2. Extraction ÉQUIPE
        fga_team = team_cible.get('tot_sFieldGoalsAttempted', 0)
        fgm_team = team_cible.get('tot_sFieldGoalsMade', 0)
        fg3m_team = team_cible.get('tot_sThreePointersMade', 0)
        fta_team = team_cible.get('tot_sFreeThrowsAttempted', 0)
        tov_team = team_cible.get('tot_sTurnovers', 0)
        orb_team = team_cible.get('tot_sReboundsOffensive', 0)
        opp_drb = team_opp.get('tot_sReboundsDefensive', 0)
        
        orb_pct = (orb_team / (orb_team + opp_drb) * 100) if (orb_team + opp_drb) > 0 else 0
        tov_pct = (tov_team / (fga_team + 0.44 * fta_team + tov_team) * 100) if (fga_team + 0.44 * fta_team + tov_team) > 0 else 0
        ft_rate = (fta_team / fga_team * 100) if fga_team > 0 else 0
        efg_pct = ((fgm_team + 0.5 * fg3m_team) / fga_team * 100) if fga_team > 0 else 0
        
        equipe_data.append({
            'Match': match_name, 'Points_marques': team_cible.get('score', 0),
            'Points_encaisses': team_opp.get('score', 0), '2p%': team_cible.get('tot_sTwoPointersPercentage', 0),
            '3p%': team_cible.get('tot_sThreePointersPercentage', 0), 'FT%': team_cible.get('tot_sFreeThrowsPercentage', 0),
            'ORB%': round(orb_pct, 2), 'TOV%': round(tov_pct, 2), 'FT_rate': round(ft_rate, 3), 'eFG%': round(efg_pct, 2)
        })

        # 3. Extraction TIRS
        tirs_match = team_cible.get('shot', [])
        for tir in tirs_match:
            tir['Match'] = match_name
        tous_tirs_cible.extend(tirs_match)

        # 4. Extraction PLAY-BY-PLAY
        if 'pbp' in data and id_cible is not None:
            pbp_sorted = sorted(data['pbp'], key=lambda x: x.get('actionNumber', 0))
            
            player_map = {}
            current_lineup_pno = set()
            possession_start_time = None
            shot_clock_max = 24
            
            for pno, p_data in team_cible['pl'].items():
                pno_str = str(pno)
                player_map[pno_str] = p_data.get('scoreboardName') or p_data.get('name') or f"Joueur_{pno_str}"
                if p_data.get('starter') == 1:
                    current_lineup_pno.add(pno_str)
            
            for event in pbp_sorted:
                tno = str(event.get('tno', ''))
                action = event.get('actionType', '')
                sub_type = event.get('subType', '')
                pno_event = str(event.get('pno', ''))
                current_time = parse_time(event.get('gt', '00:00'))
                
                success = 1 if event.get('success') == 1 else 0
                
                # --- A. GESTION DE L'HORLOGE & LATE SHOTS ---
                if action == 'jumpball' and sub_type == 'won' and tno == id_cible:
                    possession_start_time = current_time
                    shot_clock_max = 24
                elif (action == 'turnover' and tno == id_opp) or \
                     (action in ['2pt', '3pt', 'freethrow'] and success == 1 and tno == id_opp):
                    possession_start_time = current_time
                    shot_clock_max = 24
                elif action == 'rebound' and sub_type == 'defensive' and tno == id_cible:
                    possession_start_time = current_time
                    shot_clock_max = 24
                elif action == 'rebound' and isinstance(sub_type, str) and 'offensive' in sub_type.lower() and tno == id_cible:
                    possession_start_time = current_time
                    shot_clock_max = 14
                    
                elif action in ['2pt', '3pt'] and tno == id_cible:
                    if possession_start_time is not None:
                        time_elapsed = possession_start_time - current_time
                        shot_clock_remaining = shot_clock_max - time_elapsed
                        
                        interval = None
                        if 0 <= shot_clock_remaining <= 4: interval = '0-4s'
                        elif 4 < shot_clock_remaining <= 8: interval = '4-8s'
                        elif 8 < shot_clock_remaining <= 12: interval = '8-12s'
                        elif 12 < shot_clock_remaining <= 16: interval = '12-16s'
                        elif 16 < shot_clock_remaining <= 20: interval = '16-20s'
                        elif 20 < shot_clock_remaining <= 24: interval = '20-24s'
                        
                        if interval:
                            shot_clock_raw.append({'Intervalle': interval, 'Action': action, 'Success': success})
                        
                        if 0 <= shot_clock_remaining <= 4:
                            player_name = event.get('player') or player_map.get(pno_event, 'Inconnu')
                            late_shots_raw.append({'Player': player_name, 'Shot Type': action, 'Success': success})
                    
                    possession_start_time = None

                # --- B. TEMPO & MACRO ZONES ---
                if tno == id_cible and action in ['2pt', '3pt']:
                    q = event.get('qualifier', [])
                    if isinstance(q, str):
                        try: q = ast.literal_eval(q)
                        except: q = []
                    elif not isinstance(q, list):
                        q = []
                    tempo = 'Transition' if 'fastbreak' in q else 'Demi-terrain'
                    pts = 0
                    if success == 1:
                        pts = 3 if action == '3pt' else 2
                        
                    if action == '3pt':
                        zone_macro = '3 Points'
                    elif 'pointsinthepaint' in q or (isinstance(sub_type, str) and sub_type in ['layup', 'dunk']):
                        zone_macro = 'Raquette (Peinture)'
                    else:
                        zone_macro = 'Mi-distance'
                        
                    tous_tirs_pbp.append({
                        'Match': match_name,
                        'Tempo': tempo, 
                        'Points': pts,
                        'Action': action,
                        'Success': success,
                        'Zone_Macro': zone_macro
                    })
                
                # --- C. LINEUPS ---
                if action == 'substitution' and tno == id_cible:
                    if not pno_event or pno_event == '0': continue
                    if sub_type == 'in':
                        current_lineup_pno.add(pno_event)
                        if pno_event not in player_map:
                            player_map[pno_event] = event.get('scoreboardName') or event.get('player') or f"Joueur_{pno_event}"
                    elif sub_type == 'out' and pno_event in current_lineup_pno:
                        current_lineup_pno.remove(pno_event)
                    continue
                    
                if len(current_lineup_pno) != 5:
                    continue
                    
                lineup_names = sorted([player_map.get(pid, f"Joueur_{pid}") for pid in current_lineup_pno])
                lineup_key = tuple(lineup_names)
                if lineup_key not in global_lineup_stats:
                    global_lineup_stats[lineup_key] = {
                        "off_fga": 0, "off_tov": 0, "off_last_fta": 0, "off_oreb": 0,
                        "def_fga": 0, "def_tov": 0, "def_last_fta": 0, "def_oreb": 0,
                        "pts_scored": 0, "pts_allowed": 0
                    }
                stats = global_lineup_stats[lineup_key]
                
                points = 0
                if success == 1:
                    if action == '2pt': points = 2
                    elif action == '3pt': points = 3
                    elif action == 'freethrow': points = 1
                    
                if points > 0:
                    if tno == id_cible: stats['pts_scored'] += points
                    elif tno == id_opp: stats['pts_allowed'] += points
                    
                prefix = "off_" if tno == id_cible else "def_" if tno == id_opp else None
                if prefix:
                    if action in ['2pt', '3pt']: stats[prefix + 'fga'] += 1
                    elif action == 'turnover': stats[prefix + 'tov'] += 1
                    elif action == 'freethrow' and sub_type in ['1of1', '2of2', '3of3']: stats[prefix + 'last_fta'] += 1
                    elif action == 'rebound' and isinstance(sub_type, str) and 'offensive' in sub_type.lower(): stats[prefix + 'oreb'] += 1

    results_lineups = []
    for lineup, s in global_lineup_stats.items():
        off_poss = s["off_fga"] + s["off_tov"] + s["off_last_fta"] - s["off_oreb"]
        def_poss = s["def_fga"] + s["def_tov"] + s["def_last_fta"] - s["def_oreb"]
        if off_poss > 0 or def_poss > 0:
            pts_scored = s["pts_scored"]
            pts_allowed = s["pts_allowed"]
            plus_minus = pts_scored - pts_allowed
            off_rtg = (pts_scored / off_poss * 100) if off_poss > 0 else 0
            def_rtg = (pts_allowed / def_poss * 100) if def_poss > 0 else 0
            results_lineups.append({
                "Lineup": ", ".join(lineup), "Off Poss": off_poss, "Def Poss": def_poss,
                "Pts Scored": pts_scored, "Pts Allowed": pts_allowed, "+/-": plus_minus,
                "Off Rtg": round(off_rtg, 1), "Def Rtg": round(def_rtg, 1), "Net Rtg": round(off_rtg - def_rtg, 1)
            })
    df_lineups = pd.DataFrame(results_lineups).sort_values("Off Poss", ascending=False) if results_lineups else pd.DataFrame()

    df_ls_raw = pd.DataFrame(late_shots_raw)
    stats_ls = []
    if not df_ls_raw.empty:
        for player in df_ls_raw['Player'].unique():
            p_df = df_ls_raw[df_ls_raw['Player'] == player]
            f2_made = len(p_df[(p_df['Shot Type'] == '2pt') & (p_df['Success'] == 1)])
            f2_att = len(p_df[p_df['Shot Type'] == '2pt'])
            f3_made = len(p_df[(p_df['Shot Type'] == '3pt') & (p_df['Success'] == 1)])
            f3_att = len(p_df[p_df['Shot Type'] == '3pt'])
            
            pts = (f2_made * 2) + (f3_made * 3)
            tot_att = f2_att + f3_att
            ppp = round(pts / tot_att, 2) if tot_att > 0 else 0
            p2_pct = (f2_made / f2_att * 100) if f2_att > 0 else 0
            p3_pct = (f3_made / f3_att * 100) if f3_att > 0 else 0
            
            stats_ls.append({
                'Joueur': player, 'Pts': pts, 'PPP': ppp, 'Total Tirs (0-4s)': tot_att,
                '2FGM': f2_made, '2FGA': f2_att, '3FGM': f3_made, '3FGA': f3_att,
                '2p%': round(p2_pct, 1), '3p%': round(p3_pct, 1)
            })
    df_late_shots = pd.DataFrame(stats_ls).sort_values(by=['Pts', 'Total Tirs (0-4s)'], ascending=[False, False]) if stats_ls else pd.DataFrame()

    df_sc_raw = pd.DataFrame(shot_clock_raw)
    stats_sc = []
    if not df_sc_raw.empty:
        total_shots_all = len(df_sc_raw)
        intervals = ['20-24s', '16-20s', '12-16s', '8-12s', '4-8s', '0-4s']
        for interval in intervals:
            i_df = df_sc_raw[df_sc_raw['Intervalle'] == interval]
            tot_att = len(i_df)
            if tot_att == 0:
                stats_sc.append({
                    'Temps Restant': interval, 'Tirs Pris': 0, 'Usage Rate (%)': 0.0,
                    'PPP': 0.0, 'eFG%': 0.0
                })
                continue
                
            f2_made = len(i_df[(i_df['Action'] == '2pt') & (i_df['Success'] == 1)])
            f3_made = len(i_df[(i_df['Action'] == '3pt') & (i_df['Success'] == 1)])
            
            pts = (f2_made * 2) + (f3_made * 3)
            ppp = round(pts / tot_att, 2)
            fgm = f2_made + f3_made
            efg_pct = round(((fgm + 0.5 * f3_made) / tot_att) * 100, 1)
            usage_rate = round((tot_att / total_shots_all) * 100, 1)
            
            stats_sc.append({
                'Temps Restant': interval, 'Tirs Pris': tot_att,
                'Usage Rate (%)': usage_rate, 'PPP': ppp, 'eFG%': efg_pct
            })
    df_shot_clock = pd.DataFrame(stats_sc)

    return pd.DataFrame(joueurs_data), pd.DataFrame(equipe_data), pd.DataFrame(tous_tirs_cible), pd.DataFrame(tous_tirs_pbp), df_lineups, df_late_shots, df_shot_clock