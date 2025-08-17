import requests
from bs4 import BeautifulSoup
zakaz_all = []
for i in range(3):
    print(i)
    session = requests.Session()
    session.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/90.0.4430.93 Safari/537.36")
    })
    url = f"https://zakupki.gov.ru/epz/order/extendedsearch/results.html?searchString=&morphology=on&search-filter=%D0%94%D0%B0%D1%82%D0%B5+%D0%BE%D0%B1%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F&pageNumber={i+1}&sortDirection=false&recordsPerPage=_50&showLotsInfoHidden=false&savedSearchSettingsIdHidden=&sortBy=UPDATE_DATE&fz44=on&fz223=on&af=on&ca=on&pc=on&pa=on&placingWayList=&selectedLaws=&priceFromGeneral=&priceFromGWS=&priceFromUnitGWS=&priceToGeneral=&priceToGWS=&priceToUnitGWS=&currencyIdGeneral=-1&publishDateFrom=&publishDateTo=&applSubmissionCloseDateFrom=&applSubmissionCloseDateTo=&customerIdOrg=&customerFz94id=&customerTitle=&okpd2Ids=&okpd2IdsCodes="
    response = session.get(url)
    soup = BeautifulSoup(response.text, features="html.parser")
    # print(soup)
    zakazi = soup.find_all("div", class_="search-registry-entry-block box-shadow-search-input")
    for zakaz in zakazi:
        # Собираем необходимые блоки
        id_stat_block = zakaz.find("div", class_="d-flex registry-entry__header-mid align-items-center")
        right_block = zakaz.find("div", class_="col col d-flex flex-column registry-entry__right-block b-left")
        price_block = right_block.find("div", class_="price-block")
        data_block = right_block.find("div", class_="data-block mt-auto")
        published = data_block.find_all("div", "col-6")
        # Сами собираемые данные из блоков выше
        date_published = published[0].find("div", class_="data-block__value").get_text(strip=True)
        date_update = published[1].find("div", class_="data-block__value").get_text(strip=True)
        status = id_stat_block.find("div", class_="registry-entry__header-mid__title text-normal").get_text(strip=True)
        id = id_stat_block.find("a").get_text(strip=True)
        zakazchik = zakaz.find("div", class_="registry-entry__body-href").get_text(strip=True)
        price = right_block.find("div", class_="price-block__value").get_text(strip=True)
        zakazchik_href = zakaz.find("div", class_="registry-entry__body-href").find("a")["href"]
        zakaz_href = "https://zakupki.gov.ru/"+id_stat_block.find("a")["href"]
        # print(date_published, status, id, zakazchik, price, zakaz_href)
        print(zakaz_href)
        response = requests.get(zakaz_href)
        soup = BeautifulSoup(response.text, features="html.parser")
        # main_info = soup.find("div", class_="col")
        # print(main_info)
        # block_title = main_info("h2", class_="blockInfo__title")
        # print(main_info)
        main = soup.find_all("section", class_="blockInfo__section section")
        if main:
            for row in main:
                try:
                    # print(1)
                    title = row.find("span", class_="section__title").get_text(strip=True)
                    # print(11)
                    value = row.find("span", class_="section__info").get_text(strip=True)
                    # print(111)
                    print(f"{title}: {value}")
                    text = f"Дата публикации заказа: {date_published}. Статус заказа: {status}. Номер заказа: {id}. Начальная цена заказа: {price}. Ссылка на зака: {zakaz_href}"
                    if text not in zakaz_all:
                        zakaz_all.append(text)
                except:
                    pass
        else:
            main = soup.find_all("div", class_="col-9 mr-auto")
            if main:
                # print("row2")
                for row in main:
                    try:
                        title = row.find("div", class_="common-text__title")
                        # print(2)
                        value = row.find("div", class_="common-text__value")
                        # print(22)
                        title = (title.get_text(strip=True) or "")
                        # print(222)
                        value = (value.get_text(strip=True) or "")
                        print(f"{title}: {value}")
                        text = f"Дата публикации заказа: {date_published}. Статус заказа: {status}. Номер заказа: {id}. Начальная цена заказа: {price}. Ссылка на зака: {zakaz_href}"
                        if text not in zakaz_all:
                            zakaz_all.append(text)
                    except:
                        pass
            else:
                print("MAIN", main)
print("____________________________________пропарсил____________________________________")
print(len(zakaz_all))
