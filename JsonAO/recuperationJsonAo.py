from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import json
import time
import urllib3

# Désactiver les warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========================
# CONFIG
# ========================
LOGIN_URL = "https://www.alliance-procurement.com/#/login"
AO_URL = "https://www.alliance-procurement.com/#/appels_offres"
API_URL = "https://www.alliance-procurement.com/api/get_appels_offres_fournisseur"
QUESTIONS_API_URL = "https://www.alliance-procurement.com/api/get_questions_ao_frs"
DETAILS_API_URL = "https://www.alliance-procurement.com/api/form_appels_offre_reponse"

EMAIL = "AO.BPCE@wissalgroup.com"
PASSWORD = "W!k3ys2023"

chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1400,900")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

# Liste pour stocker tous les AO avec leurs détails
all_ao_details = []

try:
    print("=== ÉTAPE 1: CONNEXION ===")
    print("Ouverture de la page de login...")
    driver.get(LOGIN_URL)
    time.sleep(3)

    # --- Accepter les CGU si popup ---
    try:
        bouton_cgu = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Accepter') or contains(text(),'OK') or contains(text(),'CGU')]"))
        )
        bouton_cgu.click()
        print("✓ CGU acceptées")
        time.sleep(2)
    except Exception as e:
        print("Pas de CGU détectées ou déjà acceptées")

    print("Remplissage du formulaire...")
    
    try:
        champ_email = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[placeholder*='email'], input[placeholder*='Email']")))
    except:
        champ_email = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='email'], #email")))
    
    champ_email.clear()
    champ_email.send_keys(EMAIL)
    time.sleep(1)

    try:
        champ_password = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[placeholder*='mot de passe'], input[placeholder*='Password']")))
    except:
        champ_password = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='password'], #password")))

    champ_password.clear()
    champ_password.send_keys(PASSWORD)
    time.sleep(1)

    try:
        bouton_connexion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], button.btn-login, button.connexion")))
    except:
        bouton_connexion = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Connexion') or contains(text(),'Login')]")))

    bouton_connexion.click()
    print("✓ Formulaire soumis")

    print("Attente de la redirection...")
    wait.until(lambda driver: "profil" in driver.current_url or "appels" in driver.current_url or "dashboard" in driver.current_url)
    print(f"✓ Redirection réussie vers: {driver.current_url}")
    time.sleep(5)

    print("\n=== ÉTAPE 2: NAVIGATION VERS LES APPELS D'OFFRES ===")
    
    try:
        lien_ao = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'appels_offres') or contains(text(), 'Appels') or contains(text(), 'AO')]")))
        lien_ao.click()
        print("✓ Clic sur le lien des AO dans le menu")
        time.sleep(5)
    except:
        print("Lien menu non trouvé, navigation directe...")
        driver.get(AO_URL)
        time.sleep(5)

    wait.until(EC.url_contains("appels_offres"))
    print(f"✓ Page AO chargée: {driver.current_url}")

    print("\n=== ÉTAPE 3: ATTENTE DU CHARGEMENT COMPLET ===")
    
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".appel-offre, .ao-item, table, .list-item, [ng-repeat]")))
        print("✓ Éléments des AO détectés")
    except:
        print("⚠ Éléments spécifiques non trouvés, continuation...")

    print("Attente supplémentaire pour le chargement JS...")
    time.sleep(10)

    print("\n=== ÉTAPE 4: RÉCUPÉRATION DES COOKIES ET TOKENS ===")
    selenium_cookies = driver.get_cookies()
    cookies_dict = {c['name']: c['value'] for c in selenium_cookies}
    
    print("Cookies récupérés:", list(cookies_dict.keys()))
    print("Valeur auth_token:", cookies_dict.get('auth_token', 'Non trouvé')[:50] + "...")

    # Récupérer également le token depuis le localStorage
    try:
        auth_token = driver.execute_script("return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');")
        if auth_token:
            print("✓ Token récupéré depuis le storage")
    except:
        print("⚠ Impossible de récupérer le token depuis le storage")

    print("\n=== ÉTAPE 5: RÉCUPÉRATION DE LA LISTE DES AO ===")
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.alliance-procurement.com",
        "Referer": "https://www.alliance-procurement.com/#/appels_offres",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    # Récupérer la liste des AO avec différents payloads
    payloads = [
        {"page": 1, "limit": 100},
        {"page": 1, "limit": 50, "statut": "all"},
        {}
    ]
    
    ao_list_data = None
    for i, payload in enumerate(payloads):
        print(f"Essai payload {i+1}: {payload}")
        response = requests.post(API_URL, headers=headers, cookies=cookies_dict, json=payload, verify=False, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Réponse 200 - Structure: {type(data)}")
            
            if isinstance(data, dict) and data.get('data'):
                ao_list_data = data
                print(f"✓ {len(ao_list_data['data'])} AO trouvés avec le payload {i+1}")
                break
            elif isinstance(data, list) and len(data) > 0:
                ao_list_data = {"data": data}
                print(f"✓ {len(data)} AO trouvés avec le payload {i+1}")
                break
            else:
                print("✗ Données vides ou structure inattendue")
        else:
            print(f"✗ Erreur {response.status_code}")
    
    if not ao_list_data or not ao_list_data.get('data'):
        print("✗ Impossible de récupérer la liste des AO")
        # Essayer une méthode alternative : scrapping direct de la page
        print("Tentative de récupération directe depuis la page...")
        try:
            elements_ao = driver.find_elements(By.CSS_SELECTOR, ".appel-offre, .ao-item, tr, li, [ng-repeat]")
            print(f"Éléments AO trouvés sur la page: {len(elements_ao)}")
            
            # Si on trouve des éléments, on va devoir cliquer sur chacun
            if len(elements_ao) > 0:
                print("Passage à la méthode de clic sur chaque AO...")
                all_ao_details = scrap_ao_via_clics(driver, wait, elements_ao)
                if all_ao_details:
                    with open("tous_les_ao_details_clics.json", "w", encoding="utf-8") as f:
                        json.dump(all_ao_details, f, ensure_ascii=False, indent=2)
                    print("✓ Données sauvegardées via méthode clics")
                driver.quit()
                exit(0)
        except Exception as e:
            print(f"Erreur lors du scrapping direct: {e}")
        
        driver.quit()
        exit(1)
    
    # Sauvegarder la liste des AO
    with open("liste_ao.json", "w", encoding="utf-8") as f:
        json.dump(ao_list_data, f, ensure_ascii=False, indent=2)
    print("✓ Liste sauvegardée dans liste_ao.json")
    
    print("\n=== ÉTAPE 6: RÉCUPÉRATION DES DÉTAILS DE CHAQUE AO ===")
    
    successful_ao = 0
    for index, ao in enumerate(ao_list_data.get('data', [])):
        try:
            print(f"\n--- Traitement de l'AO {index+1}/{len(ao_list_data.get('data', []))} ---")
            print(f"Référence: {ao.get('reference_interne', 'N/A')}")
            print(f"Titre: {ao.get('titre', 'N/A')}")
            
            # Récupérer l'ID de l'AO
            ao_id = ao.get('id')
            if not ao_id:
                print("⚠ ID de l'AO non trouvé, recherche d'identifiants alternatifs...")
                # Essayer d'autres clés possibles pour l'ID
                ao_id = ao.get('_id') or ao.get('id_ao') or ao.get('ao_id')
                if not ao_id:
                    print("✗ Aucun ID trouvé, passage au suivant")
                    continue
            
            print(f"ID de l'AO: {ao_id}")
            
            # ÉTAPE 1: Récupérer les questions de l'AO
            questions_payload = {"id_ao": ao_id}
            print(f"Envoi requête questions: {QUESTIONS_API_URL}")
            
            questions_response = requests.post(
                QUESTIONS_API_URL, 
                headers=headers, 
                cookies=cookies_dict, 
                json=questions_payload, 
                verify=False, 
                timeout=30
            )
            
            questions_data = {}
            if questions_response.status_code == 200:
                questions_data = questions_response.json()
                print(f"✓ Questions récupérées - Type: {type(questions_data)}")
                if questions_data:
                    print(f"  Données questions: {len(questions_data)} éléments")
            else:
                print(f"✗ Erreur questions: {questions_response.status_code} - {questions_response.text[:100]}")
            
            # ÉTAPE 2: Récupérer les détails complets de l'AO
            details_payload = {"id_ao": ao_id}
            print(f"Envoi requête détails: {DETAILS_API_URL}")
            
            details_response = requests.post(
                DETAILS_API_URL, 
                headers=headers, 
                cookies=cookies_dict, 
                json=details_payload, 
                verify=False, 
                timeout=30
            )
            
            details_data = {}
            if details_response.status_code == 200:
                details_data = details_response.json()
                print(f"✓ Détails récupérés - Type: {type(details_data)}")
                if details_data:
                    print(f"  Données détails: {len(details_data)} éléments")
                    successful_ao += 1
            else:
                print(f"✗ Erreur détails: {details_response.status_code} - {details_response.text[:100]}")
            
            # Combiner toutes les données
            ao_complete = {
                "info_generales": ao,
                "questions": questions_data,
                "details_complets": details_data,
                "date_extraction": time.strftime("%Y-%m-%d %H:%M:%S"),
                "statut": "succès" if details_data else "échec"
            }
            
            all_ao_details.append(ao_complete)
            
            # Sauvegarder individuellement
            filename = f"ao_{ao_id}_{index+1}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(ao_complete, f, ensure_ascii=False, indent=2)
            
            # Vérifier si le fichier n'est pas vide
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > 100:  # Fichier non vide
                    print(f"✓ AO {index+1} sauvegardé ({len(content)} caractères)")
                else:
                    print(f"⚠ Fichier très petit: {filename} ({len(content)} caractères)")
            
            # Pause pour éviter de surcharger le serveur
            time.sleep(1)
            
        except Exception as e:
            print(f"✗ Erreur lors du traitement de l'AO {index+1}: {e}")
            continue
    
    # Sauvegarder tous les AO dans un fichier unique
    print(f"\n=== SAUVEGARDE FINALE ===")
    print(f"AO traités avec succès: {successful_ao}/{len(ao_list_data.get('data', []))}")
    
    with open("tous_les_ao_details.json", "w", encoding="utf-8") as f:
        json.dump(all_ao_details, f, ensure_ascii=False, indent=2)
    
    # Vérifier la taille du fichier final
    with open("tous_les_ao_details.json", "r", encoding="utf-8") as f:
        content = f.read()
        print(f"✓ Fichier final sauvegardé ({len(content)} caractères)")
    
    print(f"✓ Total d'AO traités: {len(all_ao_details)}")

except Exception as e:
    print(f"✗ Erreur générale: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("Fermeture du navigateur...")
    driver.quit()

print("\n=== FIN DU SCRIPT ===")

def scrap_ao_via_clics(driver, wait, elements_ao):
    """Méthode alternative: cliquer sur chaque AO pour récupérer le contenu"""
    print("=== DÉBUT SCRAPPING PAR CLICS ===")
    ao_details = []
    
    for index, element in enumerate(elements_ao):
        try:
            print(f"\n--- Clic sur l'AO {index+1}/{len(elements_ao)} ---")
            
            # Faire défiler jusqu'à l'élément
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)
            
            # Attendre que l'élément soit cliquable
            element = wait.until(EC.element_to_be_clickable(element))
            
            # Cliquer sur l'AO
            element.click()
            print("✓ Clic effectué")
            time.sleep(3)
            
            # Attendre que les détails se chargent
            try:
                # Chercher les éléments de détail dans la page
                details_selectors = [
                    ".ao-details", ".details-content", ".modal-content",
                    "[ng-if]", "[ng-show]", ".content", ".description"
                ]
                
                details_text = ""
                for selector in details_selectors:
                    try:
                        detail_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for el in detail_elements:
                            if el.is_displayed():
                                text = el.text.strip()
                                if text and len(text) > 10:
                                    details_text += text + "\n\n"
                    except:
                        pass
                
                if not details_text:
                    # Essayer de récupérer le texte de toute la page modale
                    details_text = driver.find_element(By.TAG_NAME, "body").text
                
                ao_detail = {
                    "index": index,
                    "details": details_text,
                    "date_extraction": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                ao_details.append(ao_detail)
                print(f"✓ Détails récupérés ({len(details_text)} caractères)")
                
            except Exception as e:
                print(f"✗ Erreur récupération détails: {e}")
            
            # Revenir à la liste (fermer la modale ou retour)
            try:
                close_buttons = driver.find_elements(By.CSS_SELECTOR, ".close, [aria-label='Fermer'], button[ng-click]")
                for btn in close_buttons:
                    if btn.is_displayed():
                        btn.click()
                        break
            except:
                # Si pas de bouton fermer, essayer retour arrière
                driver.execute_script("window.history.back()")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"✗ Erreur lors du clic sur l'AO {index+1}: {e}")
            continue
    
    return ao_details