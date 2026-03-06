import os
import sqlite3
import argparse


def get_brave_cookies(url):
    brave_path = os.path.expanduser(
        "~/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default",
    )
    cookies_db = os.path.join(brave_path, "Cookies")

    if not os.path.exists(cookies_db):
        raise FileNotFoundError("Brave cookies database not found")

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
    with open("./src/utils/cookies.txt", "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.writelines(
            f"{row['host_key']}\t{'TRUE' if row['host_key'].startswith('.') else 'FALSE'}\t"
            f"{row['path']}\t{'TRUE' if row['is_secure'] else 'FALSE'}\t"
            f"{row['expires_utc']}\t{row['name']}\t{row['value']}\n"
            for row in cursor.fetchall()
        )

    conn.close()
    print("Cookies saved to cookies.txt in Netscape format.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract Brave cookies to Netscape format"
    )
    parser.add_argument("url", help="URL to extract cookies for")
    args = parser.parse_args()
    get_brave_cookies(args.url)


if __name__ == "__main__":
    main()
