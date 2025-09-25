import requests
from bs4 import BeautifulSoup
import json
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Désactiver les warnings SSL (à utiliser avec précaution)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ScraperAppelsOffres:
    def __init__(self):
        # Configuration de la session avec retry strategy
        self.session = requests.Session()
        
        # Stratégie de retry
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(self.headers)
        
        # Désactiver la vérification SSL
        self.session.verify = False

    def se_connecter(self, login_page_url, login_post_url, email, password):
        """Établir la connexion au site"""
        try:
            # 1. Récupérer la page de login (GET)
            print("Récupération de la page de login...")
            response_get = self.session.get(login_page_url, timeout=30, verify=False)
            response_get.raise_for_status()
            soup = BeautifulSoup(response_get.text, 'html.parser')
            
            # Chercher les tokens CSRF
            csrf_token = None
            token_selectors = [
                'input[name="csrf_token"]',
                'input[name="authenticity_token"]',
                'input[name="token"]',
                'input[name="_token"]',
                'meta[name="csrf-token"]'
            ]
            
            for selector in token_selectors:
                element = soup.select_one(selector)
                if element:
                    csrf_token = element.get('value') or element.get('content')
                    if csrf_token:
                        break
            
            # Préparer les données de connexion
            payload = {
                'email': email,
                'password': password,
            }
            
            # Ajouter le token CSRF s'il existe
            if csrf_token:
                payload['csrf_token'] = csrf_token
                print(f"Token CSRF trouvé: {csrf_token[:20]}...")
            else:
                print("Aucun token CSRF trouvé")
            
            # Se connecter
            print("Tentative de connexion...")
            # Utiliser 'login_post_url' au lieu de 'login_page_url'
            response_post = self.session.post(login_post_url, data=payload, timeout=30, verify=False)
            response_post.raise_for_status()

            
            # Vérifier si la connexion a réussi
            if response_post.status_code == 200:
                print("✓ Connexion réussie")
                # Sauvegarder la réponse pour analyse
                with open('page_apres_connexion.html', 'w', encoding='utf-8') as f:
                    f.write(response_post.text)
                return True
            else:
                print(f"✗ Échec de la connexion: {response_post.status_code}")
                # Sauvegarder quand même pour debug
                with open('erreur_connexion.html', 'w', encoding='utf-8') as f:
                    f.write(response_post.text)
                return False
                
        except requests.exceptions.SSLError as e:
            print(f"Erreur SSL: {e}")
            print("Tentative avec vérification SSL désactivée...")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Erreur de requête: {e}")
            return False
        except Exception as e:
            print(f"Erreur lors de la connexion: {e}")
            return False

    def obtenir_html_complet(self, url, nom_fichier):
        """Obtenir et sauvegarder le HTML complet"""
        try:
            print(f"Récupération de {url}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200:
                # Sauvegarder le HTML brut
                with open(f'{nom_fichier}_brut.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                # Sauvegarder le HTML formaté avec BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                with open(f'{nom_fichier}_formate.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                
                print(f"✓ HTML sauvegardé dans {nom_fichier}_brut.html et {nom_fichier}_formate.html")
                
                # Sauvegarder aussi les en-têtes pour debug
                with open('headers_info.txt', 'w', encoding='utf-8') as f:
                    f.write(f"URL: {url}\n")
                    f.write(f"Status: {response.status_code}\n")
                    f.write("Headers:\n")
                    for key, value in response.headers.items():
                        f.write(f"  {key}: {value}\n")
                
                return soup
            else:
                print(f"✗ Erreur HTTP: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Erreur: {e}")
            return None

    def analyser_structure(self, soup):
        """Analyser la structure HTML pour trouver des patterns"""
        print("\n=== ANALYSE DE LA STRUCTURE ===")
        
        # Compter les balises principales
        balises = ['div', 'table', 'tr', 'li', 'article', 'section']
        for balise in balises:
            elements = soup.find_all(balise)
            if elements:
                print(f"{balise.upper()}: {len(elements)} éléments trouvés")
                
                # Trouver les classes les plus communes
                classes = {}
                for el in elements[:20]:  # Regarder les 20 premiers
                    if el.get('class'):
                        for cls in el.get('class'):
                            classes[cls] = classes.get(cls, 0) + 1
                
                if classes:
                    print(f"  Classes communes: {dict(sorted(classes.items(), key=lambda x: x[1], reverse=True)[:5])}")

# Configuration - À ADAPTER
CONFIG = {
    'login_page_url': 'https://www.alliance-procurement.com/#/login', 
    'login_post_url': 'https://www.alliance-procurement.com/api/login',  
    'ao_url': 'https://www.alliance-procurement.com/#/appels_offres',
    'email': 'AO.BPCE@wissalgroup.com',
    'password': 'W!k3ys2023'
}

# Utilisation
if __name__ == "__main__":
    scraper = ScraperAppelsOffres()
    
    # Étape 1: Se connecter
    if scraper.se_connecter(CONFIG['login_page_url'], CONFIG['login_post_url'], CONFIG['email'], CONFIG['password']):
        # Étape 2: Obtenir le HTML des appels d'offres
        soup = scraper.obtenir_html_complet(CONFIG['ao_url'], 'appels_offres')
        
        if soup:
            # Étape 3: Analyser la structure
            scraper.analyser_structure(soup)
            
            print("\n" + "="*50)
            print("✓ Les fichiers HTML ont été sauvegardés :")
            print("- appels_offres_brut.html : HTML brut")
            print("- appels_offres_formate.html : HTML formaté")
            print("- headers_info.txt : informations des en-têtes")
            print("\nMaintenant vous pouvez ouvrir ces fichiers")
            print("et voir la structure pour adapter les sélecteurs.")
        else:
            print("Échec de la récupération du HTML")
    else:
        print("Échec de la connexion")