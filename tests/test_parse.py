import pytest
from unittest.mock import Mock, patch
import requests
from bs4 import BeautifulSoup


def test_price_extraction_from_text():

    def extract_price(price_text):
        if not price_text:
            return 0
        cleaned = price_text.replace(' руб.', '').replace(' ', '').replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return 0

    test_cases = [
        ("100 000 руб.", 100000),
        ("50 000,50 руб.", 50000.5),
        ("1 000 руб.", 1000),
        ("500 руб.", 500),
        ("бесплатно", 0),
        ("", 0),
        ("не число", 0)
    ]

    for price_text, expected in test_cases:
        result = extract_price(price_text)
        assert result == expected, f"Ожидалось {expected}, получили {result} для '{price_text}'"


@patch('requests.Session')
def test_main_parsing_loop(MockSession):

    mock_session_instance = Mock()
    MockSession.return_value = mock_session_instance

    list_html = """
    <div class="search-registry-entry-block box-shadow-search-input">
        <div class="d-flex registry-entry__header-mid align-items-center">
            <div class="registry-entry__header-mid__title text-normal">Статус: Размещено</div>
            <a href="/order/123">№ 123</a>
        </div>
        <div class="registry-entry__body-href">Министерство Обороны</div>
        <div class="col col d-flex flex-column registry-entry__right-block b-left">
            <div class="price-block__value">100 000 руб.</div>
            <div class="data-block mt-auto">
                <div class="col-6"><div class="data-block__value">01.01.2024</div></div>
                <div class="col-6"><div class="data-block__value">02.01.2024</div></div>
            </div>
        </div>
    </div>
    """

    detail_html = """
    <section class="blockInfo__section section">
        <span class="section__title">Название:</span>
        <span class="section__info">Тестовая закупка</span>
    </section>
    """

    mock_response_list = Mock()
    mock_response_list.text = list_html

    mock_response_detail = Mock()
    mock_response_detail.text = detail_html

    mock_session_instance.get.side_effect = [mock_response_list, mock_response_detail]

    zakaz_all = []

    session = requests.Session()
    session.headers.update({"User-Agent": "test"})

    response = session.get("https://zakupki.gov.ru/page=1")
    soup = BeautifulSoup(response.text, 'html.parser')
    zakazi = soup.find_all("div", class_="search-registry-entry-block box-shadow-search-input")

    for zakaz in zakazi:
        id_stat_block = zakaz.find("div", class_="d-flex registry-entry__header-mid align-items-center")
        right_block = zakaz.find("div", class_="col col d-flex flex-column registry-entry__right-block b-left")

        date_published = right_block.find("div", class_="data-block__value").get_text(strip=True)
        status = id_stat_block.find("div", class_="registry-entry__header-mid__title text-normal").get_text(strip=True)
        id = id_stat_block.find("a").get_text(strip=True)
        zakazchik = zakaz.find("div", class_="registry-entry__body-href").get_text(strip=True)
        price = right_block.find("div", class_="price-block__value").get_text(strip=True)
        zakaz_href = "https://zakupki.gov.ru/" + id_stat_block.find("a")["href"]

        detail_response = session.get(zakaz_href)
        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')

        text = f"Дата: {date_published}. Статус: {status}. Номер: {id}. Цена: {price}"
        zakaz_all.append(text)

    assert len(zakaz_all) == 1
    assert "Статус: Размещено" in zakaz_all[0]
    assert "Цена: 100 000 руб." in zakaz_all[0]
    assert mock_session_instance.get.call_count == 2


def test_different_detail_formats():

    html_format1 = """
    <section class="blockInfo__section section">
        <span class="section__title">Название:</span>
        <span class="section__info">Закупка 1</span>
    </section>
    """

    html_format2 = """
    <div class="col-9 mr-auto">
        <div class="common-text__title">Название:</div>
        <div class="common-text__value">Закупка 2</div>
    </div>
    """

    def parse_detail(html):
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        sections = soup.find_all("section", class_="blockInfo__section section")
        if sections:
            for section in sections:
                try:
                    title = section.find("span", class_="section__title").get_text(strip=True)
                    value = section.find("span", class_="section__info").get_text(strip=True)
                    result[title] = value
                except:
                    pass
        else:
            # Второй формат
            rows = soup.find_all("div", class_="col-9 mr-auto")
            for row in rows:
                try:
                    title = row.find("div", class_="common-text__title").get_text(strip=True)
                    value = row.find("div", class_="common-text__value").get_text(strip=True)
                    result[title] = value
                except:
                    pass
        return result
    result1 = parse_detail(html_format1)
    result2 = parse_detail(html_format2)

    assert result1["Название:"] == "Закупка 1"
    assert result2["Название:"] == "Закупка 2"


def test_error_handling_in_parsing():
    broken_html = "<div>Незакрытый тег"
    soup = BeautifulSoup(broken_html, 'html.parser')
    elements = soup.find_all("div", class_="non-existent-class")
    assert elements == []

    empty_html = "<html></html>"
    soup_empty = BeautifulSoup(empty_html, 'html.parser')
    block = soup_empty.find("div", class_="search-registry-entry-block")
    assert block is None


def test_user_agent_header():
    session = requests.Session()
    session.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/90.0.4430.93 Safari/537.36")
    })

    assert "User-Agent" in session.headers
    assert "Mozilla" in session.headers["User-Agent"]
    assert "Chrome" in session.headers["User-Agent"]


