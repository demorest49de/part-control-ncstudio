from pywinauto.controls.uiawrapper import UIAWrapper


class FakeUIAWrapper:
    def __init__(self, text: str):
        self.text = text

    def window_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text



fake_elements: list[FakeUIAWrapper] = [
    FakeUIAWrapper(""),
    FakeUIAWrapper("Pane"),
    FakeUIAWrapper("NcStudio"),
    FakeUIAWrapper("Feedrate(mm/min)"),
    FakeUIAWrapper("Setting:"),
    FakeUIAWrapper("5000"),
    FakeUIAWrapper("Actual:"),
    FakeUIAWrapper("4996"),
    FakeUIAWrapper("Current Line:"),
    FakeUIAWrapper("7307"),
    FakeUIAWrapper("Current Tool:"),
    FakeUIAWrapper("2"),
    FakeUIAWrapper("Spindle(r/min)"),
    FakeUIAWrapper("Setting:"),
    FakeUIAWrapper("24000"),
    FakeUIAWrapper("Actual:"),
    FakeUIAWrapper("24000"),
    FakeUIAWrapper("Spindle:"),
    FakeUIAWrapper("ON"),
    FakeUIAWrapper("Current Command Set:"),
    FakeUIAWrapper("G21 G90 G17"),
    FakeUIAWrapper("Part Count:"),
    FakeUIAWrapper("2"),
    FakeUIAWrapper("Repeat Process"),
    FakeUIAWrapper("0mm"),
    FakeUIAWrapper("Repeat-Process Count:"),
    FakeUIAWrapper("1/1"),
    FakeUIAWrapper("Repeat-Process Interval Time"),
    FakeUIAWrapper("100"),
    FakeUIAWrapper("Tool Message"),
    FakeUIAWrapper("Cur Tool Index:"),
    FakeUIAWrapper("2"),
    FakeUIAWrapper("Tool Diameter:"),
    FakeUIAWrapper("0mm"),
    FakeUIAWrapper("Dia. Abrasion:"),
    FakeUIAWrapper("0mm"),
    FakeUIAWrapper("Len. Abrasion:"),
    FakeUIAWrapper("0mm"),
    FakeUIAWrapper("Set Tool Param"),
    FakeUIAWrapper("Progress"),
    FakeUIAWrapper("Finish Percent:"),
    FakeUIAWrapper("86.689%"),
]    # test