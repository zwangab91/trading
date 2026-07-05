import tempfile
import unittest
from pathlib import Path

from trading_agent.storage import AuditStore


class AuditStoreTests(unittest.TestCase):
    def test_records_and_reads_event(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AuditStore(Path(directory) / "audit.sqlite3")
            event_id = store.record_event("test.event", {"ok": True})
            events = list(store.list_events())

        self.assertEqual(event_id, 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][2], "test.event")
        self.assertEqual(events[0][3], {"ok": True})


if __name__ == "__main__":
    unittest.main()

