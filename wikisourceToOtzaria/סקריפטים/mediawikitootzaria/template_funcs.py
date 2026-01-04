from mwparserfromhell.nodes.template import Template


def remove(*args) -> str:
    return ""


def new_line(*args) -> str:
    return "\n"


def space(*args) -> str:
    return " "


def bold_and_parenthesize(template: Template) -> str:
    return f"(<b>{template.params[0]}</b>) ({template.params[1]})"


def parenthesize_only(template: Template) -> str:
    return f"({" ".join(map(str, template.params))})"


def parenthesize_one(template: Template) -> str:
    return f"({template.params[0]})"


def big(template: Template) -> str:
    return f"<big>{" ".join(map(str, template.params))}</big>"


def big_bold(template: Template) -> str:
    return f"<b><big>{" ".join(map(str, template.params))}</big></b>"


def bold_italic_and_gersim(template: Template) -> str:
    return f'"<b><i>{" ".join(map(str, template.params))}</i></b>"'


def gersim_and_parenthesize(template: Template) -> str:
    return f'"{template.params[0]}" ({template.params[1]})'


def keep_some_params(template: Template, params_to_keep: list[int]) -> str:
    kept_params = [str(template.params[i]) for i in params_to_keep if i < len(template.params)]
    return " ".join(kept_params)


def mmc(template: Template) -> str:
    parts = " ".join(map(str, template.params))
    return parts.replace("לפני=", "").replace("אחרי=", "")


def mz(template: Template) -> str:
    return f'({template.params[0]} {template.params[1]}) "{template.params[2]}"' if len(template.params) >= 3 else str(template.params[0])


def zp(template: Template) -> str:
    return f'"{str(template.params[0]).replace("תוכן=", "")}" ({str(template.params[1]).replace("מקור=", "")})'


def h_1(template: Template) -> str:
    return f"<h1>{" ".join(map(str, template.params))}</h1>"


def save_all(template: Template) -> str:
    return " ".join(map(str, template.params))
