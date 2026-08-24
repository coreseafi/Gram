"""
Fully automated bot runner for Railway / headless deployment.
No menus or manual input required.

Environment variables:
  ACCOUNTS                  - initData lines (newline-separated, or use ||| between accounts)
  PROXIES                   - optional proxies (same format as ACCOUNTS)
  RUN_MODE                  - all (default) | mining | social | boost
  LANGUAGE                  - en (default) | vi
  TASK_CHECK_INTERVAL_SECONDS - seconds between task runs (default: 21600 = 6h)
  BOOST_COOLDOWN_SECONDS    - seconds between boost cycles (default: 7200 = 2h)
  MINING_SESSION_SECONDS    - expected mining session length (default: 14400 = 4h)
  MAX_CONCURRENT            - parallel accounts (default: all)
"""

import asyncio
import os
import sys
import traceback

from colorama import Fore, Style, init

init(autoreset=True)

DEFAULT_LANGUAGE = "en"
DEFAULT_RUN_MODE = "all"


def log(msg: str, color=Fore.CYAN):
    print(f"{color}{msg}{Style.RESET_ALL}", flush=True)


async def run_automation():
    language = os.getenv("LANGUAGE", DEFAULT_LANGUAGE).lower()
    if language not in ("en", "vi"):
        language = DEFAULT_LANGUAGE

    run_mode = os.getenv("RUN_MODE", DEFAULT_RUN_MODE).lower()
    if run_mode == "both":
        run_mode = "all"

    from scripts.common import (
        BOOST_COOLDOWN_SECONDS,
        MINING_SESSION_SECONDS,
        TASK_CHECK_INTERVAL_SECONDS,
        load_accounts,
        load_proxies,
    )

    accounts = load_accounts()
    if not accounts:
        log("ERROR: No accounts configured. Set ACCOUNTS env var or accounts.txt", Fore.RED)
        sys.exit(1)

    log("=" * 60, Fore.GREEN)
    log("Gram Network Bot — Automated Mode", Fore.GREEN)
    log(f"Accounts: {len(accounts)} | Proxies: {len(load_proxies())}", Fore.GREEN)
    log(f"Mode: {run_mode} | Language: {language}", Fore.GREEN)
    log(f"Mining session: {MINING_SESSION_SECONDS}s (4h)", Fore.GREEN)
    log(f"Boost cooldown: {BOOST_COOLDOWN_SECONDS}s (2h)", Fore.GREEN)
    log(f"Task check interval: {TASK_CHECK_INTERVAL_SECONDS}s (6h)", Fore.GREEN)
    log("=" * 60, Fore.GREEN)

    tasks = []

    if run_mode in ("all", "boost"):
        from scripts.boost import run_boost

        tasks.append(asyncio.create_task(run_boost(language), name="boost"))

    if run_mode in ("all", "social"):
        from scripts.social import run_social

        tasks.append(asyncio.create_task(run_social(language), name="social"))

    if run_mode in ("all", "mining"):
        from scripts.mining import run_mining

        tasks.append(asyncio.create_task(run_mining(language), name="mining"))

    if not tasks:
        log(
            f"ERROR: Invalid RUN_MODE '{run_mode}'. Use: all, mining, social, or boost",
            Fore.RED,
        )
        sys.exit(1)

    await asyncio.gather(*tasks)


def main():
    try:
        asyncio.run(run_automation())
    except KeyboardInterrupt:
        log("Stopped by user", Fore.YELLOW)
    except Exception:
        log(f"Automation error:\n{traceback.format_exc()}", Fore.RED)
        sys.exit(1)


if __name__ == "__main__":
    main()
