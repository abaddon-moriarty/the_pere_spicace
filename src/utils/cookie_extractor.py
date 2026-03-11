#!/usr/bin/env python3
import logging
import sqlite3
import argparse


from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_brave_cookies(url):
    # Create Path instance first, then call expanduser()
    brave_path = Path(
        "~/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default",
    ).expanduser()
    cookies_db = brave_path / "Cookies"

    if not cookies_db.exists():
        msg = "Brave cookies database not found"
        raise FileNotFoundError(msg)

    conn = sqlite3.connect(f"file:{cookies_db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    domain = url.split("://")[-1].split("/")[0]
    query = """
        SELECT host_key, path, is_secure, expires_utc, name, value, is_httponly
        FROM cookies WHERE host_key LIKE ? OR host_key LIKE ?
    """
    cursor.execute(query, (f"%{domain}", f".{domain}"))

    # Write to cookies.txt in Netscape format
    with Path.open("./src/utils/cookies.txt", "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for row in cursor.fetchall():
            line = (
                f"{row['host_key']}\t"
                f"{'TRUE' if row['host_key'].startswith('.') else 'FALSE'}\t"
                f"{row['path']}\t"
                f"{'TRUE' if row['is_secure'] else 'FALSE'}\t"
                f"{row['expires_utc']}\t"
                f"{row['name']}\t"
                f"{row['value']}\n"
            )
            f.write(line)

    conn.close()
    logger.info("Cookies saved to cookies.txt in Netscape format.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract Brave cookies to Netscape format",
    )
    parser.add_argument("url", help="URL to extract cookies for")
    args = parser.parse_args()
    get_brave_cookies(args.url)


if __name__ == "__main__":
    main()
