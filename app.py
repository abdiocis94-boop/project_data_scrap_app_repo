# app.py - Application Streamlit pour le scraping de CoinAfrique

import streamlit as st
import pandas as pd
from requests import get
from bs4 import BeautifulSoup as bs 
import os
import time
from datetime import datetime
import base64

# Configuration de la page
st.set_page_config(
    page_title="CoinAfrique Scraper",
    page_icon="🛒",
    layout="wide"
)

# Titre de l'application
st.title("🛒 CoinAfrique Scraper - Sénégal")
st.markdown("---")

# Fonction de scraping
@st.cache_data(show_spinner=False)
def scraping(url, stop, progress_bar=None):
    """
    Fonction pour scraper les données de CoinAfrique
    """
    df = pd.DataFrame()
    total_pages = stop
    
    for index_page in range(1, stop+1):
        # Mise à jour de la barre de progression
        if progress_bar:
            progress_bar.progress(index_page / total_pages, 
                                 text=f"Page {index_page}/{total_pages}")
        
        url_page = f'{url}?page={index_page}'
        try:
            res = get(url_page, timeout=10)
            soup = bs(res.content, 'html.parser')
            containers = soup.find_all('div', 'col s6 m4 l3')
            data = []
            
            for container in containers:
                try:
                    type_habit = container.find('p', 'ad__card-description').a.text
                    prix = container.find('p', 'ad__card-price').a.text.strip('CFA')
                    adresse = container.find('p', 'ad__card-location').span.text
                    image = container.find('img', 'ad__card-img')['src']
                    
                    dic = {
                        "type": type_habit, 
                        "prix": prix,
                        "adresse": adresse, 
                        "image": image,
                        "date_scraping": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    data.append(dic)
                except Exception as e:
                    continue
            
            if data:
                DF = pd.DataFrame(data)
                df = pd.concat([df, DF], axis=0).reset_index(drop=True)
                
        except Exception as e:
            st.warning(f"Erreur sur la page {index_page}: {str(e)}")
            continue
    
    return df

# Fonction pour créer un lien de téléchargement
def get_csv_download_link(df, filename, text="📥 Télécharger CSV"):
    """
    Génère un lien de téléchargement pour un DataFrame
    """
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="\
        display: inline-block;\
        padding: 0.5rem 1rem;\
        background-color: #4CAF50;\
        color: white;\
        text-decoration: none;\
        border-radius: 5px;\
        font-weight: bold;\
        margin: 5px;">{text}</a>'
    return href

# Barre latérale pour les paramètres
with st.sidebar:
    st.header("⚙️ Paramètres de scraping")
    st.markdown("---")
    
    # Sélection du nombre de pages
    pages = st.slider("Nombre de pages à scraper", 1, 20, 5, 
                     help="Plus de pages = plus de données mais temps de traitement plus long")
    
    # Bouton pour démarrer le scraping
    start_scraping = st.button("🚀 Lancer le scraping", 
                              type="primary", 
                              use_container_width=True)
    
    st.markdown("---")
    st.info("**Note:** Chaque page contient environ 20-30 annonces.")
    
    # Section informations
    with st.expander("ℹ️ Informations"):
        st.markdown("""
        **Catégories disponibles:**
        1. Vêtements Homme
        2. Chaussures Homme
        3. Vêtements Enfants
        4. Chaussures Enfants
        
        **Données collectées:**
        - Type d'article
        - Prix (CFA)
        - Adresse
        - Image
        - Date du scraping
        """)

# Contenu principal
if start_scraping:
    # URLs pour le scraping
    urls = {
        "Vêtements Homme": 'https://sn.coinafrique.com/categorie/vetements-homme',
        "Chaussures Homme": 'https://sn.coinafrique.com/categorie/chaussures-homme',
        "Vêtements Enfants": 'https://sn.coinafrique.com/categorie/vetements-enfants',
        "Chaussures Enfants": 'https://sn.coinafrique.com/categorie/chaussures-enfants'
    }
    
    # Initialiser les DataFrames
    dataframes = {}
    
    # Conteneur pour la progression
    progress_container = st.container()
    
    with progress_container:
        st.subheader("📊 Progression du scraping")
        progress_bar = st.progress(0, text="Préparation...")
        
        # Scraping pour chaque catégorie
        categories = list(urls.keys())
        for i, category in enumerate(categories):
            st.write(f"**{category}**...")
            
            # Barre de progression pour cette catégorie
            category_progress = st.progress(0, text=f"Page 1/{pages}")
            
            # Scraping
            df = scraping(urls[category], pages, category_progress)
            dataframes[category] = df
            
            # Supprimer la barre de progression de la catégorie
            category_progress.empty()
            
            # Mise à jour de la barre principale
            progress_bar.progress((i + 1) / len(categories), 
                                 text=f"{i + 1}/{len(categories)} catégories terminées")
        
        progress_bar.empty()
        st.success("✅ Scraping terminé avec succès !")
    
    # Section des statistiques
    st.subheader("📈 Statistiques des données collectées")
    
    cols = st.columns(4)
    for idx, (category, df) in enumerate(dataframes.items()):
        with cols[idx % 4]:
            st.metric(
                label=category,
                value=f"{len(df)} annonces",
                delta=f"{len(df)//pages} annonces/page" if pages > 0 else "0"
            )
    
    # Section d'affichage des données
    st.subheader("👁️ Aperçu des données")
    
    # Sélecteur de catégorie pour l'aperçu
    selected_category = st.selectbox(
        "Choisir une catégorie à afficher:",
        list(dataframes.keys())
    )
    
    if selected_category in dataframes:
        df_display = dataframes[selected_category]
        st.dataframe(
            df_display.head(10),
            use_container_width=True,
            column_config={
                "image": st.column_config.ImageColumn("Image", width="small"),
                "prix": st.column_config.NumberColumn("Prix (CFA)", format="%d CFA"),
                "type": st.column_config.TextColumn("Type d'article", width="medium"),
                "adresse": st.column_config.TextColumn("Adresse", width="medium"),
                "date_scraping": st.column_config.DatetimeColumn("Date de scraping")
            }
        )
        
        # Afficher quelques images
        if not df_display.empty and 'image' in df_display.columns:
            st.subheader("🖼️ Quelques images des annonces")
            image_urls = df_display['image'].dropna().head(6).tolist()
            if image_urls:
                cols = st.columns(3)
                for idx, img_url in enumerate(image_urls[:6]):
                    with cols[idx % 3]:
                        st.image(img_url, caption=f"Annonce {idx+1}", use_column_width=True)
    
    # Section de téléchargement
    st.subheader("📥 Téléchargement des données")
    
    # Créer un dossier data s'il n'existe pas
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Enregistrer les fichiers CSV
    st.write("Téléchargez les données complètes au format CSV:")
    
    download_cols = st.columns(4)
    for idx, (category, df) in enumerate(dataframes.items()):
        with download_cols[idx % 4]:
            # Générer le nom du fichier
            filename = f"{category.lower().replace(' ', '_')}.csv"
            filepath = os.path.join(data_dir, filename)
            
            # Sauvegarder le fichier
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            # Créer le lien de téléchargement
            st.markdown(get_csv_download_link(df, filename, f"📥 {category}"), 
                       unsafe_allow_html=True)
            
            # Afficher des infos supplémentaires
            st.caption(f"{len(df)} annonces")
    
    # Option pour télécharger toutes les données en un seul fichier Excel
    st.markdown("---")
    st.subheader("📦 Option avancée")
    
    if st.button("📊 Générer un fichier Excel avec toutes les données", 
                use_container_width=True):
        with st.spinner("Génération du fichier Excel..."):
            excel_path = os.path.join(data_dir, "toutes_donnees_coinafrique.xlsx")
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for category, df in dataframes.items():
                    # Nettoyer le nom de la feuille
                    sheet_name = category[:31]  # Excel limite à 31 caractères
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Lire le fichier Excel pour le téléchargement
            with open(excel_path, "rb") as f:
                excel_data = f.read()
            
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" \
                    download="toutes_donnees_coinafrique.xlsx" \
                    style="display: inline-block;\
                           padding: 0.75rem 1.5rem;\
                           background-color: #2196F3;\
                           color: white;\
                           text-decoration: none;\
                           border-radius: 5px;\
                           font-weight: bold;\
                           font-size: 1.1em;">📊 Télécharger le fichier Excel complet</a>'
            
            st.markdown(href, unsafe_allow_html=True)
            st.success("Fichier Excel généré avec succès !")

else:
    # Page d'accueil
    st.markdown("""
    ## 📋 Bienvenue sur CoinAfrique Scraper
    
    Cette application vous permet de:
    
    1. **Scraper les données** depuis CoinAfrique Sénégal
    2. **Visualiser les annonces** en temps réel
    3. **Télécharger les données** au format CSV ou Excel
    
    ### 🎯 Catégories disponibles:
    - 👕 Vêtements pour Hommes
    - 👞 Chaussures pour Hommes
    - 👶 Vêtements pour Enfants
    - 👟 Chaussures pour Enfants
    
    ### 🚀 Comment utiliser:
    1. Configurez le nombre de pages dans la barre latérale
    2. Cliquez sur "Lancer le scraping"
    3. Visualisez les données collectées
    4. Téléchargez les fichiers CSV ou Excel
    
    ---
    
    **💡 Conseil:** Commencez avec 2-3 pages pour tester, puis augmentez selon vos besoins.
    """)
    
    # Exemple de structure de données
    with st.expander("👁️ Exemple de données collectées"):
        example_data = pd.DataFrame({
            "type": ["Chemise homme", "Baskets Nike", "Robe enfant"],
            "prix": [5000, 25000, 3500],
            "adresse": ["Dakar", "Thiès", "Mbour"],
            "image": [
                "https://example.com/image1.jpg",
                "https://example.com/image2.jpg",
                "https://example.com/image3.jpg"
            ],
            "date_scraping": ["2024-01-06 10:30:00"] * 3
        })
        st.dataframe(example_data, use_container_width=True)

# Pied de page
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
    Application développée avec ❤️ en utilisant Streamlit | 
    Données provenant de <a href='https://sn.coinafrique.com' target='_blank'>CoinAfrique Sénégal</a>
    </div>
    """,
    unsafe_allow_html=True
)
