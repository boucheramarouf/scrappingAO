from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

class ScraperSeleniumAO:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Optionnel : lance Chrome en mode headless
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        self.driver = webdriver.Chrome(options=chrome_options)

    def se_connecter(self, login_url, email, password):
        try:
            print("Ouverture de la page de connexion...")
            self.driver.get(login_url)

            # Sauvegarder le HTML initial pour debug
            with open("debug_login_ao.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)

            wait = WebDriverWait(self.driver, 20)

            # ⚠️ Ces sélecteurs doivent être vérifiés dans debug_login_ao.html
            champ_email = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[placeholder*='Email']"))
            )
            champ_password = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[placeholder*='Mot de passe']"))
            )
            bouton_connexion = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], button.login-button"))
            )

            champ_email.send_keys(email)
            champ_password.send_keys(password)
            bouton_connexion.click()

            # Attendre une indication claire de connexion réussie
            wait.until(EC.url_contains("#/appels_offres"))
            print("✓ Connexion réussie et redirection détectée.")
            return True
        except Exception as e:
            print(f"✗ Erreur de connexion : {e}")
            return False

    def obtenir_html_complet(self, url, nom_fichier):
        try:
            print(f"Accès à {url} ...")
            self.driver.get(url)

            wait = WebDriverWait(self.driver, 20)
            # ⚠️ Adapter ce sélecteur à un élément unique de la page des AO
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.appel-offre-card, table.appels-offres"))
            )

            time.sleep(3)  # Laisse le temps pour que tout le contenu dynamique soit chargé

            page_source = self.driver.page_source
            with open(f"{nom_fichier}.html", "w", encoding="utf-8") as f:
                f.write(page_source)

            soup = BeautifulSoup(page_source, "html.parser")
            print(f"✓ HTML final sauvegardé dans {nom_fichier}.html")
            return soup
        except Exception as e:
            print(f"✗ Erreur lors de la récupération de la page : {e}")
            return None

    def fermer(self):
        self.driver.quit()


# ========================
# Utilisation
# ========================
CONFIG = {
    'login_url': 'https://www.alliance-procurement.com/#/login',
    'ao_url': 'https://www.alliance-procurement.com/#/appels_offres',
    'email': 'AO.BPCE@wissalgroup.com',
    'password': 'W!k3ys2023'
}

if __name__ == "__main__":
    scraper = ScraperSeleniumAO()

    if scraper.se_connecter(CONFIG['login_url'], CONFIG['email'], CONFIG['password']):
        soup = scraper.obtenir_html_complet(CONFIG['ao_url'], "appels_offres_selenium")
        if soup:
            print("Exemple d’éléments trouvés :")
            for item in soup.select("div, li, article")[:5]:
                print(item.text.strip()[:100])

    scraper.fermer()
