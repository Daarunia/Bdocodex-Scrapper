# BDO Codex Scraper

Ce projet est un scraper web qui extrait des recettes culinaires depuis le site [BDO Codex](https://bdocodex.com). Il utilise **Scrapy** et **Selenium** pour naviguer sur le site et récupérer les données.

## 📌 Prérequis

Avant d'exécuter le script, assurez-vous d'avoir installé les éléments suivants sur votre machine :

- **Python 3.12**
- **Google Chrome** (dernière version)
- **Chromedriver** (compatible avec votre version de Chrome)

## 📦 Installation

Copiez-collez ces commandes dans votre terminal :

```bash
# 1. Cloner le dépôt
git clone https://github.com/votre-repo/bdocodex-scraper.git
cd bdocodex-scraper

# 2. Créer un environnement virtuel (optionnel mais recommandé)
python -m venv venv
source venv/bin/activate  # Sur macOS/Linux
venv\Scripts\activate     # Sur Windows

# 3. Installer les dépendances
pip install scrapy selenium

# 4. Vérifier l'installation de Chromedriver
chromedriver --version
google-chrome --version
```

Si **Chromedriver** n'est pas installé, téléchargez-le [ici](https://chromedriver.chromium.org/downloads) et placez-le dans le dossier du projet.

## 🚀 Utilisation

Lancez le scraper avec :

```bash
scrapy crawl bdocodex
```

Pour sauvegarder les résultats dans un fichier JSON :

```bash
scrapy crawl bdocodex -o resultats.json
```

## 📂 Résultats

Les résultats extraits incluent :

- **ID**
- **Nom**
- **Icône**
- **Métier requis** (cuisine, alchimie, etc.)
- **Niveau minimum**
- **Expérience gagnée**
- **Poids**
- **Ingrédients nécessaires**
- **Récompenses obtenues**

Les résultats seront stockés dans **resultats.json** sous forme de liste d'objets JSON.

## 🛠 Dépannage

- **Problème avec Chromedriver ?**  
  Vérifiez que la version installée correspond à votre version de **Google Chrome** :
  ```bash
  chromedriver --version
  google-chrome --version
  ```

- **Erreur `selenium.common.exceptions.TimeoutException` ?**  
  Le site peut avoir changé sa structure. Vérifiez les sélecteurs CSS/XPath dans le code.

---
🔗 Développé par Maxime Van Eygen
