"""Block every upload unless PyPI explicitly reports the exact version absent."""

from __future__ import annotations

import argparse
import http.client
import json
import re
import ssl


def version_is_absent(status: int) -> bool:
    """Only an authoritative 404 permits the first publication attempt."""

    return type(status) is int and status == 404


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"\d+\.\d+\.\d+", args.version) is None:
        raise SystemExit("pypi-version-invalid")
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    connection = http.client.HTTPSConnection("pypi.org", timeout=10, context=context)
    try:
        connection.request("GET", f"/pypi/runa-sdk/{args.version}/json")
        response = connection.getresponse()
        status = response.status
    except (OSError, http.client.HTTPException):
        status = 0
    finally:
        connection.close()
    if not version_is_absent(status):
        print(
            json.dumps(
                {
                    "category": "pypi-version-not-authoritatively-absent",
                    "requirement": "R-095-13",
                    "verdict": "blocked",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print('{"requirement":"R-095-13","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
