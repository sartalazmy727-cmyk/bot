# bot.py
# -*- coding: utf-8 -*-

"""
AOU Kuwait Telegram Bot — FINAL (Updated)

✅ بوابة جهة اتصال (للأعضاء فقط) + يقبل الكويت فقط (+965)
✅ السوبر أدمن فقط (IDs محددة) يقدر:
   - تشغيل/إيقاف خدمة الأرقام
   - مسح قوائم الأرقام (المقبولة/المرفوضة)
   - إخفاء/إظهار الأزرار للعامة
   - تغيير أسماء الأزرار
   - إدارة الأدمن الإضافيين
   - التحكم الكامل بالتقويم (تلقائي/مخصص/حذف) + (إرفاق PDF/صورة/نص)
✅ الأدمن الإضافي يقدر:
   - رفع/تعديل/حذف (ملف/صورة/نص) لأقسام الخدمات والملخصات
   - إضافة/تعديل/حذف القروبات العامة
   - إضافة/حذف روابط قروبات الكليات
   - مشاهدة الأرقام المقبولة/المرفوضة + تصدير Excel (بدون مسح/تغيير)
✅ زر "التقويم الجامعي": يسمح للأدمن بإرفاق (PDF/صورة/نص) داخل الزر نفسه.
✅ زر "السحب والإضافة": أصبح قابلاً للإدارة بواسطة الأدمن فقط (PDF/صورة/نص).
✅ تصدير الأرقام إلى ملف Excel (Sheet للمقبولة وSheet للمرفوضة)

المتطلبات:
  pip install python-telegram-bot==21.6 openpyxl

ملاحظة:
- ضع توكنك بدل "123456789"
- SUPER_ADMIN_IDS تم تثبيتها حسب طلبك
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, List, Optional, Set, Tuple

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from telegram import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatType
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================================================
# BASIC SETTINGS
# =========================================================
TOKEN = "8308362115:AAFj9WDYSjF0YYlvo1r1bgkRPyXi49h1VJ4"  # <- غيّره
DATA_FILE = "bot_data.json"
DATA_LOCK = RLock()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
LOG = logging.getLogger("AOU_BOT_FINAL")

MAX_TEXT_LEN = 3600
MAX_INBOX = 300

# ✅ السوبر أدمن فقط (حسب طلبك)
SUPER_ADMIN_IDS: Set[int] = {8136678328, 164796308, 8318266324}

# =========================================================
# LINKS
# =========================================================
UNIV_URL = "https://www.aou.edu.kw/ar/Pages/default.aspx"
ADMISSION_URL = "https://www.aou.edu.kw/ar/admission/pages/undergraduate-apply.aspx"
AOU_CALENDAR_PAGE_EN = "https://www.aou.edu.kw/students/Pages/academic-calendar.aspx"
AOU_CALENDAR_PAGE_AR = "https://www.aou.edu.kw/ar/students/Pages/academic-calendar.aspx"
AOU_SOCIAL_LINKTREE = "https://linktr.ee/aou_kw"

# =========================================================
# TEXTS
# =========================================================
WELCOME_TEXT = (
    "مرحبًا بك 👋\n"
    "أنا بوت الجامعة العربية المفتوحة (AOU) – الكويت 🇰🇼\n"
    "أساعدك في الاستفسارات الأكاديمية، القبول، الجداول، والخدمات الطلابية 📚\n"
    "اختر من الأزرار بالأسفل ✅"
)

CONTACT_PROMPT_TEXT = (
    "📲 قبل استخدام البوت، شارك رقمك (جهة الاتصال).\n"
    "✅ يقبل أرقام الكويت فقط (+965).\n"
)

IMPORTANT_NOTICE_TEXT = (
    "تنبيه مهم 📌\n"
    "هذا البوت مخصص لطلبة وطالبات الكويت فقط 🇰🇼\n"
    "ولضمان قبولك في البوت ✅\n"
    "يرجى مشاركة جهات الاتصال حتى نتمكن من التحقق بسرعة وتوفير الجهد والوقت.\n"
    "شكرًا لتعاونكم 🤍"
)

AOU_ABOUT = (
    "🎓 الجامعة العربية المفتوحة (AOU) – فرع الكويت\n\n"
    "• تعليم مدمج (حضوري + إلكتروني)\n"
    "• مرونة مناسبة للطلاب والموظفين\n\n"
    f"🔗 موقع الجامعة: {UNIV_URL}"
)

AOU_ADMISSION = (
    "✅ القبول (مختصر)\n\n"
    "1) شهادة الثانوية العامة أو ما يعادلها.\n"
    "2) نسبة لا تقل عن 60% أو GPA لا يقل عن 2.00.\n"
    "3) إذا كان المعدل أقل: يمكن التقديم بشرط خبرة عمل 4 سنوات بعد الثانوية.\n"
    "4) لتخصص تقنية المعلومات (IT): يشترط أن تكون الثانوية علمية.\n\n"
    f"🔗 رابط القبول/التقديم: {ADMISSION_URL}"
)

AOU_MAJORS = (
    "📚 التخصصات (بكالوريوس) في AOU – الكويت\n\n"
    "🏢 كلية إدارة الأعمال:\n"
    "• المحاسبة • الاقتصاد • MIS • الإدارة • التسويق • الممارسات النظمية\n\n"
    "💻 كلية دراسات الحاسوب:\n"
    "• ITC\n\n"
    "👩‍🏫 كلية التربية:\n"
    "• التربية الابتدائية • التربية الخاصة\n\n"
    "🌍 كلية اللغات:\n"
    "• برامج لغات حسب المتاح بالفرع."
)

# ✅ أصبح زر السحب والإضافة قابل للإدارة (PDF/صورة/نص) للأدمن فقط
AOU_ADD_DROP_FALLBACK = (
    "✏️ السحب والإضافة\n\n"
    "✅ الإضافة: خلال فترة السحب والإضافة حسب التقويم.\n"
    "✅ السحب: يحق لك الانسحاب خلال أول 6 أسابيع من الفصل.\n\n"
    "💰 الاسترجاع المالي (مختصر):\n"
    "• خلال السحب والإضافة: 100%\n"
    "• الأسبوع الثاني: 70% (W)\n"
    "• الأسبوع الثالث: 50% (W)\n"
    "• بعد الأسبوع الثالث: لا يوجد استرجاع (W)"
)

CONTACT_INFO = (
    "📞 التواصل – الجامعة العربية المفتوحة (الكويت)\n\n"
    "📍 العارضية الصناعية – الفروانية – الصفاة 13033 – الكويت\n"
    "☎️ +965 24394400\n"
    "📠 +965 24394200\n"
    "✉️ info@aou.edu.kw\n\n"
    f"🔗 موقع الجامعة: {UNIV_URL}\n"
    f"📲 منصات الجامعة: {AOU_SOCIAL_LINKTREE}"
)

# =========================================================
# VALIDATION REGEX
# =========================================================
URL_REGEX = re.compile(r"(https?://\S+|www\.\S+|t\.me/\S+|chat\.whatsapp\.com/\S+|wa\.me/\S+|api\.whatsapp\.com/\S+)", flags=re.IGNORECASE)
TG_USERNAME_REGEX = re.compile(r"^@[A-Za-z0-9_]{4,}$")
TG_LINK_REGEX = re.compile(r"^(?:https?://)?t\.me/[A-Za-z0-9_+/=-]+", flags=re.IGNORECASE)
WA_LINK_REGEX = re.compile(r"^(?:https?://)?(?:chat\.whatsapp\.com/|wa\.me/|api\.whatsapp\.com/)\S+$", flags=re.IGNORECASE)

# =========================================================
# FIXED NAV BUTTONS
# =========================================================
BTN_BACK = "⬅️ رجوع"
BTN_HOME = "🏠 القائمة الرئيسية"
BTN_CANCEL = "❌ إلغاء"
BTN_YES = "✅ نعم"
BTN_NO = "❌ لا"

BTN_ADMIN_SETTINGS = "⚙️ الإعدادات"

BTN_UNIV_NUMBERS = "☎️ أرقام الجامعة"
BTN_CONTACT_ADMIN = "📩 مراسلة الإدارة"
BTN_SOCIALS = "📲 منصات الجامعة"

BTN_INBOX_SHOW = "📨 رسائل الأعضاء"
BTN_INBOX_CLEAR = "🧹 مسح الرسائل"

BTN_CAL_SHOW = "📅 عرض التقويم"
BTN_CAL_REFRESH = "🔄 تحديث روابط التقويم"
BTN_CAL_AUTO_ON = "✅ تشغيل التحديث التلقائي"
BTN_CAL_AUTO_OFF = "⛔ إيقاف التحديث التلقائي"
BTN_CAL_SET_MANUAL = "✏️ تقويم مخصص"
BTN_CAL_USE_AUTO = "🟢 استخدام تلقائي"
BTN_CAL_CLEAR = "🗑️ حذف/إخفاء التقويم"

BTN_GG_MENU = "👥 إدارة القروب العام"
BTN_CC_MENU = "📲 خدمة الأرقام"
BTN_AM_MENU = "👮 إدارة الأدمن"
BTN_HIDE_MENU = "👁️‍🗨️ إخفاء/إظهار الأزرار"
BTN_RENAME_MENU = "✏️ تعديل أسماء الأزرار"

BTN_GG_ADD = "➕ إضافة قروب"
BTN_GG_EDIT = "✏️ تعديل قروب"
BTN_GG_DEL = "➖ حذف قروب"
BTN_GG_LIST = "📋 عرض القروبات"
BTN_GG_USER_TG = "📢 قروبات تيليجرام"
BTN_GG_USER_WA = "📱 قروبات واتساب"

BTN_CC_ENABLE = "✅ تشغيل الخدمة"
BTN_CC_DISABLE = "⛔ إيقاف الخدمة"
BTN_CC_SHOW_OK = "📗 الأرقام المقبولة"
BTN_CC_SHOW_BAD = "📕 الأرقام المرفوضة"
BTN_CC_CLEAR_OK = "🧹 مسح المقبولة"
BTN_CC_CLEAR_BAD = "🧹 مسح المرفوضة"
BTN_CC_EXPORT_XLSX = "📤 تصدير الأرقام (Excel)"

BTN_AM_ADD = "➕ إضافة أدمن"
BTN_AM_DEL = "➖ حذف أدمن"
BTN_AM_LIST = "📋 عرض الأدمن"

BTN_UPLOAD_FILE = "📎 رفع ملف/صورة"
BTN_EDIT_TEXT = "✏️ تعديل النص"
BTN_DEL_FILE = "🗑️ حذف الملف"
BTN_DELETE_SECTION = "🗑️ حذف القسم"

# Colleges view
BTN_COLLEGE_ABOUT = "📌 نبذة"
BTN_COLLEGE_URL = "🔗 رابط الكلية"
BTN_COLLEGE_WA = "📱 قروبات واتساب"
BTN_COLLEGE_TG = "📢 قروبات تيليجرام"
BTN_ADD_WA = "➕ إضافة واتساب"
BTN_DEL_WA = "➖ حذف واتساب"
BTN_ADD_TG = "➕ إضافة تيليجرام"
BTN_DEL_TG = "➖ حذف تيليجرام"

# =========================================================
# DYNAMIC BUTTON KEYS (rename/hide)
# =========================================================
KEY_MAIN_COLLEGES = "main_colleges"
KEY_MAIN_ADMISSION = "main_admission"
KEY_MAIN_MAJORS = "main_majors"
KEY_MAIN_ADD_DROP = "main_add_drop"
KEY_MAIN_CALENDAR = "main_calendar"
KEY_MAIN_SUMMARIES = "main_summaries"
KEY_MAIN_SERVICES = "main_services"
KEY_MAIN_GROUPS = "main_groups"
KEY_MAIN_CONTACT = "main_contact"
KEY_MAIN_ABOUT = "main_about"

KEY_SERV_SCHEDULE = "serv_schedule"
KEY_SERV_ANNUAL = "serv_annual"
KEY_SERV_EXAMS = "serv_exams"
KEY_SERV_REG_CONT = "serv_reg_cont"
KEY_SERV_REG_NEW = "serv_reg_new"
KEY_SERV_ABSENCE = "serv_absence"
KEY_SERV_DEPRIVATION = "serv_deprivation"
KEY_SERV_STRIKE = "serv_strike"

KEY_SUM_BOOKS = "sum_books"
KEY_SUM_NOTES = "sum_notes"

DEFAULT_LABELS: Dict[str, str] = {
    KEY_MAIN_COLLEGES: "🏫 الكليات",
    KEY_MAIN_ADMISSION: "✅ القبول",
    KEY_MAIN_MAJORS: "📚 التخصصات",
    KEY_MAIN_ADD_DROP: "✏️ السحب والإضافة",
    KEY_MAIN_CALENDAR: "📅 التقويم الجامعي",
    KEY_MAIN_SUMMARIES: "🗂️ الملخصات",
    KEY_MAIN_SERVICES: "🧰 الخدمات الطلابية",
    KEY_MAIN_GROUPS: "👥 القروب العام",
    KEY_MAIN_CONTACT: "📞 التواصل",
    KEY_MAIN_ABOUT: "ℹ️ عن الجامعة",
    KEY_SERV_SCHEDULE: "🗓️ الجدول",
    KEY_SERV_ANNUAL: "🗺️ الخطة السنوية",
    KEY_SERV_EXAMS: "🧾 جدول الامتحانات",
    KEY_SERV_REG_CONT: "📝 تقويم تسجيل المستمرين",
    KEY_SERV_REG_NEW: "🆕 تقويم تسجيل المستجدين",
    KEY_SERV_ABSENCE: "📉 نسبة الغياب",
    KEY_SERV_DEPRIVATION: "⛔ الحرمان",
    KEY_SERV_STRIKE: "🧾 طي القيد",
    KEY_SUM_BOOKS: "📚 كتب",
    KEY_SUM_NOTES: "🗂️ ملخصات",
}

HIDEABLE_KEYS: List[str] = list(DEFAULT_LABELS.keys())

# =========================================================
# CONTENT ITEMS (services/summaries + NEW: add_drop + calendar_attach)
# =========================================================
CONTENT_KEYS: Dict[str, str] = {
    KEY_SERV_SCHEDULE: "schedule",
    KEY_SERV_ANNUAL: "annual_plan",
    KEY_SERV_EXAMS: "exams",
    KEY_SERV_REG_CONT: "reg_cont",
    KEY_SERV_REG_NEW: "reg_new",
    KEY_SERV_ABSENCE: "absence",
    KEY_SERV_DEPRIVATION: "deprivation",
    KEY_SERV_STRIKE: "strike",
    KEY_SUM_BOOKS: "sum_books",
    KEY_SUM_NOTES: "sum_notes",
}
CONTENT_KEY_ADD_DROP = "add_drop"          # ✅ محتوى زر السحب والإضافة
CONTENT_KEY_CALENDAR_ATTACH = "calendar_attach"  # ✅ محتوى زر التقويم (مرفق/نص)

# =========================================================
# DATA MODEL + STORAGE
# =========================================================
@dataclass
class BotData:
    users: Set[int]
    extra_admins: Set[int]
    inbox: List[Dict[str, str]]

    general_groups: List[Dict[str, str]]  # {id,name,telegram,whatsapp}
    colleges: Dict[str, Dict[str, Any]]  # {name:{about,url,whatsapp:list,telegram:list}}

    calendar: Dict[str, str]  # links only + manual text (legacy) + modes
    contact_collection_enabled: bool
    contacts_ok: List[Dict[str, str]]
    contacts_rejected: List[Dict[str, str]]

    content_items: Dict[str, Dict[str, str]]  # item_key->{text,file_id,file_type,file_name,mime_type,updated_at}
    hidden_buttons: List[str]
    button_labels: Dict[str, str]


def now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def clip(text: str) -> str:
    s = "" if text is None else str(text)
    return s if len(s) <= MAX_TEXT_LEN else s[: MAX_TEXT_LEN - 3] + "..."


def normalize_digits(s: str) -> str:
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    return (s or "").translate(trans)


def contains_link(text: str) -> bool:
    return bool(text and URL_REGEX.search(text))


def safe_int(s: Any) -> Optional[int]:
    s = str(s).strip()
    return int(s) if s.isdigit() else None


def deny_no_perm() -> str:
    return "⛔ ليس لديك صلاحية في التعديل."


def _default_calendar() -> Dict[str, str]:
    return {
        "pdf1": "",
        "pdf2": "",
        "last_updated": "لم يتم التحديث بعد",
        "last_source": "غير معروف",  # website/manual/cleared
        "auto_enabled": "true",
        "display_mode": "auto",  # auto/manual/cleared
        "manual_text": "",  # legacy manual text (super admin)
    }


def _default_colleges() -> Dict[str, Dict[str, Any]]:
    base_url = "https://www.aou.edu.kw/ar/academic-programs/Pages/default.aspx"
    return {
        "🏢 كلية إدارة الأعمال": {"about": "مجالات الإدارة والمحاسبة والاقتصاد وMIS والتسويق.", "url": base_url, "whatsapp": [], "telegram": []},
        "💻 كلية دراسات الحاسوب": {"about": "تقنية المعلومات والمهارات البرمجية والدعم التقني.", "url": base_url, "whatsapp": [], "telegram": []},
        "👩‍🏫 كلية التربية": {"about": "برامج التربية والتعليم والتربية الخاصة والابتدائية.", "url": base_url, "whatsapp": [], "telegram": []},
        "🌍 كلية اللغات": {"about": "اللغات والترجمة حسب البرامج المتاحة في الفرع.", "url": base_url, "whatsapp": [], "telegram": []},
    }


def _default_content_items() -> Dict[str, Dict[str, str]]:
    def item() -> Dict[str, str]:
        return {"text": "", "file_id": "", "file_type": "", "file_name": "", "mime_type": "", "updated_at": ""}

    keys = set(CONTENT_KEYS.values())
    # ✅ إضافات جديدة:
    keys.add(CONTENT_KEY_ADD_DROP)
    keys.add(CONTENT_KEY_CALENDAR_ATTACH)
    return {k: item() for k in keys}


def _migrate_general_groups(raw: dict) -> List[Dict[str, str]]:
    gg_list = raw.get("general_groups", None)
    if isinstance(gg_list, list):
        out: List[Dict[str, str]] = []
        for item in gg_list:
            if not isinstance(item, dict):
                continue
            out.append(
                {
                    "id": str(item.get("id") or str(int(time.time() * 1000))),
                    "name": str(item.get("name") or "قروب"),
                    "telegram": str(item.get("telegram") or ""),
                    "whatsapp": str(item.get("whatsapp") or ""),
                }
            )
        return out

    old_single = raw.get("general_group", "")
    if isinstance(old_single, str) and old_single.strip():
        return [{"id": str(int(time.time() * 1000)), "name": "القروب العام", "telegram": old_single.strip(), "whatsapp": ""}]
    return []


def load_data() -> BotData:
    if not os.path.exists(DATA_FILE):
        return BotData(
            users=set(),
            extra_admins=set(),
            inbox=[],
            general_groups=[],
            colleges=_default_colleges(),
            calendar=_default_calendar(),
            contact_collection_enabled=False,
            contacts_ok=[],
            contacts_rejected=[],
            content_items=_default_content_items(),
            hidden_buttons=[],
            button_labels={},
        )

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        users = set(int(x) for x in raw.get("users", []) if str(x).isdigit())
        extra_admins = set(int(x) for x in raw.get("extra_admins", []) if str(x).isdigit())

        inbox = raw.get("inbox", [])
        if not isinstance(inbox, list):
            inbox = []

        general_groups = _migrate_general_groups(raw)

        colleges = raw.get("colleges", None)
        if not isinstance(colleges, dict) or not colleges:
            colleges = _default_colleges()
        else:
            for cname, cobj in list(colleges.items()):
                if not isinstance(cobj, dict):
                    colleges.pop(cname, None)
                    continue
                cobj.setdefault("about", "")
                cobj.setdefault("url", "")
                cobj.setdefault("whatsapp", [])
                cobj.setdefault("telegram", [])
                if not isinstance(cobj["whatsapp"], list):
                    cobj["whatsapp"] = []
                if not isinstance(cobj["telegram"], list):
                    cobj["telegram"] = []

        calendar = raw.get("calendar", {})
        if not isinstance(calendar, dict):
            calendar = _default_calendar()
        for k, v in _default_calendar().items():
            calendar.setdefault(k, v)

        contact_collection_enabled = bool(raw.get("contact_collection_enabled", False))

        contacts_ok = raw.get("contacts_ok", [])
        contacts_rejected = raw.get("contacts_rejected", [])
        if not isinstance(contacts_ok, list):
            contacts_ok = []
        if not isinstance(contacts_rejected, list):
            contacts_rejected = []

        defaults = _default_content_items()
        content_items = raw.get("content_items", None)
        if not isinstance(content_items, dict):
            content_items = defaults
        else:
            for k, v in defaults.items():
                if k not in content_items or not isinstance(content_items.get(k), dict):
                    content_items[k] = v
                else:
                    for fk, fv in v.items():
                        content_items[k].setdefault(fk, fv)

        hidden_buttons = raw.get("hidden_buttons", [])
        if not isinstance(hidden_buttons, list):
            hidden_buttons = []

        button_labels = raw.get("button_labels", {})
        if not isinstance(button_labels, dict):
            button_labels = {}

        return BotData(
            users=users,
            extra_admins=extra_admins,
            inbox=inbox,
            general_groups=general_groups,
            colleges=colleges,
            calendar={str(k): str(v) for k, v in calendar.items()},
            contact_collection_enabled=contact_collection_enabled,
            contacts_ok=contacts_ok,
            contacts_rejected=contacts_rejected,
            content_items={str(k): {str(kk): str(vv) for kk, vv in (v or {}).items()} for k, v in content_items.items()},
            hidden_buttons=[str(x) for x in hidden_buttons],
            button_labels={str(k): str(v) for k, v in button_labels.items()},
        )
    except Exception as e:
        LOG.exception("Load failed: %s", e)
        return BotData(
            users=set(),
            extra_admins=set(),
            inbox=[],
            general_groups=[],
            colleges=_default_colleges(),
            calendar=_default_calendar(),
            contact_collection_enabled=False,
            contacts_ok=[],
            contacts_rejected=[],
            content_items=_default_content_items(),
            hidden_buttons=[],
            button_labels={},
        )


def save_data(data: BotData) -> None:
    raw = {
        "users": list(data.users),
        "extra_admins": list(data.extra_admins),
        "inbox": data.inbox,
        "general_groups": data.general_groups,
        "colleges": data.colleges,
        "calendar": data.calendar,
        "contact_collection_enabled": data.contact_collection_enabled,
        "contacts_ok": data.contacts_ok,
        "contacts_rejected": data.contacts_rejected,
        "content_items": data.content_items,
        "hidden_buttons": data.hidden_buttons,
        "button_labels": data.button_labels,
    }
    tmp = f"{DATA_FILE}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


DATA = load_data()


def data_mutate(mutator) -> None:
    with DATA_LOCK:
        mutator()
        save_data(DATA)


def data_read(getter):
    with DATA_LOCK:
        return getter()


# =========================================================
# PERMISSIONS
# =========================================================
def is_super_admin(uid: int) -> bool:
    return uid in SUPER_ADMIN_IDS


def is_admin(uid: int) -> bool:
    with DATA_LOCK:
        return is_super_admin(uid) or (uid in DATA.extra_admins)


def all_admin_ids() -> Set[int]:
    with DATA_LOCK:
        return set(SUPER_ADMIN_IDS) | set(DATA.extra_admins)


# =========================================================
# BUTTON LABELS + HIDE
# =========================================================
def label_for(key: str) -> str:
    with DATA_LOCK:
        custom = DATA.button_labels.get(key, "").strip()
    return custom if custom else DEFAULT_LABELS.get(key, key)


def is_hidden_for_public(key: str) -> bool:
    with DATA_LOCK:
        return key in set(DATA.hidden_buttons)


def resolve_key_by_text(text: str, keys: List[str]) -> Optional[str]:
    for k in keys:
        if text == label_for(k):
            return k
    return None


def toggle_hidden(key: str) -> None:
    def _mut():
        s = set(DATA.hidden_buttons)
        if key in s:
            s.remove(key)
        else:
            s.add(key)
        DATA.hidden_buttons = sorted(s)

    data_mutate(_mut)


def set_label(key: str, new_label: str) -> None:
    new_label = (new_label or "").strip()

    def _mut():
        if not new_label:
            DATA.button_labels.pop(key, None)
        else:
            DATA.button_labels[key] = new_label

    data_mutate(_mut)


# =========================================================
# CONTACT GATE (KUWAIT ONLY)
# =========================================================
def normalize_kw_phone(raw: str) -> Tuple[Optional[str], str]:
    """
    Accept:
      - +965XXXXXXXX
      - 965XXXXXXXX
      - local 8 digits starting with 2/5/6/9 -> +965
    """
    s = normalize_digits(raw or "")
    s = re.sub(r"[^\d+]", "", s)

    if not s:
        return None, "empty"

    if s.startswith("00"):
        s = "+" + s[2:]

    if s.startswith("+"):
        if s.startswith("+965") and len(s) == 12 and s[4:].isdigit():
            return s, "ok"
        return None, "non_kw_country_code"

    if s.startswith("965") and len(s) == 11 and s[3:].isdigit():
        return "+965" + s[3:], "ok"

    if len(s) == 8 and s.isdigit() and s[0] in {"2", "5", "6", "9"}:
        return "+965" + s, "ok"

    return None, "invalid_format"


def contact_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 مشاركة رقمي", request_contact=True)], [KeyboardButton(BTN_HOME)]],
        resize_keyboard=True,
    )


def _user_has_saved_phone(uid: int) -> bool:
    uid_s = str(uid)
    with DATA_LOCK:
        for x in DATA.contacts_ok:
            if str(x.get("id")) == uid_s:
                return True
    return False


def contact_gate_required(update: Update) -> bool:
    if not update.effective_user or not update.effective_chat:
        return False
    if update.effective_chat.type != ChatType.PRIVATE:
        return False
    uid = update.effective_user.id
    if is_admin(uid):
        return False
    enabled = data_read(lambda: bool(DATA.contact_collection_enabled))
    return enabled and (not _user_has_saved_phone(uid))


def _append_contact_ok(user, phone: str) -> None:
    def _mut():
        uid_s = str(user.id)
        for x in DATA.contacts_ok:
            if str(x.get("id")) == uid_s:
                return
        DATA.contacts_ok.append(
            {
                "time": now_str(),
                "id": uid_s,
                "name": user.full_name or "—",
                "username": f"@{user.username}" if user.username else "بدون معرف",
                "phone": phone,
            }
        )

    data_mutate(_mut)


def _append_contact_rejected(user, raw: str, reason: str) -> None:
    data_mutate(
        lambda: DATA.contacts_rejected.append(
            {
                "time": now_str(),
                "id": str(user.id),
                "name": user.full_name or "—",
                "username": f"@{user.username}" if user.username else "بدون معرف",
                "raw": raw,
                "reason": reason,
            }
        )
    )


def contacts_ok_text(limit: int = 200) -> str:
    ok_list = data_read(lambda: list(DATA.contacts_ok))
    if not ok_list:
        return "📗 لا توجد أرقام كويتية محفوظة."
    lines = [f"📗 الأرقام الكويتية المقبولة: {len(ok_list)}", ""]
    for i, x in enumerate(reversed(ok_list[-limit:]), start=1):
        lines.append(f"{i}) {x.get('phone')} | {x.get('name')} | {x.get('username')} | ID:{x.get('id')} | {x.get('time')}")
    return clip("\n".join(lines))


def contacts_bad_text(limit: int = 200) -> str:
    bad_list = data_read(lambda: list(DATA.contacts_rejected))
    if not bad_list:
        return "📕 لا توجد أرقام مرفوضة."
    lines = [f"📕 الأرقام المرفوضة: {len(bad_list)}", ""]
    for i, x in enumerate(reversed(bad_list[-limit:]), start=1):
        lines.append(
            f"{i}) {x.get('raw')} | سبب:{x.get('reason')} | {x.get('name')} | {x.get('username')} | ID:{x.get('id')} | {x.get('time')}"
        )
    return clip("\n".join(lines))


def build_contacts_excel(path: str) -> None:
    ok_list = data_read(lambda: list(DATA.contacts_ok))
    bad_list = data_read(lambda: list(DATA.contacts_rejected))

    wb = Workbook()
    ws_ok = wb.active
    ws_ok.title = "Accepted"
    ws_bad = wb.create_sheet("Rejected")

    ok_headers = ["time", "id", "name", "username", "phone"]
    bad_headers = ["time", "id", "name", "username", "raw", "reason"]

    ws_ok.append(ok_headers)
    for x in ok_list:
        ws_ok.append([x.get("time", ""), x.get("id", ""), x.get("name", ""), x.get("username", ""), x.get("phone", "")])

    ws_bad.append(bad_headers)
    for x in bad_list:
        ws_bad.append([x.get("time", ""), x.get("id", ""), x.get("name", ""), x.get("username", ""), x.get("raw", ""), x.get("reason", "")])

    # Auto-fit-ish columns
    for ws in (ws_ok, ws_bad):
        for col in range(1, ws.max_column + 1):
            col_letter = get_column_letter(col)
            max_len = 10
            for row in range(1, ws.max_row + 1):
                v = ws.cell(row=row, column=col).value
                if v is not None:
                    max_len = max(max_len, len(str(v)))
            ws.column_dimensions[col_letter].width = min(max_len + 2, 45)

    wb.save(path)


# =========================================================
# LINK NORMALIZATION
# =========================================================
def normalize_telegram_link(v: str) -> Optional[str]:
    v = (v or "").strip()
    if not v:
        return None
    if TG_USERNAME_REGEX.match(v):
        return v
    if v.lower().startswith("t.me/"):
        v = "https://" + v
    if TG_LINK_REGEX.match(v):
        if not v.lower().startswith("http"):
            v = "https://" + v
        return v
    return None


def normalize_whatsapp_link(v: str) -> Optional[str]:
    v = (v or "").strip()
    if not v:
        return None
    if v.lower().startswith("wa.me/"):
        v = "https://" + v
    if WA_LINK_REGEX.match(v):
        if not v.lower().startswith("http"):
            v = "https://" + v
        return v
    return None


def open_url_for_display(v: str) -> Optional[str]:
    s = (v or "").strip()
    if not s:
        return None
    if s.startswith("@"):
        return f"https://t.me/{s[1:]}"
    if s.lower().startswith("t.me/"):
        return "https://" + s
    if s.lower().startswith("http"):
        return s
    return None


def open_buttons(telegram_link: str, whatsapp_link: str) -> Optional[InlineKeyboardMarkup]:
    buttons: List[List[InlineKeyboardButton]] = []
    t_url = open_url_for_display(telegram_link)
    w_url = open_url_for_display(whatsapp_link)
    row: List[InlineKeyboardButton] = []
    if t_url:
        row.append(InlineKeyboardButton("فتح تيليجرام", url=t_url))
    if w_url:
        row.append(InlineKeyboardButton("فتح واتساب", url=w_url))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons) if buttons else None


# =========================================================
# CONTENT ITEMS (services/summaries + add_drop + calendar_attach)
# =========================================================
def get_content_item(item_key: str) -> Dict[str, str]:
    with DATA_LOCK:
        base = _default_content_items().get(item_key, {})
        v = DATA.content_items.get(item_key, base)
        return dict(v)


def set_content_text(item_key: str, value: str) -> None:
    value = (value or "").strip()

    def _mut():
        DATA.content_items.setdefault(item_key, _default_content_items().get(item_key, {}))
        DATA.content_items[item_key]["text"] = value
        DATA.content_items[item_key]["updated_at"] = now_str()

    data_mutate(_mut)


def set_content_file(item_key: str, file_id: str, file_type: str, file_name: str, mime_type: str) -> None:
    def _mut():
        DATA.content_items.setdefault(item_key, _default_content_items().get(item_key, {}))
        DATA.content_items[item_key]["file_id"] = file_id
        DATA.content_items[item_key]["file_type"] = file_type
        DATA.content_items[item_key]["file_name"] = file_name
        DATA.content_items[item_key]["mime_type"] = mime_type
        DATA.content_items[item_key]["updated_at"] = now_str()

    data_mutate(_mut)


def delete_content_file(item_key: str) -> None:
    def _mut():
        DATA.content_items.setdefault(item_key, _default_content_items().get(item_key, {}))
        DATA.content_items[item_key]["file_id"] = ""
        DATA.content_items[item_key]["file_type"] = ""
        DATA.content_items[item_key]["file_name"] = ""
        DATA.content_items[item_key]["mime_type"] = ""
        DATA.content_items[item_key]["updated_at"] = now_str()

    data_mutate(_mut)


def delete_content_section(item_key: str) -> None:
    def _mut():
        DATA.content_items[item_key] = _default_content_items().get(item_key, {})
        DATA.content_items[item_key]["updated_at"] = now_str()

    data_mutate(_mut)


def content_is_empty(item_key: str) -> bool:
    item = get_content_item(item_key)
    return (not (item.get("text") or "").strip()) and (not (item.get("file_id") or "").strip())


async def send_content_to_user(update: Update, item_key: str, fallback_text: Optional[str] = None) -> None:
    if not update.message:
        return
    item = get_content_item(item_key)
    text = (item.get("text") or "").strip()
    file_id = (item.get("file_id") or "").strip()
    file_type = (item.get("file_type") or "").strip()

    if file_id:
        try:
            if file_type == "photo":
                await update.message.reply_photo(photo=file_id, caption=clip(text) if text else None)
            else:
                await update.message.reply_document(document=file_id, caption=clip(text) if text else None)
            return
        except Exception:
            pass

    if text:
        await update.message.reply_text(clip(text))
        return

    await update.message.reply_text(clip(fallback_text) if fallback_text else "غير متوفر حاليًا.")


# =========================================================
# CALENDAR (links only, no PDF reading) + admin attachment via content_items
# =========================================================
def _http_get(url: str, timeout: int = 35) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AOU-Bot)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _normalize_pdf_url(u: str) -> str:
    u = u.strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("/"):
        return "https://www.aou.edu.kw" + u
    return "https://www.aou.edu.kw/" + u


def _extract_pdf_links(html_text: str) -> List[str]:
    found = set()
    for m in re.findall(r'href="([^"]+\.pdf)"', html_text, flags=re.IGNORECASE):
        found.add(_normalize_pdf_url(m))
    for m in re.findall(r'src="([^"]+\.pdf)"', html_text, flags=re.IGNORECASE):
        found.add(_normalize_pdf_url(m))
    for m in re.findall(r'(https?://[^\s"<>]+\.pdf)', html_text, flags=re.IGNORECASE):
        found.add(m)
    for m in re.findall(r'(/[^"\s<>]+\.pdf)', html_text, flags=re.IGNORECASE):
        found.add(_normalize_pdf_url(m))
    return list(found)


def _score_pdf_link(url: str) -> int:
    u = url.lower()
    score = 0
    if "academic" in u or "calendar" in u:
        score += 5
    if "students" in u:
        score += 2
    if "publishingimages" in u:
        score += 1
    if "admission" in u:
        score -= 2
    return score


def cal_auto_enabled() -> bool:
    return str(data_read(lambda: DATA.calendar.get("auto_enabled", "true"))).lower() == "true"


def cal_display_mode() -> str:
    return str(data_read(lambda: DATA.calendar.get("display_mode", "auto"))).lower()


def refresh_calendar_links(force: bool = False) -> Tuple[bool, str]:
    if not force and (not cal_auto_enabled() or cal_display_mode() != "auto"):
        return True, "⏸️ التحديث التلقائي موقوف أو التقويم ليس تلقائيًا."

    try:
        html_en = _http_get(AOU_CALENDAR_PAGE_EN).decode("utf-8", errors="ignore")
        html_ar = _http_get(AOU_CALENDAR_PAGE_AR).decode("utf-8", errors="ignore")
        links = list({*(_extract_pdf_links(html_en) + _extract_pdf_links(html_ar))})
        links = [x for x in links if x.lower().endswith(".pdf")]
        if not links:
            return False, "❌ لم أجد روابط PDF في صفحة التقويم."

        links = sorted(links, key=_score_pdf_link, reverse=True)
        pdf1 = links[0]
        pdf2 = links[1] if len(links) > 1 else ""

        def _mut():
            DATA.calendar["pdf1"] = pdf1
            DATA.calendar["pdf2"] = pdf2
            DATA.calendar["last_updated"] = now_str()
            DATA.calendar["last_source"] = "website"

        data_mutate(_mut)
        return True, "✅ تم تحديث روابط التقويم من موقع الجامعة."
    except Exception as e:
        LOG.exception("Calendar update failed: %s", e)
        return False, "❌ حدث خطأ أثناء تحديث روابط التقويم."


def calendar_text_plain() -> str:
    c = data_read(lambda: dict(DATA.calendar))
    mode = str(c.get("display_mode", "auto")).lower()
    auto = "✅ شغال" if str(c.get("auto_enabled", "true")).lower() == "true" else "⏸️ موقوف"

    if mode == "cleared":
        return clip(
            "📅 التقويم الجامعي\n\n"
            "⚠️ التقويم غير متوفر حاليًا.\n"
            "يرجى مراجعة الإدارة أو انتظار التحديث.\n\n"
            f"🔗 صفحة التقويم: {AOU_CALENDAR_PAGE_EN}"
        )

    if mode == "manual":
        manual = (c.get("manual_text") or "").strip() or "⚠️ لا يوجد نص مخصص."
        return clip(
            "📅 التقويم الجامعي (مخصص)\n\n"
            f"{manual}\n\n"
            f"آخر تحديث: {c.get('last_updated','—')}\n"
            f"التحديث التلقائي: {auto}\n"
            f"🔗 صفحة التقويم: {AOU_CALENDAR_PAGE_EN}"
        )

    pdf1 = c.get("pdf1", "") or "غير متوفر"
    pdf2 = c.get("pdf2", "") or "غير متوفر"
    return clip(
        "📅 التقويم الجامعي\n\n"
        f"التحديث التلقائي: {auto}\n"
        f"آخر تحديث: {c.get('last_updated','—')}\n\n"
        "روابط PDF (من موقع الجامعة):\n"
        f"1) {pdf1}\n"
        f"2) {pdf2}\n\n"
        f"🔗 صفحة التقويم: {AOU_CALENDAR_PAGE_EN}"
    )


def calendar_links_buttons() -> Optional[InlineKeyboardMarkup]:
    c = data_read(lambda: dict(DATA.calendar))
    if str(c.get("display_mode", "auto")).lower() != "auto":
        return None
    pdf1 = (c.get("pdf1") or "").strip()
    pdf2 = (c.get("pdf2") or "").strip()
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    if pdf1.startswith("http"):
        row.append(InlineKeyboardButton("فتح PDF 1", url=pdf1))
    if pdf2.startswith("http"):
        row.append(InlineKeyboardButton("فتح PDF 2", url=pdf2))
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows) if rows else None


# =========================================================
# INBOX
# =========================================================
def push_inbox(item: Dict[str, str]) -> None:
    def _mut():
        DATA.inbox.append(item)
        if len(DATA.inbox) > MAX_INBOX:
            DATA.inbox[:] = DATA.inbox[-MAX_INBOX:]

    data_mutate(_mut)


def clear_inbox() -> None:
    data_mutate(lambda: DATA.inbox.clear())


def format_inbox_plain(last_n: int = 50) -> str:
    inbox = data_read(lambda: list(DATA.inbox))
    if not inbox:
        return "📨 لا توجد رسائل محفوظة."
    msgs = inbox[-last_n:]
    lines = ["📨 آخر رسائل الأعضاء:", ""]
    for i, m in enumerate(reversed(msgs), start=1):
        lines.append(f"{i}) الوقت: {m.get('time','—')}")
        lines.append(f"   الاسم: {m.get('name','—')}")
        lines.append(f"   المستخدم: {m.get('username','بدون معرف')}")
        lines.append(f"   ID: {m.get('id','—')}")
        lines.append(f"   الرسالة: {m.get('text','')}")
        lines.append("-" * 30)
    return clip("\n".join(lines))


async def forward_to_admins(app: Application, text: str) -> None:
    for aid in all_admin_ids():
        try:
            await app.bot.send_message(chat_id=aid, text=clip(text))
        except Exception:
            pass


# =========================================================
# KEYBOARDS
# =========================================================
def kb_confirm() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_YES), KeyboardButton(BTN_NO)], [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)]],
        resize_keyboard=True,
    )


def kb_wait_cancel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)], [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)]], resize_keyboard=True)


def kb_main(uid: int) -> ReplyKeyboardMarkup:
    isadm = is_admin(uid)

    def show(key: str) -> bool:
        return isadm or (not is_hidden_for_public(key))

    rows: List[List[KeyboardButton]] = []

    r1: List[KeyboardButton] = []
    if show(KEY_MAIN_COLLEGES):
        r1.append(KeyboardButton(label_for(KEY_MAIN_COLLEGES)))
    if show(KEY_MAIN_ADMISSION):
        r1.append(KeyboardButton(label_for(KEY_MAIN_ADMISSION)))
    if r1:
        rows.append(r1)

    r2: List[KeyboardButton] = []
    if show(KEY_MAIN_MAJORS):
        r2.append(KeyboardButton(label_for(KEY_MAIN_MAJORS)))
    if show(KEY_MAIN_ADD_DROP):
        r2.append(KeyboardButton(label_for(KEY_MAIN_ADD_DROP)))
    if r2:
        rows.append(r2)

    r3: List[KeyboardButton] = []
    if show(KEY_MAIN_CALENDAR):
        r3.append(KeyboardButton(label_for(KEY_MAIN_CALENDAR)))
    if show(KEY_MAIN_SUMMARIES):
        r3.append(KeyboardButton(label_for(KEY_MAIN_SUMMARIES)))
    if r3:
        rows.append(r3)

    r4: List[KeyboardButton] = []
    if show(KEY_MAIN_SERVICES):
        r4.append(KeyboardButton(label_for(KEY_MAIN_SERVICES)))
    if show(KEY_MAIN_GROUPS):
        r4.append(KeyboardButton(label_for(KEY_MAIN_GROUPS)))
    if r4:
        rows.append(r4)

    r5: List[KeyboardButton] = []
    if show(KEY_MAIN_CONTACT):
        r5.append(KeyboardButton(label_for(KEY_MAIN_CONTACT)))
    if show(KEY_MAIN_ABOUT):
        r5.append(KeyboardButton(label_for(KEY_MAIN_ABOUT)))
    if r5:
        rows.append(r5)

    if isadm:
        rows.append([KeyboardButton(BTN_ADMIN_SETTINGS)])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_services(uid: int) -> ReplyKeyboardMarkup:
    isadm = is_admin(uid)

    def show(key: str) -> bool:
        return isadm or (not is_hidden_for_public(key))

    rows: List[List[KeyboardButton]] = []

    a: List[KeyboardButton] = []
    if show(KEY_SERV_SCHEDULE):
        a.append(KeyboardButton(label_for(KEY_SERV_SCHEDULE)))
    if show(KEY_SERV_ANNUAL):
        a.append(KeyboardButton(label_for(KEY_SERV_ANNUAL)))
    if a:
        rows.append(a)

    b: List[KeyboardButton] = []
    if show(KEY_SERV_EXAMS):
        b.append(KeyboardButton(label_for(KEY_SERV_EXAMS)))
    if show(KEY_SERV_ABSENCE):
        b.append(KeyboardButton(label_for(KEY_SERV_ABSENCE)))
    if b:
        rows.append(b)

    c: List[KeyboardButton] = []
    if show(KEY_SERV_DEPRIVATION):
        c.append(KeyboardButton(label_for(KEY_SERV_DEPRIVATION)))
    if show(KEY_SERV_STRIKE):
        c.append(KeyboardButton(label_for(KEY_SERV_STRIKE)))
    if c:
        rows.append(c)

    d: List[KeyboardButton] = []
    if show(KEY_SERV_REG_CONT):
        d.append(KeyboardButton(label_for(KEY_SERV_REG_CONT)))
    if show(KEY_SERV_REG_NEW):
        d.append(KeyboardButton(label_for(KEY_SERV_REG_NEW)))
    if d:
        rows.append(d)

    rows.append([KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_summaries(uid: int) -> ReplyKeyboardMarkup:
    isadm = is_admin(uid)

    def show(key: str) -> bool:
        return isadm or (not is_hidden_for_public(key))

    rows: List[List[KeyboardButton]] = []
    r: List[KeyboardButton] = []
    if show(KEY_SUM_BOOKS):
        r.append(KeyboardButton(label_for(KEY_SUM_BOOKS)))
    if show(KEY_SUM_NOTES):
        r.append(KeyboardButton(label_for(KEY_SUM_NOTES)))
    if r:
        rows.append(r)
    rows.append([KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_contact(uid: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_UNIV_NUMBERS), KeyboardButton(BTN_SOCIALS)],
            [KeyboardButton(BTN_CONTACT_ADMIN)],
            [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
        ],
        resize_keyboard=True,
    )


def kb_admin(uid: int) -> ReplyKeyboardMarkup:
    rows: List[List[KeyboardButton]] = [
        [KeyboardButton(BTN_INBOX_SHOW), KeyboardButton(BTN_INBOX_CLEAR)],
        [KeyboardButton(BTN_CAL_SHOW), KeyboardButton(BTN_CAL_REFRESH)],
        [KeyboardButton(BTN_GG_MENU), KeyboardButton(BTN_CC_MENU)],
        [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
    ]
    if is_super_admin(uid):
        auto_btn = BTN_CAL_AUTO_OFF if cal_auto_enabled() else BTN_CAL_AUTO_ON
        rows.insert(2, [KeyboardButton(auto_btn), KeyboardButton(BTN_CAL_SET_MANUAL)])
        rows.insert(3, [KeyboardButton(BTN_CAL_USE_AUTO), KeyboardButton(BTN_CAL_CLEAR)])
        rows.insert(4, [KeyboardButton(BTN_HIDE_MENU), KeyboardButton(BTN_RENAME_MENU)])
        rows.insert(5, [KeyboardButton(BTN_AM_MENU)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_general_groups_admin() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_GG_LIST)],
            [KeyboardButton(BTN_GG_ADD), KeyboardButton(BTN_GG_EDIT)],
            [KeyboardButton(BTN_GG_DEL)],
            [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
        ],
        resize_keyboard=True,
    )


def kb_general_groups_user(uid: int) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(BTN_GG_USER_TG), KeyboardButton(BTN_GG_USER_WA)], [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)]]
    if is_admin(uid):
        rows.insert(1, [KeyboardButton(BTN_GG_MENU)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_contact_service_admin(uid: int) -> ReplyKeyboardMarkup:
    enabled = data_read(lambda: bool(DATA.contact_collection_enabled))
    # ✅ عرض للأدمن، لكن التغيير/المسح للسوبر فقط
    rows: List[List[KeyboardButton]] = [
        [KeyboardButton(BTN_CC_SHOW_OK), KeyboardButton(BTN_CC_SHOW_BAD)],
        [KeyboardButton(BTN_CC_EXPORT_XLSX)],
    ]
    if is_super_admin(uid):
        status = BTN_CC_DISABLE if enabled else BTN_CC_ENABLE
        rows.insert(0, [KeyboardButton(status)])
        rows.append([KeyboardButton(BTN_CC_CLEAR_OK), KeyboardButton(BTN_CC_CLEAR_BAD)])
    rows.append([KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_admin_manage() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_AM_LIST)],
            [KeyboardButton(BTN_AM_ADD), KeyboardButton(BTN_AM_DEL)],
            [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
        ],
        resize_keyboard=True,
    )


def kb_content_admin(parent_menu_text: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_UPLOAD_FILE), KeyboardButton(BTN_DEL_FILE)],
            [KeyboardButton(BTN_EDIT_TEXT), KeyboardButton(BTN_DELETE_SECTION)],
            [KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)],
            [KeyboardButton(parent_menu_text)],
        ],
        resize_keyboard=True,
    )


def kb_colleges(uid: int) -> ReplyKeyboardMarkup:
    names = data_read(lambda: list(DATA.colleges.keys()))
    rows: List[List[KeyboardButton]] = []
    for i in range(0, len(names), 2):
        row = [KeyboardButton(names[i])]
        if i + 1 < len(names):
            row.append(KeyboardButton(names[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_college_view(uid: int) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(BTN_COLLEGE_ABOUT), KeyboardButton(BTN_COLLEGE_URL)],
        [KeyboardButton(BTN_COLLEGE_WA), KeyboardButton(BTN_COLLEGE_TG)],
    ]
    if is_admin(uid):
        rows += [
            [KeyboardButton(BTN_ADD_WA), KeyboardButton(BTN_DEL_WA)],
            [KeyboardButton(BTN_ADD_TG), KeyboardButton(BTN_DEL_TG)],
        ]
    rows.append([KeyboardButton(BTN_BACK), KeyboardButton(BTN_HOME)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# =========================================================
# USER STATE / MODES
# =========================================================
USER_MODE = "mode"
USER_SELECTED_COLLEGE = "selected_college"
USER_SELECTED_ITEMKEY = "selected_itemkey"
USER_PARENT_MENU = "parent_menu"
USER_CONFIRM = "confirm"  # {action,payload,return_to}
USER_STEP = "step"
USER_TEMP = "temp"
USER_SELECTED_ID = "selected_id"
USER_CHOICE = "choice"
USER_RENAME_KEY = "rename_key"

MODE_NORMAL = "normal"
MODE_SUPPORT = "support"
MODE_SERVICES = "services"
MODE_SUMMARIES = "summaries"
MODE_CONTACT_MENU = "contact_menu"
MODE_COLLEGES = "colleges"
MODE_COLLEGE_VIEW = "college_view"
MODE_GG_USER_MENU = "gg_user_menu"

MODE_CONTENT_EDIT_TEXT = "content_edit_text"
MODE_CONTENT_UPLOAD_FILE = "content_upload_file"

MODE_CC_MENU = "cc_menu"
MODE_GG_MENU = "gg_menu"
MODE_GG_ADD = "gg_add"
MODE_GG_DEL = "gg_del"
MODE_GG_EDIT_SELECT = "gg_edit_select"
MODE_GG_EDIT_FIELD = "gg_edit_field"
MODE_GG_EDIT_VALUE = "gg_edit_value"

MODE_ADD_WA = "add_wa"
MODE_DEL_WA = "del_wa"
MODE_ADD_TG = "add_tg"
MODE_DEL_TG = "del_tg"

MODE_CAL_MANUAL_WAIT = "cal_manual_wait"
MODE_HIDE_MENU = "hide_menu"
MODE_RENAME_MENU = "rename_menu"
MODE_RENAME_VALUE = "rename_value"

MODE_AM_MENU = "am_menu"
MODE_AM_ADD = "am_add"
MODE_AM_DEL = "am_del"

MODE_CONFIRM = "confirm"


def set_mode(context: ContextTypes.DEFAULT_TYPE, mode: str) -> None:
    context.user_data[USER_MODE] = mode


def get_mode(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get(USER_MODE, MODE_NORMAL)


def set_selected_college(context: ContextTypes.DEFAULT_TYPE, cname: Optional[str]) -> None:
    if cname:
        context.user_data[USER_SELECTED_COLLEGE] = cname
    else:
        context.user_data.pop(USER_SELECTED_COLLEGE, None)


def get_selected_college(context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    return context.user_data.get(USER_SELECTED_COLLEGE)


def set_selected_content(context: ContextTypes.DEFAULT_TYPE, item_key: Optional[str], parent_menu_text: Optional[str]) -> None:
    if item_key:
        context.user_data[USER_SELECTED_ITEMKEY] = item_key
    else:
        context.user_data.pop(USER_SELECTED_ITEMKEY, None)
    if parent_menu_text:
        context.user_data[USER_PARENT_MENU] = parent_menu_text
    else:
        context.user_data.pop(USER_PARENT_MENU, None)


def get_selected_itemkey(context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    return context.user_data.get(USER_SELECTED_ITEMKEY)


def get_parent_menu_text(context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    return context.user_data.get(USER_PARENT_MENU)


def reset_flow(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()


# =========================================================
# CONFIRM SYSTEM
# =========================================================
def start_confirm(context: ContextTypes.DEFAULT_TYPE, action: str, payload: dict, return_to: dict) -> None:
    context.user_data[USER_CONFIRM] = {"action": action, "payload": payload, "return_to": return_to}
    set_mode(context, MODE_CONFIRM)


async def confirm_return(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id

    ret = (context.user_data.get(USER_CONFIRM) or {}).get("return_to", {}) or {}
    target = ret.get("target", "main")

    context.user_data.pop(USER_CONFIRM, None)
    context.user_data.pop(USER_STEP, None)
    context.user_data.pop(USER_TEMP, None)
    context.user_data.pop(USER_SELECTED_ID, None)
    context.user_data.pop(USER_CHOICE, None)
    context.user_data.pop(USER_RENAME_KEY, None)
    set_mode(context, MODE_NORMAL)

    if target == "admin":
        await update.message.reply_text("⚙️", reply_markup=kb_admin(uid))
        return
    if target == "services":
        set_mode(context, MODE_SERVICES)
        await update.message.reply_text("🧰", reply_markup=kb_services(uid))
        return
    if target == "summaries":
        set_mode(context, MODE_SUMMARIES)
        await update.message.reply_text("🗂️", reply_markup=kb_summaries(uid))
        return
    if target == "gg_admin":
        set_mode(context, MODE_GG_MENU)
        await update.message.reply_text("👥", reply_markup=kb_general_groups_admin())
        return
    if target == "college_view":
        await update.message.reply_text("🏫", reply_markup=kb_college_view(uid))
        return
    if target == "am_menu":
        set_mode(context, MODE_AM_MENU)
        await update.message.reply_text("👮", reply_markup=kb_admin_manage())
        return

    await update.message.reply_text("🏠", reply_markup=kb_main(uid))


async def run_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id

    cfg = context.user_data.get(USER_CONFIRM) or {}
    action = str(cfg.get("action") or "")
    payload: Dict[str, Any] = cfg.get("payload") or {}

    super_only = {
        "toggle_hide",
        "rename_button",
        "calendar_clear",
        "contact_toggle",
        "contact_clear_ok",
        "contact_clear_bad",
        "admin_add",
        "admin_del",
        "calendar_use_auto",
        "calendar_auto_on",
        "calendar_auto_off",
    }
    admin_required = {
        "inbox_clear",
        "content_del_file",
        "content_del_section",
        "gg_add",
        "gg_del",
        "college_add_wa",
        "college_del_wa",
        "college_add_tg",
        "college_del_tg",
    }

    if action in super_only and not is_super_admin(uid):
        await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
        await confirm_return(update, context)
        return

    if action in admin_required and not is_admin(uid):
        await update.message.reply_text("❌ غير متاح.", reply_markup=kb_main(uid))
        await confirm_return(update, context)
        return

    # ---- Execute ----
    if action == "inbox_clear":
        clear_inbox()

    elif action == "toggle_hide":
        key = str(payload.get("key", ""))
        if key in HIDEABLE_KEYS:
            toggle_hidden(key)

    elif action == "rename_button":
        key = str(payload.get("key", ""))
        value = str(payload.get("value", ""))
        if key in HIDEABLE_KEYS:
            set_label(key, value)

    elif action == "content_del_file":
        item_key = str(payload.get("item_key", ""))
        delete_content_file(item_key)

    elif action == "content_del_section":
        item_key = str(payload.get("item_key", ""))
        delete_content_section(item_key)

    elif action == "gg_add":
        group = payload.get("group")
        if isinstance(group, dict):
            def _mut():
                DATA.general_groups.append(
                    {
                        "id": str(group.get("id")),
                        "name": str(group.get("name", "قروب")),
                        "telegram": str(group.get("telegram", "")),
                        "whatsapp": str(group.get("whatsapp", "")),
                    }
                )
            data_mutate(_mut)

    elif action == "gg_del":
        gid = str(payload.get("id", ""))
        def _mut():
            DATA.general_groups = [x for x in DATA.general_groups if str(x.get("id")) != gid]
        data_mutate(_mut)

    elif action == "contact_toggle":
        enabled = bool(payload.get("enabled"))
        data_mutate(lambda: setattr(DATA, "contact_collection_enabled", enabled))

    elif action == "contact_clear_ok":
        data_mutate(lambda: DATA.contacts_ok.clear())

    elif action == "contact_clear_bad":
        data_mutate(lambda: DATA.contacts_rejected.clear())

    elif action == "calendar_clear":
        def _mut():
            DATA.calendar["display_mode"] = "cleared"
            DATA.calendar["manual_text"] = ""
            DATA.calendar["pdf1"] = ""
            DATA.calendar["pdf2"] = ""
            DATA.calendar["last_updated"] = now_str()
            DATA.calendar["last_source"] = "cleared"
        data_mutate(_mut)

    elif action == "calendar_use_auto":
        def _mut():
            DATA.calendar["display_mode"] = "auto"
            DATA.calendar["last_updated"] = now_str()
            DATA.calendar["last_source"] = "website"
        data_mutate(_mut)

    elif action == "calendar_auto_on":
        data_mutate(lambda: DATA.calendar.__setitem__("auto_enabled", "true"))

    elif action == "calendar_auto_off":
        data_mutate(lambda: DATA.calendar.__setitem__("auto_enabled", "false"))

    elif action == "admin_add":
        new_id = safe_int(payload.get("id", ""))
        if new_id and new_id not in SUPER_ADMIN_IDS:
            data_mutate(lambda: DATA.extra_admins.add(new_id))

    elif action == "admin_del":
        rem_id = safe_int(payload.get("id", ""))
        if rem_id and rem_id not in SUPER_ADMIN_IDS:
            data_mutate(lambda: DATA.extra_admins.discard(rem_id))

    elif action == "college_add_wa":
        cname = str(payload.get("cname", ""))
        link = str(payload.get("link", ""))
        def _mut():
            col = DATA.colleges.get(cname)
            if isinstance(col, dict):
                lst = col.get("whatsapp", [])
                if isinstance(lst, list) and link not in lst:
                    lst.append(link)
                    col["whatsapp"] = lst
        data_mutate(_mut)

    elif action == "college_del_wa":
        cname = str(payload.get("cname", ""))
        link = str(payload.get("link", ""))
        def _mut():
            col = DATA.colleges.get(cname)
            if isinstance(col, dict):
                lst = col.get("whatsapp", [])
                if isinstance(lst, list):
                    col["whatsapp"] = [x for x in lst if x != link]
        data_mutate(_mut)

    elif action == "college_add_tg":
        cname = str(payload.get("cname", ""))
        link = str(payload.get("link", ""))
        def _mut():
            col = DATA.colleges.get(cname)
            if isinstance(col, dict):
                lst = col.get("telegram", [])
                if isinstance(lst, list) and link not in lst:
                    lst.append(link)
                    col["telegram"] = lst
        data_mutate(_mut)

    elif action == "college_del_tg":
        cname = str(payload.get("cname", ""))
        link = str(payload.get("link", ""))
        def _mut():
            col = DATA.colleges.get(cname)
            if isinstance(col, dict):
                lst = col.get("telegram", [])
                if isinstance(lst, list):
                    col["telegram"] = [x for x in lst if x != link]
        data_mutate(_mut)

    await update.message.reply_text("✅ تم التنفيذ.", reply_markup=kb_main(uid))
    await confirm_return(update, context)


# =========================================================
# TELEGRAM COMMAND SCOPES
# =========================================================
async def refresh_scoped_commands(app: Application) -> None:
    admin_cmds = [
        BotCommand("start", "تشغيل البوت"),
        BotCommand("help", "مساعدة"),
        BotCommand("myid", "عرض آيديك"),
        BotCommand("admin", "إعدادات (للأدمن)"),
    ]
    user_cmds = [c for c in admin_cmds if c.command != "admin"]

    try:
        await app.bot.set_my_commands(user_cmds, scope=BotCommandScopeDefault())
    except Exception:
        pass

    for aid in all_admin_ids():
        try:
            await app.bot.set_my_commands(admin_cmds, scope=BotCommandScopeChat(chat_id=aid))
        except BadRequest:
            pass
        except Exception:
            pass


async def post_init(app: Application) -> None:
    await refresh_scoped_commands(app)


# =========================================================
# AUTO JOBS
# =========================================================
async def calendar_auto_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        ok, note = await asyncio.to_thread(refresh_calendar_links, False)
        LOG.info("Auto calendar => %s | %s", ok, note)
    except Exception as e:
        LOG.exception("Auto job error: %s", e)


def setup_jobs(app: Application) -> None:
    app.job_queue.run_repeating(calendar_auto_job, interval=12 * 60 * 60, first=90)


# =========================================================
# COMMANDS
# =========================================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id
    data_mutate(lambda: DATA.users.add(uid))
    reset_flow(context)

    if contact_gate_required(update):
        await update.message.reply_text(WELCOME_TEXT)
        await update.message.reply_text(CONTACT_PROMPT_TEXT)
        await update.message.reply_text(IMPORTANT_NOTICE_TEXT, reply_markup=contact_kb())
        return

    await update.message.reply_text(WELCOME_TEXT, reply_markup=kb_main(uid))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id
    await update.message.reply_text("🆘 المساعدة\nاستخدم الأزرار للتنقل.", reply_markup=kb_main(uid))


async def myid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    await update.message.reply_text(f"🆔 آيديك: {update.effective_user.id}")


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ غير متاح.", reply_markup=kb_main(uid))
        return
    reset_flow(context)
    await update.message.reply_text("⚙️ إعدادات:", reply_markup=kb_admin(uid))


# =========================================================
# CONTACT HANDLER
# =========================================================
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user or not update.effective_chat:
        return
    if update.effective_chat.type != ChatType.PRIVATE:
        return

    uid = update.effective_user.id

    if is_admin(uid):
        await update.message.reply_text("✅ أنت أدمن — لن يتم حفظ رقمك.", reply_markup=kb_main(uid))
        return

    enabled = data_read(lambda: bool(DATA.contact_collection_enabled))
    if not enabled:
        await update.message.reply_text("⛔ خدمة الأرقام غير مفعلة حاليًا.", reply_markup=kb_main(uid))
        return

    if _user_has_saved_phone(uid):
        await update.message.reply_text("✅ رقمك محفوظ مسبقًا.", reply_markup=kb_main(uid))
        return

    c = update.message.contact
    if not c:
        return

    if c.user_id and int(c.user_id) != int(uid):
        raw = (c.phone_number or "").strip()
        _append_contact_rejected(update.effective_user, raw, "not_self")
        await update.message.reply_text("❌ لازم تشارك رقمك أنت فقط.", reply_markup=contact_kb())
        return

    raw = (c.phone_number or "").strip()
    e164, reason = normalize_kw_phone(raw)
    if e164:
        _append_contact_ok(update.effective_user, e164)
        await update.message.reply_text("✅ تم قبولك وحفظ رقمك بنجاح 🤍", reply_markup=kb_main(uid))
    else:
        _append_contact_rejected(update.effective_user, raw, reason)
        await update.message.reply_text("❌ الرقم غير كويتي أو غير صحيح. تم رفضه.", reply_markup=contact_kb())


# =========================================================
# MEDIA HANDLER (admin upload for selected content)
# =========================================================
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    if get_mode(context) != MODE_CONTENT_UPLOAD_FILE:
        return

    item_key = get_selected_itemkey(context)
    parent_menu_text = get_parent_menu_text(context) or label_for(KEY_MAIN_SERVICES)
    if not item_key:
        set_mode(context, MODE_NORMAL)
        await update.message.reply_text("❌ خطأ في الحالة.", reply_markup=kb_main(uid))
        return

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        set_content_file(item_key, file_id=file_id, file_type="photo", file_name="photo.jpg", mime_type="image/jpeg")
        set_mode(context, MODE_NORMAL)
        await update.message.reply_text("✅ تم رفع الصورة.", reply_markup=kb_content_admin(parent_menu_text))
        return

    doc = update.message.document
    if doc:
        set_content_file(
            item_key,
            file_id=doc.file_id,
            file_type="document",
            file_name=doc.file_name or "file",
            mime_type=doc.mime_type or "",
        )
        set_mode(context, MODE_NORMAL)
        await update.message.reply_text("✅ تم رفع الملف.", reply_markup=kb_content_admin(parent_menu_text))
        return

    await update.message.reply_text("❌ أرسل ملف أو صورة.", reply_markup=kb_wait_cancel())


# =========================================================
# GENERAL GROUPS HELPERS
# =========================================================
def _gg_find(gg_id: str) -> Optional[Dict[str, str]]:
    with DATA_LOCK:
        for g in DATA.general_groups:
            if str(g.get("id")) == str(gg_id):
                return dict(g)
    return None


def _gg_list_text() -> str:
    groups = data_read(lambda: list(DATA.general_groups))
    if not groups:
        return "❌ لا توجد قروبات مضافة."
    lines = ["👥 القروبات:", ""]
    for i, g in enumerate(groups, start=1):
        lines.append(f"{i}) {g.get('name','قروب')}")
        if g.get("telegram"):
            lines.append(f"   تيليجرام: {g.get('telegram')}")
        if g.get("whatsapp"):
            lines.append(f"   واتساب: {g.get('whatsapp')}")
        lines.append(f"   ID: {g.get('id')}")
        lines.append("")
    return clip("\n".join(lines))


async def show_groups_platform(update: Update, platform: str) -> None:
    if not update.message:
        return
    groups = data_read(lambda: list(DATA.general_groups))
    if not groups:
        await update.message.reply_text("❌ لا توجد قروبات مضافة حاليًا.")
        return

    shown = 0
    for g in groups[:60]:
        t = g.get("telegram", "")
        w = g.get("whatsapp", "")
        if platform == "tg" and not t:
            continue
        if platform == "wa" and not w:
            continue

        txt = f"👥 {g.get('name','قروب')}\n"
        if t:
            txt += f"تيليجرام: {t}\n"
        if w:
            txt += f"واتساب: {w}\n"
        await update.message.reply_text(clip(txt.strip()), reply_markup=open_buttons(t, w))
        shown += 1
        if shown >= 12:
            break

    if shown == 0:
        await update.message.reply_text("❌ لا توجد قروبات على هذه المنصة حالياً.")


# =========================================================
# HIDE / RENAME MENUS TEXT
# =========================================================
def hide_menu_text() -> str:
    hidden = set(data_read(lambda: list(DATA.hidden_buttons)))
    lines = ["👁️‍🗨️ إخفاء/إظهار الأزرار للعامة", "", "أرسل رقم الزر لتبديل حالته:", ""]
    for i, k in enumerate(HIDEABLE_KEYS, start=1):
        status = "🚫 مخفي" if k in hidden else "✅ ظاهر"
        lines.append(f"{i}) {label_for(k)} — {status}")
    return clip("\n".join(lines))


def rename_menu_text() -> str:
    lines = ["✏️ تعديل أسماء الأزرار", "", "أرسل رقم الزر لتعديل اسمه:", ""]
    for i, k in enumerate(HIDEABLE_KEYS, start=1):
        lines.append(f"{i}) {label_for(k)}")
    lines.append("")
    lines.append("ملاحظة: إرسال اسم فارغ يعيد الاسم الافتراضي.")
    return clip("\n".join(lines))


# =========================================================
# BACK NAV
# =========================================================
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id
    mode = get_mode(context)

    if contact_gate_required(update):
        await update.message.reply_text("🔒 يلزم مشاركة رقمك أولًا.", reply_markup=contact_kb())
        return

    if mode == MODE_CONFIRM:
        await confirm_return(update, context)
        return

    selected_college = get_selected_college(context)
    if selected_college:
        set_selected_college(context, None)
        set_mode(context, MODE_COLLEGES)
        await update.message.reply_text("🏫 اختر الكلية:", reply_markup=kb_colleges(uid))
        return

    if mode in {MODE_SERVICES, MODE_SUMMARIES, MODE_CONTACT_MENU, MODE_GG_USER_MENU, MODE_COLLEGES}:
        set_mode(context, MODE_NORMAL)
        set_selected_content(context, None, None)
        await update.message.reply_text("🏠", reply_markup=kb_main(uid))
        return

    if mode in {MODE_CONTENT_EDIT_TEXT, MODE_CONTENT_UPLOAD_FILE}:
        parent = get_parent_menu_text(context) or label_for(KEY_MAIN_SERVICES)
        set_mode(context, MODE_NORMAL)
        # العودة حسب الأب
        if parent == label_for(KEY_MAIN_SUMMARIES):
            set_mode(context, MODE_SUMMARIES)
            await update.message.reply_text("🗂️", reply_markup=kb_summaries(uid))
        elif parent == label_for(KEY_MAIN_SERVICES):
            set_mode(context, MODE_SERVICES)
            await update.message.reply_text("🧰", reply_markup=kb_services(uid))
        else:
            # مثال: التقويم أو السحب والإضافة
            await update.message.reply_text("🏠", reply_markup=kb_main(uid))
        return

    if mode in {MODE_SUPPORT, MODE_CC_MENU, MODE_GG_MENU, MODE_HIDE_MENU, MODE_RENAME_MENU, MODE_RENAME_VALUE, MODE_CAL_MANUAL_WAIT, MODE_AM_MENU, MODE_AM_ADD, MODE_AM_DEL}:
        set_mode(context, MODE_NORMAL)
        if is_admin(uid):
            await update.message.reply_text("⚙️", reply_markup=kb_admin(uid))
        else:
            await update.message.reply_text("🏠", reply_markup=kb_main(uid))
        return

    set_mode(context, MODE_NORMAL)
    await update.message.reply_text("🏠", reply_markup=kb_main(uid))


# =========================================================
# TEXT ROUTER
# =========================================================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    uid = user.id
    text = (update.message.text or "").strip()
    data_mutate(lambda: DATA.users.add(uid))

    # HOME
    if text == BTN_HOME:
        reset_flow(context)
        if contact_gate_required(update):
            await update.message.reply_text(WELCOME_TEXT)
            await update.message.reply_text(CONTACT_PROMPT_TEXT)
            await update.message.reply_text(IMPORTANT_NOTICE_TEXT, reply_markup=contact_kb())
            return
        await update.message.reply_text(WELCOME_TEXT, reply_markup=kb_main(uid))
        return

    # BACK
    if text == BTN_BACK:
        await go_back(update, context)
        return

    # BLOCK if gate required
    if contact_gate_required(update):
        await update.message.reply_text("🔒 يلزم مشاركة رقمك أولًا للمتابعة.", reply_markup=contact_kb())
        return

    mode = get_mode(context)

    # CANCEL
    if text == BTN_CANCEL and mode != MODE_NORMAL:
        set_mode(context, MODE_NORMAL)
        context.user_data.pop(USER_STEP, None)
        context.user_data.pop(USER_TEMP, None)
        context.user_data.pop(USER_SELECTED_ID, None)
        context.user_data.pop(USER_CHOICE, None)
        context.user_data.pop(USER_RENAME_KEY, None)
        await update.message.reply_text("✅ تم الإلغاء.", reply_markup=kb_main(uid))
        return

    # CONFIRM
    if mode == MODE_CONFIRM:
        if text == BTN_YES:
            await run_confirm_action(update, context)
            return
        if text == BTN_NO:
            await update.message.reply_text("✅ تم الإلغاء.", reply_markup=kb_main(uid))
            await confirm_return(update, context)
            return
        await update.message.reply_text("اختر ✅ نعم أو ❌ لا.", reply_markup=kb_confirm())
        return

    # Block links for non-admin (لكن الروابط ممكن تجي من البوت نفسه عبر المحتوى)
    if not is_admin(uid) and contains_link(text):
        await update.message.reply_text("🔒 ممنوع إرسال روابط داخل البوت.", reply_markup=kb_main(uid))
        return

    # SUPPORT MODE
    if mode == MODE_SUPPORT:
        item = {
            "time": now_str(),
            "name": user.full_name or "—",
            "username": f"@{user.username}" if user.username else "بدون معرف",
            "id": str(uid),
            "text": clip(text),
        }
        push_inbox(item)
        msg = (
            "📩 رسالة جديدة\n\n"
            f"الاسم: {item['name']}\n"
            f"المعرف: {item['username']}\n"
            f"ID: {uid}\n\n"
            f"النص:\n{text}"
        )
        await forward_to_admins(context.application, msg)
        set_mode(context, MODE_NORMAL)
        await update.message.reply_text("✅ تم إرسال رسالتك للإدارة.", reply_markup=kb_main(uid))
        return

    # HIDE MENU (super only)
    if mode == MODE_HIDE_MENU:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            set_mode(context, MODE_NORMAL)
            return
        idx = safe_int(text)
        if not idx or idx < 1 or idx > len(HIDEABLE_KEYS):
            await update.message.reply_text("أرسل رقم صحيح.", reply_markup=kb_wait_cancel())
            return
        key = HIDEABLE_KEYS[idx - 1]
        start_confirm(context, "toggle_hide", {"key": key}, {"target": "admin"})
        await update.message.reply_text(f"تأكيد تبديل حالة: {label_for(key)} ؟", reply_markup=kb_confirm())
        return

    # RENAME MENU (super only)
    if mode == MODE_RENAME_MENU:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            set_mode(context, MODE_NORMAL)
            return
        idx = safe_int(text)
        if not idx or idx < 1 or idx > len(HIDEABLE_KEYS):
            await update.message.reply_text("أرسل رقم صحيح.", reply_markup=kb_wait_cancel())
            return
        key = HIDEABLE_KEYS[idx - 1]
        context.user_data[USER_RENAME_KEY] = key
        set_mode(context, MODE_RENAME_VALUE)
        await update.message.reply_text(f"أرسل الاسم الجديد للزر:\n{label_for(key)}", reply_markup=kb_wait_cancel())
        return

    if mode == MODE_RENAME_VALUE:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            set_mode(context, MODE_NORMAL)
            return
        key = str(context.user_data.get(USER_RENAME_KEY, "")).strip()
        if key not in HIDEABLE_KEYS:
            set_mode(context, MODE_NORMAL)
            await update.message.reply_text("❌ خطأ.", reply_markup=kb_admin(uid))
            return
        start_confirm(context, "rename_button", {"key": key, "value": text.strip()}, {"target": "admin"})
        await update.message.reply_text("تأكيد تعديل اسم الزر؟", reply_markup=kb_confirm())
        return

    # CALENDAR MANUAL WAIT (super only) - legacy manual text
    if mode == MODE_CAL_MANUAL_WAIT:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            set_mode(context, MODE_NORMAL)
            return
        manual = text.strip()

        def _mut():
            DATA.calendar["display_mode"] = "manual"
            DATA.calendar["manual_text"] = manual
            DATA.calendar["last_updated"] = now_str()
            DATA.calendar["last_source"] = "manual"

        data_mutate(_mut)
        set_mode(context, MODE_NORMAL)
        await update.message.reply_text("✅ تم حفظ التقويم المخصص.", reply_markup=kb_admin(uid))
        return

    # CONTENT EDIT TEXT
    if mode == MODE_CONTENT_EDIT_TEXT:
        if not is_admin(uid):
            await update.message.reply_text("❌ غير متاح.", reply_markup=kb_main(uid))
            set_mode(context, MODE_NORMAL)
            return
        item_key = get_selected_itemkey(context)
        parent_menu = get_parent_menu_text(context) or label_for(KEY_MAIN_SERVICES)
        if not item_key:
            set_mode(context, MODE_NORMAL)
            await update.message.reply_text("❌ خطأ.", reply_markup=kb_main(uid))
            return
        set_content_text(item_key, text)
        set_mode(context, MODE_NORMAL)
        await update.message.reply_text("✅ تم تعديل النص.", reply_markup=kb_content_admin(parent_menu))
        return

    # COLLEGES ADD/DEL (admin)
    selected_college = get_selected_college(context)
    if mode in {MODE_ADD_WA, MODE_DEL_WA, MODE_ADD_TG, MODE_DEL_TG}:
        if not is_admin(uid) or not selected_college:
            set_mode(context, MODE_NORMAL)
            await update.message.reply_text("❌ غير متاح.", reply_markup=kb_main(uid))
            return

        value = text.strip()

        if mode == MODE_ADD_WA:
            if not normalize_whatsapp_link(value):
                await update.message.reply_text("❌ رابط واتساب غير صحيح.", reply_markup=kb_wait_cancel())
                return
            start_confirm(context, "college_add_wa", {"cname": selected_college, "link": value}, {"target": "college_view"})
            await update.message.reply_text("تأكيد إضافة رابط واتساب؟", reply_markup=kb_confirm())
            return

        if mode == MODE_DEL_WA:
            start_confirm(context, "college_del_wa", {"cname": selected_college, "link": value}, {"target": "college_view"})
            await update.message.reply_text("تأكيد حذف رابط واتساب؟", reply_markup=kb_confirm())
            return

        if mode == MODE_ADD_TG:
            if not normalize_telegram_link(value):
                await update.message.reply_text("❌ رابط/معرف تيليجرام غير صحيح.", reply_markup=kb_wait_cancel())
                return
            start_confirm(context, "college_add_tg", {"cname": selected_college, "link": value}, {"target": "college_view"})
            await update.message.reply_text("تأكيد إضافة رابط تيليجرام؟", reply_markup=kb_confirm())
            return

        if mode == MODE_DEL_TG:
            start_confirm(context, "college_del_tg", {"cname": selected_college, "link": value}, {"target": "college_view"})
            await update.message.reply_text("تأكيد حذف رابط تيليجرام؟", reply_markup=kb_confirm())
            return

    # GENERAL GROUPS ADMIN FLOWS
    if mode == MODE_GG_ADD and is_admin(uid):
        step = context.user_data.get(USER_STEP)
        temp: dict = context.user_data.get(USER_TEMP, {})

        if step == "name":
            temp["name"] = text.strip() or "قروب"
            context.user_data[USER_STEP] = "telegram"
            context.user_data[USER_TEMP] = temp
            await update.message.reply_text("أرسل رابط تيليجرام للقروب (t.me أو @username):", reply_markup=kb_wait_cancel())
            return

        if step == "telegram":
            t = normalize_telegram_link(text)
            if not t:
                await update.message.reply_text("❌ رابط تيليجرام غير صحيح.", reply_markup=kb_wait_cancel())
                return
            temp["telegram"] = t
            context.user_data[USER_STEP] = "whatsapp"
            context.user_data[USER_TEMP] = temp
            await update.message.reply_text("أرسل رابط واتساب (اختياري). اكتب - لتخطي:", reply_markup=kb_wait_cancel())
            return

        if step == "whatsapp":
            w_raw = text.strip()
            w = "" if w_raw == "-" else (normalize_whatsapp_link(w_raw) or None)
            if w_raw != "-" and w is None:
                await update.message.reply_text("❌ رابط واتساب غير صحيح. أو اكتب - للتخطي", reply_markup=kb_wait_cancel())
                return

            group = {
                "id": str(int(time.time() * 1000)),
                "name": str(temp.get("name", "قروب")),
                "telegram": str(temp.get("telegram", "")),
                "whatsapp": w or "",
            }
            context.user_data.pop(USER_STEP, None)
            context.user_data.pop(USER_TEMP, None)
            start_confirm(context, "gg_add", {"group": group}, {"target": "gg_admin"})
            await update.message.reply_text("تأكيد إضافة القروب؟", reply_markup=kb_confirm())
            return

    if mode == MODE_GG_DEL and is_admin(uid):
        gg = _gg_find(text.strip())
        if not gg:
            await update.message.reply_text("❌ ID غير صحيح.", reply_markup=kb_wait_cancel())
            return
        start_confirm(context, "gg_del", {"id": gg.get("id")}, {"target": "gg_admin"})
        await update.message.reply_text("تأكيد حذف القروب؟", reply_markup=kb_confirm())
        return

    if mode == MODE_GG_EDIT_SELECT and is_admin(uid):
        gg = _gg_find(text.strip())
        if not gg:
            await update.message.reply_text("❌ ID غير صحيح.", reply_markup=kb_wait_cancel())
            return
        context.user_data[USER_SELECTED_ID] = gg["id"]
        set_mode(context, MODE_GG_EDIT_FIELD)
        await update.message.reply_text("اكتب رقم الخيار:\n1) الاسم\n2) تيليجرام\n3) واتساب", reply_markup=kb_wait_cancel())
        return

    if mode == MODE_GG_EDIT_FIELD and is_admin(uid):
        choice = text.strip()
        if choice not in {"1", "2", "3"}:
            await update.message.reply_text("اكتب 1 أو 2 أو 3.", reply_markup=kb_wait_cancel())
            return
        context.user_data[USER_CHOICE] = choice
        set_mode(context, MODE_GG_EDIT_VALUE)
        if choice == "1":
            await update.message.reply_text("أرسل الاسم الجديد:", reply_markup=kb_wait_cancel())
        elif choice == "2":
            await update.message.reply_text("أرسل رابط تيليجرام الجديد:", reply_markup=kb_wait_cancel())
        else:
            await update.message.reply_text("أرسل رابط واتساب الجديد (أو - لمسحه):", reply_markup=kb_wait_cancel())
        return

    if mode == MODE_GG_EDIT_VALUE and is_admin(uid):
        gg_id = str(context.user_data.get(USER_SELECTED_ID, ""))
        gg = _gg_find(gg_id)
        if not gg:
            set_mode(context, MODE_GG_MENU)
            await update.message.reply_text("❌ لم أجد القروب.", reply_markup=kb_general_groups_admin())
            return

        choice = context.user_data.get(USER_CHOICE)
        if choice == "1":
            gg["name"] = text.strip() or gg.get("name", "قروب")
        elif choice == "2":
            t = normalize_telegram_link(text)
            if not t:
                await update.message.reply_text("❌ رابط تيليجرام غير صحيح.", reply_markup=kb_wait_cancel())
                return
            gg["telegram"] = t
        else:
            if text.strip() == "-":
                gg["whatsapp"] = ""
            else:
                w = normalize_whatsapp_link(text)
                if not w:
                    await update.message.reply_text("❌ رابط واتساب غير صحيح. أو اكتب - لمسحه.", reply_markup=kb_wait_cancel())
                    return
                gg["whatsapp"] = w

        def _mut():
            for i, x in enumerate(DATA.general_groups):
                if str(x.get("id")) == gg_id:
                    DATA.general_groups[i] = gg
                    break

        data_mutate(_mut)
        set_mode(context, MODE_GG_MENU)
        await update.message.reply_text("✅ تم التعديل.", reply_markup=kb_general_groups_admin())
        return

    # ADMIN MANAGE (super)
    if mode == MODE_AM_ADD:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            set_mode(context, MODE_NORMAL)
            return
        new_id = safe_int(text)
        if not new_id:
            await update.message.reply_text("أرسل رقم ID صحيح.", reply_markup=kb_wait_cancel())
            return
        start_confirm(context, "admin_add", {"id": str(new_id)}, {"target": "am_menu"})
        await update.message.reply_text("تأكيد إضافة الأدمن؟", reply_markup=kb_confirm())
        return

    if mode == MODE_AM_DEL:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            set_mode(context, MODE_NORMAL)
            return
        rem_id = safe_int(text)
        if not rem_id:
            await update.message.reply_text("أرسل رقم ID صحيح.", reply_markup=kb_wait_cancel())
            return
        start_confirm(context, "admin_del", {"id": str(rem_id)}, {"target": "am_menu"})
        await update.message.reply_text("تأكيد حذف الأدمن؟", reply_markup=kb_confirm())
        return

    # CONTENT ADMIN PANEL BUTTONS (works for: services/summaries/calendar/add-drop)
    item_key = get_selected_itemkey(context)
    parent_menu_text = get_parent_menu_text(context) or label_for(KEY_MAIN_SERVICES)
    if is_admin(uid) and item_key and text in {BTN_UPLOAD_FILE, BTN_EDIT_TEXT, BTN_DEL_FILE, BTN_DELETE_SECTION}:
        if text == BTN_UPLOAD_FILE:
            set_mode(context, MODE_CONTENT_UPLOAD_FILE)
            await update.message.reply_text("📎 أرسل ملف أو صورة الآن.\nللإلغاء: ❌ إلغاء", reply_markup=kb_wait_cancel())
            return
        if text == BTN_EDIT_TEXT:
            set_mode(context, MODE_CONTENT_EDIT_TEXT)
            await update.message.reply_text("✏️ أرسل النص الجديد:", reply_markup=kb_wait_cancel())
            return
        if text == BTN_DEL_FILE:
            start_confirm(context, "content_del_file", {"item_key": item_key}, {"target": "main"})
            await update.message.reply_text("تأكيد حذف الملف؟", reply_markup=kb_confirm())
            return
        if text == BTN_DELETE_SECTION:
            start_confirm(context, "content_del_section", {"item_key": item_key}, {"target": "main"})
            await update.message.reply_text("تأكيد حذف القسم بالكامل؟", reply_markup=kb_confirm())
            return

    # MAIN MENU (dynamic)
    k_main = resolve_key_by_text(
        text,
        [
            KEY_MAIN_COLLEGES,
            KEY_MAIN_ADMISSION,
            KEY_MAIN_MAJORS,
            KEY_MAIN_ADD_DROP,
            KEY_MAIN_CALENDAR,
            KEY_MAIN_SUMMARIES,
            KEY_MAIN_SERVICES,
            KEY_MAIN_GROUPS,
            KEY_MAIN_CONTACT,
            KEY_MAIN_ABOUT,
        ],
    )

    if k_main == KEY_MAIN_ADMISSION:
        await update.message.reply_text(AOU_ADMISSION, reply_markup=kb_main(uid))
        return

    if k_main == KEY_MAIN_MAJORS:
        await update.message.reply_text(AOU_MAJORS, reply_markup=kb_main(uid))
        return

    if k_main == KEY_MAIN_ABOUT:
        await update.message.reply_text(AOU_ABOUT, reply_markup=kb_main(uid))
        return

    # ✅ السحب والإضافة: محتوى قابل للإدارة للأدمن فقط
    if k_main == KEY_MAIN_ADD_DROP:
        set_selected_content(context, CONTENT_KEY_ADD_DROP, label_for(KEY_MAIN_ADD_DROP))
        await send_content_to_user(update, CONTENT_KEY_ADD_DROP, fallback_text=AOU_ADD_DROP_FALLBACK)
        if is_admin(uid):
            await update.message.reply_text("لوحة إدارة السحب والإضافة:", reply_markup=kb_content_admin(label_for(KEY_MAIN_ADD_DROP)))
        else:
            await update.message.reply_text("⬅️", reply_markup=kb_main(uid))
        return

    # ✅ التقويم: يعرض مرفق/نص الأدمن إن وجد، وإلا يعرض الروابط التلقائية
    if k_main == KEY_MAIN_CALENDAR:
        set_selected_content(context, CONTENT_KEY_CALENDAR_ATTACH, label_for(KEY_MAIN_CALENDAR))
        if not content_is_empty(CONTENT_KEY_CALENDAR_ATTACH):
            await send_content_to_user(update, CONTENT_KEY_CALENDAR_ATTACH, fallback_text=None)
        else:
            await update.message.reply_text(calendar_text_plain(), reply_markup=kb_main(uid), disable_web_page_preview=True)
            kb = calendar_links_buttons()
            if kb:
                await update.message.reply_text("⬇️ فتح ملفات التقويم:", reply_markup=kb)

        if is_admin(uid):
            await update.message.reply_text("لوحة إدارة التقويم:", reply_markup=kb_content_admin(label_for(KEY_MAIN_CALENDAR)))
        else:
            await update.message.reply_text("⬅️", reply_markup=kb_main(uid))
        return

    if k_main == KEY_MAIN_CONTACT:
        set_mode(context, MODE_CONTACT_MENU)
        await update.message.reply_text("📞 اختر:", reply_markup=kb_contact(uid))
        return

    if k_main == KEY_MAIN_SERVICES:
        set_mode(context, MODE_SERVICES)
        set_selected_content(context, None, None)
        await update.message.reply_text("🧰 اختر:", reply_markup=kb_services(uid))
        return

    if k_main == KEY_MAIN_SUMMARIES:
        set_mode(context, MODE_SUMMARIES)
        set_selected_content(context, None, None)
        await update.message.reply_text("🗂️ اختر:", reply_markup=kb_summaries(uid))
        return

    if k_main == KEY_MAIN_GROUPS:
        set_mode(context, MODE_GG_USER_MENU)
        await update.message.reply_text("👥 اختر المنصة:", reply_markup=kb_general_groups_user(uid))
        return

    if k_main == KEY_MAIN_COLLEGES:
        set_mode(context, MODE_COLLEGES)
        set_selected_college(context, None)
        await update.message.reply_text("🏫 اختر الكلية:", reply_markup=kb_colleges(uid))
        return

    # CONTACT MENU
    if text == BTN_UNIV_NUMBERS:
        await update.message.reply_text(CONTACT_INFO, reply_markup=kb_contact(uid), disable_web_page_preview=True)
        return

    if text == BTN_SOCIALS:
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔗 Linktree منصات الجامعة", url=AOU_SOCIAL_LINKTREE)],
                [InlineKeyboardButton("🌐 موقع الجامعة", url=UNIV_URL)],
            ]
        )
        await update.message.reply_text("📲 منصات الجامعة:", reply_markup=kb)
        return

    if text == BTN_CONTACT_ADMIN:
        set_mode(context, MODE_SUPPORT)
        await update.message.reply_text("✍️ اكتب رسالتك الآن.\nللإلغاء: ❌ إلغاء", reply_markup=kb_wait_cancel())
        return

    # SERVICES ITEM SELECT
    k_serv = resolve_key_by_text(
        text,
        [
            KEY_SERV_SCHEDULE,
            KEY_SERV_ANNUAL,
            KEY_SERV_EXAMS,
            KEY_SERV_REG_CONT,
            KEY_SERV_REG_NEW,
            KEY_SERV_ABSENCE,
            KEY_SERV_DEPRIVATION,
            KEY_SERV_STRIKE,
        ],
    )
    if k_serv:
        item = CONTENT_KEYS[k_serv]
        set_selected_content(context, item, label_for(KEY_MAIN_SERVICES))
        await send_content_to_user(update, item)
        if is_admin(uid):
            await update.message.reply_text("لوحة إدارة:", reply_markup=kb_content_admin(label_for(KEY_MAIN_SERVICES)))
        else:
            set_mode(context, MODE_SERVICES)
            await update.message.reply_text("⬅️", reply_markup=kb_services(uid))
        return

    # SUMMARIES ITEM SELECT
    k_sum = resolve_key_by_text(text, [KEY_SUM_BOOKS, KEY_SUM_NOTES])
    if k_sum:
        item = CONTENT_KEYS[k_sum]
        set_selected_content(context, item, label_for(KEY_MAIN_SUMMARIES))
        await send_content_to_user(update, item)
        if is_admin(uid):
            await update.message.reply_text("لوحة إدارة:", reply_markup=kb_content_admin(label_for(KEY_MAIN_SUMMARIES)))
        else:
            set_mode(context, MODE_SUMMARIES)
            await update.message.reply_text("⬅️", reply_markup=kb_summaries(uid))
        return

    # GENERAL GROUPS USER MENU
    if mode == MODE_GG_USER_MENU and text in {BTN_GG_USER_TG, BTN_GG_USER_WA}:
        await show_groups_platform(update, "tg" if text == BTN_GG_USER_TG else "wa")
        await update.message.reply_text("⬅️", reply_markup=kb_general_groups_user(uid))
        return

    # COLLEGES: pick college
    if mode == MODE_COLLEGES:
        cols = data_read(lambda: dict(DATA.colleges))
        if text in cols:
            set_selected_college(context, text)
            set_mode(context, MODE_COLLEGE_VIEW)
            col = cols.get(text, {})
            await update.message.reply_text(
                clip(f"{text}\n\n📌 {col.get('about','')}\n\n🔗 {col.get('url','غير متوفر')}"),
                reply_markup=kb_college_view(uid),
            )
            return

    # COLLEGE VIEW
    if get_mode(context) == MODE_COLLEGE_VIEW and (cname := get_selected_college(context)):
        col = data_read(lambda: dict(DATA.colleges.get(cname, {})))
        if text == BTN_COLLEGE_ABOUT:
            await update.message.reply_text(f"📌 {cname}\n\n{col.get('about','')}", reply_markup=kb_college_view(uid))
            return
        if text == BTN_COLLEGE_URL:
            await update.message.reply_text(f"🔗 {cname}\n{col.get('url','غير متوفر')}", reply_markup=kb_college_view(uid))
            return
        if text == BTN_COLLEGE_WA:
            gs = col.get("whatsapp", [])
            if not gs:
                await update.message.reply_text("📱 لا توجد قروبات واتساب مضافة.", reply_markup=kb_college_view(uid))
            else:
                await update.message.reply_text("📱 قروبات واتساب:\n" + "\n".join([f"- {g}" for g in gs]), reply_markup=kb_college_view(uid))
            return
        if text == BTN_COLLEGE_TG:
            gs = col.get("telegram", [])
            if not gs:
                await update.message.reply_text("📢 لا توجد قروبات تيليجرام مضافة.", reply_markup=kb_college_view(uid))
            else:
                await update.message.reply_text("📢 قروبات تيليجرام:\n" + "\n".join([f"- {g}" for g in gs]), reply_markup=kb_college_view(uid))
            return

        if is_admin(uid) and text == BTN_ADD_WA:
            set_mode(context, MODE_ADD_WA)
            await update.message.reply_text("📱 أرسل رابط واتساب:", reply_markup=kb_wait_cancel())
            return
        if is_admin(uid) and text == BTN_DEL_WA:
            set_mode(context, MODE_DEL_WA)
            await update.message.reply_text("📱 أرسل رابط واتساب المراد حذفه:", reply_markup=kb_wait_cancel())
            return
        if is_admin(uid) and text == BTN_ADD_TG:
            set_mode(context, MODE_ADD_TG)
            await update.message.reply_text("📢 أرسل رابط/معرف تيليجرام:", reply_markup=kb_wait_cancel())
            return
        if is_admin(uid) and text == BTN_DEL_TG:
            set_mode(context, MODE_DEL_TG)
            await update.message.reply_text("📢 أرسل رابط/معرف تيليجرام المراد حذفه:", reply_markup=kb_wait_cancel())
            return

    # ADMIN SETTINGS ENTRY
    if text == BTN_ADMIN_SETTINGS:
        if not is_admin(uid):
            await update.message.reply_text("❌ غير متاح.", reply_markup=kb_main(uid))
            return
        await update.message.reply_text("⚙️ إعدادات:", reply_markup=kb_admin(uid))
        return

    # ADMIN: inbox
    if is_admin(uid) and text == BTN_INBOX_SHOW:
        await update.message.reply_text(format_inbox_plain(50), reply_markup=kb_admin(uid))
        return

    if is_admin(uid) and text == BTN_INBOX_CLEAR:
        start_confirm(context, "inbox_clear", {}, {"target": "admin"})
        await update.message.reply_text("تأكيد مسح الرسائل؟", reply_markup=kb_confirm())
        return

    # ADMIN: calendar (admin settings screen)
    if is_admin(uid) and text == BTN_CAL_SHOW:
        # يعرض المرفق إن وجد وإلا يعرض الروابط
        if not content_is_empty(CONTENT_KEY_CALENDAR_ATTACH):
            set_selected_content(context, CONTENT_KEY_CALENDAR_ATTACH, label_for(KEY_MAIN_CALENDAR))
            await send_content_to_user(update, CONTENT_KEY_CALENDAR_ATTACH)
        else:
            await update.message.reply_text(calendar_text_plain(), reply_markup=kb_admin(uid), disable_web_page_preview=True)
            kb = calendar_links_buttons()
            if kb:
                await update.message.reply_text("⬇️ فتح ملفات التقويم:", reply_markup=kb)
        return

    if is_admin(uid) and text == BTN_CAL_REFRESH:
        ok, note = await asyncio.to_thread(refresh_calendar_links, True)
        await update.message.reply_text(note, reply_markup=kb_admin(uid))
        return

    if text == BTN_CAL_SET_MANUAL:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            return
        set_mode(context, MODE_CAL_MANUAL_WAIT)
        await update.message.reply_text("✏️ أرسل نص التقويم المخصص الآن:", reply_markup=kb_wait_cancel())
        return

    if text == BTN_CAL_USE_AUTO:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            return
        start_confirm(context, "calendar_use_auto", {}, {"target": "admin"})
        await update.message.reply_text("تأكيد تحويل التقويم إلى تلقائي؟", reply_markup=kb_confirm())
        return

    if text == BTN_CAL_CLEAR:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            return
        start_confirm(context, "calendar_clear", {}, {"target": "admin"})
        await update.message.reply_text("تأكيد حذف/إخفاء التقويم؟", reply_markup=kb_confirm())
        return

    if text == BTN_CAL_AUTO_ON:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            return
        start_confirm(context, "calendar_auto_on", {}, {"target": "admin"})
        await update.message.reply_text("تأكيد تشغيل التحديث التلقائي؟", reply_markup=kb_confirm())
        return

    if text == BTN_CAL_AUTO_OFF:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            return
        start_confirm(context, "calendar_auto_off", {}, {"target": "admin"})
        await update.message.reply_text("تأكيد إيقاف التحديث التلقائي؟", reply_markup=kb_confirm())
        return

    # ADMIN: groups menu
    if is_admin(uid) and text == BTN_GG_MENU:
        set_mode(context, MODE_GG_MENU)
        await update.message.reply_text("👥 إدارة القروبات:", reply_markup=kb_general_groups_admin())
        return

    if is_admin(uid) and text == BTN_GG_LIST:
        await update.message.reply_text(_gg_list_text(), reply_markup=kb_general_groups_admin())
        return

    if is_admin(uid) and text == BTN_GG_ADD:
        set_mode(context, MODE_GG_ADD)
        context.user_data[USER_STEP] = "name"
        context.user_data[USER_TEMP] = {}
        await update.message.reply_text("اكتب اسم القروب:", reply_markup=kb_wait_cancel())
        return

    if is_admin(uid) and text == BTN_GG_DEL:
        set_mode(context, MODE_GG_DEL)
        await update.message.reply_text("أرسل ID القروب المراد حذفه:", reply_markup=kb_wait_cancel())
        return

    if is_admin(uid) and text == BTN_GG_EDIT:
        set_mode(context, MODE_GG_EDIT_SELECT)
        await update.message.reply_text("أرسل ID القروب المراد تعديله:", reply_markup=kb_wait_cancel())
        return

    # ADMIN: contact service
    if is_admin(uid) and text == BTN_CC_MENU:
        set_mode(context, MODE_CC_MENU)
        await update.message.reply_text("📲 خدمة الأرقام:", reply_markup=kb_contact_service_admin(uid))
        return

    if mode == MODE_CC_MENU and is_admin(uid):
        if text == BTN_CC_SHOW_OK:
            await update.message.reply_text(contacts_ok_text(), reply_markup=kb_contact_service_admin(uid))
            return
        if text == BTN_CC_SHOW_BAD:
            await update.message.reply_text(contacts_bad_text(), reply_markup=kb_contact_service_admin(uid))
            return

        if text == BTN_CC_EXPORT_XLSX:
            # ✅ تصدير Excel للأدمن
            fn = f"contacts_export_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
            path = os.path.join(os.getcwd(), fn)
            try:
                await asyncio.to_thread(build_contacts_excel, path)
                await update.message.reply_document(document=open(path, "rb"), filename=fn, caption="📤 تم تصدير الأرقام بنجاح.")
            except Exception as e:
                LOG.exception("Export excel failed: %s", e)
                await update.message.reply_text("❌ فشل تصدير الملف.", reply_markup=kb_contact_service_admin(uid))
            finally:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
            return

        if text == BTN_CC_ENABLE:
            if not is_super_admin(uid):
                await update.message.reply_text(deny_no_perm(), reply_markup=kb_contact_service_admin(uid))
                return
            start_confirm(context, "contact_toggle", {"enabled": True}, {"target": "admin"})
            await update.message.reply_text("تأكيد تشغيل خدمة الأرقام؟", reply_markup=kb_confirm())
            return

        if text == BTN_CC_DISABLE:
            if not is_super_admin(uid):
                await update.message.reply_text(deny_no_perm(), reply_markup=kb_contact_service_admin(uid))
                return
            start_confirm(context, "contact_toggle", {"enabled": False}, {"target": "admin"})
            await update.message.reply_text("تأكيد إيقاف خدمة الأرقام؟", reply_markup=kb_confirm())
            return

        if text == BTN_CC_CLEAR_OK:
            if not is_super_admin(uid):
                await update.message.reply_text(deny_no_perm(), reply_markup=kb_contact_service_admin(uid))
                return
            start_confirm(context, "contact_clear_ok", {}, {"target": "admin"})
            await update.message.reply_text("تأكيد مسح الأرقام المقبولة؟", reply_markup=kb_confirm())
            return

        if text == BTN_CC_CLEAR_BAD:
            if not is_super_admin(uid):
                await update.message.reply_text(deny_no_perm(), reply_markup=kb_contact_service_admin(uid))
                return
            start_confirm(context, "contact_clear_bad", {}, {"target": "admin"})
            await update.message.reply_text("تأكيد مسح الأرقام المرفوضة؟", reply_markup=kb_confirm())
            return

    # SUPER: hide/rename/admin manage
    if text == BTN_HIDE_MENU:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            return
        set_mode(context, MODE_HIDE_MENU)
        await update.message.reply_text(hide_menu_text(), reply_markup=kb_wait_cancel())
        return

    if text == BTN_RENAME_MENU:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            return
        set_mode(context, MODE_RENAME_MENU)
        await update.message.reply_text(rename_menu_text(), reply_markup=kb_wait_cancel())
        return

    if text == BTN_AM_MENU:
        if not is_super_admin(uid):
            await update.message.reply_text(deny_no_perm(), reply_markup=kb_admin(uid))
            return
        set_mode(context, MODE_AM_MENU)
        await update.message.reply_text("👮 إدارة الأدمن:", reply_markup=kb_admin_manage())
        return

    if mode == MODE_AM_MENU and is_super_admin(uid):
        if text == BTN_AM_LIST:
            admins = sorted(data_read(lambda: list(DATA.extra_admins)))
            msg = "📋 لا يوجد أدمن مضاف." if not admins else ("📋 الأدمن:\n\n" + "\n".join([f"- {x}" for x in admins]))
            await update.message.reply_text(clip(msg), reply_markup=kb_admin_manage())
            return
        if text == BTN_AM_ADD:
            set_mode(context, MODE_AM_ADD)
            await update.message.reply_text("أرسل ID الأدمن لإضافته:", reply_markup=kb_wait_cancel())
            return
        if text == BTN_AM_DEL:
            set_mode(context, MODE_AM_DEL)
            await update.message.reply_text("أرسل ID الأدمن لحذفه:", reply_markup=kb_wait_cancel())
            return

    await update.message.reply_text("ما فهمت طلبك 🤝\nاستخدم الأزرار.", reply_markup=kb_main(uid))


# =========================================================
# ERROR HANDLER
# =========================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOG.exception("Unhandled error: %s", context.error)


# =========================================================
# BUILD APP
# =========================================================
def build_app() -> Application:
    if not TOKEN or TOKEN == "8308362115:AAFj9WDYSjF0YYlvo1r1bgkRPyXi49h1VJ4":
        LOG.warning("⚠️ TOKEN مازال افتراضي. غيّره قبل التشغيل الحقيقي.")

    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myid", myid_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))

    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_error_handler(error_handler)
    setup_jobs(app)
    return app


def main() -> None:
    print("✅ البوت يعمل الآن... Ctrl+C للإيقاف.")
    app = build_app()
    app.run_polling()


if __name__ == "__main__":
    main()
