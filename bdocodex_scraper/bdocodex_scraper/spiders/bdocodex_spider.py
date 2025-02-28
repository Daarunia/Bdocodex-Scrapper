import scrapy
import time
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

        # Configurer Selenium
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Initialiser Selenium WebDriver
        self.driver = webdriver.Chrome(options=chrome_options)

    def parse(self, response):
        """Parcourt toutes les pages de la table et récupère les recettes."""
        self.driver.get(response.url)
        time.sleep(3)

        # Vérifie et ferme une éventuelle popup
        self.cactch_popup()

        while True:
            response = HtmlResponse(url=self.driver.current_url, body=self.driver.page_source, encoding='utf-8')

            self.logger.warning("Extraction des recettes depuis la page...")
            
            max_items_per_page = 10  # Nombre maximal d'items par page
            item_count = 0  # Compteur d'items traités sur cette page

            for row in response.css("table.table tbody tr"):
                if item_count >= max_items_per_page:
                    break  # On stoppe la boucle si on a atteint 10 items

                recipe_id = row.css("td.dt-id::text").get()
                recipe_name = row.css("td.dt-title b::text").get()
                self.logger.warning(f"Traitement de la recette {recipe_name}...")

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

                if recipe_name:
                    yield {
                        "id": recipe_id,
                        "title": recipe_name,
                        "icon": icon_url,
                        "profession": profession,
                        "min_level": min_level,
                        "exp_gain": exp_gain,
                        "weight": weight,
                        "ingredients": ingredients,
                        "rewards": rewards
                    }
                item_count += 1

            # Vérifier s'il y a une page suivante et cliquer dessus
            if not self.next_page():
                break

        self.logger.warning("Fin du scraping.")
        self.close_spider()

    def next_page(self):
        """Clique sur 'Suivant' et attend le chargement de la nouvelle page. Retourne False si dernière page."""
        self.logger.warning("Passage à la page suivante...")

        try:
            # Sélectionner le bouton "Next"
            next_button = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.next a.page-link")))

            # Scroll jusqu'au bouton pour le rendre visible
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(1)  # Petite pause pour éviter les problèmes de timing

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
            items_list.append({
                "icon": response.urljoin(item_icon) if item_icon else None,
                "quantity": item_quantity.strip() if item_quantity else None
            })

    def close_spider(self):
        """Ferme Selenium proprement."""
        self.logger.warning("Fermeture du WebDriver Selenium...")
        self.driver.quit()

    def cactch_popup(self):
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
