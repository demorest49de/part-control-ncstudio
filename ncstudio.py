from datetime import datetime
import inspect
import json
import string
import sys
import traceback
from pathlib import Path
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import scrolledtext
from typing import Final
from typing import TypedDict
from json import JSONDecodeError

import pystray
from PIL import Image, ImageDraw
from pystray import Icon, MenuItem
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper


class CompletedBatch(TypedDict):
    date: str
    limit: int
    file_name: str


class DataJson(TypedDict):
    CURRENT_PART_LIMIT: int
    BATCHES: list[CompletedBatch]


CURRENT_PART_LIMIT: Final[string] = 'current_part_limit'
BATCHES: Final[string] = 'batches'
CHECK_INTERVAL: Final[float] = 5.0
# ERROR_INTERVAL: Final[float] = 4.0

part_limit: int = 100
# TODO поменять здесь
part_count: int = 0  # prod
# part_count: int = 4  # test
ncstudio_file_name: str = ""
is_part_count_field_not_found: bool = False

monitor_stop_event: threading.Event = threading.Event()
limit_lock: threading.Lock = threading.Lock()
part_count_lock: threading.Lock = threading.Lock()
is_part_count_field_not_found_lock: threading.Lock = threading.Lock()


# set_part_limit при установке не срабатывает  отображается
# разная цифра лимита в инфо по лимиту - ✔

# ворнинг должен отображатся первым слоем - ✔

# сохранять данные - ✔
#   - лимиты
#   - название файла программы с датастемпом что бы была история

# проверять лимит не может быть меньше или равно парт каунту - ✔
# добавить обработку исключения при парсе ncstudio_data.json - ✔
# поменять размеры окон
# поменять все на прод обратно

def get_program_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def load_data_from_json() -> dict:
    if not DATA_FILE.exists():
        return {
            CURRENT_PART_LIMIT: part_limit,
            BATCHES: []
        }
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except JSONDecodeError:
        return {
            CURRENT_PART_LIMIT: 100,
            BATCHES: []
        }


def save_data_to_json(data: dict) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


DATA_FILE: Final[Path] = get_program_directory() / "ncstudio_data.json"


def save_current_part_limit(current_part_limit: int) -> None:
    data: DataJson = load_data_from_json()
    data[CURRENT_PART_LIMIT] = current_part_limit
    save_data_to_json(data)


def load_current_part_limit() -> int:
    return load_data_from_json()[CURRENT_PART_LIMIT]


def load_data_on_startup() -> None:
    set_part_limit(load_current_part_limit())


def show_completed_batches(
        icon: Icon,
        item: MenuItem,
) -> None:
    batches: list[CompletedBatch] = load_completed_batches()

    window: tk.Tk = tk.Tk()
    window.title("История партий")
    window_width: int = 650
    window_height: int = 400

    screen_width: int = window.winfo_screenwidth()
    screen_height: int = window.winfo_screenheight()

    x: int = (screen_width - window_width) // 2
    y: int = (screen_height - window_height) // 2

    window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    history_text: scrolledtext.ScrolledText = scrolledtext.ScrolledText(
        window,
        font=("Arial", 12),
    )
    history_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    if not batches:
        history_text.insert(tk.END, "История партий пуста")
    else:
        for batch in batches:
            history_text.insert(
                tk.END,
                (
                    f'{batch["date"]}: - '
                    f'Лимит: {batch["limit"]} - '
                    f'Имя файла: {batch["file_name"]}\n'
                )
            )

    history_text.configure(state=tk.DISABLED)
    window.mainloop()


def load_completed_batches() -> list[CompletedBatch]:
    return load_data_from_json()[BATCHES]


def save_completed_batch() -> None:
    data: DataJson = load_data_from_json()
    batches: list[CompletedBatch] = data[BATCHES]

    batch: CompletedBatch = {
        "date": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "limit": get_part_limit(),
        "file_name": ncstudio_file_name,
    }
    batches.insert(0, batch)
    save_data_to_json(data)


def get_part_limit() -> int:
    with limit_lock:
        return part_limit


def get_part_count() -> int:
    with part_count_lock:
        return part_count


def set_part_limit(new_limit: int) -> None:
    global part_limit

    with limit_lock:
        part_limit = new_limit

    save_current_part_limit(new_limit)


def set_part_count(new_count: int) -> None:
    global part_count

    with part_count_lock:
        part_count = new_count


def set_is_part_count_field_not_found(is_found: bool) -> None:
    global is_part_count_field_not_found

    with is_part_count_field_not_found_lock:
        is_part_count_field_not_found = is_found


def show_limit_warning(count: int, limit: int) -> None:
    root: tk.Tk = tk.Tk()

    root.withdraw()
    root.attributes("-topmost", True)

    messagebox.showwarning(
        "Партия завершена",
        f"Изготовлено деталей: {count}\n"
        f"Лимит деталей: {limit}",
        parent=root,
    )

    root.destroy()


def show_limit_editor(icon: Icon) -> None:
    current_limit: int = get_part_limit()
    current_part_count: int = get_part_count()

    root: tk.Tk = tk.Tk()

    root.withdraw()
    root.attributes("-topmost", True)

    while True:
        new_limit: int | None = simpledialog.askinteger(
            "Лимит партии",
            "Введите количество деталей:                              ",
            initialvalue=current_limit,
            minvalue=1,
            maxvalue=100,
            parent=root,
        )

        if new_limit is None:
            break;

        if new_limit <= current_part_count:
            messagebox.showinfo(
                "Неверный лимит",
                f"Новый лимит {new_limit} не может быть меньше\n"
                f"либо равен количеству изготовленныйх деталей {current_part_count}",
                parent=root,
            )
            continue

        set_part_limit(new_limit)
        update_tray_title(tray_icon=icon)
        break

    root.destroy()


def update_tray_title(tray_icon: Icon) -> None:
    tray_icon.title = (
        f"Количество сделанных листов: {get_part_count()}\n"
        f"Текущий лимит листов: {get_part_limit()}"
    )


def open_limit_editor(
        icon: Icon,
        item: MenuItem,
) -> None:
    threading.Thread(
        target=show_limit_editor,
        args=(icon,),
        daemon=True,
    ).start()


def show_current_limit(
        icon: Icon,
        item: MenuItem,
) -> None:
    limit: int = get_part_limit()

    def show_message() -> None:
        root: tk.Tk = tk.Tk()

        root.withdraw()
        root.attributes("-topmost", True)

        messagebox.showinfo(
            "Текущий лимит",
            f"Количество деталей в партии: {limit}",
            parent=root,
        )

        root.destroy()

    threading.Thread(
        target=show_message,
        daemon=True,
    ).start()


def read_part_count_from_ncstudio(window: UIAWrapper) -> int:
    global is_part_count_field_found
    print(
        f"line: {inspect.currentframe().f_lineno}, "
        f"window: {window}")
    elements: list[UIAWrapper] = window.descendants()
    print(
        f"line: {inspect.currentframe().f_lineno}, "
        f'elements - {elements}')
    if not elements:
        raise RuntimeError(f"elements: {elements} are empty or not found")

    for index, element in enumerate(elements):
        text: str = element.window_text().strip()
        # print(f"{index}: {text}")
        if text.lower() in ("part count:", "part count:"):
            next_index: int = index + 1
            # print(f"field: {text}")
            if next_index >= len(elements):
                raise RuntimeError("index out of bounds")

            value_text: str = elements[next_index].window_text().strip()

            try:
                return int(value_text)
            except ValueError:
                raise RuntimeError(
                    f"Значение Part Count не является целым числом: {value_text!r}"
                )

    set_is_part_count_field_not_found(True)
    raise RuntimeError("part count field not found")


def find_ncstudio_window() -> UIAWrapper:
    desktopUIA: Desktop = Desktop(backend="uia")
    desktopWin32: Desktop = Desktop(backend="win32")
    is_testing: bool = True

    desktops: list[Desktop] = [desktopUIA, desktopWin32]

    for desktop in desktops:
        window = next(
            (
                window
                for window in desktop.windows()
                if (
                           "ncstudio" in (
                       title := window.window_text().lower()
                   )
                           and "config" in title
                   ) or (
                           is_testing
                           and "ncstudio ad." in title
                   )
            ),
            None,
        )
        if window:
            print(
                f"line: {inspect.currentframe().f_lineno}, "
                f'window = {window}')
            set_ncstudio_file_name(window)
            return window

    raise RuntimeError("ncstudio window not found")


def set_ncstudio_file_name(window: UIAWrapper) -> None:
    global ncstudio_file_name
    title: str = window.window_text().strip()
    print(
        f"line: {inspect.currentframe().f_lineno}, "
        f'{title}')
    ncstudio_file_name = title.rsplit(" - ", 1)[-1].strip()
    print(
        f"line: {inspect.currentframe().f_lineno}, "
        f'{ncstudio_file_name}')


def monitor_ncstudio(tray_icon: Icon) -> None:
    blocked: bool = False
    while not monitor_stop_event.is_set():
        try:
            window: UIAWrapper = find_ncstudio_window()
            # todo здесь поменять
            current_part_count: int = read_part_count_from_ncstudio(window)  # prod
            # current_part_count: int = part_count  # test

            limit: int = get_part_limit()
            update_tray_title(tray_icon)

            print(
                f"line: {inspect.currentframe().f_lineno}, "
                f"Part Count: {current_part_count}, "
                f"Limit: {limit}"
            )

            if current_part_count >= limit and not blocked:
                show_limit_warning(
                    current_part_count,
                    limit
                )
                save_completed_batch()
                set_part_count(0)
                set_part_limit(100)
                blocked = True

            if current_part_count < limit:
                blocked = False


        except Exception as error:
            traceback.print_exc()
            start_error_menu(tray_icon)

        if monitor_stop_event.wait(CHECK_INTERVAL):
            break


def create_tray_image() -> Image.Image:
    image: Image.Image = Image.new(
        mode="RGBA",
        size=(64, 64),
        # color="white",

    )

    draw: ImageDraw.Draw = ImageDraw.Draw(image)

    # draw.rectangle(
    #     xy=(8, 8, 56, 56),
    #     fill="black",
    # )

    draw.text(
        xy=(19, 20),
        text="NC",
        font_size=36,
        fill="white",
    )

    return image


def exit_program(
        icon: Icon,
        item: MenuItem,
) -> None:
    monitor_stop_event.set()
    icon.stop()


def increment_part_count() -> int:
    global part_count

    with part_count_lock:
        part_count += 1
        return part_count


# test potom udalit' poka ostavit'
def increase_test_count(
        icon: Icon,
        item: MenuItem,
) -> None:
    current_count: int = increment_part_count()
    limit: int = get_part_limit()

    update_tray_title(icon)

    print(
        f"Test Part Count: {current_count}, "
        f"Limit: {limit}"
    )


def start_tray_menu() -> Icon:
    tray_menu: pystray.Menu = pystray.Menu(

        # MenuItem(
        #     text="Test +1 increment",
        #     action=increase_test_count
        # ),
        MenuItem(
            text="Задать лимит",
            action=open_limit_editor,
            default=True,
        ),
        MenuItem(
            text="Показать текущий лимит",
            action=show_current_limit
        ),
        MenuItem(
            text="Показать историю",
            action=show_completed_batches
        ),
        pystray.Menu.SEPARATOR,
        MenuItem(
            text="Выход",
            action=exit_program
        ),
    )

    tray_icon: Icon = Icon(
        name="ncstudio_part_counter",
        icon=create_tray_image(),
        title=(
            f"Количество сделанных листов: {get_part_count()}\n"
            f"Текущий лимит листов: {get_part_limit()}"
        ),
        menu=tray_menu,
    )

    return tray_icon


def start_error_menu(tray_icon: Icon) -> None:
    tray_icon.menu = pystray.Menu(
        MenuItem(
            text="Что-то пошло не так...",
            action=None,
            enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        MenuItem(
            text="Выход",
            action=exit_program
        ),
    )

    tray_icon.title = 'Что-то пошло не так...'


def main() -> None:
    load_data_on_startup()
    print(
        f"line: {inspect.currentframe().f_lineno}, ",
        f"path: {get_program_directory()}"
    )

    tray_icon: Icon = start_tray_menu()

    monitor_thread: threading.Thread = threading.Thread(
        target=monitor_ncstudio,
        args=(tray_icon,),
        daemon=True,
    )

    monitor_thread.start()

    tray_icon.run()


if __name__ == "__main__":
    main()
