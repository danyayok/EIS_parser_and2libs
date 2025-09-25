import pytest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup, Tag
import requests
from src.main import parser_zakazi


class TestParserZakaziInitialization:
    """Тесты инициализации парсера"""

    def test_initialization(self):
        """Тест создания экземпляра парсера"""
        # Act
        parser = parser_zakazi()

        # Assert
        assert parser.zakaz_all == []
        assert parser.fast_zakaz_all == []
        assert parser.second_one == 0
        assert parser.session is not None
        assert "User-Agent" in parser.session.headers
        assert "Mozilla" in parser.session.headers["User-Agent"]

    def test_clear_results(self):
        """Тест очистки результатов"""
        # Arrange
        parser = parser_zakazi()
        parser.zakaz_all = [{"id": "1"}]
        parser.fast_zakaz_all = [{"id": "2"}]
        parser.second_one = 5

        # Act
        parser.clear_results()

        # Assert
        assert parser.zakaz_all == []
        assert parser.fast_zakaz_all == []
        assert parser.second_one == 0


class TestParsePage:
    """Тесты парсинга страницы"""

    @patch('src.main.requests.Session.get')
    def test_parse_page_success(self, mock_get):
        """Успешный парсинг страницы с закупками"""
        # Arrange
        mock_response = Mock()
        mock_response.text = """
        <html>
            <div class="search-registry-entry-block box-shadow-search-input">
                <div class="registry-entry__header-mid__title">Статус: Размещено</div>
                <a href="/order/123">№ 123</a>
                <div class="price-block__value">100 000 руб.</div>
            </div>
            <div class="search-registry-entry-block box-shadow-search-input">
                <div class="registry-entry__header-mid__title">Статус: Завершено</div>
                <a href="/order/456">№ 456</a>
                <div class="price-block__value">200 000 руб.</div>
            </div>
        </html>
        """
        mock_get.return_value = mock_response

        parser = parser_zakazi()

        # Act
        result = parser.parse_page(0)

        # Assert
        assert len(result) == 2
        mock_get.assert_called_once()
        assert "pageNumber=1" in mock_get.call_args[0][0]
        assert "recordsPerPage=_10" in mock_get.call_args[0][0]

    @patch('src.main.requests.Session.get')
    def test_parse_page_empty(self, mock_get):
        """Парсинг пустой страницы"""
        # Arrange
        mock_response = Mock()
        mock_response.text = "<html><body>Нет закупок</body></html>"
        mock_get.return_value = mock_response

        parser = parser_zakazi()

        # Act
        result = parser.parse_page(0)

        # Assert
        assert result == []

    @patch('src.main.requests.Session.get')
    def test_parse_page_network_error(self, mock_get):
        # Arrange
        mock_get.side_effect = requests.exceptions.ConnectionError("Нет сети")

        parser = parser_zakazi()

        assert parser.parse_page(0) == []


class TestDoZakaz:
    """Тесты парсинга отдельной закупки"""

    @pytest.fixture
    def sample_zakaz_element(self):
        """Фикстура с примером элемента закупки"""
        html = """
        <div class="search-registry-entry-block box-shadow-search-input">
            <div class="d-flex registry-entry__header-mid align-items-center">
                <div class="registry-entry__header-mid__title text-normal">Статус: Размещено</div>
                <a href="/epz/order/notice/ea44/view/common-info.html?regNumber=123456">№ 123456</a>
            </div>
            <div class="registry-entry__body-block">
                <div class="registry-entry__body-value">Поставка компьютеров и оргтехники</div>
            </div>
            <div class="registry-entry__body-href">
                <a href="/epz/order/notice/ea44/view/supplier-info.html?regNumber=123456">
                    Министерство Обороны Российской Федерации
                </a>
            </div>
            <div class="col col d-flex flex-column registry-entry__right-block b-left">
                <div class="price-block">
                    <div class="price-block__value">15 000 000 руб.</div>
                </div>
                <div class="data-block mt-auto">
                    <div class="col-6">
                        <div class="data-block__value">15.01.2024</div>
                    </div>
                    <div class="col-6">
                        <div class="data-block__value">16.01.2024</div>
                    </div>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        return soup.find("div", class_="search-registry-entry-block")

    def test_do_zakaz_success(self, sample_zakaz_element):
        parser = parser_zakazi()
        result = parser.do_zakaz(sample_zakaz_element)
        assert result is not None
        assert result != {}  # Должен вернуть данные, а не пустой словарь
        if result:  # Проверяем только если данные есть
            assert result['id'] == '№ 123456'
            assert result['status'] == 'Статус: Размещено'
            assert result['title'] == 'Поставка компьютеров и оргтехники'
            assert result['zakazchik'] == 'Министерство Обороны Российской Федерации'
            assert result['price'] == '15 000 000 руб.'
            assert result['date_published'] == '15.01.2024'
            assert result['date_update'] == '16.01.2024'
            assert 'https://zakupki.gov.ru/' in result['zakaz_href']
            assert result['rows'] == []

    def test_do_zakaz_incomplete_data(self):
        """Парсинг элемента с неполными данными"""
        # Arrange
        html = """
        <div class="search-registry-entry-block">
            <div>Неполные данные без ID и цены</div>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        incomplete_element = soup.find("div")

        parser = parser_zakazi()

        # Act
        result = parser.do_zakaz(incomplete_element)

        # Assert
        assert result == {}

    def test_do_zakaz_none_element(self):
        """Парсинг None элемента"""
        # Arrange
        parser = parser_zakazi()

        # Act
        result = parser.do_zakaz(None)

        # Assert
        assert result == {}

    @pytest.mark.parametrize("missing_field,expected", [
        ("id", {}),
        ("price", {}),
        ("zakazchik", {}),
    ])
    def test_do_zakaz_missing_required_fields(self, missing_field, expected, sample_zakaz_element):
        """Парсинг с отсутствующими обязательными полями"""
        # Arrange
        parser = parser_zakazi()

        # Симулируем отсутствие поля
        if missing_field == "id":
            sample_zakaz_element.find("a").decompose()  # Удаляем элемент с ID
        elif missing_field == "price":
            sample_zakaz_element.find("div", class_="price-block__value").decompose()
        elif missing_field == "zakazchik":
            sample_zakaz_element.find("div", class_="registry-entry__body-href").decompose()

        # Act
        result = parser.do_zakaz(sample_zakaz_element)

        # Assert
        assert result == expected


class TestDoInsideZakaz:
    """Тесты парсинга детальной страницы закупки"""

    @pytest.fixture
    def sample_zakaz_data(self):
        """Фикстура с базовыми данными закупки"""
        return {
            'id': '123456',
            'zakaz_href': 'https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=123456',
            'rows': []
        }

    @patch('src.main.requests.Session.get')
    def test_do_inside_zakaz_format1_success(self, mock_get, sample_zakaz_data):
        """Успешный парсинг детальной страницы (формат 1)"""
        # Arrange
        mock_response = Mock()
        mock_response.text = """
        <html>
            <section class="blockInfo__section section">
                <span class="section__title">Наименование закупки:</span>
                <span class="section__info">Поставка компьютерной техники</span>
            </section>
            <section class="blockInfo__section section">
                <span class="section__title">Заказчик:</span>
                <span class="section__info">Минобороны России</span>
            </section>
            <section class="blockInfo__section section">
                <span class="section__title">Начальная цена:</span>
                <span class="section__info">15 000 000 руб.</span>
            </section>
        </html>
        """
        mock_get.return_value = mock_response

        parser = parser_zakazi()

        # Act
        result = parser.do_inside_zakaz(sample_zakaz_data)

        # Assert
        assert len(result['rows']) == 3
        assert {'Наименование закупки:': 'Поставка компьютерной техники'} in result['rows']
        assert {'Заказчик:': 'Минобороны России'} in result['rows']
        assert {'Начальная цена:': '15 000 000 руб.'} in result['rows']

    @patch('src.main.requests.Session.get')
    def test_do_inside_zakaz_format2_success(self, mock_get, sample_zakaz_data):
        """Успешный парсинг детальной страницы (формат 2)"""
        # Arrange
        mock_response = Mock()
        mock_response.text = """
        <html>
            <div class="col-9 mr-auto">
                <div class="common-text__title">Наименование объекта закупки:</div>
                <div class="common-text__value">Поставка серверного оборудования</div>
            </div>
            <div class="col-9 mr-auto">
                <div class="common-text__title">Ответственное лицо:</div>
                <div class="common-text__value">Иванов И.И.</div>
            </div>
        </html>
        """
        mock_get.return_value = mock_response

        parser = parser_zakazi()
        initial_second_one = parser.second_one

        # Act
        result = parser.do_inside_zakaz(sample_zakaz_data)

        # Assert
        assert len(result['rows']) == 2
        assert {'Наименование объекта закупки:': 'Поставка серверного оборудования'} in result['rows']
        assert {'Ответственное лицо:': 'Иванов И.И.'} in result['rows']
        assert parser.second_one == initial_second_one + 1  # Счетчик увеличился

    @patch('src.main.requests.Session.get')
    def test_do_inside_zakaz_duplicate_prevention(self, mock_get, sample_zakaz_data):
        """Проверка предотвращения дубликатов"""
        # Arrange
        mock_response = Mock()
        mock_response.text = """
        <section class="blockInfo__section section">
            <span class="section__title">Тест:</span>
            <span class="section__info">Значение</span>
        </section>
        """
        mock_get.return_value = mock_response

        parser = parser_zakazi()
        # Добавляем закупку с таким же ID
        parser.zakaz_all.append({'id': '123456', 'rows': []})

        # Act
        result = parser.do_inside_zakaz(sample_zakaz_data)

        # Assert
        assert len(result['rows']) == 0  # Дубликат не должен добавиться

    @patch('src.main.requests.Session.get')
    def test_do_inside_zakaz_network_error(self, mock_get, sample_zakaz_data):
        """Обработка сетевой ошибки при парсинге детальной страницы"""
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout("Таймаут")

        parser = parser_zakazi()

        # Act
        result = parser.do_inside_zakaz(sample_zakaz_data)

        # Assert
        assert result == sample_zakaz_data
        assert len(result['rows']) == 0  # 3 попытки

    @patch('src.main.requests.Session.get')
    def test_do_inside_zakaz_unparseable_format(self, mock_get, sample_zakaz_data):
        mock_response = Mock()
        mock_response.text = "<html><body>Неизвестный формат</body></html>"
        mock_get.return_value = mock_response

        parser = parser_zakazi()

        # Act
        result = parser.do_inside_zakaz(sample_zakaz_data)

        # Assert - должен вернуть исходные данные без изменений
        assert result == sample_zakaz_data
        assert len(result['rows']) == 0

    def test_do_inside_zakaz_no_href(self):
        """Парсинг без ссылки на детальную страницу"""
        # Arrange
        parser = parser_zakazi()
        data_without_href = {'id': '123', 'rows': []}  # Нет zakaz_href

        # Act
        result = parser.do_inside_zakaz(data_without_href)

        # Assert
        assert result == data_without_href


class TestMainMethod:
    """Тесты основного метода парсера"""

    @patch('src.main.parser_zakazi.do_inside_zakaz')
    @patch('src.main.parser_zakazi.do_zakaz')
    @patch('src.main.parser_zakazi.parse_page')
    def test_main_success_flow(self, mock_parse_page, mock_do_zakaz, mock_do_inside_zakaz):
        """Успешный полный цикл парсинга"""
        # Arrange
        mock_parse_page.return_value = [Mock(), Mock()]  # 2 закупки на странице
        mock_do_zakaz.return_value = {'id': '123', 'zakaz_href': 'test', 'rows': []}
        mock_do_inside_zakaz.return_value = {'id': '123', 'zakaz_href': 'test', 'rows': [{'test': 'data'}]}

        parser = parser_zakazi()

        # Act
        parser.main(2)  # 2 страницы

        # Assert
        assert mock_parse_page.call_count == 2
        assert mock_do_zakaz.call_count == 4  # 2 страницы × 2 закупки
        assert mock_do_inside_zakaz.call_count == 4
        assert len(parser.zakaz_all) == 4

    @patch('src.main.parser_zakazi.parse_page')
    def test_main_empty_pages(self, mock_parse_page):
        """Парсинг пустых страниц"""
        # Arrange
        mock_parse_page.return_value = []  # Пустые страницы

        parser = parser_zakazi()

        # Act
        parser.main(3)  # 3 пустые страницы

        # Assert
        assert mock_parse_page.call_count == 3
        assert len(parser.zakaz_all) == 0

    @patch('src.main.parser_zakazi.parse_page')
    def test_main_with_invalid_data(self, mock_parse_page):
        """Парсинг с невалидными данными"""
        # Arrange
        mock_element = Mock()
        # Настраиваем mock чтобы do_zakaz возвращал {} для невалидных данных
        mock_parse_page.return_value = [mock_element]

        parser = parser_zakazi()

        # Act
        parser.main(1)

        # Assert
        assert len(parser.zakaz_all) == 0
        assert mock_parse_page.call_count == 1


class TestStats:
    """Тесты статистики"""

    def test_get_stats_empty(self):
        """Статистика пустого парсера"""
        # Arrange
        parser = parser_zakazi()

        # Act
        stats = parser.get_stats()

        # Assert
        assert stats['total_zakazi'] == 0
        assert stats['second_format_count'] == 0

    def test_get_stats_with_data(self):
        """Статистика парсера с данными"""
        # Arrange
        parser = parser_zakazi()
        parser.zakaz_all = [{'id': '1'}, {'id': '2'}, {'id': '3'}]
        parser.second_one = 2

        # Act
        stats = parser.get_stats()

        # Assert
        assert stats['total_zakazi'] == 3
        assert stats['second_format_count'] == 2


class TestEdgeCases:
    """Тесты граничных случаев"""

    @pytest.mark.parametrize("count", [0, 1, 5, 100])
    @patch('src.main.parser_zakazi.parse_page')
    def test_main_different_page_counts(self, mock_parse_page, count):
        """Тест разного количества страниц"""
        # Arrange
        mock_parse_page.return_value = []

        parser = parser_zakazi()

        # Act
        parser.main(count)

        # Assert
        assert mock_parse_page.call_count == count

    @patch('src.main.requests.Session.get')
    def test_special_characters_handling(self, mock_get):
        mock_response = Mock()
        mock_response.text = """
        <html>
            <div class="search-registry-entry-block box-shadow-search-input">
                <div class="d-flex registry-entry__header-mid align-items-center">
                    <div class="registry-entry__header-mid__title text-normal">Статус: &quot;Размещено&quot;</div>
                    <a href="/epz/order/notice/ea44/view/common-info.html?regNumber=123&amp;test">№ 123&amp;test</a>
                </div>
                <div class="registry-entry__body-block">
                    <div class="registry-entry__body-value">Тест &amp; проверка</div>
                </div>
                <div class="registry-entry__body-href">
                    <a href="#">Заказчик &amp; Ко</a>
                </div>
                <div class="col col d-flex flex-column registry-entry__right-block b-left">
                    <div class="price-block">
                        <div class="price-block__value">100&amp;000 руб.</div>
                    </div>
                    <div class="data-block mt-auto">
                        <div class="col-6">
                            <div class="data-block__value">01.01.2024</div>
                        </div>
                        <div class="col-6">
                            <div class="data-block__value">02.01.2024</div>
                        </div>
                    </div>
                </div>
            </div>
        </html>
        """
        mock_get.return_value = mock_response
        parser = parser_zakazi()
        result = parser.parse_page(0)
        assert len(result) == 1
        if result:
            zakaz_data = parser.do_zakaz(result[0])
            assert zakaz_data != {}


class TestIntegration:
    """Интеграционные тесты"""

    @patch('src.main.requests.Session.get')
    def test_full_integration(self, mock_get):
        list_response = Mock()
        list_response.text = """
        <html>
            <div class="search-registry-entry-block box-shadow-search-input">
                <div class="d-flex registry-entry__header-mid align-items-center">
                    <div class="registry-entry__header-mid__title text-normal">Статус: Размещено</div>
                    <a href="/epz/order/notice/ea44/view/common-info.html?regNumber=999">№ 999</a>
                </div>
                <div class="registry-entry__body-block">
                    <div class="registry-entry__body-value">Интеграционный тест</div>
                </div>
                <div class="registry-entry__body-href">
                    <a href="#">Тестовый заказчик</a>
                </div>
                <div class="col col d-flex flex-column registry-entry__right-block b-left">
                    <div class="price-block">
                        <div class="price-block__value">500 000 руб.</div>
                    </div>
                    <div class="data-block mt-auto">
                        <div class="col-6">
                            <div class="data-block__value">15.01.2024</div>
                        </div>
                        <div class="col-6">
                            <div class="data-block__value">16.01.2024</div>
                        </div>
                    </div>
                </div>
            </div>
        </html>
        """

        detail_response = Mock()
        detail_response.text = """
        <html>
            <section class="blockInfo__section section">
                <span class="section__title">Интеграционное поле:</span>
                <span class="section__info">Интеграционное значение</span>
            </section>
        </html>
        """

        # Настраиваем mock чтобы он возвращал разные ответы для разных URL
        def side_effect(url, *args, **kwargs):
            if "pageNumber=1" in url:
                return list_response
            else:
                return detail_response
        mock_get.side_effect = side_effect
        parser = parser_zakazi()
        parser.main(1)
        assert len(parser.zakaz_all) == 1
        if parser.zakaz_all:  # Проверяем только если есть данные
            assert parser.zakaz_all[0]['id'] == '№ 999'
            assert len(parser.zakaz_all[0]['rows']) >= 0