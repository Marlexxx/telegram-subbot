import json
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = "8572534648:AAF1xbYQUnp93W81K8SmQF7UenpKf6cc4O0"
CHAT_ID = "2035807800"
DATA_FILE = "subs_data.json"
# ──────────────────────────────────────────────────────────────────────────────


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def pct_emoji(pct: float) -> str:
    if pct > 0:
        return f"📈 +{pct:.1f}%"
    elif pct < 0:
        return f"📉 {pct:.1f}%"
    else:
        return f"➡️ 0%"


def week_key(date: datetime) -> str:
    monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")


def month_key(date: datetime) -> str:
    return date.strftime("%Y-%m")


def get_subs_day(data: dict, date_str: str) -> int | None:
    """Calcule les subs du jour = total du jour - total de la veille."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    yesterday_str = (d - timedelta(days=1)).strftime("%Y-%m-%d")
    if date_str in data and yesterday_str in data:
        return data[date_str] - data[yesterday_str]
    return None


# ─── COMMANDES ────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Bot de suivi des abonnés lancé !\n"
        f"Ton Chat ID : <code>{chat_id}</code>\n\n"
        f"📌 Commandes disponibles :\n"
        f"  /add &lt;nombre&gt; — Enregistrer le total membres du canal\n"
        f"  /today — Voir le récap du jour\n"
        f"  /weekly — Récap de la semaine\n"
        f"  /monthly — Récap du mois\n"
        f"  /history — Historique des 7 derniers jours",
        parse_mode="HTML"
    )


async def add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Enregistre le total membres du canal. Usage: /add 4480"""
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("❌ Usage : /add <nombre>\nExemple : /add 4480")
        return

    total = int(ctx.args[0])
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    data = load_data()

    data[today] = total
    save_data(data)

    msg = f"✅ <b>Enregistré pour le {today}</b>\n\n"
    msg += f"👥 Membres du canal : <b>{total:,}</b>\n"

    if yesterday in data:
        prev_total = data[yesterday]
        subs_day_today = total - prev_total
        msg += f"📊 Subs day : <b>+{subs_day_today:,}</b>\n"

        # % entre subs day d'hier et subs day d'aujourd'hui
        subs_day_yesterday = get_subs_day(data, yesterday)
        if subs_day_yesterday is not None and subs_day_yesterday > 0:
            pct = ((subs_day_today - subs_day_yesterday) / subs_day_yesterday) * 100
            msg += f"📈 Croissance subs day : {pct_emoji(pct)}\n"
            msg += f"(Hier : +{subs_day_yesterday:,} subs | Aujourd'hui : +{subs_day_today:,} subs)"
        else:
            msg += f"ℹ️ Pas assez de données pour comparer les subs day."
    else:
        msg += "ℹ️ Pas de données hier pour calculer les subs day."

    await update.message.reply_text(msg, parse_mode="HTML")


async def today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    if today_str not in data:
        await update.message.reply_text("❌ Aucune donnée pour aujourd'hui. Utilise /add <nombre>")
        return

    total = data[today_str]
    msg = f"📊 <b>Récap du {today_str}</b>\n\n"
    msg += f"👥 Membres du canal : <b>{total:,}</b>\n"

    if yesterday_str in data:
        prev_total = data[yesterday_str]
        subs_day_today = total - prev_total
        msg += f"📊 Subs day : <b>+{subs_day_today:,}</b>\n"

        subs_day_yesterday = get_subs_day(data, yesterday_str)
        if subs_day_yesterday is not None and subs_day_yesterday > 0:
            pct = ((subs_day_today - subs_day_yesterday) / subs_day_yesterday) * 100
            msg += f"📈 Croissance subs day : {pct_emoji(pct)}\n"
            msg += f"(Hier : +{subs_day_yesterday:,} subs | Aujourd'hui : +{subs_day_today:,} subs)"
    else:
        msg += "ℹ️ Pas de données hier pour calculer les subs day."

    await update.message.reply_text(msg, parse_mode="HTML")


async def weekly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    now = datetime.now()

    monday_this = now - timedelta(days=now.weekday())
    monday_prev = monday_this - timedelta(weeks=1)
    sunday_prev = monday_this - timedelta(days=1)

    def get_week_data(start: datetime, end: datetime):
        result = {}
        d = start
        while d <= end:
            key = d.strftime("%Y-%m-%d")
            if key in data:
                result[key] = data[key]
            d += timedelta(days=1)
        return result

    this_week = get_week_data(monday_this, now)

    if not this_week:
        await update.message.reply_text("❌ Aucune donnée cette semaine.")
        return

    sorted_this = sorted(this_week.items())
    last_day, last_count = sorted_this[-1]

    # Total subs day de la semaine
    total_subs_week = 0
    for date_str, _ in sorted_this:
        sd = get_subs_day(data, date_str)
        if sd is not None:
            total_subs_week += sd

    msg = f"📅 <b>Récap Hebdomadaire</b>\n"
    msg += f"Semaine du {monday_this.strftime('%d/%m')} au {now.strftime('%d/%m/%Y')}\n\n"
    msg += f"👥 Membres du canal : <b>{last_count:,}</b>\n"
    msg += f"📊 Subs cette semaine : <b>+{total_subs_week:,}</b>\n"

    msg += "\n\n📆 <b>Détail par jour :</b>\n"
    for date_str, count in sorted_this:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"][d.weekday()]
        sd = get_subs_day(data, date_str)
        if sd is not None:
            arrow = "🟢" if sd >= 0 else "🔴"
            msg += f"  {arrow} {day_name} {d.strftime('%d/%m')} : {count:,} membres | +{sd:,} subs\n"
        else:
            msg += f"  ⚪ {day_name} {d.strftime('%d/%m')} : {count:,} membres\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def monthly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    now = datetime.now()

    this_month = now.strftime("%Y-%m")
    this_month_data = {k: v for k, v in data.items() if k.startswith(this_month)}

    if not this_month_data:
        await update.message.reply_text("❌ Aucune donnée ce mois-ci.")
        return

    sorted_this = sorted(this_month_data.items())
    last_day, last_count = sorted_this[-1]

    total_subs_month = 0
    for date_str, _ in sorted_this:
        sd = get_subs_day(data, date_str)
        if sd is not None:
            total_subs_month += sd

    msg = f"🗓️ <b>Récap Mensuel — {now.strftime('%B %Y').capitalize()}</b>\n\n"
    msg += f"👥 Membres du canal : <b>{last_count:,}</b>\n"
    msg += f"📊 Subs ce mois : <b>+{total_subs_month:,}</b>\n"

    msg += "\n\n📆 <b>Détail par semaine :</b>\n"
    weeks = {}
    for date_str, count in sorted_this:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        wk = week_key(d)
        if wk not in weeks:
            weeks[wk] = []
        weeks[wk].append((date_str, count))

    for wk, wdata in sorted(weeks.items()):
        wk_start = datetime.strptime(wk, "%Y-%m-%d")
        wk_label = f"Sem. {wk_start.strftime('%d/%m')}"
        wk_subs = sum(get_subs_day(data, ds) or 0 for ds, _ in wdata)
        wk_last_count = wdata[-1][1]
        msg += f"  📅 {wk_label} : {wk_last_count:,} membres | +{wk_subs:,} subs\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    now = datetime.now()

    msg = "📜 <b>Historique — 7 derniers jours</b>\n\n"

    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        key = d.strftime("%Y-%m-%d")
        day_name = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"][d.weekday()]

        if key in data:
            total = data[key]
            sd = get_subs_day(data, key)
            if sd is not None:
                arrow = "🟢" if sd >= 0 else "🔴"
                msg += f"{arrow} <b>{day_name} {d.strftime('%d/%m')}</b> : {total:,} membres | +{sd:,} subs\n"
            else:
                msg += f"⚪ <b>{day_name} {d.strftime('%d/%m')}</b> : {total:,} membres\n"
        else:
            msg += f"❓ <b>{day_name} {d.strftime('%d/%m')}</b> : pas de données\n"

    await update.message.reply_text(msg, parse_mode="HTML")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("weekly", weekly))
    app.add_handler(CommandHandler("monthly", monthly))
    app.add_handler(CommandHandler("history", history))

    print("🤖 Bot démarré...")
    app.run_polling()


if __name__ == "__main__":
    main()
