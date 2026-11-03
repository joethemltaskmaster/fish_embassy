from django.db import connection
from django.test import TestCase


class DatabaseConnectsTest(TestCase):
    def test_database_is_reachable(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_postgres_engine_is_used(self):
        # Guards against accidentally running tests on SQLite, which would
        # silently pass the smoke test but break row locking and triggers.
        self.assertEqual(connection.vendor, "postgresql")