from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import urllib3
import os
from datetime import datetime

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========================
# CONFIG
# ========================
LOGIN_URL = "https://www.alliance-procurement.com/#/login"
AO_URL = "https://www.alliance-procurement.com/#/appels_offres"

EMAIL = "AO.BPCE@wissalgroup.com"
PASSWORD = "W!k3ys2023"

# Fichiers de stockage
EXISTING_AO_FILE = "/opt/airflow/data/AOJsonAlliance/tous_les_ao_details.json"
NEW_AO_FILE = "/opt/airflow/data/AOJsonAlliance/nouveaux_ao.json"

chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1400,900")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

def load_existing_ao():
    """Charge les AO existants depuis le fichier JSON"""
    if os.path.exists(EXISTING_AO_FILE):
        try:
            with open(EXISTING_AO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_ao_data(ao_data):
    """Sauvegarde les AO dans le fichier principal"""
    with open(EXISTING_AO_FILE, 'w', encoding='utf-8') as f:
        json.dump(ao_data, f, ensure_ascii=False, indent=2)

def save_new_ao_only(new_ao_data):
    """Sauvegarde uniquement les nouveaux AO dans un fichier séparé"""
    with open(NEW_AO_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_ao_data, f, ensure_ascii=False, indent=2)

def is_ao_duplicate(new_ao, existing_ao_list):
    """Vérifie si un AO est déjà présent dans la liste existante"""
    for existing_ao in existing_ao_list:
        # Comparaison basée sur les champs clés
        if (new_ao.get('fields', {}).get('Intitulé Poste') == existing_ao.get('fields', {}).get('Intitulé Poste') and
            new_ao.get('fields', {}).get('Référence Interne') == existing_ao.get('fields', {}).get('Référence Interne') and
            new_ao.get('fields', {}).get('Date de clôture') == existing_ao.get('fields', {}).get('Date de clôture')):
            return True
    return False

def scrap_ao_via_clics(driver, wait, elements_ao, existing_ao_list):
    """Scrape les AO en détectant les doublons"""
    new_ao_details = []
    existing_count = 0
    
    for index, element in enumerate(elements_ao, start=1):
        try:
            print(f"\n--- Traitement AO {index}/{len(elements_ao)} ---")

            # Cliquer sur l'AO
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            wait.until(EC.element_to_be_clickable(element))
            element.click()
            print("✓ AO cliqué")

            # Attendre que le panneau droit se mette à jour
            wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.panel.wrapper p.ng-scope span.ng-binding")
            ))
            time.sleep(0.5)

            # Extraire les données
            fields = {}
            for p in driver.find_elements(By.CSS_SELECTOR, "div.panel.wrapper p.ng-scope"):
                spans = p.find_elements(By.CSS_SELECTOR, "span.ng-binding")
                if len(spans) >= 2:
                    label = spans[0].text.strip()
                    value = spans[1].text.strip()
                    if label:
                        fields[label] = value

            # Créer l'objet AO
            ao_detail = {
                "index": len(existing_ao_list) + len(new_ao_details) + 1,
                "fields": fields,
                "date_extraction": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            # Vérifier les doublons
            if is_ao_duplicate(ao_detail, existing_ao_list):
                print(f"⏭️  AO {index} déjà existant - ignoré")
                existing_count += 1
            else:
                new_ao_details.append(ao_detail)
                print(f"✅ Nouvel AO détecté - {len(fields)} champs récupérés")

        except Exception as e:
            print(f"❌ Erreur sur AO {index}: {e}")
            continue

    return new_ao_details, existing_count

def main():
    # Charger les AO existants
    existing_ao_list = load_existing_ao()
    print(f"📊 {len(existing_ao_list)} AO existants chargés")

    try:
        # === CONNEXION ===
        driver.get(LOGIN_URL)
        time.sleep(3)

        try:
            bouton_cgu = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Accepter') or contains(text(),'OK')]"))
            )
            bouton_cgu.click()
            print("✓ CGU acceptées")
            time.sleep(2)
        except:
            print("ℹ️ Pas de popup CGU")

        # Saisie des identifiants
        champ_email = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
        champ_email.clear()
        champ_email.send_keys(EMAIL)

        champ_password = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
        champ_password.clear()
        champ_password.send_keys(PASSWORD)

        bouton_connexion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        bouton_connexion.click()
        print("✓ Formulaire soumis")

        wait.until(lambda d: "profil" in d.current_url or "dashboard" in d.current_url or "appels" in d.current_url)
        time.sleep(5)

        # === NAVIGATION VERS PAGE AO ===
        try:
            lien_ao = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'appels_offres')]")))
            lien_ao.click()
            print("✓ Lien AO cliqué")
            time.sleep(5)
        except:
            driver.get(AO_URL)
            time.sleep(5)

        wait.until(EC.url_contains("appels_offres"))
        print("✓ Page AO chargée")

        # Sauvegarder le HTML pour inspection
        with open("page_ao.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("✓ HTML de la page AO sauvegardé")

        # === TROUVER LES AO ===
        elements_ao = driver.find_elements(By.CSS_SELECTOR, "a.list-group-item.hover-anchor.b-a.no-select.ng-scope")
        print(f"🔍 {len(elements_ao)} AO détectés sur la page")

        if not elements_ao:
            print("❌ Aucun AO trouvé - vérifiez le sélecteur CSS dans page_ao.html")
            return

        # === SCRAPER LES NOUVEAUX AO ===
        new_ao_details, existing_count = scrap_ao_via_clics(driver, wait, elements_ao, existing_ao_list)

        # === SAUVEGARDE DES RÉSULTATS ===
        if new_ao_details:
            # Mettre à jour la liste complète
            updated_ao_list = existing_ao_list + new_ao_details
            save_ao_data(updated_ao_list)
            
            # Sauvegarder uniquement les nouveaux AO pour l'import BD
            save_new_ao_only(new_ao_details)
            
            print(f"\n🎉 SCRAPING TERMINÉ AVEC SUCCÈS!")
            print(f"✅ {len(new_ao_details)} NOUVEAUX AO ajoutés")
            print(f"⏭️  {existing_count} AO existants ignorés")
            print(f"📁 Fichier principal mis à jour: {EXISTING_AO_FILE}")
            print(f"📁 Nouveaux AO pour la BD: {NEW_AO_FILE}")
            
            # Afficher les nouveaux AO
            print(f"\n📋 LISTE DES NOUVEAUX AO:")
            for i, ao in enumerate(new_ao_details, 1):
                titre = ao.get('fields', {}).get('Intitulé Poste', 'Sans titre')[:50]
                ref = ao.get('fields', {}).get('Référence Interne', 'N/A')
                print(f"   {i}. {titre}... (Ref: {ref})")
                
        else:
            print(f"\nℹ️  AUCUN NOUVEL AO TROUVÉ")
            print(f"📊 Total d'AO dans la base: {len(existing_ao_list)}")
            
            # Créer un fichier vide pour les nouveaux AO
            save_new_ao_only([])

    except Exception as e:
        print(f"❌ Erreur générale: {e}")

    finally:
        driver.quit()
        print("\n=== FIN DU SCRIPT ===")

if __name__ == "__main__":
    main()