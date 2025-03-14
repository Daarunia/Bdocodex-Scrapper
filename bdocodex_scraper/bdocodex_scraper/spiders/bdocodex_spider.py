import scrapy
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from scrapy.http import HtmlResponse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException

class BdoCodexSpider(scrapy.Spider):
    name = "bdocodex"
    allowed_domains = ["bdocodex.com"]
    start_urls = ["https://bdocodex.com/fr/recipes/culinary/"]

    def __init__(self, *args, **kwargs):
        super(BdoCodexSpider, self).__init__(*args, **kwargs)

        # Configuration de Selenium
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Initialisation du WebDriver Selenium
        self.driver = webdriver.Chrome(options=chrome_options)
        self.items_to_scrape = set()  # Liste des URLs des items à scraper
        self.recipes = []  # Liste des recettes
        self.items = []  # Liste des items
        self.items_scraped = 0  # Compteur pour suivre le nombre d'items scrappés
        self.total_items = 0  # Nombre total d'items à scraper

    def parse(self, response):
        """Parcourt toutes les pages de la table et récupère les recettes."""
        self.driver.get(response.url)
        time.sleep(3)

        # Vérifier et fermer une éventuelle popup
        self.catch_popup()

        while True:
            response = HtmlResponse(url=self.driver.current_url, body=self.driver.page_source, encoding='utf-8')
            self.logger.warning("Extraction des recettes depuis la page...")

            max_items_per_page = 10  # Limite d'items par page
            rows = response.css("table.table tbody tr")
            rows_count = len(rows)

            self.logger.warning(f"Nombre d'éléments (lignes) trouvés : {rows_count}")

            for i, row in enumerate(rows):
                if i >= max_items_per_page:  # Limite de 10 items max
                    break  # Arrêter la boucle si on a atteint 10 items

                recipe_name = row.css("td.dt-title b::text").get()
                self.logger.warning(f"Traitement de la recette {recipe_name}...")

                if recipe_name:
                    recipe_id = row.css("td.dt-id::text").get()
                    icon_url = row.css("td.dt-icon img::attr(src)").get()
                    icon_url = response.urljoin(icon_url) if icon_url else None

                    levels = [lvl.strip() for lvl in row.css("td.dt-level::text").getall() if lvl.strip()]
                    profession = levels[0] if len(levels) > 0 else None
                    min_level = levels[1] if len(levels) > 1 else None
                    exp_gain = levels[2] if len(levels) > 2 else None
                    weight = levels[3] if len(levels) > 3 else None

                    reward_cells = row.css("td.dt-reward")
                    ingredients = []
                    rewards = []

                    if len(reward_cells) >= 2:
                        self.parse_item(ingredients, reward_cells[0].css("div.iconset_wrapper_medium"), response)
                        self.parse_item(rewards, reward_cells[1].css("div.iconset_wrapper_medium"), response)

                    # Ajouter les liens des items externes à la liste des items à scraper
                    for item_link in reward_cells[0].css("a::attr(href)").getall():
                        item_url = response.urljoin(item_link)
                        self.items_to_scrape.add(item_url)

                    # Ajouter la recette dans la liste des recettes
                    self.recipes.append({
                        "id": recipe_id,
                        "title": recipe_name,
                        "icon": icon_url,
                        "profession": profession,
                        "min_level": min_level,
                        "exp_gain": exp_gain,
                        "weight": weight,
                        "ingredients": ingredients,
                        "rewards": rewards
                    })

            # Vérifier s'il y a une page suivante et cliquer dessus
            if not self.next_page():
                break

        # Suppression des doublons dans les URLs des items à scraper
        self.items_to_scrape = list(set(self.items_to_scrape))
        self.total_items = len(self.items_to_scrape)
        self.logger.warning(f"Total d'items à scraper: {self.total_items}")

        # Scraper les items externes
        self.logger.warning("Début du scraping des items externes...")
        for item_url in self.items_to_scrape:
            yield scrapy.Request(item_url, callback=self.parse_external_item)

        # Quand tous les items sont scrappés, appeler finish_scraping
        yield scrapy.Request(url='"https://bdocodex.com/', callback=self.finish_scraping)

    def parse_external_item(self, response):
        """Visite une page externe et récupère les informations de l'item."""
        item_url = response.url
        self.logger.warning(f"Scraping de l'item à l'URL : {item_url}")

        # Utilisation de Selenium pour charger la page
        self.driver.get(item_url)

        # Attente explicite pour s'assurer que la page est bien chargée
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.card.item_info")))
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'attente du chargement de la page : {str(e)}")
            return None  # Retourne None si la page n'est pas complètement chargée

        # Récupérer l'HTML après le chargement complet de la page avec Selenium
        html_content = self.driver.page_source
        response = HtmlResponse(url=self.driver.current_url, body=html_content, encoding='utf-8')

        item_data = {}

        # Extraire les données de l'item
        if response:
            item_data["name"] = response.css("div.item_title#item_name b::text").get()
            item_data["icon"] = response.urljoin(response.css("img::attr(src)").get())
            item_data["description"] = response.css("div.card-body p::text").get()

            # Log de l'item récupéré
            self.logger.warning(f"Récupération de l'item : {item_data['name']}...")
            self.items_scraped += 1
            self.logger.warning(f"Nombre d'item scrappé : {self.items_scraped}")

        # Ne retourner que les données si elles sont valides
        if item_data:
            self.items.append(item_data)
        else:
            self.logger.warning(f"Aucun élément trouvé à l'URL : {item_url}")

    def next_page(self):
        """Clique sur 'Suivant' et attend le chargement de la nouvelle page. Retourne False si dernière page."""
        self.logger.warning("Passage à la page suivante...")

        try:
            # Sélectionner le bouton "Next"
            next_button = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.next a.page-link")))

            # Scroll jusqu'au bouton pour le rendre visible
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(1)

            # Attendre qu'il soit cliquable et cliquer dessus
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(next_button)).click()

            return True

        except ElementClickInterceptedException:
            self.logger.warning("Dernière page atteinte.")
            return False
        except TimeoutException:
            self.logger.warning("Erreur : Impossible de cliquer sur 'Suivant'.")
            return False

    def parse_item(self, items_list, html_items, response):
        """Extrait les ingrédients et récompenses d'une recette."""
        for item in html_items:
            item_icon = item.css("img::attr(src)").get()
            item_quantity = item.css("div.quantity_small::text").get()
            item_url = item.css("a::attr(href)").get()
            items_list.append({
                "icon": response.urljoin(item_icon) if item_icon else None,
                "quantity": item_quantity.strip() if item_quantity else None,
                "item_url": item_url.strip() if item_url else None
            })

    def catch_popup(self):
        """Vérifie si une pop-up de consentement est présente et clique sur le 2ème bouton."""
        try:
            self.logger.warning("Vérification de la pop-up de consentement...")

            # Attendre que la pop-up soit présente
            popup = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "qc-cmp2-ui")))

            if popup.is_displayed():
                self.logger.warning("Pop-up détectée, tentative de fermeture...")

                # Sélectionner le **deuxième bouton** dans la pop-up
                WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.XPATH, "(//div[@class='qc-cmp2-summary-buttons']//button)[2]"))).click()
                self.logger.warning("Pop-up fermée avec succès.")
                time.sleep(1)

        except TimeoutException:
            self.logger.warning("Pas de pop-up détectée.")
        except NoSuchElementException:
            self.logger.warning("Impossible de trouver le bouton de la pop-up.")

    def save_data(self):
        """Sauvegarde les recettes et les items dans un fichier JSON unique."""  
        # Combiner les deux listes (recettes et items) dans un seul dictionnaire
        data = {
            "recipes": self.recipes,  # Liste des recettes
            "items": self.items  # Liste des items
        }

        # Sauvegarder les données dans un seul fichier JSON
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        self.logger.warning("Les données ont été sauvegardées dans 'data.json'.")

    def finish_scraping(self, response):
        """Fonction de callback pour finir le scraping et fermer Selenium."""
        self.logger.warning("Tous les éléments ont été scrappés. Fermeture du WebDriver Selenium...")
        self.save_data()  # Sauvegarder les données après que tout a été scrappé
        self.close_spider()  # Fermer Selenium proprement
        self.logger.warning("Fin du scrapping.")

    def close_spider(self):
        """Ferme Selenium proprement."""
        self.logger.warning("Fermeture du WebDriver Selenium...")
        self.driver.quit()