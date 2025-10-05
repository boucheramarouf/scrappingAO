# -*- coding: utf-8 -*-
# pro_unity_scraper_otp_debug_fixed.py
import os, json, time, urllib3, re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
# ========= CONFIG =========
LOGIN_URL = "https://platform.pro-unity.com/login"
AO_URL    = "https://platform.pro-unity.com/Supplier/jobs/newopportunities"
EMAIL     = os.getenv("PU_EMAIL")    or "bouchera.marouf@wi-keys.com"
PASSWORD  = os.getenv("PU_PASSWORD") or "W1keys@2025"
 
chrome_options = Options()
chrome_options.add_argument("--window-size=1400,900")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
# chrome_options.add_argument("--headless=new")  # si besoin
 
def wait_and_click(driver, locator, timeout=8):
    try:
        el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
        return True
    except:
        return False
 
def accept_cookies(driver, wait):
    try:
        cookie_selectors = [
            "#onetrust-accept-btn-handler",
        ]
        for selector in cookie_selectors:
            if wait_and_click(driver, (By.CSS_SELECTOR, selector), 3):
                print("✅ Cookies acceptés")
                time.sleep(0.6)
                return True
        # fallback xpath
        if wait_and_click(driver, (By.XPATH, "//button[contains(., 'Accepter') or contains(., 'Accept') or contains(., 'OK')]"), 3):
            print("✅ Cookies acceptés (xpath)")
            time.sleep(0.6)
            return True
        print("ℹ️ Aucune bannière cookies détectée")
        return False
    except Exception as e:
        print(f"ℹ️ Gestion cookies: {e}")
        return False
 
def close_marketing_modal(driver):
    """Ferme la fenêtre modale de marketing"""
    try:
        if wait_and_click(driver, (By.CSS_SELECTOR, "[data-cy='close-marketing-modal-button']"), 3):
            print("✅ Modale fermée (data-cy)"); return True
        if wait_and_click(driver, (By.CSS_SELECTOR, ".close-btn.icon-close-small"), 3):
            print("✅ Modale fermée (.close-btn)"); return True
        if wait_and_click(driver, (By.CSS_SELECTOR, ".cdk-overlay-backdrop"), 2):
            print("✅ Modale fermée (backdrop)"); return True
        return False
    except Exception as e:
        print(f"⚠️ Erreur modale: {e}")
        return False
 
def wait_for_otp_input(driver, wait):
    """Attend que le formulaire OTP soit visible et bloque l'exécution jusqu'à la saisie"""
    print("⏳ Vérification OTP…")
    try:
        otp_inputs = wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "input.digit-input, input.input-text, input[type='text'][inputmode='numeric'], input[placeholder*='code' i]")
            )
        )
        print("✅ Formulaire OTP détecté")
        code = input("👉 Code OTP (6 chiffres) : ").strip()
        while not code.isdigit() or len(code) != 6:
            print("❌ Code invalide. 6 chiffres.")
            code = input("👉 Code OTP (6 chiffres) : ").strip()
        if len(otp_inputs) > 1:
            for i, d in enumerate(code[:len(otp_inputs)]):
                otp_inputs[i].clear(); otp_inputs[i].send_keys(d); time.sleep(0.05)
        else:
            otp_inputs[0].clear(); otp_inputs[0].send_keys(code)
        otp_inputs[-1].send_keys(Keys.ENTER)
        print("✅ OTP soumis")
        return True
    except Exception:
        print("ℹ️ Aucun OTP requis")
        return False
 
def do_login(driver, wait):
    print("🚀 Connexion…")
    driver.get(LOGIN_URL)
    time.sleep(1.2)
    accept_cookies(driver, wait)
 
    print("📧 Saisie email…")
    email_input = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "input[type='email'], input[name*='email' i], input[placeholder*='email' i]")
    ))
    email_input.clear(); email_input.send_keys(EMAIL); email_input.send_keys(Keys.ENTER)
 
    print("🔑 Saisie mot de passe…")
    pwd_input = wait.until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, "input[type='password'], pu-password-input input, input[placeholder*='password' i]")
    ))
    pwd_input.clear(); pwd_input.send_keys(PASSWORD); pwd_input.send_keys(Keys.ENTER)
 
    time.sleep(2.0)
    wait_for_otp_input(driver, wait)
 
    try:
        WebDriverWait(driver, 25).until(EC.any_of(
            EC.url_contains("/Supplier"),
            EC.presence_of_element_located((By.CSS_SELECTOR, "header, [data-testid='dashboard'], [data-cy='opportunities-menu']"))
        ))
        print("✅ Connecté")
    except Exception:
        print("⚠️ État connecté incertain (on continue)")
 
# ================ LISTE (on charge >10 avec scroll) ================
def wait_job_list_ready(driver, timeout=30):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job-item"))
    )
 
def get_expected_count(driver):
    """Lit 'NN New opportunities' si présent (pour savoir quand s'arrêter)."""
    try:
        els = driver.find_elements(By.XPATH, "//*[contains(normalize-space(.),'New opportunities')]")
        for el in els:
            txt = (el.text or "").strip()
            m = re.search(r"\b(\d{1,4})\b", txt)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return None
 
def scroll_once_and_maybe_click_more(driver):
    """Fait défiler + clique un éventuel bouton 'Load/Show more'."""
    # bouton "Load more" si présent
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(.,'Load more') or contains(.,'Show more')]")
        if btn.is_displayed():
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
    except Exception:
        pass
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.6)
 
# ================ DÉTAIL (tout extraire sous <app-ta-job-post-details>) ================
DETAIL_URL_REGEX = r".*/Supplier/job-posts/([0-9a-fA-F-]+)/details$"
 
def _q(root, css):
    try:
        return root.find_element(By.CSS_SELECTOR, css)
    except Exception:
        return None
 
def _text(el):
    if not el:
        return ""
    try:
        inner = el.get_attribute("innerText") or ""
    except Exception:
        inner = ""
    try:
        tcont = el.get_attribute("textContent") or ""
    except Exception:
        tcont = ""
    return (tcont if len(tcont.strip()) > len(inner.strip()) else inner).strip()
 
def _qt(root, css):
    return _text(_q(root, css))
 
def get_job_root(driver, timeout=25):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "app-ta-job-post-details"))
    )
 
def wait_job_detail_ready(driver, timeout=25):
    WebDriverWait(driver, timeout).until(EC.any_of(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "app-ta-job-post-details")),
        EC.presence_of_element_located((By.CSS_SELECTOR, "app-ta-job-post-details"))
    ))
 
def expand_all_view_more_in(root, driver):
    try:
        btns = root.find_elements(By.XPATH, ".//span[contains(@class,'view') and contains(normalize-space(.),'View more')]")
        for b in btns:
            if b.is_displayed():
                try:
                    driver.execute_script("arguments[0].click();", b)
                except Exception:
                    try: b.click()
                    except Exception: pass
    except Exception:
        pass
 
def extract_summary_panels(root) -> dict:
    out = {}
    # Left: Duration / Location
    left = _q(root, "app-job-post-summary .left-box")
    if left:
        out["duration_lines"]  = [ _text(li) for li in left.find_elements(By.CSS_SELECTOR, "ul.reset-list > li") ]
        out["location_address"] = _qt(left, "pu-remote-option-tag .remote-option--address")
        out["remote_option"]    = _qt(left, "pu-remote-option-tag .remote-option")
    # Middle: Rate / Payment
    mid = _q(root, "app-job-post-summary .middle-box")
    if mid:
        rv = _q(mid, "rate-viewer")
        out["rate_block"]    = _text(rv) if rv else _text(mid)
        out["payment_items"] = [ _text(li) for li in mid.find_elements(By.CSS_SELECTOR, ".payment-list li") ]
    # Right: Tender / Contracting party / MSP (via XPath sur le H3)
    right = _q(root, "app-job-post-summary .right-box")
    if right:
        out["tender_block"] = _text(_q(right, "public-procurement-container")) or ""
        try:
            cp_span = right.find_element(By.XPATH, ".//h3[normalize-space()='Contracting party']/following::ul[1]//li//div[contains(@class,'details')]//span")
            out["contracting_party"] = _text(cp_span)
        except Exception:
            pass
        try:
            cp_a = right.find_element(By.XPATH, ".//h3[normalize-space()='Contracting party']/following::ul[1]//li//div[contains(@class,'details')]//a")
            out["framework_agreement_download"] = _text(cp_a)
        except Exception:
            pass
        try:
            msp_span = right.find_element(By.XPATH, ".//h3[contains(normalize-space(),'Managed service provider')]/following::ul[1]//li//div[contains(@class,'details')]//span")
            out["msp"] = _text(msp_span)
        except Exception:
            pass
    return out
 
def parse_details_accordion(driver, root) -> dict:
    out = {"job_type":"", "description_acc":"", "roles":[], "skills":[], "languages":[], "locations":{}}
    # ul.details-list sous l’accordion "Details"
    ul = None
    for xp in [
        ".//pu-accordion-group[contains(@class,'first-accordion')]//ul[contains(@class,'details-list')]",
        ".//ul[contains(@class,'details-list')]"
    ]:
        els = root.find_elements(By.XPATH, xp)
        if els:
            ul = els[0]; break
    if not ul:
        return out
 
    expand_all_view_more_in(ul, driver)
    lis = ul.find_elements(By.XPATH, "./li")
    current = None
 
    def header_norm(t): return re.sub(r"\s+", " ", (t or "").strip()).lower()
 
    for li in lis:
        cls = li.get_attribute("class") or ""
        if "header" in cls:
            current = header_norm(_text(li))
            continue
        if not current:
            continue
 
        if current == "job type":
            out["job_type"] = _text(li)
 
        elif current == "description":
            desc_el = None
            for xp in [
                ".//div[contains(@class,'container-description')]",
                ".//div[contains(@class,'request-for-proposal-container-description')]",
                ".//div[contains(@class,'quill-styles')]",
                "."
            ]:
                els = li.find_elements(By.XPATH, xp)
                if els:
                    desc_el = els[0]; break
            out["description_acc"] = _text(desc_el)
 
        elif current == "roles":
            spans = li.find_elements(By.XPATH, ".//span")
            title = _text(spans[0]) if spans else _text(li)
            mandatory = "mandatory" in title.lower()
            title = re.sub(r"\(mandatory\).*", "", title, flags=re.I).strip()
            exp_label, exp_value = "Most recent experience", ""
            if len(spans) >= 2:
                details = _text(spans[1])
                m = re.search(r"(Most\s+recent\s+experience)\s+(.*)$", details, flags=re.I)
                if m:
                    exp_label, exp_value = m.group(1), m.group(2).strip()
                else:
                    exp_value = details
            out["roles"].append({"title": title, "mandatory": mandatory,
                                 "experience_label": exp_label, "experience_value": exp_value})
 
        elif current == "skills":
            spans = li.find_elements(By.XPATH, ".//span")
            if not spans: continue
            name = _text(spans[0])
            details = _text(spans[1]) if len(spans)>1 else ""
            m = re.search(r"Level\s+([A-Za-z ]+)", details, flags=re.I)
            level = m.group(1).strip() if m else ""
            m = re.search(r"Most\s+recent\s+experience\s+([^\n]+)$", details, flags=re.I)
            recent = m.group(1).strip() if m else ""
            out["skills"].append({"name": name, "level": level, "recent_experience": recent})
 
        elif current == "languages":
            spans = li.find_elements(By.XPATH, ".//span")
            if not spans: continue
            lang = _text(spans[0])
            details = _text(spans[1]) if len(spans)>1 else ""
            m = re.search(r"Level\s+([^\n]+)$", details, flags=re.I)
            level = m.group(1).strip() if m else ""
            out["languages"].append({"name": lang, "level": level})
 
        elif current == "locations":
            spans = li.find_elements(By.XPATH, ".//span")
            label = _text(spans[0]) if spans else ""
            value = _text(spans[1]) if len(spans)>1 else _text(li)
            if label:
                out["locations"][label] = value
 
    return out
 
def extract_full_job_detail(driver) -> dict:
    wait_job_detail_ready(driver, 25)
    root = get_job_root(driver, 25)
    expand_all_view_more_in(root, driver)
 
    out = {"detail_url": driver.current_url}
    m = re.match(DETAIL_URL_REGEX, driver.current_url or "")
    out["job_id"] = m.group(1) if m else ""
 
    # En-tête
    out["title"]          = _qt(root, "h1 [data-cy='module-title'], .jp-page-title")
    out["jobpost_name"]   = _qt(root, ".jobpost-name")
    out["company"]        = _qt(root, ".company-name")
    out["published_date"] = _qt(root, ".company-name .published-date")
    out["deadline"]       = _qt(root, ".status .status-container")
 
    # Résumés
    out.update(extract_summary_panels(root))
 
    # Description centrale (si présente)
    central_desc = ""
    for sel in [
        "pu-view-more .container-description",
        ".container-description.quill-styles",
        ".request-for-proposal-container-description.quill-styles",
        "[data-cy='job-description']",
        ".job-description",
        "pu-rich-text",
        ".content .quill-styles",
        ".description"
    ]:
        el = _q(root, sel)
        if el:
            central_desc = _text(el); break
    out["description"] = central_desc
 
    # Accordion "Details"
    out.update(parse_details_accordion(driver, root))
    return out
 
# ================ TON FONCTIONNEMENT QUI “MARCHAIT”, MAIS BOOSTÉ ================
def scrape_new_opportunities_descriptions(driver):
    """
    On garde le même nom de fonction qu'avant, mais :
      - on scrolle pour charger TOUTES les cartes,
      - on clique chaque offre au fur et à mesure (sans perdre la position),
      - on extrait TOUT le détail (pas seulement la description).
    """
    results = []
    seen = set()
    expected = get_expected_count(driver)  # peut être None
    no_change_loops = 0
    max_loops = 200
 
    for loop in range(max_loops):
        # cartes visibles actuellement
        triggers = driver.find_elements(By.CSS_SELECTOR, "[data-cy^='job-post-name-link']")
        new_dc = []
        for t in triggers:
            dc = t.get_attribute("data-cy")
            if dc and dc not in seen:
                new_dc.append(dc)
 
        if not new_dc:
            no_change_loops += 1
        else:
            no_change_loops = 0
 
        for dc in new_dc:
            # re-récupérer l'élément (éviter stale) et cliquer
            try:
                trigger = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, f"[data-cy='{dc}']"))
                )
                title = (trigger.text or "").strip()
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", trigger)
                try:
                    trigger.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", trigger)
 
                detail = extract_full_job_detail(driver)
                detail["title_from_list"] = title
                results.append(detail)
                seen.add(dc)
                print(f"✓ {len(seen)} — {title[:70]} (desc {len(detail.get('description',''))} ch.)")
 
            finally:
                # revenir à la liste
                try:
                    driver.back()
                    wait_job_list_ready(driver, 20)
                except Exception:
                    driver.get(AO_URL)
                    wait_job_list_ready(driver, 20)
 
        # conditions d'arrêt
        if expected and len(seen) >= expected:
            break
        if no_change_loops >= 6:
            # tenter un petit “réveil” avant de sortir
            driver.execute_script("window.scrollBy(0, -400);"); time.sleep(0.3)
            no_change_loops = 0
 
        # charger la suite
        scroll_once_and_maybe_click_more(driver)
 
    return results
 
# ================ (ton scraper API existant, inchangé) ================
def scrap_json_api_fixed(driver):
    print("📡 Récupération des données via API (version corrigée)...")
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": AO_URL,
        "X-Requested-With": "XMLHttpRequest"
    }
    s = requests.Session()
    for k, v in cookies.items():
        s.cookies.set(k, v)
    results = []
    page = 1
    base_url = "https://platform.pro-unity.com/api/vnext/supplier/jobposts"
    while True:
        print(f"\n📄 Récupération page {page}...")
        url = f"{base_url}?page.PageNumber={page}&page.PageSize=50&filter.category=NewOpportunities"
        try:
            print(f"   URL: {url}")
            response = s.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"   ❌ Erreur HTTP {response.status_code}")
                break
            data = response.json()
            print(f"   ✅ Données récupérées, clés: {list(data.keys())}")
            jobposts = data.get("response", [])
            if not jobposts:
                print("✅ Fin des pages (aucun job trouvé)")
                break
            print(f"📋 {len(jobposts)} AO trouvés sur la page {page}")
            for i, job in enumerate(jobposts, 1):
                job_id = job.get("id")
                if not job_id:
                    print(f"    ⚠️ AO {i} sans ID, ignoré")
                    continue
                print(f"  🔍 Détails AO {i}/{len(jobposts)}: {job.get('title', 'Sans titre')[:50]}...")
                detail_url = f"{base_url}/{job_id}"
                try:
                    detail_response = s.get(detail_url, headers=headers, timeout=30)
                    if detail_response.status_code == 200:
                        detail = detail_response.json()
                        ao_data = {
                            "id": job_id,
                            "titre": job.get("title"),
                            "reference": job.get("reference"),
                            "statut": job.get("status"),
                            "date_creation": job.get("createdDate"),
                            "date_limite": job.get("deadlineDate"),
                            "description": job.get("description"),
                            "categorie": job.get("category"),
                            "localisation": job.get("location"),
                            "client": job.get("client", {}),
                            "budget": job.get("budget"),
                            "duree": job.get("duration"),
                            "competences_requises": job.get("requiredSkills", []),
                            "details_complets": detail,
                            "date_extraction": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        ao_data = {k: v for k, v in ao_data.items() if v is not None}
                        results.append(ao_data)
                        print(f"    ✅ Détails récupérés - Ref: {job.get('reference', 'N/A')}")
                    else:
                        print(f"    ❌ Erreur HTTP {detail_response.status_code} pour les détails")
                except Exception as e:
                    print(f"    ❌ Erreur détails AO {i}: {e}")
            current_page = data.get("currentPage", 0)
            total_results = data.get("totalResults", 0)
            has_more = data.get("hasMoreResults", False)
            print(f"   📊 Page {current_page}/{total_results} - Plus de résultats: {has_more}")
            if not has_more:
                print("✅ Dernière page atteinte")
                break
            page += 1
            time.sleep(1)
        except Exception as e:
            print(f"❌ Erreur lors de la récupération page {page}: {e}")
            break
    return results
 
# ================ MAIN ================
def main():
    driver = webdriver.Chrome(options=chrome_options)
    wait   = WebDriverWait(driver, 30)
 
    try:
        do_login(driver, wait)
 
        print("🌐 Navigation vers la page des opportunités...")
        driver.get(AO_URL)
        time.sleep(2)
 
        print("🔄 Vérification de la présence d'une modale marketing...")
        close_marketing_modal(driver)
        time.sleep(1)
 
        # attendre que la liste soit présente
        wait_job_list_ready(driver, 30)
 
        # --- Extraction par clic sur chaque carte (boostée) ---
        print("📝 Extraction complète (ouverture de chaque offre)…")
        descriptions = scrape_new_opportunities_descriptions(driver)
 
        # Sauvegarder les détails
        with open("/opt/airflow/data/AOJsonProUnity/pro_unity_descriptions.json", "w", encoding="utf-8") as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
        print(f"💾 {len(descriptions)} fiches enregistrées -> pro_unity_descriptions.json")
 
        # (Optionnel) garder l’API si tu veux comparer :
        # results = scrap_json_api_fixed(driver)
        # with open("pro_unity_ao_fixed.json", "w", encoding="utf-8") as f:
        #     json.dump(results, f, ensure_ascii=False, indent=2)
        # print(f"💾 Exporté {len(results)} AO -> pro_unity_ao_fixed.json")
 
    except Exception as e:
        print(f"⛔ Erreur générale: {e}")
        with open("error_page_fixed.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("💾 Page d'erreur sauvegardée: error_page_fixed.html")
        raise
    finally:
        driver.quit()
 
if __name__ == "__main__":
    main()