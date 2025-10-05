from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

from datetime import datetime, timedelta
import sys
import os
import json

# Ajouter le chemin des scripts au PATH
sys.path.insert(0, '/opt/airflow/dags/scripts')

# Importer votre gestionnaire de base de données
from bd_manager import AODataManager

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 3),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def run_alliance_scraping():
    """
    Exécute le script de scraping Alliance Procurement
    """
    import subprocess
    
    print("🔄 Démarrage du scraping Alliance Procurement...")
    
    result = subprocess.run(
        [sys.executable, "/opt/airflow/dags/scripts/scraperAOAlliance.py"],
        capture_output=True,
        text=True,
        cwd="/opt/airflow"  # Définir le répertoire de travail
    )
    
    # Logs de débogage
    if result.stdout:
        print("=== SCRAPING STDOUT ===")
        print(result.stdout)
    if result.stderr:
        print("=== SCRAPING STDERR ===")
        print(result.stderr)
    
    # Vérifier le succès de l'exécution
    result.check_returncode()
    print("✅ Scraping Alliance terminé avec succès")

def import_to_mongodb():
    """
    Importe les nouveaux AO détectés dans MongoDB
    """
    print("🔄 Démarrage de l'importation vers MongoDB...")
    
    # Utiliser l'URL MongoDB de votre configuration Docker
    manager = AODataManager("mongodb://admin:password@mongodb:27017/AO_Database?authSource=admin")
    
    # Chemin vers le fichier des nouveaux AO
    json_file = "/opt/airflow/data/AOJsonAlliance/nouveaux_ao.json"
    
    # Vérifier si le fichier existe
    if not os.path.exists(json_file):
        print("ℹ️  Aucun fichier de nouveaux AO trouvé")
        return
    
    # Lire le fichier JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            nouveaux_ao = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture fichier JSON: {e}")
        return
    
    if not nouveaux_ao:
        print("ℹ️  Aucun nouvel AO à importer")
        return
    
    print(f"📊 {len(nouveaux_ao)} nouveaux AO détectés pour importation")
    
    # Insérer dans MongoDB
    result = manager.insert_new_ao_only(json_file, "json1")
    
    if result:
        print(f"✅ {len(result)} nouveaux AO importés avec succès dans MongoDB")
        
        # Statistiques finales
        total_ao = manager.collection.count_documents({})
        print(f"📈 Total d'AO dans la base: {total_ao}")
    else:
        print("❌ Aucun AO importé - vérifiez les logs")

def cleanup_temp_files():
    """
    Nettoyage des fichiers temporaires (optionnel)
    """
    print("🧹 Nettoyage des fichiers temporaires...")
    
    # Vous pouvez choisir de vider le fichier nouveaux_ao.json après import
    # ou le garder pour référence
    nouveaux_ao_file = "/opt/airflow/data/AOJsonAlliance/nouveaux_ao.json"
    
    if os.path.exists(nouveaux_ao_file):
        # Option 1: Vider le fichier
        with open(nouveaux_ao_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print("✅ Fichier nouveaux_ao.json vidé")
        
        # Option 2: Supprimer le fichier (décommentez si préféré)
        # os.remove(nouveaux_ao_file)
        # print("✅ Fichier nouveaux_ao.json supprimé")

# Définition du DAG
with DAG(
    'scraping_ao_alliance_automatise',
    default_args=default_args,
    description='Scraping automatique des AO Alliance + Import MongoDB',
    schedule='0 */2 * * *',  # ⏰ Toutes les 2 heures
    catchup=False,
    tags=['scraping', 'alliance', 'mongodb', 'automation'],
    max_active_runs=1,
) as dag:


    # Tâches
    start = EmptyOperator(task_id='debut_workflow')


    
    scraping_task = PythonOperator(
        task_id='scraping_alliance',
        python_callable=run_alliance_scraping,
        dag=dag,
    )
    
    import_task = PythonOperator(
        task_id='import_mongodb',
        python_callable=import_to_mongodb,
        dag=dag,
    )
    
    cleanup_task = PythonOperator(
        task_id='nettoyage_fichiers',
        python_callable=cleanup_temp_files,
        dag=dag,
    )
    
    end = EmptyOperator(task_id='fin_workflow')

    # 🔗 Définition du workflow
    start >> scraping_task >> import_task >> cleanup_task >> end

    # Alternative sans nettoyage automatique:
    # start >> scraping_task >> import_task >> end