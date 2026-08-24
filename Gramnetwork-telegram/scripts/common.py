import asyncio
import os
import urllib.parse
from typing import Optional

import aiohttp
from aiohttp_socks import ProxyConnector
from colorama import Fore, Style

BASE_URL = "https://app.gramnetwork.online"
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNTS_FILE = os.path.join(ROOT_DIR, "accounts.txt")
PROXIES_FILE = os.path.join(ROOT_DIR, "proxies.txt")

MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "6"))
MAX_RETRIES = 3
RETRY_DELAY = 2

MINING_SESSION_SECONDS = int(os.getenv("MINING_SESSION_SECONDS", str(4 * 3600)))
BOOST_COOLDOWN_SECONDS = int(os.getenv("BOOST_COOLDOWN_SECONDS", str(2 * 3600)))
TASK_CHECK_INTERVAL_SECONDS = int(os.getenv("TASK_CHECK_INTERVAL_SECONDS", str(6 * 3600)))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": f"{BASE_URL}/",
    "Origin": BASE_URL,
}


def print_border(text: str, color=Fore.CYAN, width: int = 80):
    text = text.strip()
    if len(text) > width - 4:
        text = text[: width - 7] + "..."
    padded = f" {text} ".center(width - 2)
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")


def is_valid_init_data(line: str) -> bool:
    return (
        "user=" in line
        and "auth_date=" in line
        and ("hash=" in line or "signature=" in line)
    )


def load_lines(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    lines = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or line in {"...", "…"}:
                continue
            upper = line.upper()
            if upper.startswith("INIT_DATA") or upper.startswith("PROXY"):
                continue
            if path.endswith("accounts.txt") and not is_valid_init_data(line):
                continue
            if path.endswith("proxies.txt") and normalize_proxy(line) is None:
                continue
            lines.append(line)
    return lines


def normalize_proxy(proxy: str) -> Optional[str]:
    proxy = proxy.strip()
    if not proxy or proxy in {"...", "…"}:
        return None
    if proxy.startswith(("http://", "https://", "socks5://", "socks4://")):
        return proxy
    parts = proxy.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        if not host or not port.isdigit():
            return None
        return f"socks5://{user}:{password}@{host}:{port}"
    if len(parts) == 2 and parts[1].isdigit():
        return f"socks5://{parts[0]}:{parts[1]}"
    return None


def account_label(init_data: str) -> str:
    try:
        params = urllib.parse.parse_qs(init_data)
        user_raw = params.get("user", [""])[0]
        if user_raw:
            import json

            user = json.loads(user_raw)
            if user.get("username"):
                return f"@{user['username']}"
            if user.get("first_name"):
                return str(user["first_name"])
            if user.get("id"):
                return f"ID {user['id']}"
    except Exception:
        pass
    return init_data[:24] + "..."


class GramClient:
    def __init__(self, init_data: str, proxy: Optional[str] = None):
        self.init_data = init_data
        self.proxy = normalize_proxy(proxy) if proxy else None
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        connector = None
        if self.proxy:
            connector = ProxyConnector.from_url(self.proxy)
        self._session = aiohttp.ClientSession(headers=DEFAULT_HEADERS, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        assert self._session is not None
        url = f"{BASE_URL}{path}"
        last_error = "Unknown error"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with self._session.request(method, url, **kwargs) as resp:
                    text = await resp.text()
                    if resp.status >= 500:
                        last_error = f"HTTP {resp.status}"
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    try:
                        return await resp.json(content_type=None)
                    except Exception:
                        last_error = text[:200] or f"HTTP {resp.status}"
                        await asyncio.sleep(RETRY_DELAY)
            except Exception as exc:
                last_error = str(exc)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)

        return {"success": False, "message": last_error}

    def _encoded_init(self) -> str:
        return urllib.parse.quote(self.init_data, safe="")

    async def get_user_data(self) -> dict:
        return await self._request(
            "GET",
            f"/api/get_user_data.php?initData={self._encoded_init()}",
        )

    async def get_tasks(self) -> dict:
        return await self._request(
            "GET",
            f"/api/get_tasks.php?initData={self._encoded_init()}",
        )

    async def _post_init(self, path: str, extra: Optional[dict] = None) -> dict:
        body = f"initData={self._encoded_init()}"
        if extra:
            body += "".join(
                f"&{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}"
                for k, v in extra.items()
            )
        return await self._request(
            "POST",
            path,
            data=body,
            headers={**DEFAULT_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        )

    async def start_mining(self) -> dict:
        return await self._post_init("/api/start_mining.php")

    async def claim_mining(self) -> dict:
        return await self._post_init("/api/claim_mining.php")

    async def claim_daily(self) -> dict:
        return await self._post_init("/api/claim_daily.php")

    async def complete_task(self, task_id: int) -> dict:
        return await self._post_init("/api/complete_task.php", {"task_id": task_id})

    async def boost_energy(self) -> dict:
        return await self._post_init("/api/boost_energy.php")

    async def boost_power(self) -> dict:
        return await self._post_init("/api/boost_power.php")


def load_accounts() -> list[str]:
    env = os.getenv("ACCOUNTS", "").strip()
    if env:
        if "|||" in env:
            candidates = [line.strip() for line in env.split("|||") if line.strip()]
        else:
            candidates = [line.strip() for line in env.splitlines() if line.strip()]
        return [line for line in candidates if is_valid_init_data(line)]
    return load_lines(ACCOUNTS_FILE)


def load_proxies() -> list[str]:
    env = os.getenv("PROXIES", "").strip()
    if env:
        if "|||" in env:
            candidates = [line.strip() for line in env.split("|||") if line.strip()]
        else:
            candidates = [line.strip() for line in env.splitlines() if line.strip()]
        return [line for line in candidates if normalize_proxy(line)]
    return load_lines(PROXIES_FILE)


async def run_accounts(worker, language: str):
    accounts = load_accounts()
    proxies = load_proxies()

    if not accounts:
        msg = {
            "vi": "Không tìm thấy tài khoản hợp lệ (accounts.txt hoặc biến ACCOUNTS)",
            "en": "No valid accounts found (accounts.txt or ACCOUNTS env var)",
        }
        print(f"{Fore.RED}❌ {msg[language]}{Style.RESET_ALL}")
        return

    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def wrapped(index: int, init_data: str):
        proxy = proxies[index % len(proxies)] if proxies else None
        async with sem:
            await worker(index, init_data, proxy, language)

    await asyncio.gather(*(wrapped(i, acc) for i, acc in enumerate(accounts)))
