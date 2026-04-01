import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Importation de toutes tes fonctions depuis utils.py
from utils import (
    draw_fiba_half_court_light, 
    convert_to_metric, 
    get_zone, 
    get_color, 
    charger_donnees_json,
    plot_tempo_donut,
    plot_zone_repartition,
    plot_zone_ppp
)

st.set_page_config(layout="wide")

if 'page' not in st.session_state:
    st.session_state.page = 'accueil'

def changer_page(nouvelle_page):
    st.session_state.page = nouvelle_page

# ==========================================
#             PAGE D'ACCUEIL
# ==========================================
if st.session_state.page == 'accueil':
    st.markdown("<h1 style='text-align: center;'>Outil d'analyse - Toulouse Basketball Club</h1>", unsafe_allow_html=True)

    st.write("Application démo par Arthur Frindel")
    st.write("Toutes les données présentées datent du 25/03/2026")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.button("Analyse de notre équipe", on_click=changer_page, args=('option1',))
    with col2:
        st.button("Analyse du prochain adversaire", on_click=changer_page, args=('option2',))
    with col3:
        st.button("Scouting joueurs", on_click=changer_page, args=('option3',))

    # 2. Ajout du logo APRÈS les options
    st.divider() # Optionnel : ajoute une ligne de séparation pour plus de clarté
    
    # On utilise à nouveau des colonnes pour centrer le logo sous les boutons
    col_logo_g, col_logo_c, col_logo_d = st.columns([1, 1, 1])
    with col_logo_c:
        st.image("logo_toulouse_2.png", use_container_width=True)

# ==========================================
#             PAGE OPTION 1 : ANALYSE TOULOUSE
# ==========================================
elif st.session_state.page == 'option1':
    st.title("Analyse de notre équipe")
    st.button("⬅️ Retour à l'accueil", on_click=changer_page, args=('accueil',))
    st.divider()
    
    df_joueurs, df_equipe, df_shots, df_pbp, df_lineups, df_late_shots, df_shot_clock = charger_donnees_json('toulouse_data', 'TOULOUSE')
    
    if df_joueurs.empty and df_equipe.empty:
        st.warning("⚠️ Dossier `toulouse_data` introuvable ou vide. Assurez-vous que le dossier contenant les JSON est au même niveau que `app.py`.")
    else:
        tab_stats, tab_shotmap, tab_tempo, tab_shot_clock, tab_lineups, tab_late_shots = st.tabs([
            "Statistiques générales", "Shotmap & zones de tirs", "Analyse du pace", "Gestion de l'horloge", "Analyse des lineups", "Tirs en fin de possession"
        ])
        
        with tab_stats:
            st.subheader("Statistiques de l'Équipe")

            subtab1, subtab2 = st.tabs(["Moyennes Globales", "Par Match"])
            with subtab1:
                df_equipe_group = df_equipe.drop(columns=['Match']).mean().round(2)
                st.dataframe(pd.DataFrame(df_equipe_group, columns=['Moyenne']), width='stretch')
                
            with subtab2:
                st.dataframe(df_equipe, width='stretch', hide_index=True)

            st.divider()

            st.subheader("Statistiques Moyennes des Joueurs")
            df_joueurs_group = df_joueurs.groupby(["Joueur"]).mean().round(2).sort_values(by=["Eval"], ascending=False)
            st.dataframe(df_joueurs_group, width='stretch')
            
        with tab_shotmap:
            st.subheader("Shotmap (5 Derniers Matchs)")
            if df_shots.empty or df_equipe.empty:
                st.info("Aucune donnée de tir disponible.")
            else:
                derniers_matchs = df_equipe['Match'].tail(5).tolist()
                st.write("**La carte des tirs ci-dessous est basée sur les matchs suivants :**")
                for m in derniers_matchs: st.write(f"- {m}")
                    
                df_shots_recent = df_shots[df_shots['Match'].isin(derniers_matchs)].copy()
                if df_shots_recent.empty:
                    st.warning("Aucun tir répertorié sur les 5 derniers matchs.")
                else:
                    with st.spinner("Génération de la shotmap..."):
                        df_shots_recent[['x_metric', 'y_metric']] = df_shots_recent.apply(convert_to_metric, axis=1)
                        df_shots_recent['zone'] = df_shots_recent.apply(get_zone, axis=1)

                        zone_stats = df_shots_recent.groupby('zone').agg(
                            Fait=('r', 'sum'), Total=('r', 'count')
                        ).reset_index()
                        zone_stats['Pourcentage'] = (zone_stats['Fait'] / zone_stats['Total'] * 100).round().fillna(0).astype(int)

                        zone_coords = {
                            '3PT Corner Gauche': (-7, 1.5), '3PT Corner Droit': (7, 1.5),
                            '3PT Aile Gauche': (-5.5, 6), '3PT Aile Droite': (5.5, 6),
                            '3PT Axe': (0, 8.5), 'Raquette Bas': (0, 1.5),
                            'Raquette Haut': (0, 4.5), 'Mi-dist Gauche': (-4, 3),
                            'Mi-dist Droit': (4, 3), 'Mi-dist Axe': (0, 6.5)
                        }

                        fig, ax = plt.subplots(figsize=(10, 9))
                        fig.patch.set_facecolor('#FFFFFF')
                        draw_fiba_half_court_light(ax)

                        for _, row in zone_stats.iterrows():
                            zone_name = row['zone']
                            if zone_name in zone_coords:
                                x_coord, y_coord = zone_coords[zone_name]
                                pct = row['Pourcentage']
                                text = f"{row['Fait']}/{row['Total']}\n{pct}%"
                                # APPEL MIS A JOUR
                                ax.text(x_coord, y_coord, text, ha='center', va='center', fontsize=10, fontweight='bold',
                                        bbox=dict(facecolor=get_color(pct, zone_name), edgecolor='black', boxstyle='round,pad=0.5', alpha=0.9))

                        #plt.title("SHOT BREAKDOWN - TOULOUSE (5 DERNIERS MATCHS)", fontsize=18, fontweight='bold', color='#1A1A1A', pad=10)
                        plt.tight_layout()
                        
                        col_shotmap, _ = st.columns([2, 1])
                        with col_shotmap: st.pyplot(fig)
                        
                st.divider()
                st.subheader("Répartition et Efficacité par Macro-Zone (Toute la Saison)")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    fig_repartition = plot_zone_repartition(df_pbp)
                    st.pyplot(fig_repartition)
                with col_g2:
                    fig_ppp = plot_zone_ppp(df_pbp)
                    st.pyplot(fig_ppp)

        with tab_tempo:
            #st.subheader("Rythme de jeu : Répartition des Points (Toulouse)")
            if df_pbp.empty:
                st.info("Aucune donnée Play-by-Play trouvée pour analyser le rythme.")
            else:
                with st.spinner("Génération du graphique de rythme..."):
                    fig_tempo = plot_tempo_donut(df_pbp)
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2: st.pyplot(fig_tempo)

        with tab_shot_clock:
            st.subheader("Gestion des possessions (Temps restant à l'horloge)")
            st.write("Analyse de l'efficacité et du volume de tirs en fonction du temps restant à l'horloge de tir.")
            if df_shot_clock.empty:
                st.info("Aucune donnée d'horloge trouvée.")
            else:
                styled_sc = df_shot_clock.style.background_gradient(
                    subset=['Usage Rate (%)'], cmap='Blues'
                ).background_gradient(
                    subset=['PPP', 'eFG%'], cmap='RdYlGn', vmin=0
                ).format(precision=1)
                st.dataframe(styled_sc, width='stretch', hide_index=True)

        with tab_lineups:
            st.subheader("Efficacité des lienups")
            #st.write("Le **Net Rating** représente la différence entre l'efficacité offensive et défensive sur 100 possessions.")
            if df_lineups.empty:
                st.info("Aucune donnée Lineup trouvée.")
            else:
                with st.form(key="form_toulouse_lineup"):
                    min_poss = st.slider("Filtre : Nombre minimum de possessions offensives", 
                                         min_value=1, max_value=int(df_lineups['Off Poss'].max()), value=10)
                    st.form_submit_button("Appliquer le filtre")
                
                df_lineups_filtered = df_lineups[df_lineups['Off Poss'] >= min_poss].copy()
                if df_lineups_filtered.empty:
                    st.warning("Aucun 5 majeur ne correspond à ce filtre.")
                else:
                    styled_df = df_lineups_filtered.style.background_gradient(
                        subset=['Net Rtg', '+/-'], cmap='RdYlGn', vmax=30, vmin=-30
                    ).format(precision=1)
                    st.dataframe(styled_df, height=500, width='stretch', hide_index=True)

        with tab_late_shots:
            st.subheader("Tirs en fin de possession (0-4 secondes)")
            st.write("Analyse des tirs pris en fin de possessions")
            if df_late_shots.empty:
                st.info("Aucune donnée trouvée pour les fins de possession.")
            else:
                styled_late_shots = df_late_shots.style.background_gradient(
                    subset=['Pts'], cmap='Oranges'
                ).background_gradient(
                    subset=['PPP'], cmap='RdYlGn', vmin=0, vmax=2
                ).format(precision=1)
                st.dataframe(styled_late_shots, width='stretch', hide_index=True)


# ==========================================
#             PAGE OPTION 2 : ANALYSE ÉQUIPE (BOULOGNE)
# ==========================================
elif st.session_state.page == 'option2':
    st.title("Analyse du prochain adversaire : Boulogne-sur-Mer")
    st.write("Seules les données des 5 derniers matchs sont prises en compte")
    st.button("⬅️ Retour à l'accueil", on_click=changer_page, args=('accueil',))
    st.divider()
    
    df_joueurs, df_equipe, df_shots, df_pbp, df_lineups, df_late_shots, df_shot_clock = charger_donnees_json('boulogne_mer_data', 'BOULOGNE')
    
    if df_joueurs.empty and df_equipe.empty:
        st.warning("⚠️ Dossier `boulogne_mer_data` introuvable ou vide.")
    else:
        tab_stats, tab_shotmap, tab_tempo, tab_shot_clock, tab_lineups, tab_late_shots = st.tabs([
            "Statistiques générales", "Shotmap & zones de tirs", "Analyse du pace", "Gestion de l'horloge", "Analyse des lineups", "Tirs en fin de possession"
        ])
        
        with tab_stats:
            st.subheader("Statistiques de l'Équipe")

            subtab1, subtab2 = st.tabs(["Moyennes Globales", "Par Match"])
            with subtab1:
                df_equipe_group = df_equipe.drop(columns=['Match']).mean().round(2)
                st.dataframe(pd.DataFrame(df_equipe_group, columns=['Moyenne']), width='stretch')
                
            with subtab2:
                st.dataframe(df_equipe, width='stretch', hide_index=True)

            st.divider()

            st.subheader("Statistiques Moyennes des Joueurs")
            df_joueurs_group = df_joueurs.groupby(["Joueur"]).mean().round(2).sort_values(by=["Eval"], ascending=False)
            st.dataframe(df_joueurs_group, width='stretch')
        
        with tab_shotmap:
            st.subheader("Shotmap (5 Derniers Matchs)")
            if df_shots.empty or df_equipe.empty:
                st.info("Aucune donnée de tir disponible pour générer la shotmap.")
            else:
                derniers_matchs = df_equipe['Match'].tail(5).tolist()
                st.write("**Analyse basée sur les matchs suivants :**")
                for m in derniers_matchs: st.write(f"- {m}")
                    
                df_shots_recent = df_shots[df_shots['Match'].isin(derniers_matchs)].copy()
                if df_shots_recent.empty:
                    st.warning("Aucun tir répertorié sur les 5 derniers matchs.")
                else:
                    with st.spinner("Génération des visuels..."):
                        df_shots_recent[['x_metric', 'y_metric']] = df_shots_recent.apply(convert_to_metric, axis=1)
                        df_shots_recent['zone'] = df_shots_recent.apply(get_zone, axis=1)

                        zone_stats = df_shots_recent.groupby('zone').agg(
                            Fait=('r', 'sum'), Total=('r', 'count')
                        ).reset_index()
                        zone_stats['Pourcentage'] = (zone_stats['Fait'] / zone_stats['Total'] * 100).round().fillna(0).astype(int)

                        zone_coords = {
                            '3PT Corner Gauche': (-7, 1.5), '3PT Corner Droit': (7, 1.5),
                            '3PT Aile Gauche': (-5.5, 6), '3PT Aile Droite': (5.5, 6),
                            '3PT Axe': (0, 8.5), 'Raquette Bas': (0, 1.5),
                            'Raquette Haut': (0, 4.5), 'Mi-dist Gauche': (-4, 3),
                            'Mi-dist Droit': (4, 3), 'Mi-dist Axe': (0, 6.5)
                        }

                        fig, ax = plt.subplots(figsize=(10, 9))
                        fig.patch.set_facecolor('#FFFFFF')
                        draw_fiba_half_court_light(ax)

                        for _, row in zone_stats.iterrows():
                            zone_name = row['zone']
                            if zone_name in zone_coords:
                                x_coord, y_coord = zone_coords[zone_name]
                                pct = row['Pourcentage']
                                text = f"{row['Fait']}/{row['Total']}\n{pct}%"
                                # APPEL MIS A JOUR
                                ax.text(x_coord, y_coord, text, ha='center', va='center', fontsize=10, fontweight='bold',
                                        bbox=dict(facecolor=get_color(pct, zone_name), edgecolor='black', boxstyle='round,pad=0.5', alpha=0.9))

                        #plt.title("SHOT BREAKDOWN - BOULOGNE (5 DERNIERS MATCHS)", fontsize=18, fontweight='bold', color='#1A1A1A', pad=10)
                        plt.tight_layout()
                        
                        col_shotmap, _ = st.columns([2, 1])
                        with col_shotmap:
                            st.pyplot(fig)
                        
                        st.divider()
                        
                        st.subheader("Répartition et Efficacité par Macro-Zone")
                        col_g1, col_g2 = st.columns(2)
                        with col_g1:
                            fig_repartition = plot_zone_repartition(df_pbp)
                            st.pyplot(fig_repartition)
                        with col_g2:
                            fig_ppp = plot_zone_ppp(df_pbp)
                            st.pyplot(fig_ppp)

        with tab_tempo:
            #st.subheader("⚡ Rythme de jeu : Répartition des Points")
            if df_pbp.empty:
                st.info("Aucune donnée Play-by-Play trouvée pour analyser le rythme.")
            else:
                with st.spinner("Génération du graphique de rythme..."):
                    fig_tempo = plot_tempo_donut(df_pbp)
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2: st.pyplot(fig_tempo)

        with tab_shot_clock:
            st.subheader("Gestion des possessions (Temps restant à l'horloge)")
            st.write("Analyse de l'efficacité et du volume de tirs en fonction du temps restant à l'horloge de tir.")
            if df_shot_clock.empty:
                st.info("Aucune donnée d'horloge trouvée.")
            else:
                styled_sc = df_shot_clock.style.background_gradient(
                    subset=['Usage Rate (%)'], cmap='Blues'
                ).background_gradient(
                    subset=['PPP', 'eFG%'], cmap='RdYlGn', vmin=0
                ).format(precision=1)
                st.dataframe(styled_sc, width='stretch', hide_index=True)

        with tab_lineups:
            st.subheader("Efficacité des lienups")
            #st.write("Le **Net Rating** représente la différence entre l'efficacité offensive et défensive sur 100 possessions.")
            if df_lineups.empty:
                st.info("Aucune donnée Lineup trouvée.")
            else:
                with st.form(key="form_boulogne_lineup"):
                    min_poss = st.slider("Filtre : Nombre minimum de possessions offensives", 
                                         min_value=1, max_value=int(df_lineups['Off Poss'].max()), value=10)
                    st.form_submit_button("Appliquer le filtre")
                
                df_lineups_filtered = df_lineups[df_lineups['Off Poss'] >= min_poss].copy()
                if df_lineups_filtered.empty:
                    st.warning("Aucun 5 majeur ne correspond à ce filtre.")
                else:
                    styled_df = df_lineups_filtered.style.background_gradient(
                        subset=['Net Rtg', '+/-'], cmap='RdYlGn', vmax=30, vmin=-30
                    ).format(precision=1)
                    st.dataframe(styled_df, height=500, width='stretch', hide_index=True)

        with tab_late_shots:
            st.subheader("Tirs en fin de possession (0-4 secondes)")
            st.write("Analyse des tirs pris en fin de possessions")
            if df_late_shots.empty:
                st.info("Aucune donnée trouvée pour les fins de possession.")
            else:
                styled_late_shots = df_late_shots.style.background_gradient(
                    subset=['Pts'], cmap='Oranges'
                ).background_gradient(
                    subset=['PPP'], cmap='RdYlGn', vmin=0, vmax=2
                ).format(precision=1)
                st.dataframe(styled_late_shots, width='stretch', hide_index=True)

# ==========================================
#             PAGE OPTION 3 : SCOUTING BASKET
# ==========================================
elif st.session_state.page == 'option3':
    st.title("Scouting de Joueurs")
    st.button("⬅️ Retour à l'accueil", on_click=changer_page, args=('accueil',))
    st.divider()
    
    st.write("Sélectionnez le championnat que vous souhaitez analyser pour afficher les statistiques des joueurs.")

    championnat_choisi = st.selectbox("Choisissez un championnat :", ("Nationale 1", "Betclic Elite Espoirs 2"))

    if championnat_choisi == "Nationale 1":
        fichier_csv = "moyennes_joueurs_nm1_25_03_2026.csv" 
    else:
        fichier_csv = "moyennes_joueurs_espoir_elite2_25_03_2026.csv"

    try:
        df_scouting = pd.read_csv(fichier_csv) 
        df_scouting.columns = df_scouting.columns.str.strip()
        
        colonnes_stats = ["MJ", "Min", "Pts", "Reb", "As", "Ro", "Rd", "2P%", "3P%", "TIRS%", "LF%", "TS%", "St", "Bl", "To", "Fo", "Plus_Minus", "Eval"]
        
        for stat in colonnes_stats:
            if stat in df_scouting.columns:
                df_scouting[stat] = df_scouting[stat].astype(str).str.replace(',', '.', regex=False).str.replace('%', '', regex=False)
                df_scouting[stat] = pd.to_numeric(df_scouting[stat], errors='coerce').fillna(0)

        st.success(f"Données chargées pour : **{championnat_choisi}**")
        
        with st.expander("Filtres avancés (Statistiques minimales)"):
            st.write("Indiquez les valeurs minimales souhaitées pour filtrer les joueurs :")
            if 'Matchs' in df_scouting.columns:
                min_matchs = st.number_input("Minimum de Matchs joués", min_value=0, value=10, step=1)
                df_scouting = df_scouting[df_scouting['Matchs'] >= min_matchs]
            
            st.divider() 
            cols = st.columns(4)
            for i, stat in enumerate(colonnes_stats):
                if stat in df_scouting.columns:
                    with cols[i % 4]:
                        val_min = st.number_input(f"Min {stat}", value=0.0, step=1.0)
                        df_scouting = df_scouting[df_scouting[stat] >= val_min]

        st.caption(f"Nombre de joueurs correspondants à ces critères : **{len(df_scouting)}**")
        st.dataframe(df_scouting, width='stretch', hide_index=True)

    except FileNotFoundError:
        st.error(f"⚠️ Impossible de trouver le fichier `{fichier_csv}`.")