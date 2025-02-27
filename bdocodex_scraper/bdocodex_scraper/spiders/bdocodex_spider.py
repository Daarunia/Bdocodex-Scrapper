import scrapy
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from scrapy.http import HtmlResponse

class BdoCodexSpider(scrapy.Spider):
    name = "bdocodex"
    allowed_domains = ["bdocodex.com"]
    start_urls = ["https://bdocodex.com/fr/recipes/culinary/"]

    def __init__(self, *args, **kwargs):
        super(BdoCodexSpider, self).__init__(*args, **kwargs)

        # Configurer Selenium (mode headless)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Initialiser Selenium WebDriver
        self.driver = webdriver.Chrome(options=chrome_options)

    def parse(self, response):
        """Parse la page principale et extrait les informations des recettes."""
        response = HtmlResponse(url=response.url, body=self.fetch_page_with_scroll(response.url), encoding='utf-8')

        self.logger.warning("Début de l'extraction des recettes depuis la table...")
        for row in response.css("table.table tbody tr"):
            # Récupération de l'ID, du nom et de l'icône de la recette
            recipe_id = row.css("td.dt-id::text").get()
            recipe_name = row.css("td.dt-title b::text").get()
            icon_url = row.css("td.dt-icon img::attr(src)").get()
            icon_url = response.urljoin(icon_url) if icon_url else None

            # Récupération de la profession, niveau et expérience
            levels = [lvl.strip() for lvl in row.css("td.dt-level::text").getall() if lvl.strip()]
            profession = levels[0] if len(levels) > 0 else None
            min_level = levels[1] if len(levels) > 1 else None
            exp_gain = levels[2] if len(levels) > 2 else None
            weight = levels[3] if len(levels) > 3 else None

            # Extraction des ingrédients et récompenses
            reward_cells = row.css("td.dt-reward")  # Liste des 2 cellules contenant les ingrédients et les récompenses
            ingredients = []
            rewards = []

            if len(reward_cells) >= 2:
                # Extraction des ingrédients
                for ingredient in reward_cells[0].css("div.iconset_wrapper_medium"):
                    ingredient_icon = ingredient.css("img::attr(src)").get()
                    ingredient_quantity = ingredient.css("div.quantity_small::text").get()
                    ingredients.append({
                        "icon": response.urljoin(ingredient_icon) if ingredient_icon else None,
                        "quantity": ingredient_quantity.strip() if ingredient_quantity else None
                    })

                # Extraction des récompenses finales
                for reward in reward_cells[1].css("div.iconset_wrapper_medium"):
                    reward_icon = reward.css("img::attr(src)").get()
                    reward_quantity = reward.css("div.quantity_small::text").get()
                    rewards.append({
                        "icon": response.urljoin(reward_icon) if reward_icon else None,
                        "quantity": reward_quantity.strip() if reward_quantity else None
                    })

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
            else:
                self.logger.warning("Recette sans nom trouvée, passage au suivant.")

    def fetch_page_with_scroll(self, url):
        """Ouvre une page avec Selenium, effectue un scroll progressif et récupère le HTML chargé."""
        self.logger.warning(f"Ouverture de la page {url} avec Selenium...")
        self.driver.get(url)

        scroll_pause_time = 0.5
        scroll_step = 2000
        current_scroll = 0
        scroll_height = self.driver.execute_script("return document.body.scrollHeight")

        self.logger.warning("Début du scroll pour charger le contenu...")
        while current_scroll < scroll_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_scroll});")
            current_scroll += scroll_step
            time.sleep(scroll_pause_time)
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")

        self.logger.warning("Scroll terminé. Attente du chargement final...")
        time.sleep(5)

        html = self.driver.page_source
        self.logger.warning("HTML récupéré, fermeture du driver Selenium.")
        self.driver.quit()

        return html