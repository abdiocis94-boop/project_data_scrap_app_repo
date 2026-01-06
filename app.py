import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import json
import time
import os

# ============================================
# CONFIGURATION - VERSION SIMPLIFIÉE
# ============================================
st.set_page_config(
    page_title="CoinAfrique Scraper Pro",
    page_icon="👕"
)

# Initialisation de session
if 'df_raw' not in st.session_state:
    st.session_state.df_raw = None
if 'df_clean' not in st.session_state:
    st.session_state.df_clean = None

# ============================================
# FONCTIONS DE SCRAPING (basées sur votre code)
# ============================================

def scrape_coin_afrique(url, pages=3):
    """Fonction de scraping sécurisée"""
    all_data = []
    
    for page_num in range(1, pages + 1):
        try:
            page_url = f"{url}?page={page_num}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(page_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                articles = soup.find_all('div', class_='col s6 m4 l3')
                
                for article in articles:
                    try:
                        # Extraction des données
                        title_elem = article.find('p', class_='ad__card-description')
                        price_elem = article.find('p', class_='ad__card-price')
                        loc_elem = article.find('p', class_='ad__card-location')
                        img_elem = article.find('img', class_='ad__card-img')
                        
                        if all([title_elem, price_elem, loc_elem]):
                            title = title_elem.a.text.strip() if title_elem.a else "Sans titre"
                            price_text = price_elem.a.text.strip() if price_elem.a else "0 CFA"
                            
                            # Nettoyage du prix
                            price_num = ''.join(filter(str.isdigit, price_text))
                            price_num = int(price_num) if price_num else 0
                            
                            location = loc_elem.span.text.strip() if loc_elem.span else "Non spécifié"
                            image = img_elem.get('src', '') if img_elem else ''
                            
                            all_data.append({
                                'Titre': title,
                                'Prix_texte': price_text,
                                'Prix_numerique': price_num,
                                'Localisation': location,
                                'Image': image,
                                'Page': page_num,
                                'Date_scraping': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                    except:
                        continue
                
                time.sleep(1)  # Respect du serveur
                
            else:
                st.warning(f"Page {page_num}: Code {response.status_code}")
                
        except Exception as e:
            st.error(f"Erreur page {page_num}: {str(e)[:100]}")
    
    return pd.DataFrame(all_data) if all_data else pd.DataFrame()

# ============================================
# FONCTIONS DE NETTOYAGE
# ============================================

def clean_data(df):
    """Nettoie les données scrapées"""
    if df.empty:
        return df
    
    df_clean = df.copy()
    
    # Filtre des prix aberrants
    df_clean = df_clean[df_clean['Prix_numerique'] > 0]
    df_clean = df_clean[df_clean['Prix_numerique'] < 10000000]  # < 10 millions CFA
    
    # Extraction de la ville
    df_clean['Ville'] = df_clean['Localisation'].apply(
        lambda x: x.split(',')[0].strip() if ',' in str(x) else str(x)
    )
    
    # Catégorie de prix
    bins = [0, 5000, 20000, 50000, 200000, float('inf')]
    labels = ['Très bas', 'Bas', 'Moyen', 'Élevé', 'Très élevé']
    df_clean['Catégorie_prix'] = pd.cut(df_clean['Prix_numerique'], bins=bins, labels=labels)
    
    return df_clean

# ============================================
# INTERFACE UTILISATEUR
# ============================================

def main():
    # Titre principal
    st.title("👕 CoinAfrique Scraper Pro")
    st.markdown("---")
    
    # Sidebar - Navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Choisissez une page :",
            ["🏠 Accueil", "🔍 Scraper", "📥 Télécharger", "📊 Dashboard", "⭐ Évaluation"]
        )
        
        st.markdown("---")
        st.info("**État des données :**")
        if st.session_state.df_raw is not None:
            st.success(f"✅ {len(st.session_state.df_raw)} annonces scrapées")
    
    # ==================== PAGE ACCUEIL ====================
    if page == "🏠 Accueil":
        st.header("Bienvenue sur CoinAfrique Scraper")
        
        st.markdown("""
        ### 📋 Fonctionnalités principales :
        
        1. **🔍 Scraping intelligent**
           - Récupération multi-pages
           - Gestion automatique des erreurs
           - Respect des délais serveur
        
        2. **📥 Export des données**
           - Format CSV (Excel compatible)
           - Format JSON
           - Données brutes et nettoyées
        
        3. **📊 Dashboard analytique**
           - Graphiques interactifs
           - Statistiques détaillées
           - Filtres dynamiques
        
        4. **⭐ Système d'évaluation**
           - Feedback utilisateur
           - Amélioration continue
        """)
        
        # URLs suggérées
        with st.expander("🔗 URLs de test recommandées"):
            st.code("""
            https://sn.coinafrique.com/categorie/telephones
            https://sn.coinafrique.com/categorie/ordinateurs
            https://sn.coinafrique.com/categorie/electromenager
            """)
        
        # Vérification des dépendances
        st.markdown("---")
        st.subheader("✅ Vérification du système")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("Streamlit: OK")
        with col2:
            st.success("Pandas: OK")
        with col3:
            try:
                import plotly
                st.success(f"Plotly: {plotly.__version__}")
            except:
                st.error("Plotly: ERREUR")
    
    # ==================== PAGE SCRAPER ====================
    elif page == "🔍 Scraper":
        st.header("🔍 Scraping de données")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            url = st.text_input(
                "URL CoinAfrique à scraper :",
                value="https://sn.coinafrique.com/categorie/telephones",
                help="Collez l'URL d'une catégorie CoinAfrique"
            )
        
        with col2:
            pages = st.slider("Nombre de pages :", 1, 5, 2)
        
        if st.button("🚀 Lancer le scraping", type="primary", use_container_width=True):
            with st.spinner(f"Scraping en cours ({pages} pages)..."):
                df = scrape_coin_afrique(url, pages)
                
                if not df.empty:
                    st.session_state.df_raw = df
                    st.session_state.df_clean = clean_data(df)
                    
                    st.success(f"✅ {len(df)} annonces récupérées avec succès !")
                    
                    # Aperçu
                    st.subheader("👁️ Aperçu des données")
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    # Statistiques rapides
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Annonces", len(df))
                    col2.metric("Prix moyen", f"{df['Prix_numerique'].mean():,.0f} CFA")
                    col3.metric("Pages", df['Page'].nunique())
                    
                else:
                    st.warning("Aucune donnée n'a pu être récupérée. Essayez une autre URL.")
    
    # ==================== PAGE TÉLÉCHARGER ====================
    elif page == "📥 Télécharger":
        st.header("📥 Téléchargement des données")
        
        if st.session_state.df_raw is not None:
            df_raw = st.session_state.df_raw
            df_clean = st.session_state.df_clean
            
            tab1, tab2 = st.tabs(["Données brutes", "Données nettoyées"])
            
            with tab1:
                st.subheader(f"Données brutes ({len(df_raw)} annonces)")
                st.dataframe(df_raw.head(), use_container_width=True)
                
                # Téléchargement brut
                csv_raw = df_raw.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "📥 Télécharger CSV (brut)",
                    csv_raw,
                    f"coin_afrique_brut_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            with tab2:
                if df_clean is not None and not df_clean.empty:
                    st.subheader(f"Données nettoyées ({len(df_clean)} annonces)")
                    st.dataframe(df_clean.head(), use_container_width=True)
                    
                    csv_clean = df_clean.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "📥 Télécharger CSV (nettoyé)",
                        csv_clean,
                        f"coin_afrique_net_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        type="primary",
                        use_container_width=True
                    )
                else:
                    st.info("Les données nettoyées ne sont pas disponibles.")
        
        else:
            st.warning("Aucune donnée disponible. Veuillez d'abord scraper des données.")
    
    # ==================== PAGE DASHBOARD ====================
    elif page == "📊 Dashboard":
        st.header("📊 Dashboard analytique")
        
        if st.session_state.df_clean is not None and not st.session_state.df_clean.empty:
            df = st.session_state.df_clean
            
            # Métriques principales
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Annonces", len(df))
            col2.metric("Prix moyen", f"{df['Prix_numerique'].mean():,.0f} CFA")
            col3.metric("Prix min", f"{df['Prix_numerique'].min():,.0f} CFA")
            col4.metric("Prix max", f"{df['Prix_numerique'].max():,.0f} CFA")
            
            st.markdown("---")
            
            # Graphiques
            tab1, tab2, tab3 = st.tabs(["📈 Distribution", "📍 Localisation", "🏷️ Catégories"])
            
            with tab1:
                # Histogramme des prix
                fig1 = px.histogram(df, x='Prix_numerique', nbins=20,
                                  title='Distribution des prix',
                                  labels={'Prix_numerique': 'Prix (CFA)'})
                st.plotly_chart(fig1, use_container_width=True)
            
            with tab2:
                if 'Ville' in df.columns:
                    ville_counts = df['Ville'].value_counts().head(10)
                    fig2 = px.bar(x=ville_counts.values, y=ville_counts.index,
                                orientation='h',
                                title='Top 10 des villes',
                                labels={'x': 'Nombre d\'annonces', 'y': 'Ville'})
                    st.plotly_chart(fig2, use_container_width=True)
            
            with tab3:
                if 'Catégorie_prix' in df.columns:
                    cat_counts = df['Catégorie_prix'].value_counts()
                    fig3 = px.pie(values=cat_counts.values, names=cat_counts.index,
                                title='Répartition par catégorie de prix')
                    st.plotly_chart(fig3, use_container_width=True)
            
            # Tableau détaillé
            st.markdown("---")
            st.subheader("📋 Données détaillées")
            st.dataframe(df, use_container_width=True)
            
        else:
            st.info("Scrapez et nettoyez d'abord des données pour afficher le dashboard.")
    
    # ==================== PAGE ÉVALUATION ====================
    elif page == "⭐ Évaluation":
        st.header("⭐ Évaluez cette application")
        
        with st.form("form_evaluation"):
            st.subheader("Votre expérience")
            
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Votre nom (optionnel)")
                usage = st.selectbox("Fréquence d'utilisation",
                                   ["Première fois", "Occasionnel", "Régulier"])
            
            with col2:
                email = st.text_input("Email (optionnel)")
                role = st.selectbox("Votre rôle",
                                  ["Étudiant", "Professionnel", "Chercheur", "Autre"])
            
            st.subheader("Évaluation (1 = Très mauvais, 5 = Excellent)")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                facilite = st.slider("Facilité d'utilisation", 1, 5, 3)
                vitesse = st.slider("Vitesse de scraping", 1, 5, 3)
            
            with col2:
                qualite = st.slider("Qualité des données", 1, 5, 3)
                utilite = st.slider("Utilité du dashboard", 1, 5, 3)
            
            with col3:
                design = st.slider("Design de l'interface", 1, 5, 3)
                satisfaction = st.slider("Satisfaction globale", 1, 5, 3)
            
            st.subheader("Vos commentaires")
            points_forts = st.text_area("Ce que vous avez aimé")
            ameliorations = st.text_area("Suggestions d'amélioration")
            
            # Soumission
            if st.form_submit_button("✅ Soumettre l'évaluation", use_container_width=True):
                # Création du dossier evaluations s'il n'existe pas
                os.makedirs("evaluations", exist_ok=True)
                
                # Données d'évaluation
                eval_data = {
                    "date": datetime.now().isoformat(),
                    "evaluation": {
                        "facilite": facilite,
                        "vitesse": vitesse,
                        "qualite": qualite,
                        "utilite": utilite,
                        "design": design,
                        "satisfaction": satisfaction
                    },
                    "commentaires": {
                        "points_forts": points_forts,
                        "ameliorations": ameliorations
                    },
                    "utilisateur": {
                        "usage": usage,
                        "role": role
                    }
                }
                
                # Sauvegarde
                filename = f"evaluations/evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(eval_data, f, ensure_ascii=False, indent=2)
                
                st.success("✅ Merci pour votre évaluation !")
                st.balloons()
    
    # Pied de page
    st.markdown("---")
    st.caption("CoinAfrique Scraper Pro v2.0 • Déployé avec Streamlit Cloud")

# ============================================
# POINT D'ENTRÉE
# ============================================

if __name__ == "__main__":
    main()
