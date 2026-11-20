import os
import unittest
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient
from app.main import app, database_options


class InfrastructureTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_liveness_does_not_need_a_database(self):
        with patch('app.main.psycopg.connect') as connect:
            response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        connect.assert_not_called()

    def test_database_failure_has_503_without_connection_details(self):
        with patch('app.main.psycopg.connect', side_effect=psycopg.OperationalError('secret-dsn')):
            response = self.client.get('/readyz')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'indisponivel'})
        self.assertNotIn('secret-dsn', response.text)

    def test_readiness_actually_queries_database(self):
        with patch('app.main.psycopg.connect') as connect:
            response = self.client.get('/readyz')
            cursor = connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            cursor.execute.assert_called_once_with('SELECT 1')
        self.assertEqual(response.status_code, 200)

    def test_browser_origin_is_allowed(self):
        response = self.client.get('/healthz', headers={'Origin': 'http://localhost:5173'})
        self.assertEqual(response.headers.get('access-control-allow-origin'), 'http://localhost:5173')

    def test_external_origin_is_not_allowed(self):
        response = self.client.get('/healthz', headers={'Origin': 'https://example.org'})
        self.assertNotIn('access-control-allow-origin', response.headers)

    def test_container_database_port_overrides_host_port(self):
        with patch.dict(os.environ, {'PGHOST': 'db', 'PGPORT': '5432', 'DB_PORT': '5433'}):
            self.assertEqual(database_options()['port'], 5432)
            self.assertEqual(database_options()['host'], 'db')


if __name__ == '__main__':
    unittest.main()
