
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Final

import pystray
from PIL import Image, ImageDraw
from pystray import Icon, MenuItem
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper

CHECK_INTERVAL: Final[float] = 10.0
ERROR_INTERVAL: Final[float] = 10.0

part_limit: int = 100
part_count: int = 0
monitor_stop_event: threading.Event = threading.Event()
limit_lock: threading.Lock = threading.Lock()
part_count_lock: threading.Lock = threading.Lock()


# set_part_limit при установке не срабатывает  отображается
# разная цифра лимита в инфо по лимиту - ✔

# ворнинг должен отображатся первым слоем - ✔

# сохранять данные
# - лимиты
# - название файла программы с датастемпом что бы была история


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


def set_part_count(new_count: int) -> None:
    global part_count

    with part_count_lock:
        part_count = new_count


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

    root: tk.Tk = tk.Tk()

    root.withdraw()
    root.attributes("-topmost", True)

    new_limit: int | None = simpledialog.askinteger(
        "Лимит партии",
        "Введите количество деталей:",
        initialvalue=current_limit,
        minvalue=1,
        maxvalue=100,
        parent=root,
    )

    if new_limit is not None:
        set_part_limit(new_limit)

        messagebox.showinfo(
            "Лимит изменён",
            f"Новый лимит партии: {new_limit}",
            parent=root,
        )

        update_tray_title(tray_icon=icon)

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


def read_part_count(window: UIAWrapper) -> int:
    print(f"window: {window}")
    elements: list[UIAWrapper] = window.descendants()
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

    raise RuntimeError("part count field not found")


def find_ncstudio_window() -> UIAWrapper:
    # todo здесь поменять
    desktop: Desktop = Desktop(backend="uia")
    # desktop: Desktop = Desktop(backend="win32")

    for window in desktop.windows():
        title: str = window.window_text()
        print(f"Window: {title!r}")
        if "ncstudio" in title.lower() and "config" in title.lower():
            return window

    raise RuntimeError("ncstudio window not found")


def monitor_ncstudio(tray_icon: Icon) -> None:
    global part_count
    blocked: bool = False
    while not monitor_stop_event.is_set():
        try:
            # todo здесь поменять
            window: UIAWrapper = find_ncstudio_window()
            current_part_count: int = read_part_count(window)
            set_part_count(current_part_count)
            # current_part_count: int = get_part_count()
            limit: int = get_part_limit()
            update_tray_title(tray_icon)

            print(
                f"Part Count: {current_part_count}, "
                f"Limit: {limit}"
            )

            if current_part_count >= limit and not blocked:
                show_limit_warning(
                    current_part_count,
                    limit
                )
                set_part_count(0)
                set_part_limit(100)
                blocked = True

            if current_part_count < limit:
                blocked = False


        except Exception as error:
            print(
                f"Error: {type(error).__name__}: {error!r}"
            )

            if monitor_stop_event.wait(ERROR_INTERVAL):
                break

            continue

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


def main() -> None:
    tray_menu: pystray.Menu = pystray.Menu(

        MenuItem(
            text="Test +1 increment",
            action=increase_test_count
        ),
        MenuItem(
            text="Задать лимит",
            action=open_limit_editor,
        ),
        MenuItem(
            text="Показать текущий лимит",
            action=show_current_limit,
            default=True,
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

    monitor_thread: threading.Thread = threading.Thread(
        target=monitor_ncstudio,
        args=(tray_icon,),
        daemon=True,
    )

    monitor_thread.start()

    tray_icon.run()


if __name__ == "__main__":
    main()
