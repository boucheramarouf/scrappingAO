from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import urllib3

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========================
# CONFIG
# ========================
LOGIN_URL = "https://www.alliance-procurement.com/#/login"
AO_URL = "https://www.alliance-procurement.com/#/appels_offres"

EMAIL = "AO.BPCE@wissalgroup.com"
PASSWORD = "W!k3ys2023"

chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1400,900")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

all_ao_details = []


def scrap_ao_via_clics(driver, wait, elements_ao):
    """Clique sur chaque AO et extrait les détails affichés"""
    ao_details = []
    for index, element in enumerate(elements_ao, start=1):
        try:
            print(f"\n--- Clic sur AO {index}/{len(elements_ao)} ---")

            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            wait.until(EC.element_to_be_clickable(element))
            element.click()
            print("✓ AO cliqué")
            time.sleep(3)

            # Chercher les détails (modale, panneau, etc.)
            details_selectors = [
                ".ao-details", ".details-content", ".modal-content",
                ".description", ".content", "[ng-if]", "[ng-show]"
            ]

            details_text = ""
            for selector in details_selectors:
                try:
                    detail_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in detail_elements:
                        if el.is_displayed():
                            text = el.text.strip()
                            if text and len(text) > 20:
                                details_text += text + "\n\n"
                except:
                    pass

            if not details_text:
                details_text = driver.find_element(By.TAG_NAME, "body").text[:2000]

            ao_detail = {
                "index": index,
                "details": details_text,
                "date_extraction": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            ao_details.append(ao_detail)
            print(f"✓ Détails récupérés ({len(details_text)} caractères)")

            # Fermer la modale si nécessaire
            try:
                close_buttons = driver.find_elements(By.CSS_SELECTOR, ".close, [aria-label='Fermer'], button[ng-click]")
                for btn in close_buttons:
                    if btn.is_displayed():
                        btn.click()
                        break
            except:
                pass

            time.sleep(2)

        except Exception as e:
            print(f"✗ Erreur sur AO {index}: {e}")
            continue

    return ao_details


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
        print("Pas de popup CGU")

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
    print("✓ HTML de la page AO sauvegardé dans page_ao.html")

    # === TROUVER LES AO ===
    elements_ao = driver.find_elements(By.CSS_SELECTOR, "div.ao-card")  # ⚠️ À ajuster après inspection du HTML
    print(f"{len(elements_ao)} AO détectés")

    if not elements_ao:
        print("✗ Aucun AO trouvé - ajuste le sélecteur CSS selon page_ao.html")
    else:
        all_ao_details = scrap_ao_via_clics(driver, wait, elements_ao)

        with open("tous_les_ao_details.json", "w", encoding="utf-8") as f:
            json.dump(all_ao_details, f, ensure_ascii=False, indent=2)
        print("✓ Tous les AO sauvegardés dans tous_les_ao_details.json")

except Exception as e:
    print("✗ Erreur générale:", e)

finally:
    driver.quit()
    print("\n=== FIN DU SCRIPT ===")
