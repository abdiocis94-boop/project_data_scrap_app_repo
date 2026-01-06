

# app.py
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import numpy as np
import io
import json
import time

# Configuration de la page
st.set_page_config(
    page_title="CoinAfrique Scraper",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des variables de session
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None
if 'cleaned_data' not in st.session_state:
    st.session_state.cleaned_data = None
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None

# ============================================
# SECTION 1: FONCTIONS DE SCRAPING
# ============================================

@st.cache_data(show_spinner=False)
def scraping_coin_afrique(url, pages=5):
    """
    Scrape les données de CoinAfrique pour une catégorie spécifique
    """
    df = pd.DataFrame()
    
    for index_page in range(1, pages + 1):
        page_url = f'{url}?page={index_page}'
        
        try:
            # récupération de la page en url
            res = requests.get(page_url, timeout=10)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.content, 'html.parser')
            
            # récupération des conteneurs
            containers = soup.find_all('div', 'col s6 m4 l3')
            
            if not containers:
                st.warning(f"Aucun contenu trouvé sur la page {index_page}")
                break
            
            data = []
            for container in containers:
                try:
                    # Extraction des données
                    type_habit = container.find('p', 'ad__card-description').a.text.strip()
                    prix_text = container.find('p', 'ad__card-price').a.text.strip()
                    prix = prix_text.replace('CFA', '').replace(' ', '').strip()
                    adresse = container.find('p', 'ad__card-location').span.text.strip()
                    image = container.find('img', 'ad__card-img')['src']
                    
                    # URL de l'annonce
                    annonce_url = 'https://sn.coinafrique.com' + container.find('a')['href']
                    
                    dic = {
                        "type": type_habit,
                        "prix_texte": prix_text,
                        "prix_numerique": prix,
                        "adresse": adresse,
                        "image_url": image,
                        "annonce_url": annonce_url,
                        "page_scrapee": index_page,
                        "date_scraping": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "categorie": url.split('/')[-1]
                    }
                    data.append(dic)
                except Exception as e:
                    continue
            
            if data:
                df_page = pd.DataFrame(data)
                df = pd.concat([df, df_page], ignore_index=True)
                st.info(f"✅ Page {index_page} scrapée: {len(df_page)} annonces trouvées")
            
            # Pause pour respecter le serveur
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur de connexion page {index_page}: {e}")
            break
        except Exception as e:
            st.error(f"Erreur page {index_page}: {e}")
            break
    
    return df

def get_all_categories():
    """Retourne les catégories disponibles"""
    categories = {
        "👔 Vêtements Homme": "https://sn.coinafrique.com/categorie/vetements-homme",
        "👞 Chaussures Homme": "https://sn.coinafrique.com/categorie/chaussures-homme",
        "👶 Vêtements Enfants": "https://sn.coinafrique.com/categorie/vetements-enfants",
        "👟 Chaussures Enfants": "https://sn.coinafrique.com/categorie/chaussures-enfants",
        "👗 Vêtements Femme": "https://sn.coinafrique.com/categorie/vetements-femme",
        "👠 Chaussures Femme": "https://sn.coinafrique.com/categorie/chaussures-femme",
        "📱 Téléphones": "https://sn.coinafrique.com/categorie/telephones",
        "💻 Ordinateurs": "https://sn.coinafrique.com/categorie/ordinateurs"
    }
    return categories

# ============================================
# SECTION 2: FONCTIONS DE NETTOYAGE
# ============================================

def clean_scraped_data(df):
    """
    Nettoie les données scrapées de CoinAfrique
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    df_clean = df.copy()
    
    # 1. Nettoyage des prix
    # Supprimer les caractères non numériques sauf les points pour les décimales
    df_clean['prix_nettoye'] = df_clean['prix_numerique'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    
    # Convertir en numérique
    df_clean['prix_numerique'] = pd.to_numeric(df_clean['prix_nettoye'], errors='coerce')
    
    # Supprimer les prix absurdes (trop bas ou trop haut)
    df_clean = df_clean[(df_clean['prix_numerique'] > 100) & (df_clean['prix_numerique'] < 10000000)]
    
    # 2. Nettoyage des adresses
    # Standardiser les noms de villes
    ville_mapping = {
        'DAKAR': 'Dakar',
        'DKR': 'Dakar',
        'THIES': 'Thiès',
        'THIES': 'Thiès',
        'SAINT-LOUIS': 'Saint-Louis',
        'KAOLACK': 'Kaolack',
        'ZIGUINCHOR': 'Ziguinchor',
        'MBOUR': 'Mbour'
    }
    
    df_clean['ville'] = df_clean['adresse'].str.upper()
    for old, new in ville_mapping.items():
        df_clean['ville'] = df_clean['ville'].str.replace(old, new, regex=False)
    df_clean['ville'] = df_clean['ville'].str.title()
    
    # 3. Catégorisation des produits
    # Créer des sous-catégories basées sur les mots-clés
    keywords = {
        'chemise': 'Chemises',
        'pantalon': 'Pantalons',
        'jean': 'Jeans',
        't-shirt': 'T-Shirts',
        'costume': 'Costumes',
        'chaussure': 'Chaussures',
        'basket': 'Baskets',
        'sandale': 'Sandales',
        'robe': 'Robes',
        'jupe': 'Jupes',
        'enfant': 'Vêtements Enfants',
        'bébé': 'Vêtements Bébé'
    }
    
    df_clean['sous_categorie'] = 'Autre'
    for keyword, categorie in keywords.items():
        mask = df_clean['type'].str.contains(keyword, case=False, na=False)
        df_clean.loc[mask, 'sous_categorie'] = categorie
    
    # 4. Ajout de métriques
    df_clean['prix_categorie'] = pd.cut(df_clean['prix_numerique'], 
                                       bins=[0, 5000, 10000, 20000, 50000, float('inf')],
                                       labels=['Très bas', 'Bas', 'Moyen', 'Élevé', 'Très élevé'])
    
    # 5. Formatage des dates
    df_clean['date_scraping'] = pd.to_datetime(df_clean['date_scraping'])
    df_clean['jour_semaine'] = df_clean['date_scraping'].dt.day_name()
    df_clean['heure'] = df_clean['date_scraping'].dt.hour
    
    # Supprimer la colonne temporaire
    df_clean = df_clean.drop(columns=['prix_nettoye'])
    
    return df_clean

# ============================================
# SECTION 3: FONCTIONS DE VISUALISATION
# ============================================

def create_dashboard(df):
    """
    Crée un dashboard interactif pour les données CoinAfrique
    """
    if df is None or df.empty:
        st.warning("Aucune donnée à afficher")
        return
    
    st.subheader("📊 Dashboard des Annonces CoinAfrique")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_annonces = len(df)
        st.metric("Nombre total d'annonces", total_annonces)
    
    with col2:
        prix_moyen = df['prix_numerique'].mean()
        st.metric("Prix moyen", f"{prix_moyen:,.0f} CFA")
    
    with col3:
        prix_min = df['prix_numerique'].min()
        st.metric("Prix minimum", f"{prix_min:,.0f} CFA")
    
    with col4:
        prix_max = df['prix_numerique'].max()
        st.metric("Prix maximum", f"{prix_max:,.0f} CFA")
    
    st.markdown("---")
    
    # Graphiques
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Distribution", "📍 Localisation", "🏷️ Catégories", "📋 Données"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Histogramme des prix
            fig = px.histogram(df, x='prix_numerique', nbins=30,
                             title='Distribution des Prix',
                             labels={'prix_numerique': 'Prix (CFA)', 'count': 'Nombre d\'annonces'},
                             color_discrete_sequence=['#FF4B4B'])
            fig.update_layout(bargap=0.1)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Box plot par catégorie
            fig = px.box(df, x='categorie', y='prix_numerique',
                        title='Distribution des Prix par Catégorie',
                        labels={'prix_numerique': 'Prix (CFA)', 'categorie': 'Catégorie'},
                        color='categorie')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Top villes
            top_villes = df['ville'].value_counts().head(10)
            fig = px.bar(x=top_villes.values, y=top_villes.index,
                        orientation='h',
                        title='Top 10 des Villes',
                        labels={'x': 'Nombre d\'annonces', 'y': 'Ville'},
                        color=top_villes.values,
                        color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Carte des prix moyens par ville
            prix_par_ville = df.groupby('ville')['prix_numerique'].mean().sort_values(ascending=False).head(10)
            fig = px.bar(x=prix_par_ville.values, y=prix_par_ville.index,
                        orientation='h',
                        title='Prix Moyen par Ville (Top 10)',
                        labels={'x': 'Prix moyen (CFA)', 'y': 'Ville'},
                        color=prix_par_ville.values,
                        color_continuous_scale='Plasma')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            # Répartition par sous-catégorie
            sous_cat_counts = df['sous_categorie'].value_counts().head(15)
            fig = px.pie(values=sous_cat_counts.values, 
                        names=sous_cat_counts.index,
                        title='Répartition par Sous-Catégorie',
                        hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Heatmap catégorie vs prix
            pivot_table = df.pivot_table(values='prix_numerique', 
                                       index='sous_categorie',
                                       columns='prix_categorie',
                                       aggfunc='count',
                                       fill_value=0)
            
            if not pivot_table.empty:
                fig = px.imshow(pivot_table,
                              title='Relation Catégorie vs Gamme de Prix',
                              labels=dict(x="Gamme de Prix", y="Sous-Catégorie", color="Nombre d'annonces"),
                              aspect="auto")
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        # Filtres interactifs
        st.subheader("🔍 Filtres Interactifs")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            categories_filter = st.multiselect(
                "Catégories",
                options=df['categorie'].unique(),
                default=df['categorie'].unique()[:2]
            )
        
        with col2:
            villes_filter = st.multiselect(
                "Villes",
                options=df['ville'].unique(),
                default=df['ville'].unique()[:3] if len(df['ville'].unique()) > 0 else []
            )
        
        with col3:
            prix_range = st.slider(
                "Plage de prix (CFA)",
                min_value=int(df['prix_numerique'].min()),
                max_value=int(df['prix_numerique'].max()),
                value=(int(df['prix_numerique'].min()), int(df['prix_numerique'].max()))
            )
        
        # Application des filtres
        filtered_df = df[
            (df['categorie'].isin(categories_filter)) &
            (df['ville'].isin(villes_filter if villes_filter else df['ville'].unique())) &
            (df['prix_numerique'] >= prix_range[0]) &
            (df['prix_numerique'] <= prix_range[1])
        ]
        
        # Affichage des données filtrées
        st.dataframe(
            filtered_df[['type', 'prix_texte', 'ville', 'categorie', 'sous_categorie', 'date_scraping']].head(20),
            use_container_width=True,
            hide_index=True
        )
        
        # Bouton de téléchargement des données filtrées
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger les données filtrées (CSV)",
            data=csv,
            file_name=f"coin_afrique_filtre_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# ============================================
# SECTION 4: FORMULAIRE D'ÉVALUATION
# ============================================

def evaluation_form():
    """
    Formulaire d'évaluation de l'application
    """
    st.subheader("📝 Évaluation de l'Application")
    
    with st.form("evaluation_form"):
        # Section informations
        st.markdown("### Vos Informations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            nom = st.text_input("Nom (optionnel)")
            email = st.text_input("Email (optionnel)")
        
        with col2:
            profession = st.selectbox(
                "Votre profession",
                ["", "Étudiant", "Commerçant", "Data Analyst", "Développeur", "Chercheur", "Autre"]
            )
            frequence = st.selectbox(
                "Fréquence d'utilisation prévue",
                ["", "Quotidienne", "Hebdomadaire", "Mensuelle", "Occasionnelle"]
            )
        
        # Section évaluation
        st.markdown("### Évaluation des Fonctionnalités")
        
        st.write("Notez de 1 (Très mauvais) à 5 (Excellent):")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            facilite_utilisation = st.slider("Facilité d'utilisation", 1, 5, 3)
            vitesse_scraping = st.slider("Vitesse du scraping", 1, 5, 3)
        
        with col2:
            qualite_donnees = st.slider("Qualité des données", 1, 5, 3)
            utilite_dashboard = st.slider("Utilité du dashboard", 1, 5, 3)
        
        with col3:
            design_interface = st.slider("Design de l'interface", 1, 5, 3)
            satisfaction_globale = st.slider("Satisfaction globale", 1, 5, 3)
        
        # Section feedback
        st.markdown("### Votre Feedback")
        
        points_positifs = st.text_area("Ce que vous avez aimé")
        ameliorations = st.text_area("Suggestions d'amélioration")
        bugs_problemes = st.text_area("Bugs ou problèmes rencontrés")
        
        # Section supplémentaire
        recommandation = st.radio(
            "Recommanderiez-vous cette application à un collègue/ami?",
            ["Oui", "Non", "Peut-être"]
        )
        
        commentaire_final = st.text_area("Commentaire final (optionnel)")
        
        # Bouton de soumission
        submitted = st.form_submit_button("✅ Soumettre l'évaluation", type="primary")
        
        if submitted:
            # Création de l'objet d'évaluation
            evaluation_data = {
                "date_soumission": datetime.now().isoformat(),
                "informations": {
                    "nom": nom if nom else "Anonyme",
                    "profession": profession,
                    "frequence_utilisation": frequence
                },
                "evaluations": {
                    "facilite_utilisation": facilite_utilisation,
                    "vitesse_scraping": vitesse_scraping,
                    "qualite_donnees": qualite_donnees,
                    "utilite_dashboard": utilite_dashboard,
                    "design_interface": design_interface,
                    "satisfaction_globale": satisfaction_globale
                },
                "feedback": {
                    "points_positifs": points_positifs,
                    "ameliorations": ameliorations,
                    "bugs_problemes": bugs_problemes
                },
                "recommandation": recommandation,
                "commentaire_final": commentaire_final
            }
            
            # Simulation d'envoi (à remplacer par vraie intégration)
            try:
                # Option 1: Sauvegarde locale (pour test)
                filename = f"evaluations/evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                # Créer le dossier s'il n'existe pas
                import os
                os.makedirs("evaluations", exist_ok=True)
                
                # Sauvegarder dans un fichier JSON
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(evaluation_data, f, ensure_ascii=False, indent=2)
                
                # Option 2: Pour Google Forms (à décommenter et configurer)
                """
                # URL de votre Google Forms
                google_forms_url = "VOTRE_URL_GOOGLE_FORMS"
                
                # Mapping des champs Google Forms
                form_data = {
                    'entry.1234567890': nom,  # Remplacer par vos IDs
                    'entry.0987654321': email,
                    # ... autres champs
                }
                
                response = requests.post(google_forms_url, data=form_data)
                if response.status_code == 200:
                    st.success("Évaluation envoyée à Google Forms!")
                """
                
                # Option 3: Pour Kobo Toolbox (à décommenter et configurer)
                """
                kobo_url = "VOTRE_URL_KOBO_API"
                headers = {
                    'Authorization': 'Token VOTRE_TOKEN',
                    'Content-Type': 'application/json'
                }
                response = requests.post(kobo_url, json=evaluation_data, headers=headers)
                """
                
                st.success("✅ Évaluation soumise avec succès!")
                st.balloons()
                
                # Afficher un résumé
                with st.expander("📋 Voir le résumé de votre évaluation"):
                    st.json(evaluation_data)
                
                # Option de téléchargement
                if st.button("📥 Télécharger mon évaluation"):
                    json_str = json.dumps(evaluation_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="Cliquez pour télécharger",
                        data=json_str,
                        file_name=f"evaluation_coin_afrique_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                    
            except Exception as e:
                st.error(f"Erreur lors de la soumission: {str(e)}")

# ============================================
# SECTION 5: INTERFACE PRINCIPALE
# ============================================

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/711/711769.png", width=60)
        st.title("👕 CoinAfrique Scraper")
        
        st.markdown("---")
        
        # Navigation
        page = st.selectbox(
            "Navigation",
            ["🏠 Accueil", "🔍 Scraper des données", "📥 Télécharger données", 
             "📊 Dashboard", "⭐ Évaluer l'application"]
        )
        
        st.markdown("---")
        
        # Information sur les données
        if st.session_state.scraped_data is not None:
            st.info(f"📊 Données chargées: {len(st.session_state.scraped_data)} annonces")
        
        st.markdown("---")
        st.caption("Version 1.0 | © 2024")
    
    # Page d'accueil
    if page == "🏠 Accueil":
        st.title("👕 Bienvenue sur CoinAfrique Scraper")
        
        st.markdown("""
        ### 📋 À propos de cette application
        
        Cette application vous permet de:
        
        1. **🔍 Scraper des annonces** depuis CoinAfrique Sénégal
           - Plusieurs catégories disponibles (vêtements, chaussures, etc.)
           - Configuration du nombre de pages à scraper
           - Données en temps réel
        
        2. **📥 Télécharger les données** scrapées
           - Données brutes (non nettoyées)
           - Données nettoyées et structurées
           - Formats supportés: CSV, Excel, JSON
        
        3. **📊 Visualiser les données** avec un dashboard interactif
           - Statistiques et métriques
           - Graphiques et visualisations
           - Filtres interactifs
        
        4. **⭐ Évaluer l'application**
           - Donner votre feedback
           - Signaler des problèmes
           - Proposer des améliorations
        """)
        
        st.markdown("---")
        
        # Aperçu des catégories disponibles
        st.subheader("🏷️ Catégories Disponibles")
        
        categories = get_all_categories()
        cols = st.columns(3)
        
        for idx, (name, url) in enumerate(categories.items()):
            with cols[idx % 3]:
                st.info(f"**{name}**")
                st.caption(f"URL: {url[:40]}...")
        
        # Guide rapide
        with st.expander("📖 Guide de démarrage rapide"):
            st.markdown("""
            1. **Aller dans '🔍 Scraper des données'**
            2. **Choisir une catégorie** dans la liste
            3. **Définir le nombre de pages** (1-10)
            4. **Cliquer sur 'Lancer le scraping'**
            5. **Explorer les données** dans le dashboard
            """)
    
    # Page de scraping
    elif page == "🔍 Scraper des données":
        st.title("🔍 Scraper des Données CoinAfrique")
        
        # Sélection de la catégorie
        categories = get_all_categories()
        selected_category_name = st.selectbox(
            "Sélectionnez une catégorie:",
            list(categories.keys())
        )
        
        selected_url = categories[selected_category_name]
        
        # Configuration du scraping
        col1, col2 = st.columns(2)
        
        with col1:
            pages = st.slider("Nombre de pages à scraper:", 1, 10, 3)
        
        with col2:
            st.markdown("**Options avancées:**")
            clean_auto = st.checkbox("Nettoyer automatiquement les données", value=True)
        
        # Bouton de scraping
        if st.button("🚀 Lancer le scraping", type="primary", use_container_width=True):
            with st.spinner(f"Scraping des annonces {selected_category_name}..."):
                try:
                    df = scraping_coin_afrique(selected_url, pages=pages)
                    
                    if df is not None and not df.empty:
                        st.session_state.scraped_data = df
                        st.session_state.selected_category = selected_category_name
                        
                        # Nettoyage automatique
                        if clean_auto:
                            st.session_state.cleaned_data = clean_scraped_data(df)
                        
                        st.success(f"✅ {len(df)} annonces scrapées avec succès!")
                        
                        # Aperçu des données
                        st.subheader("👁️ Aperçu des données scrapées")
                        st.dataframe(df.head(), use_container_width=True)
                        
                        # Statistiques rapides
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Annonces scrapées", len(df))
                            st.metric("Pages parcourues", df['page_scrapee'].nunique())
                        with col2:
                            avg_price = pd.to_numeric(df['prix_numerique'], errors='coerce').mean()
                            st.metric("Prix moyen", f"{avg_price:,.0f} CFA" if not pd.isna(avg_price) else "N/A")
                            st.metric("Villes différentes", df['adresse'].nunique())
                    
                    else:
                        st.warning("⚠️ Aucune donnée n'a pu être scrapée. Vérifiez l'URL ou réessayez.")
                        
                except Exception as e:
                    st.error(f"❌ Erreur lors du scraping: {str(e)}")
        
        # Exemple de données
        with st.expander("👀 Voir un exemple de données scrapées"):
            example_data = {
                "type": ["Chemise homme slim fit", "Basket Nike Air Max", "Robe de soirée"],
                "prix_texte": ["15 000 CFA", "45 000 CFA", "25 000 CFA"],
                "adresse": ["Dakar, Plateau", "Pikine, Guédiawaye", "Mermoz, Dakar"],
                "categorie": ["vetements-homme", "chaussures-homme", "vetements-femme"]
            }
            st.dataframe(pd.DataFrame(example_data))
    
    # Page de téléchargement
    elif page == "📥 Télécharger données":
        st.title("📥 Télécharger les Données")
        
        if st.session_state.scraped_data is None:
            st.warning("ℹ️ Aucune donnée disponible. Veuillez d'abord scraper des données.")
        else:
            # Onglets pour différents formats
            tab1, tab2, tab3 = st.tabs(["📄 Données Brutes", "✨ Données Nettoyées", "📤 Exporter vers..."])
            
            with tab1:
                st.subheader("Données Brutes (non nettoyées)")
                st.dataframe(st.session_state.scraped_data.head(10), use_container_width=True)
                
                # Options de téléchargement pour données brutes
                raw_df = st.session_state.scraped_data
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    csv_raw = raw_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv_raw,
                        file_name=f"coin_afrique_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    json_raw = raw_df.to_json(orient='records', indent=2, force_ascii=False)
                    st.download_button(
                        label="📥 Télécharger JSON",
                        data=json_raw,
                        file_name=f"coin_afrique_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col3:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        raw_df.to_excel(writer, index=False, sheet_name='Donnees_Brutes')
                    
                    st.download_button(
                        label="📥 Télécharger Excel",
                        data=buffer.getvalue(),
                        file_name=f"coin_afrique_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            
            with tab2:
                if st.session_state.cleaned_data is not None:
                    st.subheader("Données Nettoyées")
                    st.dataframe(st.session_state.cleaned_data.head(10), use_container_width=True)
                    
                    # Options de téléchargement pour données nettoyées
                    clean_df = st.session_state.cleaned_data
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        csv_clean = clean_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 Télécharger CSV",
                            data=csv_clean,
                            file_name=f"coin_afrique_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        json_clean = clean_df.to_json(orient='records', indent=2, force_ascii=False)
                        st.download_button(
                            label="📥 Télécharger JSON",
                            data=json_clean,
                            file_name=f"coin_afrique_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    
                    with col3:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            clean_df.to_excel(writer, index=False, sheet_name='Donnees_Nettoyees')
                        
                        st.download_button(
                            label="📥 Télécharger Excel",
                            data=buffer.getvalue(),
                            file_name=f"coin_afrique_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.info("ℹ️ Les données nettoyées ne sont pas disponibles. Lancez d'abord le nettoyage.")
                    
                    if st.button("🧹 Nettoyer les données maintenant"):
                        with st.spinner("Nettoyage en cours..."):
                            st.session_state.cleaned_data = clean_scraped_data(st.session_state.scraped_data)
                            st.success("✅ Données nettoyées avec succès!")
                            st.rerun()
            
            with tab3:
                st.subheader("Options d'export avancées")
                
                # Export personnalisé
                st.write("**Sélectionnez les colonnes à exporter:**")
                
                if st.session_state.cleaned_data is not None:
                    df_source = st.session_state.cleaned_data
                else:
                    df_source = st.session_state.scraped_data
                
                columns = st.multiselect(
                    "Colonnes:",
                    options=df_source.columns.tolist(),
                    default=df_source.columns.tolist()[:5]
                )
                
                if columns:
                    df_export = df_source[columns]
                    
                    # Prévisualisation
                    st.write("**Aperçu de l'export:**")
                    st.dataframe(df_export.head(), use_container_width=True)
                    
                    # Format d'export
                    export_format = st.selectbox(
                        "Format d'export:",
                        ["CSV", "Excel", "JSON", "HTML"]
                    )
                    
                    if export_format == "CSV":
                        export_data = df_export.to_csv(index=False, encoding='utf-8-sig')
                        mime_type = "text/csv"
                        extension = "csv"
                    elif export_format == "Excel":
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df_export.to_excel(writer, index=False, sheet_name='Donnees_Exportees')
                        export_data = buffer.getvalue()
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        extension = "xlsx"
                    elif export_format == "JSON":
                        export_data = df_export.to_json(orient='records', indent=2, force_ascii=False)
                        mime_type = "application/json"
                        extension = "json"
                    else:  # HTML
                        export_data = df_export.to_html(index=False)
                        mime_type = "text/html"
                        extension = "html"
                    
                    st.download_button(
                        label=f"📥 Télécharger {export_format}",
                        data=export_data,
                        file_name=f"coin_afrique_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}",
                        mime=mime_type,
                        use_container_width=True
                    )
    
    # Page Dashboard
    elif page == "📊 Dashboard":
        st.title("📊 Dashboard des Données")
        
        if st.session_state.cleaned_data is not None and not st.session_state.cleaned_data.empty:
            create_dashboard(st.session_state.cleaned_data)
        elif st.session_state.scraped_data is not None and not st.session_state.scraped_data.empty:
            st.info("⚠️ Les données nettoyées ne sont pas disponibles. Nettoyage automatique en cours...")
            
            with st.spinner("Nettoyage des données..."):
                st.session_state.cleaned_data = clean_scraped_data(st.session_state.scraped_data)
            
            if st.session_state.cleaned_data is not None and not st.session_state.cleaned_data.empty:
                create_dashboard(st.session_state.cleaned_data)
            else:
                st.error("❌ Impossible de créer le dashboard. Les données pourraient être vides.")
        else:
            st.warning("""
            ℹ️ Aucune donnée disponible pour le dashboard.
            
            Veuillez:
            1. Aller dans '🔍 Scraper des données'
            2. Choisir une catégorie
            3. Lancer le scraping
            4. Revenir sur cette page
            """)
    

    # Page d'évaluation



