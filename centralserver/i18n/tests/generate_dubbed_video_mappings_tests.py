from django.test import TestCase
from mock import patch


class DubbedVideosFromAPITests(TestCase):

    def setUp(self):
        self.sample_api_return = [
            {
                "readable_id": "mark-rothko-no-3-no-13-1949",
                "youtube_ids":
                {
                    "ru": "EweIZwA_paM",
                    "en": "FnkATpF4O2Q"
                },
                "title": "Mark Rothko's No. 3/No. 13, 1949"},
            {
                "readable_id": "quadratic-equations-in-standard-form",
                "youtube_ids":
                {
                    "ru": "DqWHvrzmKZY",
                    "xh": "7lubbHiRLZQ",
                    "en": "ty4Ohya4hdE",
                    "pt": "vQ5AZDPKGOo",
                    "tr": "owzyuYP0m_k",
                    "sw": "GXb2XUZ5DSc",
                    "fr": "lBqQb8PtLEc",
                    "ur": "08zA5-EXd1g",
                    "ar": "gNJ4h-LV6Xk",
                    "es": "SN19Rx31yOY",
                    "ja": "pIplaA_qUf8",
                    "pl": "Shf6LZISu24"
                },
                "title": "Example: Quadratics in standard form"
            },
        ]

        # patch requests.get to return our sample API return value
        self.patcher = patch('requests.get')
        self.addCleanup(self.patcher.stop)

    def test_returns_a_dict(self):
        pass
