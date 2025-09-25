import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
from src.main import parser_zakazi


class TestParserZakazi:
    def test_initialization(self):
        parser = parser_zakazi()
        assert parser.zakaz_all == []
        assert parser.second_one == 0
        assert parser.session is not None
    def test_valid_html(self):
        parser = parser_zakazi()
        valid_html_page = 'html enter here'

