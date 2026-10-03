from decimal import Decimal, getcontext
import re

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

getcontext().prec = 100

DIGITS = "0123456789ABCDEFGHIJ"


def digit_value(ch):
    ch = ch.upper()
    if ch not in DIGITS:
        raise ValueError("Invalid digit")
    return DIGITS.index(ch)


def digit_char(n):
    n = int(n)
    if n < 0 or n >= len(DIGITS):
        raise ValueError("Invalid digit")
    return DIGITS[n]


def base_name(base):
    names = {
        2: "Binary", 8: "Octal", 10: "Decimal", 16: "Hexadecimal"
    }
    return names.get(base, f"Base-{base}")


def base_to_decimal(text, base):
    text = str(text).strip().upper()
    if not text:
        raise ValueError("Empty number")

    negative = False
    if text.startswith("-"):
        negative, text = True, text[1:]
    elif text.startswith("+"):
        text = text[1:]

    if not text or text.count(".") > 1:
        raise ValueError("Invalid number")

    if "." in text:
        integer_part, fraction_part = text.split(".")
    else:
        integer_part, fraction_part = text, ""

    integer_part = integer_part or "0"

    for ch in integer_part + fraction_part:
        if ch not in DIGITS or digit_value(ch) >= base:
            raise ValueError(f"Invalid digit: {ch}")

    result = Decimal(0)
    for ch in integer_part:
        result = result * Decimal(base) + Decimal(digit_value(ch))

    power = Decimal(1)
    for ch in fraction_part:
        power *= Decimal(base)
        result += Decimal(digit_value(ch)) / power

    return -result if negative else result


def decimal_to_base(number, base, precision=60):
    number = Decimal(number)
    if number == 0:
        return "0"

    negative = number < 0
    if negative:
        number = -number

    integer_part = int(number)
    if integer_part == 0:
        integer_text = "0"
    else:
        result_digits = []
        n = integer_part
        while n > 0:
            n, remainder = divmod(n, base)
            result_digits.append(digit_char(remainder))
        integer_text = "".join(reversed(result_digits))

    fraction = number - Decimal(integer_part)
    if fraction == 0:
        result = integer_text
    else:
        fraction_digits = []
        for _ in range(precision):
            if fraction == 0:
                break
            fraction *= Decimal(base)
            d = int(fraction)
            fraction -= Decimal(d)
            fraction_digits.append(digit_char(d))

        while fraction_digits and fraction_digits[-1] == "0":
            fraction_digits.pop()

        result = integer_text
        if fraction_digits:
            result += "." + "".join(fraction_digits)

    return "-" + result if negative else result


def convert_base(value, from_base, to_base):
    return decimal_to_base(base_to_decimal(value, from_base), to_base)


class ExpressionParser:
    def __init__(self, expression, base):
        self.expression = expression.upper().replace("×", "*").replace("÷", "/").replace("−", "-")
        self.base = base
        self.tokens = self.tokenize(self.expression)
        self.position = 0

    def tokenize(self, expression):
        tokens = []
        i = 0
        while i < len(expression):
            ch = expression[i]
            if ch.isspace():
                i += 1
                continue
            if ch in "+-*/()":
                tokens.append(ch)
                i += 1
                continue
            if ch in DIGITS or ch == ".":
                start = i
                dots = 0
                while i < len(expression):
                    c = expression[i]
                    if c in DIGITS:
                        i += 1
                    elif c == ".":
                        dots += 1
                        if dots > 1:
                            raise ValueError("Invalid decimal point")
                        i += 1
                    else:
                        break
                number = expression[start:i]
                base_to_decimal(number, self.base)
                tokens.append(number)
                continue
            raise ValueError(f"Invalid character: {ch}")
        return tokens

    def current(self):
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def eat(self):
        token = self.current()
        self.position += 1
        return token

    def parse(self):
        if not self.tokens:
            raise ValueError("Empty expression")
        result = self.expression_rule()
        if self.current() is not None:
            raise ValueError("Unexpected token")
        return result

    def expression_rule(self):
        result = self.term()
        while self.current() in ("+", "-"):
            op = self.eat()
            value = self.term()
            result = result + value if op == "+" else result - value
        return result

    def term(self):
        result = self.factor()
        while self.current() in ("*", "/"):
            op = self.eat()
            value = self.factor()
            if op == "*":
                result *= value
            else:
                if value == 0:
                    raise ZeroDivisionError()
                result /= value
        return result

    def factor(self):
        token = self.current()
        if token is None:
            raise ValueError("Expected number")
        if token == "-":
            self.eat()
            return -self.factor()
        if token == "+":
            self.eat()
            return self.factor()
        if token == "(":
            self.eat()
            result = self.expression_rule()
            if self.current() != ")":
                raise ValueError("Missing )")
            self.eat()
            return result
        self.eat()
        return base_to_decimal(token, self.base)


def calculate_expression(expression, base):
    return ExpressionParser(expression, base).parse()


# ---------- UI helpers ----------

BG = (6/255, 27/255, 57/255, 1)
BLUE = (7/255, 84/255, 165/255, 1)
ORANGE = (1, 185/255, 0, 1)
PURPLE = (142/255, 37/255, 244/255, 1)
GREEN = (32/255, 168/255, 90/255, 1)
LIGHT = (229/255, 234/255, 242/255, 1)
DARK_INPUT = (6/255, 37/255, 66/255, 1)
WHITE = (1, 1, 1, 1)
YELLOW = (1, 210/255, 63/255, 1)


class CalcButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.color = WHITE
        self.font_size = dp(16)
        self.bold = True


class ICTCalculatorRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.padding = dp(10)
        self.spacing = dp(5)
        self.active_base = 10
        self.current_number = ""
        self.expression = ""
        self.just_calculated = False
        self.page = 1
        self.build_main()

    def label(self, text, size=14, color=WHITE, **kwargs):
        return Label(text=text, font_size=dp(size), color=color, **kwargs)

    def button(self, text, callback, bg=BLUE, size=16):
        b = CalcButton(text=text, font_size=dp(size), background_color=bg)
        b.bind(on_release=callback)
        return b

    def build_main(self):
        self.clear_widgets()
        self.page = 1
        self.active_base = 10
        self.current_number = ""
        self.expression = ""
        self.just_calculated = False

        self.add_widget(self.label("ICT CALCULATOR", 23, WHITE, size_hint_y=None, height=dp(40)))
        self.add_widget(self.label("Number System Calculator", 12, (155/255,184/255,221/255,1),
                                   size_hint_y=None, height=dp(25)))

        self.main_expr_label = self.label("", 14, (143/255,175/255,213/255,1),
                                          size_hint_y=None, height=dp(28))
        self.main_expr_label.halign = "right"
        self.add_widget(self.main_expr_label)

        self.entries = {}
        for name, base in [("BIN",2),("OCT",8),("DEC",10),("HEX",16)]:
            row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(5))
            b = self.button(name, lambda _, x=base: self.select_main_base(x), BLUE, 13)
            b.size_hint_x = .18
            row.add_widget(b)
            e = TextInput(text="0", multiline=False, halign="right", font_size=dp(21),
                          foreground_color=WHITE, background_color=DARK_INPUT,
                          cursor_color=WHITE, padding=[dp(5), dp(10)])
            e.bind(focus=lambda obj, focus, x=base: self.select_main_base(x) if focus else None)
            e.bind(text=lambda obj, value, x=base: self.main_direct_input(x))
            row.add_widget(e)
            self.entries[base] = e
            self.add_widget(row)

        self.active_label = self.label("ACTIVE BASE: DECIMAL", 11, YELLOW,
                                       size_hint_y=None, height=dp(25))
        self.add_widget(self.active_label)

        more = self.button("MORE BASE\n(Base 2 - 20)", self.show_more, BLUE, 15)
        more.size_hint_y = None
        more.height = dp(55)
        self.add_widget(more)

        grid = GridLayout(cols=6, rows=5, spacing=dp(4), size_hint_y=1)

        self.main_digit_buttons = {}
        for k in "ABCDEF":
            b = self.button(k, lambda _, x=k: self.main_number(x))
            self.main_digit_buttons[k] = b
            grid.add_widget(b)

        for text, cmd, bg in [
            ("7", lambda _: self.main_number("7"), BLUE),
            ("8", lambda _: self.main_number("8"), BLUE),
            ("9", lambda _: self.main_number("9"), BLUE),
            ("÷", lambda _: self.main_operator("/"), ORANGE),
            ("×", lambda _: self.main_operator("*"), ORANGE),
            ("(", lambda _: self.main_parenthesis("("), ORANGE),
            ("4", lambda _: self.main_number("4"), BLUE),
            ("5", lambda _: self.main_number("5"), BLUE),
            ("6", lambda _: self.main_number("6"), BLUE),
            ("+", lambda _: self.main_operator("+"), ORANGE),
            ("−", lambda _: self.main_operator("-"), ORANGE),
            (")", lambda _: self.main_parenthesis(")"), ORANGE),
            ("1", lambda _: self.main_number("1"), BLUE),
            ("2", lambda _: self.main_number("2"), BLUE),
            ("3", lambda _: self.main_number("3"), BLUE),
            (".", lambda _: self.main_number("."), BLUE),
            ("=", lambda _: self.main_equal(), PURPLE),
            ("AC", lambda _: self.main_clear(), LIGHT),
            ("0", lambda _: self.main_number("0"), BLUE),
            ("⌫", lambda _: self.main_backspace(), LIGHT),
        ]:
            b = self.button(text, cmd, bg, 15)
            if text in ("AC", "⌫"):
                b.color = (16/255,33/255,61/255,1)
            grid.add_widget(b)

        self.add_widget(grid)
        self.add_widget(self.label("BIN / OCT / DEC / HEX ঘরে ক্লিক করে সরাসরি সংখ্যা লিখুন",
                                   9, (126/255,159/255,199/255,1),
                                   size_hint_y=None, height=dp(24)))
        self.update_main_keyboard()

    def select_main_base(self, base):
        self.active_base = base
        self.active_label.text = f"ACTIVE BASE: {base_name(base).upper()}"
        self.update_main_keyboard()

    def update_main_keyboard(self):
        for key, b in self.main_digit_buttons.items():
            b.disabled = digit_value(key) >= self.active_base
        # Grid children with numeric text
        if not hasattr(self, "entries"):
            return

    def main_number(self, key):
        key = key.upper()
        if key != "." and digit_value(key) >= self.active_base:
            return
        if self.just_calculated:
            self.expression = ""
            self.current_number = ""
            self.just_calculated = False
        if key == ".":
            if "." in self.current_number:
                return
            self.current_number = (self.current_number + ".") if self.current_number else "0."
        else:
            if self.current_number == "0":
                self.current_number = key
            else:
                self.current_number += key
        self.main_convert_current()

    def main_convert_current(self):
        if not self.current_number:
            return
        try:
            value = base_to_decimal(self.current_number, self.active_base)
            self.update_main_displays(value, self.active_base, self.current_number)
        except Exception:
            pass

    def update_main_displays(self, value, selected_base=None, selected_text=None):
        for base, e in self.entries.items():
            e.unbind(text=self._dummy) if hasattr(self, "_dummy") else None
            e.text = selected_text if selected_base == base and selected_text is not None else decimal_to_base(value, base)

    def main_direct_input(self, base):
        if not hasattr(self, "entries"):
            return
        text = self.entries[base].text.strip().upper()
        if not text:
            return
        try:
            value = base_to_decimal(text, base)
            self.active_base = base
            self.active_label.text = f"ACTIVE BASE: {base_name(base).upper()}"
            self.current_number = text
            self.expression = ""
            self.just_calculated = False
            self.update_main_displays(value, base, text)
            self.update_main_keyboard()
        except Exception:
            pass

    def main_operator(self, operator):
        base = self.active_base
        if self.current_number:
            try:
                value = base_to_decimal(self.current_number, base)
            except Exception:
                return
            self.expression += decimal_to_base(value, 10)
            self.current_number = ""
        if not self.expression:
            if operator == "-":
                self.expression = "-"
            else:
                return
        elif self.expression[-1:] in "+-*/":
            self.expression = self.expression[:-1] + operator
        else:
            self.expression += operator
        self.main_show_expression()

    def main_parenthesis(self, symbol):
        base = self.active_base
        if symbol == "(":
            if self.current_number:
                try:
                    value = base_to_decimal(self.current_number, base)
                except Exception:
                    return
                self.expression += decimal_to_base(value, 10) + "*"
                self.current_number = ""
            self.expression += "("
        else:
            if self.current_number:
                try:
                    value = base_to_decimal(self.current_number, base)
                except Exception:
                    return
                self.expression += decimal_to_base(value, 10)
                self.current_number = ""
            self.expression += ")"
        self.main_show_expression()

    def main_show_expression(self):
        self.main_expr_label.text = self.expression.replace("*","×").replace("/","÷")

    def main_equal(self):
        if self.current_number:
            try:
                value = base_to_decimal(self.current_number, self.active_base)
                self.expression += decimal_to_base(value, 10)
                self.current_number = ""
            except Exception:
                return
        if not self.expression:
            return
        try:
            result = calculate_expression(self.expression, 10)
            self.update_main_displays(result)
            self.current_number = decimal_to_base(result, self.active_base)
            self.main_expr_label.text = self.expression.replace("*","×").replace("/","÷") + " ="
            self.expression = ""
            self.just_calculated = True
        except ZeroDivisionError:
            self.main_expr_label.text = "ERROR: Division by zero"
        except Exception:
            self.main_expr_label.text = "ERROR: Invalid expression"

    def main_backspace(self):
        if self.just_calculated:
            self.just_calculated = False
            self.current_number = ""
            self.main_set_zero()
            return
        if self.current_number:
            self.current_number = self.current_number[:-1] or "0"
            self.main_convert_current()
        elif self.expression:
            self.expression = self.expression[:-1]
            self.main_show_expression()

    def main_clear(self):
        self.current_number = ""
        self.expression = ""
        self.just_calculated = False
        self.main_expr_label.text = ""
        self.main_set_zero()

    def main_set_zero(self):
        for e in self.entries.values():
            e.text = "0"

    # ---------- More Base page ----------

    def show_more(self, *_):
        self.clear_widgets()
        self.page = 2
        self.more_current = ""
        self.more_expression = ""
        self.more_just_calculated = False

        header = BoxLayout(size_hint_y=None, height=dp(55))
        back = self.button("←", lambda _: self.build_main(), BLUE, 24)
        back.size_hint_x = .18
        header.add_widget(back)
        header.add_widget(self.label("MORE BASE", 21, WHITE))
        self.add_widget(header)

        self.add_widget(self.label("FROM BASE", 11, WHITE, size_hint_y=None, height=dp(25)))
        values = [f"{b} - {base_name(b)}" for b in range(2,21)]
        self.from_spinner = Spinner(text="10 - Decimal", values=values,
                                    size_hint_y=None, height=dp(48),
                                    background_normal="", background_color=BLUE,
                                    color=WHITE, font_size=dp(14))
        self.from_spinner.bind(text=lambda *_: self.more_base_changed())
        self.add_widget(self.from_spinner)

        self.add_widget(self.label("TO BASE", 11, WHITE, size_hint_y=None, height=dp(25)))
        self.to_spinner = Spinner(text="16 - Hexadecimal", values=values,
                                  size_hint_y=None, height=dp(48),
                                  background_normal="", background_color=PURPLE,
                                  color=WHITE, font_size=dp(14))
        self.to_spinner.bind(text=lambda *_: self.more_convert_current())
        self.add_widget(self.to_spinner)

        self.more_expr_label = self.label("", 12, (143/255,175/255,213/255,1),
                                          size_hint_y=None, height=dp(28))
        self.more_expr_label.halign = "right"
        self.add_widget(self.more_expr_label)

        self.more_display = TextInput(text="0", multiline=False, halign="right",
                                      font_size=dp(21), foreground_color=WHITE,
                                      background_color=DARK_INPUT, size_hint_y=None, height=dp(58))
        self.more_display.bind(text=self.more_direct_entry)
        self.add_widget(self.more_display)

        self.more_active = self.label("ACTIVE INPUT BASE: DECIMAL", 10, YELLOW,
                                      size_hint_y=None, height=dp(25))
        self.add_widget(self.more_active)
        self.add_widget(self.label("RESULT", 10, WHITE, size_hint_y=None, height=dp(24)))

        self.more_result = TextInput(text="", readonly=True, multiline=False, halign="right",
                                     font_size=dp(20), foreground_color=(96/255,216/255,1,1),
                                     background_color=DARK_INPUT, size_hint_y=None, height=dp(55))
        self.add_widget(self.more_result)

        grid = GridLayout(cols=6, spacing=dp(4), size_hint_y=1)
        self.more_digit_buttons = {}
        for k in "ABCDEFGHIJ":
            b = self.button(k, lambda _, x=k: self.more_number(x), BLUE, 13)
            self.more_digit_buttons[k] = b
            grid.add_widget(b)

        for text, cmd, bg in [
            ("÷", lambda _: self.more_operator("/"), ORANGE),
            ("×", lambda _: self.more_operator("*"), ORANGE),
            ("7", lambda _: self.more_number("7"), BLUE),
            ("8", lambda _: self.more_number("8"), BLUE),
            ("9", lambda _: self.more_number("9"), BLUE),
            ("+", lambda _: self.more_operator("+"), ORANGE),
            ("4", lambda _: self.more_number("4"), BLUE),
            ("5", lambda _: self.more_number("5"), BLUE),
            ("6", lambda _: self.more_number("6"), BLUE),
            ("−", lambda _: self.more_operator("-"), ORANGE),
            ("(", lambda _: self.more_parenthesis("("), ORANGE),
            (")", lambda _: self.more_parenthesis(")"), ORANGE),
            ("1", lambda _: self.more_number("1"), BLUE),
            ("2", lambda _: self.more_number("2"), BLUE),
            ("3", lambda _: self.more_number("3"), BLUE),
            ("0", lambda _: self.more_number("0"), BLUE),
            (".", lambda _: self.more_number("."), BLUE),
            ("=", lambda _: self.more_equal(), PURPLE),
            ("AC", lambda _: self.more_clear(), LIGHT),
            ("⌫", lambda _: self.more_backspace(), LIGHT),
        ]:
            b = self.button(text, cmd, bg, 13)
            if text in ("AC","⌫"):
                b.color = (16/255,33/255,61/255,1)
            grid.add_widget(b)

        conv = self.button("CONVERT", lambda _: self.more_convert_only(), GREEN, 14)
        home = self.button("HOME", lambda _: self.build_main(), PURPLE, 14)
        grid.add_widget(conv)
        grid.add_widget(home)
        self.add_widget(grid)
        self.update_more_keyboard()

    def get_from_base(self):
        return int(self.from_spinner.text.split("-")[0].strip())

    def get_to_base(self):
        return int(self.to_spinner.text.split("-")[0].strip())

    def more_base_changed(self):
        self.more_current = ""
        self.more_expression = ""
        self.more_just_calculated = False
        self.more_display.text = "0"
        self.more_expr_label.text = ""
        self.more_result.text = ""
        self.update_more_keyboard()

    def update_more_keyboard(self):
        base = self.get_from_base()
        self.more_active.text = f"ACTIVE INPUT BASE: {base_name(base).upper()}"
        for key, b in self.more_digit_buttons.items():
            b.disabled = digit_value(key) >= base

    def more_number(self, key):
        key = key.upper()
        base = self.get_from_base()
        if key != "." and digit_value(key) >= base:
            return
        if self.more_just_calculated:
            self.more_expression = ""
            self.more_current = ""
            self.more_just_calculated = False
        if key == ".":
            if "." in self.more_current:
                return
            self.more_current = self.more_current + "." if self.more_current else "0."
        else:
            self.more_current = key if self.more_current == "0" else self.more_current + key
        self.more_display.text = self.more_current
        self.more_convert_current()

    def more_direct_entry(self, *_):
        if not hasattr(self, "more_display"):
            return
        text = self.more_display.text.strip().upper()
        base = self.get_from_base()
        valid = ""
        dot = False
        for ch in text:
            if ch == "." and not dot:
                valid += ch
                dot = True
            elif ch in DIGITS and digit_value(ch) < base:
                valid += ch
        if valid != text:
            self.more_display.text = valid
        self.more_current = valid
        if valid:
            try:
                base_to_decimal(valid, base)
                self.more_convert_current()
            except Exception:
                pass

    def more_convert_current(self, *_):
        value = self.more_current.strip()
        if not value:
            return
        try:
            self.more_result.text = convert_base(value, self.get_from_base(), self.get_to_base())
        except Exception:
            self.more_result.text = "Invalid Number"

    def more_operator(self, operator):
        base = self.get_from_base()
        if self.more_current:
            try:
                base_to_decimal(self.more_current, base)
            except Exception:
                return
            self.more_expression += self.more_current
            self.more_current = ""
        if not self.more_expression:
            if operator == "-":
                self.more_expression = "-"
            else:
                return
        elif self.more_expression[-1:] in "+-*/":
            self.more_expression = self.more_expression[:-1] + operator
        else:
            self.more_expression += operator
        self.more_expr_label.text = self.more_expression.replace("*","×").replace("/","÷")
        self.more_display.text = ""

    def more_parenthesis(self, symbol):
        base = self.get_from_base()
        if symbol == "(":
            if self.more_current:
                try:
                    base_to_decimal(self.more_current, base)
                except Exception:
                    return
                self.more_expression += self.more_current + "*"
                self.more_current = ""
            self.more_expression += "("
        else:
            if self.more_current:
                try:
                    base_to_decimal(self.more_current, base)
                except Exception:
                    return
                self.more_expression += self.more_current
                self.more_current = ""
            self.more_expression += ")"
        self.more_expr_label.text = self.more_expression.replace("*","×").replace("/","÷")
        self.more_display.text = ""

    def more_equal(self):
        base = self.get_from_base()
        to_base = self.get_to_base()
        if self.more_current:
            try:
                base_to_decimal(self.more_current, base)
            except Exception:
                return
            self.more_expression += self.more_current
            self.more_current = ""
        if not self.more_expression:
            return
        try:
            result = calculate_expression(self.more_expression, base)
            output = decimal_to_base(result, to_base)
            self.more_result.text = output
            self.more_display.text = output
            self.more_expr_label.text = self.more_expression.replace("*","×").replace("/","÷") + " ="
            self.more_current = output
            self.more_expression = ""
            self.more_just_calculated = True
        except ZeroDivisionError:
            self.more_result.text = "Division by zero"
        except Exception:
            self.more_result.text = "Invalid expression"

    def more_convert_only(self):
        value = self.more_display.text.strip()
        if not value:
            return
        try:
            self.more_result.text = convert_base(value, self.get_from_base(), self.get_to_base())
        except Exception:
            self.more_result.text = "Invalid Number"

    def more_backspace(self):
        if self.more_just_calculated:
            self.more_just_calculated = False
            self.more_current = ""
            self.more_display.text = "0"
            self.more_result.text = ""
            return
        if self.more_current:
            self.more_current = self.more_current[:-1] or "0"
            self.more_display.text = self.more_current
            self.more_convert_current()
        elif self.more_expression:
            self.more_expression = self.more_expression[:-1]
            self.more_expr_label.text = self.more_expression.replace("*","×").replace("/","÷")

    def more_clear(self):
        self.more_current = ""
        self.more_expression = ""
        self.more_just_calculated = False
        self.more_expr_label.text = ""
        self.more_display.text = "0"
        self.more_result.text = ""


class ICTCalculatorApp(App):
    title = "ICT Calculator"

    def build(self):
        Window.clearcolor = BG
        return ICTCalculatorRoot()


if __name__ == "__main__":
    ICTCalculatorApp().run()
