import json
import pymongo
import uuid
from datetime import datetime
from typing import Dict, Any, List

class AODataManager:
    def __init__(self, connection_string: str, db_name: str = "AO_Database"):
        self.client = pymongo.MongoClient(connection_string)
        self.db = self.client[db_name]
        self.collection = self.db["Appel_offre"]

    def _get_base_document(self) -> Dict[str, Any]:
        """Structure de base pour garantir que tous les champs existent"""
        return {
            "id": str(uuid.uuid4()),
            "post": None,
            "client": None,
            "date_publication": None,
            "date_cloture": None,
            "contact": None,
            "TJM": None,
            "debut_mission": None,
            "fin_mission": None,
            "duree_mission": None,
            "adresse_mission": None,
            "modalites_payement": None,
            "modalites_travail": None,
            "details": None,
            "competences_requises": [],
            "date_extraction": None,
            "date_import": datetime.now(),
            "source": None
        }

    def transform_json1(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforme les données du premier JSON vers le schéma unifié"""
        base = self._get_base_document()
        fields = raw_data.get("fields", {})

        base.update({
            "post": fields.get("Intitulé Poste"),
            "client": fields.get("Client"),
            "date_publication": fields.get("Date d'ouverture"),
            "date_cloture": fields.get("Date de clôture"),
            "contact": fields.get("Référent"),
            "TJM": fields.get("TJM"),
            "debut_mission": fields.get("Début Prestation"),
            "fin_mission": fields.get("Fin Prestation"),
            "duree_mission": fields.get("Durée ou période"),
            "adresse_mission": fields.get("Lieu"),
            "details": fields.get("Commentaire"),
            "competences_requises": self._extract_skills_from_json1(fields.get("Infos Complémentaires", "")),
            "date_extraction": raw_data.get("date_extraction"),
            "source": "alliance_procurement"
        })
        return base

    def transform_json2(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforme les données du deuxième JSON vers le schéma unifié"""
        base = self._get_base_document()

        # Titre du poste
        post = None
        if raw_data.get("roles"):
            if isinstance(raw_data["roles"], list) and raw_data["roles"]:
                post = raw_data["roles"][0].get("title")
            elif isinstance(raw_data["roles"], dict):
                post = raw_data["roles"].get("title")

        base.update({
            "post": post or raw_data.get("title"),
            "client": raw_data.get("company"),
            "date_publication": raw_data.get("published_date"),
            "date_cloture": raw_data.get("deadline"),
            "TJM": raw_data.get("rate_block"),
            "debut_mission": self._extract_dates_from_json2(raw_data.get("duration_lines", [])),
            "fin_mission": self._extract_dates_from_json2(raw_data.get("duration_lines", [])),
            "duree_mission": self._extract_duration_from_json2(raw_data.get("duration_lines", [])),
            "adresse_mission": raw_data.get("location_address") or raw_data.get("locations", {}).get("Main address"),
            "modalites_payement": raw_data.get("payment_items", []),
            "modalites_travail": raw_data.get("remote_option"),
            "details": raw_data.get("description") or raw_data.get("description_acc"),
            "competences_requises": [
                {"name": skill.get("name"), "level": skill.get("level")}
                for skill in raw_data.get("skills", [])
            ],
            "source": "pro_unity"
        })
        return base

    def _extract_skills_from_json1(self, details: str) -> List[Dict[str, str]]:
        """Extrait les compétences depuis JSON1"""
        skills = []
        if "Compétences techniques" in details:
            lines = details.splitlines()
            for line in lines:
                if "-" in line and any(word in line for word in ["Junior", "Confirmé", "Expert", "Impératif", "Souhaitable"]):
                    parts = line.split("-")
                    if len(parts) >= 2:
                        skills.append({"name": parts[0].strip(), "level": parts[1].strip()})
        return skills

    def _extract_dates_from_json2(self, duration_lines: List[str]) -> str:
        if duration_lines:
            return duration_lines[0]
        return None

    def _extract_duration_from_json2(self, duration_lines: List[str]) -> str:
        if len(duration_lines) > 1:
            return duration_lines[1]
        return None

    def insert_new_ao_only(self, json_file: str, source_type: str):
        """Insère uniquement les nouveaux AO depuis le fichier spécifique"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except FileNotFoundError:
            print(f"❌ Fichier {json_file} non trouvé")
            return []
        except json.JSONDecodeError:
            print(f"❌ Erreur de lecture du fichier {json_file}")
            return []

        if not json_data:
            print(f"ℹ️  Aucun nouveau AO à insérer depuis {source_type}")
            return []

        transformed_data = []
        for item in json_data:
            if source_type == "json1":
                transformed = self.transform_json1(item)
            elif source_type == "json2":
                transformed = self.transform_json2(item)
            else:
                continue
            transformed_data.append(transformed)

        if transformed_data:
            result = self.collection.insert_many(transformed_data)
            print(f"✅ {len(result.inserted_ids)} NOUVEAUX AO insérés depuis {source_type}")
            return result.inserted_ids
        
        return []

# Dans bd_manager.py - modifier la connexion
if __name__ == "__main__":
    # Pour l'exécution dans Docker
    manager = AODataManager("mongodb://admin:password@mongodb:27017/AO_Database?authSource=admin")

    print("🚀 DÉBUT DE L'IMPORT DES NOUVEAUX AO")
    
    # Insérer uniquement les nouveaux AO
    nouveaux_alliance = manager.insert_new_ao_only("/opt/airflow/data/AOJsonAlliance/nouveaux_ao.json", "json1")
    
    # Pour ProUnity (garder l'ancienne méthode ou adapter selon besoin)
    # try:
    #     with open('data/AOJsonProUnity/pro_unity_descriptions.json', 'r', encoding='utf-8') as f:
    #         json2_data = json.load(f)
    #     # Ici vous pouvez aussi implémenter une logique de détection de doublons
    #     manager.insert_ao(json2_data, "json2")
    # except FileNotFoundError:
    #     print("ℹ️  Fichier ProUnity non trouvé")

    # Vérification finale
    total_ao = manager.collection.count_documents({})
    nouveaux_total = len(nouveaux_alliance)
    
    print(f"\n📊 RÉCAPITULATIF FINAL:")
    print(f"   • Nouveaux AO ajoutés: {nouveaux_total}")
    print(f"   • Total d'AO dans la base: {total_ao}")