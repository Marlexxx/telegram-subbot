import json
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = "8572534648:AAF1xbYQUnp93W81K8SmQF7UenpKf6cc4O0"          # @BotFather token
CHAT_ID = "2035807800"     # Ton chat ID (utilise /start pour le voir)
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
    """Retourne le % formaté avec couleur emoji."""
    if pct > 0:
        return f"📈 +{pct:.1f}%"
    elif pct < 0:
        return f"📉 {pct:.1f}%"
    else:
        return f"➡️ 0%"


def week_key(date: datetime) -> str:
    """Lundi de la semaine comme clé."""
    monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")


def month_key(date: datetime) -> str:
    return date.strftime("%Y-%m")


# ─── COMMANDES ────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Bot de suivi des abonnés lancé !\n"
        f"Ton Chat ID : <code>{chat_id}</code>\n\n"
        f"📌 Commandes disponibles :\n"
        f"  /add &lt;nombre&gt; — Enregistrer les subs du jour\n"
        f"  /today — Voir le récap du jour\n"
        f"  /weekly — Récap de la semaine\n"
        f"  /monthly — Récap du mois\n"
        f"  /history — Historique des 7 derniers jours",
        parse_mode="HTML"
    )


async def add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Enregistre le nombre de subs du jour. Usage: /add 1500"""
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("❌ Usage : /add <nombre>\nExemple : /add 1500")
        return

    count = int(ctx.args[0])
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_data()

    # Sauvegarde
    data[today] = count
    save_data(data)

    # Calcul du % vs hier
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    msg = f"✅ <b>Subs enregistrés pour le {today}</b>\n\n"
    msg += f"👥 <b>Subs day : {count:,}</b>\n"

    if yesterday in data and data[yesterday] > 0:
        prev = data[yesterday]
        diff = count - prev
        pct = (diff / prev) * 100
        msg += f"Variation vs hier : {pct_emoji(pct)}\n"
        msg += f"Différence : {'+'if diff>=0 else ''}{diff:,} abonnés\n"
    else:
        msg += "ℹ️ Pas de données hier pour comparer.\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Affiche le récap du jour."""
    data = load_data()
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    if today_str not in data:
        await update.message.reply_text("❌ Aucune donnée pour aujourd'hui. Utilise /add <nombre>")
        return

    count = data[today_str]
    msg = f"📊 <b>Récap du {today_str}</b>\n\n"
    msg += f"👥 <b>Subs day : {count:,}</b>\n"

    if yesterday_str in data:
        prev = data[yesterday_str]
        diff = count - prev
        pct = (diff / prev) * 100 if prev > 0 else 0
        msg += f"Variation : {pct_emoji(pct)}\n"
        msg += f"Différence : {'+'if diff>=0 else ''}{diff:,} abonnés\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def weekly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Récap de la semaine courante vs semaine précédente."""
    data = load_data()
    now = datetime.now()

    # Semaine courante : lundi → aujourd'hui
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
    prev_week = get_week_data(monday_prev, sunday_prev)

    msg = f"📅 <b>Récap Hebdomadaire</b>\n"
    msg += f"Semaine du {monday_this.strftime('%d/%m')} au {now.strftime('%d/%m/%Y')}\n\n"

    if not this_week:
        await update.message.reply_text("❌ Aucune donnée cette semaine.")
        return

    # Subs début et fin de semaine courante
    sorted_this = sorted(this_week.items())
    first_day, first_count = sorted_this[0]
    last_day, last_count = sorted_this[-1]

    msg += f"👥 <b>Subs actuels : {last_count:,}</b>\n"
    msg += f"Début de semaine : {first_count:,}\n"

    week_diff = last_count - first_count
    if first_count > 0:
        week_pct = (week_diff / first_count) * 100
        msg += f"Croissance semaine : {pct_emoji(week_pct)}\n"
        msg += f"Différence : {'+'if week_diff>=0 else ''}{week_diff:,} abonnés\n"

    # Comparaison avec semaine précédente
    if prev_week:
        sorted_prev = sorted(prev_week.items())
        prev_last = sorted_prev[-1][1]
        vs_prev_diff = last_count - prev_last
        vs_prev_pct = (vs_prev_diff / prev_last) * 100 if prev_last > 0 else 0
        msg += f"\nVs semaine précédente : {pct_emoji(vs_prev_pct)}\n"
        msg += f"(Semaine préc. terminée à {prev_last:,} subs)"
    else:
        msg += "\nℹ️ Pas de données la semaine précédente."

    # Détail jour par jour
    msg += "\n\n📆 <b>Détail par jour :</b>\n"
    prev_val = None
    for date_str, count in sorted_this:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"][d.weekday()]
        if prev_val is not None and prev_val > 0:
            diff = count - prev_val
            pct = (diff / prev_val) * 100
            arrow = "🟢" if diff >= 0 else "🔴"
            msg += f"  {arrow} {day_name} {d.strftime('%d/%m')} : {count:,} ({'+' if diff>=0 else ''}{diff:,})\n"
        else:
            msg += f"  ⚪ {day_name} {d.strftime('%d/%m')} : {count:,}\n"
        prev_val = count

    await update.message.reply_text(msg, parse_mode="HTML")


async def monthly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Récap du mois courant vs mois précédent."""
    data = load_data()
    now = datetime.now()

    this_month = now.strftime("%Y-%m")
    prev_month_dt = (now.replace(day=1) - timedelta(days=1))
    prev_month = prev_month_dt.strftime("%Y-%m")

    this_month_data = {k: v for k, v in data.items() if k.startswith(this_month)}
    prev_month_data = {k: v for k, v in data.items() if k.startswith(prev_month)}

    if not this_month_data:
        await update.message.reply_text("❌ Aucune donnée ce mois-ci.")
        return

    sorted_this = sorted(this_month_data.items())
    first_day, first_count = sorted_this[0]
    last_day, last_count = sorted_this[-1]

    msg = f"🗓️ <b>Récap Mensuel — {now.strftime('%B %Y').capitalize()}</b>\n\n"
    msg += f"👥 <b>Subs actuels : {last_count:,}</b>\n"
    msg += f"Début du mois : {first_count:,}\n"

    month_diff = last_count - first_count
    if first_count > 0:
        month_pct = (month_diff / first_count) * 100
        msg += f"Croissance du mois : {pct_emoji(month_pct)}\n"
        msg += f"Différence : {'+'if month_diff>=0 else ''}{month_diff:,} abonnés\n"

    if prev_month_data:
        sorted_prev = sorted(prev_month_data.items())
        prev_last = sorted_prev[-1][1]
        vs_prev_diff = last_count - prev_last
        vs_prev_pct = (vs_prev_diff / prev_last) * 100 if prev_last > 0 else 0
        msg += f"\nVs mois précédent : {pct_emoji(vs_prev_pct)}\n"
        msg += f"(Mois préc. terminé à {prev_last:,} subs)"
    else:
        msg += "\nℹ️ Pas de données le mois précédent."

    # Récap semaine par semaine dans le mois
    msg += "\n\n📆 <b>Détail par semaine :</b>\n"
    weeks = {}
    for date_str, count in sorted_this:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        wk = week_key(d)
        if wk not in weeks:
            weeks[wk] = {"dates": [], "counts": []}
        weeks[wk]["dates"].append(date_str)
        weeks[wk]["counts"].append(count)

    prev_week_last = None
    for wk, wdata in sorted(weeks.items()):
        wk_start = datetime.strptime(wk, "%Y-%m-%d")
        wk_label = f"Sem. {wk_start.strftime('%d/%m')}"
        wk_last = wdata["counts"][-1]
        wk_first = wdata["counts"][0]
        if prev_week_last is not None and prev_week_last > 0:
            d = wk_last - prev_week_last
            p = (d / prev_week_last) * 100
            arrow = "🟢" if d >= 0 else "🔴"
            msg += f"  {arrow} {wk_label} : {wk_last:,} ({'+' if d>=0 else ''}{d:,})\n"
        else:
            msg += f"  ⚪ {wk_label} : {wk_last:,}\n"
        prev_week_last = wk_last

    await update.message.reply_text(msg, parse_mode="HTML")


async def history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Affiche les 7 derniers jours."""
    data = load_data()
    now = datetime.now()

    msg = "📜 <b>Historique — 7 derniers jours</b>\n\n"
    prev_val = None

    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        key = d.strftime("%Y-%m-%d")
        day_name = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"][d.weekday()]

        if key in data:
            count = data[key]
            if prev_val is not None and prev_val > 0:
                diff = count - prev_val
                pct = (diff / prev_val) * 100
                arrow = "🟢" if diff >= 0 else "🔴"
                msg += f"{arrow} <b>{day_name} {d.strftime('%d/%m')}</b> : {count:,} ({'+' if diff>=0 else ''}{diff:,} | {pct:+.1f}%)\n"
            else:
                msg += f"⚪ <b>{day_name} {d.strftime('%d/%m')}</b> : {count:,}\n"
            prev_val = count
        else:
            msg += f"❓ <b>{day_name} {d.strftime('%d/%m')}</b> : pas de données\n"
            prev_val = None

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
