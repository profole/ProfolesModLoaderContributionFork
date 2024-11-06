import logging
import os
import platform
import subprocess

import dearpygui.dearpygui as dpg
import requests

import Code.dpg_tools as dpg_tools
from Code.app_vars import AppGlobalsAndConfig
from Code.loc import Localization as loc
from Code.package import ModLoader

from .barotrauma_window import BarotraumaWindow
from .mod_window import ModWindow

logger = logging.getLogger("App")


class AppInterface:
    @staticmethod
    def initialize():
        AppInterface._create_viewport_menu_bar()
        ModWindow.create_window()
        dpg.set_viewport_resize_callback(AppInterface.resize_windows)
        AppInterface.resize_windows()

    @staticmethod
    def _create_viewport_menu_bar():
        dpg.add_viewport_menu_bar(tag="main_view_bar")

        with dpg.menu(
            label=loc.get_string("menu-bar-settings-lable"), parent="main_view_bar"
        ):
            dpg.add_button(
                label=loc.get_string("btn-set-game-dir"),
                callback=BarotraumaWindow.create_window,
            )
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text(loc.get_string("btn-set-game-dir-desc"))

            dpg.add_checkbox(
                label=loc.get_string("setting-toggle-install-lua"),
                tag="settings_install_lua",
                default_value=AppGlobalsAndConfig.get("game_config_auto_lua", False),  # type: ignore
                callback=lambda s, a: AppGlobalsAndConfig.set(
                    "game_config_auto_lua", a
                ),
            )

            dpg.add_checkbox(
                label=loc.get_string("setting-toggle-skip-intro"),
                tag="settings_skip_intro",
                default_value=AppGlobalsAndConfig.get("game_config_skip_intro", False),  # type: ignore
                callback=lambda s, a: AppGlobalsAndConfig.set(
                    "game_config_skip_intro", a
                ),
            )

            dpg.add_checkbox(
                label=loc.get_string("menu-toggle-experimental"),
                default_value=AppGlobalsAndConfig.get("experimental", False),  # type: ignore
                callback=lambda s, a: AppGlobalsAndConfig.set("experimental", a),
            )

            dpg.add_combo(
                items=["eng", "rus", "ger"],
                label=loc.get_string("menu-language"),
                default_value=AppGlobalsAndConfig.get("lang", "eng"),  # type: ignore
                callback=lambda s, a: AppGlobalsAndConfig.set("lang", a),
                width=50,
            )

        dpg.add_menu_item(
            label=loc.get_string("menu-bar-start-game"),
            parent="main_view_bar",
            callback=AppInterface.start_game,
        )

    @staticmethod
    def resize_windows():
        viewport_width = dpg.get_viewport_width() - 40
        viewport_height = dpg.get_viewport_height() - 80

        windows = ["mod_window", "baro_window", "exp_game", "game_config_window"]
        for item in windows:
            if dpg.does_item_exist(item):
                dpg.configure_item(item, width=viewport_width, height=viewport_height)
                dpg_tools.center_window(item)

        half_item = [
            "active_mod_search_tag",
            "active_mods_child",
            "inactive_mod_search_tag",
            "inactive_mods_child",
        ]
        viewport_width = viewport_width / 2
        viewport_height = viewport_height / 2
        for item in half_item:
            if dpg.does_item_exist(item):
                dpg.configure_item(item, width=viewport_width, height=viewport_height)

    @staticmethod
    def start_game():
        ModLoader.save_mods()

        game_dir = AppGlobalsAndConfig.get("barotrauma_dir", None)
        if not game_dir:
            AppInterface.show_error(loc.get_string("error-game-dir-not-set"))
            return

        skip_intro = AppGlobalsAndConfig.get("game_config_skip_intro", False)
        auto_install_lua = AppGlobalsAndConfig.get("game_config_auto_lua", False)

        if auto_install_lua:
            if AppInterface.download_and_run_updater(game_dir):
                AppInterface.run_game(skip_intro, game_dir)
            else:
                AppInterface.show_error("Failed to download or run the updater.")
        else:
            AppInterface.run_game(skip_intro, game_dir)

    @staticmethod
    def show_error(message):
        with dpg.window(label="Error"):
            dpg.add_text(message)

    @staticmethod
    def download_and_run_updater(game_dir):
        system = platform.system()
        urls = {
            "Windows": "https://github.com/Luatrauma/Luatrauma.AutoUpdater/releases/download/latest/Luatrauma.AutoUpdater.win-x64.exe",
            "Darwin": "https://github.com/Luatrauma/Luatrauma.AutoUpdater/releases/download/latest/Luatrauma.AutoUpdater.osx-x64",
            "Linux": "https://github.com/Luatrauma/Luatrauma.AutoUpdater/releases/download/latest/Luatrauma.AutoUpdater.linux-x64",
        }

        file_name = {
            "Windows": "Luatrauma.AutoUpdater.win-x64.exe",
            "Darwin": "Luatrauma.AutoUpdater.osx-x64",
            "Linux": "Luatrauma.AutoUpdater.linux-x64",
        }

        if system not in urls:
            logger.error(f"Unsupported OS: {system}")
            AppInterface.show_error(loc.get_string("error-unknown-os"))
            return False

        updater_path = os.path.join(game_dir, file_name[system])
        logger.debug(f"Updater path set to: {updater_path}")

        try:
            logger.debug(f"Attempting to download updater from {urls[system]}")
            response = requests.get(urls[system], stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get("Content-Length", 0))
            logger.debug(f"Total file size: {total_size} bytes")

            downloaded_size = 0
            chunk_size = 4092
            with open(updater_path, "wb") as file:
                logger.debug("Writing updater file in chunks...")
                for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    logger.debug(
                        f"Saved chunk #{i + 1} - {downloaded_size}/{total_size} bytes downloaded ({downloaded_size / total_size * 100:.2f}%)"
                    )  # TODO: Loading bar

            logger.debug(f"Download completed and saved to {updater_path}")

            if system in ["Darwin", "Linux"]:
                logger.debug(f"Setting execute permissions for {updater_path}")
                subprocess.run(["chmod", "+x", updater_path], check=True)
                logger.debug("Execute permissions set.")

            logger.debug(f"Running updater from {updater_path}")
            result = subprocess.run([updater_path], cwd=game_dir)
            logger.debug(
                f"Updater process completed with return code: {result.returncode}"
            )

            return result.returncode == 0

        except requests.RequestException as e:
            logger.error(f"Network error while downloading updater: {e}")
            return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Error setting execute permissions: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error during download or execution: {e}")
            return False

    @staticmethod
    def run_game(skip_intro, game_dir):
        run_executable = {
            "Windows": "Barotrauma.exe",
            "Darwin": "Barotrauma.app/Contents/MacOS/Barotrauma",
            "Linux": "Barotrauma",
        }

        system = platform.system()
        if system not in run_executable:
            AppInterface.show_error(loc.get_string("error-unknown-os"))
            return

        executable_path = os.path.join(game_dir, run_executable[system])
        if not os.path.isfile(executable_path):
            AppInterface.show_error(f"Executable not found: {executable_path}")
            return

        parms = ["-skipintro"] if skip_intro else []

        try:
            subprocess.run([executable_path] + parms, cwd=game_dir)

        except Exception as e:
            logging.error(f"Error running the game: {e}")
            AppInterface.show_error(f"Error running the game: {e}")
