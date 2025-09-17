import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_requests_session(monkeypatch):
    """Фикстура для мока requests сессии"""

    # Создаём мок-объект для сессии
    mock_session = Mock()

    # HTML контент для разных URL
    list_html = """
    <div class="search-registry-entry-block box-shadow-search-input">
        <div class="d-flex registry-entry__header-mid align-items-center">
            <div class="registry-entry__header-mid__title text-normal">Статус: Размещено</div>
            <a href="/order/123">№ 123</a>
        </div>
        <div class="registry-entry__body-href">Заказчик</div>
        <div class="price-block__value">100 000 руб.</div>
        <div class="data-block__value">01.01.2024</div>
    </div>
    """

    detail_html = """
    <section class="blockInfo__section section">
        <span class="section__title">Название:</span>
        <span class="section__info">Тестовая закупка</span>
    </section>
    """

    # Настраиваем мок
    def mock_get(url, *args, **kwargs):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        if "results.html" in url:
            mock_response.text = list_html
        else:
            mock_response.text = detail_html

        return mock_response

    mock_session.get = mock_get
    mock_session.headers = {}

    # Подменяем реальную сессию
    monkeypatch.setattr('requests.Session', lambda: mock_session)

    return mock_session