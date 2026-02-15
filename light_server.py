import json
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DB_PATH = Path(__file__).with_name("app_data.db3")
HOST = "127.0.0.1"
PORT = 8000


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sample_data (
                "event id" INTEGER PRIMARY KEY AUTOINCREMENT,
                poc TEXT,
                "collectionName" TEXT,
                equipment TEXT,
                imsi TEXT,
                imei TEXT,
                provider TEXT,
                "providerCountry" TEXT,
                lat REAL,
                "long" REAL,
                "date_time collected" TEXT
            )
            """
        )
        existing = conn.execute("SELECT COUNT(*) AS c FROM sample_data").fetchone()["c"]
        if existing == 0:
            conn.executemany(
                """
                INSERT INTO sample_data (
                    poc, "collectionName", equipment, imsi, imei, provider,
                    "providerCountry", lat, "long", "date_time collected"
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Alice Johnson",
                        "Demo North",
                        "Scanner-A1",
                        "310150123456789",
                        "356938035643809",
                        "AT&T",
                        "US",
                        37.7749,
                        -122.4194,
                        "2026-01-20 09:15:00",
                    ),
                    (
                        "Brandon Lee",
                        "Demo South",
                        "Scanner-B3",
                        "310260987654321",
                        "490154203237518",
                        "T-Mobile",
                        "US",
                        34.0522,
                        -118.2437,
                        "2026-01-20 10:05:00",
                    ),
                    (
                        "Carla Mendes",
                        "Demo East",
                        "Scanner-C2",
                        "334020112233445",
                        "359881234567890",
                        "Vodafone",
                        "UK",
                        40.7128,
                        -74.0060,
                        "2026-01-20 11:40:00",
                    ),
                    (
                        "Derek Hall",
                        "Demo West",
                        "Scanner-D7",
                        "262010998877665",
                        "864502031234567",
                        "Telefonica",
                        "DE",
                        47.6062,
                        -122.3321,
                        "2026-01-20 12:25:00",
                    ),
                    (
                        "Evelyn Park",
                        "Demo Central",
                        "Scanner-E4",
                        "505010445566778",
                        "352099001761481",
                        "Telstra",
                        "AU",
                        41.8781,
                        -87.6298,
                        "2026-01-20 13:05:00",
                    ),
                ],
            )
        conn.commit()


class AppHandler(SimpleHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self._send_json({"ok": True, "db": str(DB_PATH)})
            return

        if parsed.path == "/api/sample-data":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", ["50"])[0])

            try:
                with get_conn() as conn:
                    # TODO: Replace with your real query.
                    query = """
                        SELECT
                            "event id",
                            poc,
                            "collectionName",
                            equipment,
                            imsi,
                            imei,
                            provider,
                            "providerCountry",
                            lat,
                            "long",
                            "date_time collected"
                        FROM sample_data
                        ORDER BY "event id" DESC
                        LIMIT ?
                    """
                    rows = conn.execute(query, (limit,)).fetchall()
                data = [dict(r) for r in rows]
                self._send_json({"rows": data, "count": len(data)})
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/sample-data":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b"{}"
                payload = json.loads(raw.decode("utf-8"))
                poc = payload.get("poc", "Demo POC")
                collection_name = payload.get("collectionName", "Demo Collection")
                equipment = payload.get("equipment", "Demo Equipment")
                imsi = payload.get("imsi", "000000000000000")
                imei = payload.get("imei", "000000000000000")
                provider = payload.get("provider", "Demo Provider")
                provider_country = payload.get("providerCountry", "US")
                lat = float(payload.get("lat", 0.0))
                long_value = float(payload.get("long", 0.0))
                date_time_collected = payload.get(
                    "date_time collected",
                    payload.get("date_time_collected", "2026-01-01 00:00:00"),
                )

                with get_conn() as conn:
                    # TODO: Replace with your real INSERT/UPDATE SQL.
                    cur = conn.execute(
                        """
                        INSERT INTO sample_data (
                            poc, "collectionName", equipment, imsi, imei, provider,
                            "providerCountry", lat, "long", "date_time collected"
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            poc,
                            collection_name,
                            equipment,
                            imsi,
                            imei,
                            provider,
                            provider_country,
                            lat,
                            long_value,
                            date_time_collected,
                        ),
                    )
                    conn.commit()

                self._send_json({"ok": True, "id": cur.lastrowid}, status=201)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        self._send_json({"error": "Not found"}, status=404)


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving http://{HOST}:{PORT}")
    print("Static files are served from this folder.")
    print("API endpoints: GET /api/health, GET/POST /api/sample-data")
    server.serve_forever()
