import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Projet Data Collection - Coinafrique", layout="wide")

# --- STYLE DU SIDEBAR ---
# Nouveau menu demandé
st.sidebar.title("Projet Data Collection")
selection = st.sidebar.radio(
    "Menu Principal", 
    [
        "Télécharger données brutes (Excel)", 
        "Scraping & Nettoyage (BS4)", 
        "Tableau de Bord", 
        "Évaluer l'application"
    ]
)

# --- FONCTION DE SCRAPING (BS4) ---
def collecter_donnees(url_base, nom_categorie):
    liste_annonces = []
    for page_num in range(1, 3):
        url = f"{url_base}?page={page_num}"
        try:
            reponse = requests.get(url, timeout=10)
            if reponse.status_code == 200:
                soup = BeautifulSoup(reponse.text, 'html.parser')
                containers = soup.find_all('div', class_='ad__card')
                for item in containers:
                    try:
                        nom = item.find('p', class_='ad__card-description').text.strip()
                        prix = item.find('p', class_='ad__card-price').text.strip()
                        adresse = item.find('p', class_='ad__card-location').text.strip().replace('location_on', '').strip()
                        image_lien = item.find('img', class_='ad__card-img')['src']
                        liste_annonces.append({
                            "Nom": nom, "Prix": prix, "Adresse": adresse, 
                            "Image_lien": image_lien, "Categorie": nom_categorie
                        })
                    except: continue
        except: continue
    return liste_annonces

# --- SECTION 1 : TÉLÉCHARGER DES DONNÉES BRUTES (WEB SCRAPER) ---
if selection == "Télécharger données brutes (Excel)":
    st.title("Visualisation des données brutes")
    st.write("Sélectionnez une catégorie pour visualiser et télécharger les données brutes issues de Web Scraper.")
    
    fichiers_locaux = {
        "Chiens": "chiens.xlsx",
        "Moutons": "moutons.xlsx",
        "Poules, Lapins & Pigeons": "lapins.xlsx",
        "Autres Animaux": "autres-animaux.xlsx"
    }
    
    choix_categorie = st.selectbox("Choisir une catégorie :", ["Choisir une option..."] + list(fichiers_locaux.keys()))
    
    if choix_categorie != "Choisir une option...":
        chemin_fichier = fichiers_locaux[choix_categorie]
        try:
            df_raw = pd.read_excel(chemin_fichier)
            st.success(f"Données de la catégorie '{choix_categorie}' chargées ! Nombre d'annonces : {len(df_raw)}")
            
            st.subheader(f"Aperçu des données : {choix_categorie}")
            st.dataframe(df_raw)
            
            # --- TELECHARGEMENT EN EXCEL ---
            # Pour télécharger en Excel avec Streamlit, on a besoin d'un buffer
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_raw.to_excel(writer, index=False, sheet_name='Sheet1')
            excel_data = output.getvalue()
            
            st.download_button(
                label=f"Télécharger {choix_categorie} en Excel",
                data=excel_data,
                file_name=f"{choix_categorie.lower().replace(' ', '_')}_raw.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")

# --- SECTION 2 : SCRAPING ET NETTOYAGE (BEAUTIFUL SOUP) ---
elif selection == "Scraping & Nettoyage (BS4)":
    st.title("Scraping & nettoyage")
    st.info("Utilisation de BeautifulSoup pour extraire et nettoyer les données en direct.")
    
    # Champ pour choisir le nombre de pages à scraper
    nb_pages = st.number_input("Nombre de pages à parcourir par catégorie :", min_value=1, max_value=10, value=2)
    
    urls_categories = {
        "Chiens": "https://sn.coinafrique.com/categorie/chiens",
        "Moutons": "https://sn.coinafrique.com/categorie/moutons",
        "Poules, Lapins & Pigeons": "https://sn.coinafrique.com/categorie/poules-lapins-et-pigeons",
        "Autres": "https://sn.coinafrique.com/categorie/autres-animaux"
    }
    
    # Redéfinition de la fonction pour prendre en compte le nombre de pages
    def collecter_donnees_dynamique(url_base, nom_categorie, max_p):
        liste_annonces = []
        for page_num in range(1, max_p + 1):
            url = f"{url_base}?page={page_num}"
            try:
                reponse = requests.get(url, timeout=10)
                if reponse.status_code == 200:
                    soup = BeautifulSoup(reponse.text, 'html.parser')
                    containers = soup.find_all('div', class_='ad__card')
                    for item in containers:
                        try:
                            nom = item.find('p', class_='ad__card-description').text.strip()
                            prix = item.find('p', class_='ad__card-price').text.strip()
                            adresse = item.find('p', class_='ad__card-location').text.strip().replace('location_on', '').strip()
                            image_lien = item.find('img', class_='ad__card-img')['src']
                            liste_annonces.append({
                                "Nom": nom, "Prix": prix, "Adresse": adresse, 
                                "Image_lien": image_lien, "Categorie": nom_categorie
                            })
                        except: continue
            except: continue
        return liste_annonces

    if st.button("Lancer le scraping & nettoyage"):
        toutes_donnees = []
        barre = st.progress(0)
        
        for i, (nom_cat, url_cat) in enumerate(urls_categories.items()):
            st.write(f"Extraction de la catégorie : **{nom_cat}** ({nb_pages} pages)")
            resultat = collecter_donnees_dynamique(url_cat, nom_cat, nb_pages)
            toutes_donnees.extend(resultat)
            barre.progress((i + 1) / len(urls_categories))
            
        df = pd.DataFrame(toutes_donnees)
        
        if not df.empty:
            df['Prix'] = df['Prix'].astype(str).str.replace('CFA', '', regex=False).str.replace(' ', '', regex=False).str.replace('\xa0', '', regex=False)
            df['Prix'] = pd.to_numeric(df['Prix'], errors='coerce').fillna(0).astype(int)
            
            st.session_state['df_final'] = df
            st.success(f"Opération terminée : {len(df)} annonces collectées et nettoyées !")
            # Affichage de l'intégralité du tableau avec défilement
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Aucune donnée n'a pu être récupérée. Vérifiez votre connexion.")

# --- SECTION 3 : TABLEAU DE BORD ---
elif selection == "Tableau de Bord":
    # (Le code du dashboard global reste tel quel car il fonctionne bien)
    st.title("Visualisation des données (Global)")
    
    fichiers_locaux = {
        "Chiens": "chiens.xlsx",
        "Moutons": "moutons.xlsx",
        "Poules, Lapins & Pigeons": "lapins.xlsx",
        "Autres Animaux": "autres-animaux.xlsx"
    }

    def charger_et_nettoyer_global():
        liste_df = []
        for cat, path in fichiers_locaux.items():
            try:
                temp_df = pd.read_excel(path)
                temp_df = temp_df.rename(columns={'nom': 'Nom', 'prix': 'Prix', 'adresse': 'Adresse'})
                temp_df['Categorie'] = cat
                liste_df.append(temp_df[['Nom', 'Prix', 'Adresse', 'Categorie']])
            except: continue
        if not liste_df: return None
        df_global = pd.concat(liste_df, ignore_index=True)
        df_global['Prix'] = df_global['Prix'].astype(str).str.replace('CFA', '', regex=False).str.replace(' ', '', regex=False).str.replace('\xa0', '', regex=False)
        df_global['Prix'] = pd.to_numeric(df_global['Prix'], errors='coerce').fillna(0).astype(int)
        def extraire_ville(adr):
            adr = str(adr).lower()
            return 'Dakar' if 'dakar' in adr else 'Autre ville'
        df_global['Ville'] = df_global['Adresse'].apply(extraire_ville)
        return df_global

    df_final = charger_et_nettoyer_global()

    if df_final is not None:
        st.success(f"Données consolidées : {len(df_final)} annonces.")
        st.subheader("1. Proportion par catégorie")
        st.bar_chart(df_final['Categorie'].value_counts())
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("2. Tranches de prix")
            bins = [0, 50000, 100000, 200000, 500000, 1000000, 10000000]
            labels = ["0-50k", "50k-100k", "100k-200k", "200k-500k", "500k-1M", "1M+"]
            df_final['Tranche'] = pd.cut(df_final['Prix'], bins=bins, labels=labels)
            st.bar_chart(df_final['Tranche'].value_counts())
        with col2:
            st.subheader("3. Répartition ville")
            st.bar_chart(df_final['Ville'].value_counts())
        
        st.dataframe(df_final)
    else:
        st.error("Impossible de charger les données.")

# --- SECTION 4 : EVALUATION ---
elif selection == "Évaluer l'application":
    st.title("Évaluation du Projet")
    st.write("Merci de nous donner votre avis via les liens ci-dessous.")
    
    # Liens vers les formulaires
    url_kobo = "https://ee.kobotoolbox.org/single/YxXH9Emb"
    url_google = "https://forms.gle/votre_lien_ici" # A remplacer par votre lien Google Forms
    
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("Ouvrir le formulaire Kobo", url_kobo, use_container_width=True)
    with col2:
        st.link_button("Ouvrir le formulaire Google Forms", url_google, use_container_width=True)
    
    st.info("Vous pouvez choisir l'une des deux plateformes pour soumettre votre évaluation.")
