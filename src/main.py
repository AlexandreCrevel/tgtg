import sys
import logging
import json
import argparse
from os import path
from typing import NoReturn
from packaging import version
import requests

from scanner import Scanner
from helper import Helper
from models import Config
from models.errors import TgtgAPIError, ConfigurationError

VERSION_URL = "https://api.github.com/repos/Der-Henning/tgtg/releases/latest"
VERSION = "1.14.0_rc1"


def main() -> NoReturn:
    """Wrapper for Scanner and Helper functions."""
    parser = argparse.ArgumentParser(
        description="TooGoodToGo scanner and notifier.",
        prog="scanner"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"v{_get_version_info()}"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="activate debugging mode"
    )
    parser.add_argument(
        "-t", "--tokens",
        action="store_true",
        help="display your current access tokens and exit",
    )
    parser.add_argument(
        "-f", "--favorites",
        action="store_true",
        help="display your favorites and exit"
    )
    parser.add_argument(
        "-F", "--favorite_ids",
        action="store_true",
        help="display the item ids of your favorites and exit",
    )
    parser.add_argument(
        "-a", "--add",
        nargs="+",
        metavar="item_id",
        help="add item ids to favorites and exit",
    )
    parser.add_argument(
        "-r", "--remove",
        nargs="+",
        metavar="item_id",
        help="remove item ids from favorites and exit",
    )
    parser.add_argument(
        "-R", "--remove_all",
        action="store_true",
        help="remove all favorites and exit"
    )
    args = parser.parse_args()

    prog_folder = (
        path.dirname(sys.executable)
        if getattr(sys, "_MEIPASS", False)
        else path.dirname(path.abspath(__file__))
    )
    config_file = path.join(prog_folder, "config.ini")
    log_file = path.join(prog_folder, "scanner.log")
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_file, mode="w"), logging.StreamHandler()],
    )
    log = logging.getLogger("tgtg")
    config = Config(config_file) if path.isfile(config_file) else Config()
    if config.debug or args.debug:
        # pylint: disable=E1103
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        # pylint: enable=E1103
        for logger in loggers:
            logger.setLevel(logging.DEBUG)
        log.info("Debugging mode enabled")

    if args.tokens:
        credentials = Helper(config).get_credentials()
        print("")
        print("Your TGTG credentials:")
        print("Access Token: ", credentials["access_token"])
        print("Refresh Token:", credentials["refresh_token"])
        print("User ID:      ", credentials["user_id"])
        print("")
    elif args.favorites:
        favorites = Helper(config).get_favorites()
        print("")
        print("Your favorites:")
        print(json.dumps(favorites, sort_keys=True, indent=4))
        print("")
    elif args.favorite_ids:
        favorites = Helper(config).get_favorites()
        item_ids = [fav["item"]["item_id"] for fav in favorites]
        print("")
        print("Item IDs:")
        print(" ".join(item_ids))
        print("")
    elif not args.add is None:
        helper = Helper(config)
        for item_id in args.add:
            helper.set_favorite(item_id)
        print("done.")
    elif not args.remove is None:
        helper = Helper(config)
        for item_id in args.remove:
            helper.unset_favorite(item_id)
        print("done.")
    elif args.remove_all:
        Helper(config).unset_all_favorites()
        print("done.")
    else:
        _start_scanner(config)


def _get_version_info() -> str:
    lastest_release = _get_new_version()
    if lastest_release is None:
        return VERSION
    return f"{VERSION} - Update available! See {lastest_release['html_url']}"


def _start_scanner(config: Config) -> NoReturn:
    log = logging.getLogger("tgtg")
    try:
        _print_welcome_message()
        _print_version_check()
        scanner = Scanner(config)
        scanner.run()
    except ConfigurationError as err:
        log.error("Configuration Error: %s", err)
        sys.exit(1)
    except TgtgAPIError as err:
        log.error("TGTG API Error: %s", err)
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Shutting down scanner ...")
    except SystemExit:
        sys.exit(1)


def _get_new_version() -> str:
    res = requests.get(VERSION_URL, timeout=60)
    res.raise_for_status()
    lastest_release = res.json()
    if version.parse(VERSION) < version.parse(lastest_release["tag_name"]):
        return lastest_release
    return None


def _print_version_check() -> None:
    log = logging.getLogger("tgtg")
    try:
        lastest_release = _get_new_version()
        if not lastest_release is None:
            log.info(
                "New Version %s available!", version.parse(lastest_release["tag_name"])
            )
            log.info("Please visit %s", lastest_release["html_url"])
            log.info("")
    except (
        requests.exceptions.RequestException,
        version.InvalidVersion,
        ValueError,
    ) as err:
        log.error("Failed checking for new Version! - %s", err)


def _print_welcome_message() -> None:
    log = logging.getLogger("tgtg")
    # pylint: disable=W1401
    log.info("  ____  ___  ____  ___    ____   ___   __   __ _  __ _  ____  ____  ")
    log.info(" (_  _)/ __)(_  _)/ __)  / ___) / __) / _\ (  ( \(  ( \(  __)(  _ \ ")
    log.info("   )( ( (_ \  )( ( (_ \  \___ \( (__ /    \/    //    / ) _)  )   / ")
    log.info("  (__) \___/ (__) \___/  (____/ \___)\_/\_/\_)__)\_)__)(____)(__\_) ")
    log.info("")
    log.info("Version %s", VERSION)
    log.info("©2022, Henning Merklinger")
    log.info(
        "For documentation and support please visit https://github.com/Der-Henning/tgtg"
    )
    log.info("")
    # pylint: enable=W1401


if __name__ == "__main__":
    main()
