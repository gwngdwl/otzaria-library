from __future__ import annotations

import json
import re
from collections.abc import Callable
from functools import partial

import mwparserfromhell
from mwparserfromhell.nodes.template import Template
from wikiexpand.expand import ExpansionContext
from wikiexpand.expand.templates import TemplateDict

from . import mediawikiapi, template_funcs, utils

TemplateAction = Callable[[Template], str]

wikisource_replacement_dict: dict[str, Callable[[Template], str]] = {
    "קיצור דרך": template_funcs.remove,
    "פרשן על פסוק": template_funcs.remove,
    "צמ": template_funcs.bold_and_parenthesize,
    "קטע של פירוש על פסוק": template_funcs.remove,
    "#קטע": template_funcs.remove,
    "צ": template_funcs.bold_italic_and_gersim,
    "קישור למחבר": template_funcs.remove,
    "כו": template_funcs.remove,
    "טקסט מושלם": template_funcs.remove,
    "ש": template_funcs.new_line,
    "עמוד": template_funcs.remove,
    "ק": template_funcs.parenthesize_one,
    "ג": template_funcs.big,
    "אקרוסטיכון": template_funcs.big_bold,
    "בעבודה": template_funcs.remove,
    "סרגל דקדוקי הטעמים": template_funcs.remove,
    "פפ": template_funcs.remove,
    "הערות שוליים": template_funcs.remove,
    "מ:טעמי המקרא": template_funcs.remove,
    "מ:שוליים": template_funcs.remove,
    "מכלול": template_funcs.remove,
    "ממכ": template_funcs.mmc,
    "גדול-מודגש": template_funcs.big_bold,
    "קטן": template_funcs.parenthesize_only,
    "ש-רווח": template_funcs.space,
    "ערך עם עוגן": template_funcs.big_bold,
    "מיזמים": template_funcs.remove,
    "יצירה": template_funcs.remove,
    "היברובוקס": template_funcs.remove,
    "עוגן": template_funcs.remove,
    "קט": partial(template_funcs.keep_some_params, params_to_keep=[0]),
    "ציטוטון": template_funcs.gersim_and_parenthesize,
    "מצ": template_funcs.mz,
    "צמפ": template_funcs.mz,
    "סרגל ניווט": template_funcs.remove,
    "קיצור": partial(template_funcs.keep_some_params, params_to_keep=[1]),
    "!": template_funcs.remove,
    "צפ": template_funcs.zp,
    "נ": partial(template_funcs.keep_some_params, params_to_keep=[0]),
    "ממורכז": template_funcs.save_all,
    "דף שער": template_funcs.remove,
    "הפניה-גמ": partial(template_funcs.keep_some_params, params_to_keep=[0, 1, 2]),
    "ממ": template_funcs.parenthesize_only,
    "צבע גופן": partial(template_funcs.keep_some_params, params_to_keep=[1])
}

replacement_dict: dict[str, TemplateAction] = {}


def filter_templates(string: str, all_templates: list[str] | None = None, template_dict: TemplateDict | None = None) -> list[list[str]] | bool:
    """מחזיר את התבניות ברמה העליונה של הטקסט."""
    string_2 = []
    parsed = mwparserfromhell.parse(string)
    templates = parsed.filter_templates(parsed.RECURSE_OTHERS)
    if templates:
        for template in templates:
            template_name = str(template.name).strip()
            # טיפול בתבניות מיוחדות שמתחילות ב #
            if template_name.startswith("#") and ":" in template_name:
                template_name = template_name.split(":", 1)[0].strip()
            if all_templates and template_dict and template_name in all_templates:
                template_str = convert_templates(str(template), template_dict)
            elif template_name in replacement_dict:
                template_str = replacement_dict[template_name](template)
            else:
                template_str = " ".join([str(param) for param in template.params])
            string_2.append([str(template), template.name, template_str])
        return string_2
    return False


def clean_comment(comment: str, all_templates: list | None, template_dict: TemplateDict) -> str:
    """מסיר תבניות מההערה."""
    while True:
        replace = filter_templates(comment, all_templates, template_dict)
        if not replace:
            break
        for i in replace:
            rp = i[2]
            comment = comment.replace(i[0], rp)
    return comment


def remove_templates(wikitext: str, template_dict=None) -> tuple[str, dict]:
    """
    מסיר תבניות ללא פרמטרים
    תבנית עם פרמטרים התבנית מוסרת והפרמטרים נשארים
    תבנית הערה מוסרת ונכנסת הפנייה במקומה. """
    if template_dict:
        all_templates = [i for i in template_dict.keys()]
        template_dict = templates_dict(template_dict)
    else:
        all_templates = None
        template_dict = None

    dict_comments = {}
    sup = 0
    remove_templates_dict = {
        "ש": "\n",
        "חלקי": "",
        # "גופן": "",
    }
    while True:
        replace = filter_templates(wikitext, all_templates, template_dict)
        if replace is False:
            break
        for i in replace:
            if i[1].strip() == "הערה":
                sup += 1
                dict_comments[sup] = clean_comment(i[2], all_templates, template_dict)
                rp = f'<sup style="color: gray;">{sup}</sup>'
            elif i[1].strip() in remove_templates_dict:
                rp = remove_templates_dict[i[1].strip()]
            else:
                rp = i[2]
            wikitext = wikitext.replace(i[0], rp)
    counter = 0
    sorted_dict = {}
    for num in re.findall(r'<sup style="color: gray;">(\d+)</sup>', wikitext):
        counter += 1
        wikitext = wikitext.replace(rf'<sup style="color: gray;">{num}</sup>', rf'<sup style="color: gray;">{counter}</sup>')
        sorted_dict[counter] = dict_comments[int(num)]
    return wikitext, sorted_dict


def templates_dict(dict_content: dict) -> TemplateDict:
    tpl = TemplateDict()
    for key, value in dict_content.items():
        tpl[key] = value

    return tpl


def convert_templates(mw_content: str, tpl: TemplateDict) -> str:
    ctx = ExpansionContext(templates=tpl)
    expanded_text = str(ctx.expand(mw_content))
    return expanded_text


def get_all_templates() -> None:
    import os
    base_folder = r"C:\Users\משתמש\Desktop\תבניות ויקיטקסט"
    mediawikiapi.BASE_URL = mediawikiapi.WIKISOURCE
    all_templates = mediawikiapi.get_list_by_ns(10)
    for template in all_templates:
        content = mediawikiapi.get_page_content(template)
        file_path = os.path.join(base_folder, f"{utils.sanitize_filename(template.split(":")[-1])}.txt")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        print(template)


def get_template_from_site(site: str, template_name: str, json_file_path: str) -> None:
    with open(json_file_path, "r", encoding="utf-8") as f:
        template = json.load(f)
    if not template.get(template_name):
        mediawikiapi.BASE_URL = site
        mediawikiapi.get_page_content(f"תבנית:{template_name}")
        template = [template_name] = ""
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=4)
