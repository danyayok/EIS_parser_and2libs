import requests
from bs4 import BeautifulSoup

class parser_zakazi:
    def __init__(self):
        self.zakaz_all = []
        self.fast_zakaz_all = []
        self.second_one = 0
        self.session = requests.Session()
        self.session.headers.update({
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/90.0.4430.93 Safari/537.36")
            })
    def parse_page(self, count):
        url = f"https://zakupki.gov.ru/epz/order/extendedsearch/results.html?searchString=&morphology=on&search-filter=%D0%94%D0%B0%D1%82%D0%B5+%D0%BE%D0%B1%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F&pageNumber={count + 1}&sortDirection=false&recordsPerPage=_10&showLotsInfoHidden=false&savedSearchSettingsIdHidden=&sortBy=UPDATE_DATE&fz44=on&fz223=on&af=on&ca=on&pc=on&pa=on&placingWayList=&selectedLaws=&priceFromGeneral=&priceFromGWS=&priceFromUnitGWS=&priceToGeneral=&priceToGWS=&priceToUnitGWS=&currencyIdGeneral=-1&publishDateFrom=&publishDateTo=&applSubmissionCloseDateFrom=&applSubmissionCloseDateTo=&customerIdOrg=&customerFz94id=&customerTitle=&okpd2Ids=&okpd2IdsCodes="
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, features="html.parser")
        zakazi = soup.find_all("div", class_="search-registry-entry-block box-shadow-search-input")
        return zakazi
    def do_zakaz(self, zakaz):
        # Собираем необходимые блоки
        id_stat_block = zakaz.find("div", class_="d-flex registry-entry__header-mid align-items-center")
        right_block = zakaz.find("div", class_="col col d-flex flex-column registry-entry__right-block b-left")
        data_block = right_block.find("div", class_="data-block mt-auto")
        published = data_block.find_all("div", "col-6")
        # Сами собираемые данные из блоков выше
        date_published = published[0].find("div", class_="data-block__value").get_text(strip=True)
        date_update = published[1].find("div", class_="data-block__value").get_text(strip=True)
        status = id_stat_block.find("div", class_="registry-entry__header-mid__title text-normal").get_text(strip=True)
        title = zakaz.find("div", class_="registry-entry__body-block").find("div", class_="registry-entry__body-value").get_text(strip=True)
        id = id_stat_block.find("a").get_text(strip=True)
        zakazchik = zakaz.find("div", class_="registry-entry__body-href").get_text(strip=True)
        price = right_block.find("div", class_="price-block__value").get_text(strip=True)
        zakazchik_href = zakaz.find("div", class_="registry-entry__body-href").find("a")["href"]
        zakaz_href = "https://zakupki.gov.ru/" + id_stat_block.find("a")["href"]
        if id and price and zakazchik:
            data = {
                'date_published': date_published,
                'date_update': date_update,
                'status': status,
                'title': title,
                'id': id,
                'zakaz_href': zakaz_href,
                'zakazchik': zakazchik,
                'zakazchik_href': zakazchik_href,
                'price': price,
                'rows': []
            }
            return data
        else: return {}


    def do_inside_zakaz(self, data):
        main = 0
        for _ in range(10):
            response = self.session.get(data['zakaz_href'])
            soup = BeautifulSoup(response.text, features="html.parser")
            main = soup.find_all("section", class_="blockInfo__section section")
            if main:
                break
        if main:
            for row in main:
                try:
                    title = row.find("span", class_="section__title").get_text(strip=True)
                    value = row.find("span", class_="section__info").get_text(strip=True)
                    print(title, "!!!!!!!!!!!!!!!!!!!!!!!!!!", value)
                    if not (any(item.get('id')) == data['id'] for item in self.zakaz_all):
                        data['rows'].append({title: value})
                except:
                    pass
            return data
        else:
            main = soup.find_all("div", class_="col-9 mr-auto")
            if main:
                self.second_one += 1
                for row in main:
                    try:
                        title = row.find("div", class_="common-text__title")
                        value = row.find("div", class_="common-text__value")
                        title = (title.get_text(strip=True) or "")
                        value = (value.get_text(strip=True) or "")
                        # print(f"{title}!!!!!!!!!!!!!!!!!!!!!!!!!! {value}")
                        data['rows'].append({title: value})
                    except:
                        pass
                return data
            else:
                print("oops, not parseable :(")
                return {}

    def get_stats(self):
        return {
            'total_zakazi': len(self.zakaz_all),
            'second_format_count': self.second_one
        }

    def clear_results(self):
        self.zakaz_all.clear()
        self.fast_zakaz_all.clear()
        self.second_one = 0
    def main(self, count):
        for i in range(count):
            zakazi = self.parse_page(i)
            for zakaz in zakazi:
                data = self.do_zakaz(zakaz)
                if not data:
                    continue
                self.zakaz_all.append(self.do_inside_zakaz(data))