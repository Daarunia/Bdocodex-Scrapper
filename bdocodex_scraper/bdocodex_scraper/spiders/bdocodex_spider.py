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

        # Initialiser Selenium WebDriver
        self.driver = webdriver.Chrome(options=chrome_options)

    def parse(self, response):
        self.logger.info("Ouverture de la page avec Selenium...")
        self.driver.get(response.url)

        # Attendre le chargement du lazy loading (ajuster si besoin)
        time.sleep(5)

        # Récupérer le HTML après chargement
        html = self.driver.page_source
        self.driver.quit()

        # Transformer en réponse Scrapy pour utiliser XPath / CSS selectors
        response = HtmlResponse(url=response.url, body=html, encoding='utf-8')

        # Extraction avec Scrapy (pas besoin de BeautifulSoup)
        for row in response.css("table.table tbody tr"):
            recipe_name = row.css("td:nth-child(2) a::text").get()
            if recipe_name:
                yield {"recipe": recipe_name}

    def parse_recipe(self, response):
        ingredients = response.css(".qnn-ingredients-list .qnn-list-item::text").getall()
        effects = response.css(".qnn-effects-list .qnn-list-item::text").getall()
        description = response.css(".qnn-description::text").get()

        yield {
            "title": response.meta["recipe_name"],
            "skill_level": response.meta["skill_level"],
            "energy_required": response.meta["energy_required"],
            "rewards": response.meta["rewards"],
            "ingredients": ingredients,
            "effects": effects,
            "description": description
        }
