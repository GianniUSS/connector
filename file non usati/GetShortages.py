#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, requests, sys, os, json, smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz
import config  # REN_BASE_URL, REN_API_TOKEN (+ eventuale SMTP)

# ========= utilità =========
TZ = "Europe/Rome"

def headers():
    return {"Authorization": f"Bearer {config.REN_API_TOKEN}", "Accept": "application/json"}

def base_url(path: str) -> str:
    return config.REN_BASE_URL.rstrip("/") + path

def now_date_tz():
    return datetime.now(pytz.timezone(TZ)).date()

def safe_float(x):
    try: return float(x)
    except Exception: return 0.0

def pick(d: dict, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None

def norm_name(s: str) -> str:
    return (s or "").strip().lower()

def parse_date_like(val):
    if not val:
        return None
    if isinstance(val, dict):
        for k in ("start","date","from"):
            if k in val and val[k]:
                val = val[k]; break
    s = str(val)[:10]
    for fmt in ("%Y-%m-%d","%d-%m-%Y","%Y/%m/%d","%d/%m/%Y"):
        try: return datetime.strptime(s, fmt).date()
        except Exception: pass
    try: return datetime.fromisoformat(s).date()
    except Exception: return None

# ========= progetti =========
def get_project(project_id: str):
    r = requests.get(base_url(f"/projects/{project_id}"), headers=headers(), timeout=30)
    r.raise_for_status()
    data = r.json().get("data", r.json())
    raw_start = (data.get("start_date") or data.get("start") or data.get("date") or
                 (data.get("period", {}) if isinstance(data.get("period"), dict) else {}).get("start"))
    start_date = parse_date_like(raw_start)
    return {
        "id": data.get("id", project_id),
        "name": data.get("name") or data.get("title") or f"Project {project_id}",
        "start_date": start_date,
    }

def list_projects_next_days(days: int):
    r = requests.get(base_url("/projects"), headers=headers(), timeout=30)
    r.raise_for_status()
    rows = r.json().get("data") or r.json().get("projects") or []
    d_from, d_to = now_date_tz(), now_date_tz() + timedelta(days=days)
    out = []
    for p in rows:
        start = p.get("start_date") or p.get("start") or p.get("date") \
                or (p.get("period", {}) if isinstance(p.get("period"), dict) else {}).get("start")
        sd = parse_date_like(start)
        if sd and d_from <= sd <= d_to:
            out.append({"id": p.get("id"), "name": p.get("name") or p.get("title") or f"Project {p.get('id')}"})
    return out

# ========= equipment =========
def fetch_plannedequipment(project_id: str):
    r = requests.get(base_url(f"/projects/{project_id}/plannedequipment"), headers=headers(), timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def row_reason_flags(row: dict):
    raw = row.get("reason") or row.get("status_reason") or ""
    if isinstance(raw, dict):
        raw = raw.get("name") or raw.get("label") or ""
    txt = str(raw).lower()
    is_shortage = ("carenza" in txt or "shortage" in txt)
    is_resolved = ("risolta" in txt or "resolved" in txt)
    return is_shortage, is_resolved, txt

def detect_is_subrent(row: dict) -> bool:
    if any(k in row for k in ("subrented_quantity","subrent_quantity","subhired_quantity","hired_in","hiredIn")):
        return True
    if row.get("supplier_id") or row.get("supplier"):
        return True
    is_shortage, is_resolved, _ = row_reason_flags(row)
    if is_shortage and is_resolved:
        return True
    for k in ("is_subrented","is_hired_in","external","hired"):
        if str(row.get(k)).lower() in ("1","true","yes"):
            return True
    return False

# ========= NUOVO: date riga robuste =========
def extract_event_date(row: dict):
    # 1) chiavi "standard"
    for key, sub in [
        ("event_date", None), ("project_date", None), ("date", None),
        ("start_date", None), ("start", None), ("from", None),
        ("period", "start"), ("timeframe", "start"), ("occurrence", "date")
    ]:
        if key in row and row[key]:
            v = row[key]
            if isinstance(v, dict) and sub:
                v = v.get(sub)
            d = parse_date_like(v)
            if d: return d

    # 2) chiavi "planperiod" usate da Rentman
    if row.get("planperiod_start"):
        d = parse_date_like(row["planperiod_start"])
        if d: return d
    if row.get("planperiod_end"):
        d = parse_date_like(row["planperiod_end"])
        if d: return d
    pp = row.get("planperiod")
    if isinstance(pp, dict):
        for subk in ("start", "end"):
            d = parse_date_like(pp.get(subk))
            if d: return d
    return None

# ========= calcolo carenze =========
def calc_shortages_for_project(project_id: str, event_date=None, ui_match=False,
                               strict_date=False, require_reason=False, debug=False):
    proj = get_project(project_id)
    rows_all = fetch_plannedequipment(project_id)   # conserva tutte le righe (per fallback)
    rows = rows_all[:]

    # filtro per data + fallback automatico se svuota tutto
    if event_date:
        filtered = []
        for r in rows_all:
            d = extract_event_date(r)
            if d is None and strict_date:
                d = proj.get("start_date")  # fallback alla data progetto
            if d is None and strict_date:
                continue
            if (d is None and not strict_date) or (d == event_date):
                filtered.append(r)
        rows = filtered if filtered else rows_all  # FALLBACK

    # raggruppo per nome materiale
    groups, display_name = {}, {}
    for it in rows:
        name = pick(it, "name", "equipment_name") or f"ID {pick(it,'equipment_id','item_id','id')}"
        key = norm_name(name)
        display_name[key] = name
        groups.setdefault(key, []).append(it)

    result, dbg_rows = [], []

    for key, items in groups.items():
        planned_parts  = [safe_float(pick(x,"quantity","planned_quantity","qty","required","amount")) for x in items]
        reserved_parts = [safe_float(pick(x,"reserved_quantity","reserved","booked","booked_quantity")) for x in items]

        reasons = [row_reason_flags(x) for x in items]
        reason_shortage_any = any(rs for rs, _, _ in reasons)
        reason_resolved_any = any(rv for _, rv, _ in reasons)
        reason_effective = reason_shortage_any and not reason_resolved_any

        # subrent rilevato
        subrent_parts = []
        for x in items:
            v = 0.0
            if detect_is_subrent(x):
                v = safe_float(pick(x,"subrented_quantity","subrent_quantity","subhired_quantity","hired_in","hiredIn"))
                if v == 0.0:
                    v = safe_float(pick(x,"quantity","planned_quantity","qty"))
            subrent_parts.append(v)

        # euristica 70+10 vs 80 (3+ righe, nessun subrent)
        balance_flag = [False]*len(items)
        if sum(subrent_parts) == 0.0 and len(planned_parts) >= 3:
            qmax = max(planned_parts); imax = planned_parts.index(qmax)
            others = sum(planned_parts) - qmax
            if abs(qmax - others) < 1e-9 and qmax > max(planned_parts[:imax] + planned_parts[imax+1:]):
                subrent_parts[imax] = qmax
                balance_flag[imax] = True

        # duplicati gemelli 1+1 -> 1
        planned_effective = None
        if len(planned_parts) == 2 and sum(subrent_parts) == 0.0 and sum(reserved_parts) == 0.0:
            a, b = planned_parts
            if abs(a - b) < 1e-9:
                planned_effective = a
        if planned_effective is None:
            planned_effective = sum(p for p, bf in zip(planned_parts, balance_flag) if not bf)

        reserved_sum = sum(reserved_parts)
        subrent_sum  = sum(subrent_parts)
        covered = min(planned_effective, reserved_sum + subrent_sum)
        missing = max(0.0, planned_effective - (reserved_sum + subrent_sum))

        if debug:
            dbg_rows.append({
                "name": display_name[key],
                "planned_parts": planned_parts,
                "reserved_parts": reserved_parts,
                "subrent_parts": subrent_parts,
                "planned_effective": planned_effective,
                "reserved_sum": reserved_sum,
                "subrent_sum": subrent_sum,
                "missing": missing,
                "reasons": [t for _,_,t in reasons],
                "reason_effective": reason_effective,
                "event_dates": [extract_event_date(x) for x in items]
            })

        # filtri stile UI
        if require_reason:
            if not reason_effective:
                continue
        elif ui_match:
            if not reason_effective:
                all_reason_missing = all((t is None) or (str(t).strip() == "") for _, _, t in reasons)
                if not (all_reason_missing and missing > 0):
                    continue

        if missing > 0:
            result.append({
                "project_name": proj["name"],
                "item_name": display_name[key],
                "planned": planned_effective,
                "covered": covered,
                "missing": missing
            })

    return proj, result, dbg_rows

# ========= output =========
def save_report(lines, title, debug_rows=None):
    fname = f"shortages_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(title + "\n\n")
        if not lines:
            f.write("Nessuna carenza rilevata.\n")
        else:
            for s in lines:
                f.write(f"- [{s['project_name']}] {s['item_name']} → "
                        f"pianificato {s['planned']:.0f}, coperto {s['covered']:.0f}, "
                        f"❗ mancano {s['missing']:.0f}\n")
        if debug_rows:
            f.write("\n--- DEBUG GRUPPI ---\n")
            for r in debug_rows:
                f.write(
                    f"{r['name']} | planned_parts={r['planned_parts']} reserved_parts={r['reserved_parts']} "
                    f"subrent_parts={r['subrent_parts']} → planned_eff={r['planned_effective']}, "
                    f"reserved_sum={r['reserved_sum']}, subrent_sum={r['subrent_sum']}, "
                    f"missing={r['missing']} | reasons={r['reasons']} ui_match={r['reason_effective']} "
                    f"| event_dates={r.get('event_dates')}\n"
                )
    print(f"[INFO] Report salvato in {fname}")
    return fname

# ========= notifiche =========
def notify_slack(webhook_url: str, title: str, lines):
    try:
        blocks = [{"type":"section","text":{"type":"mrkdwn","text":f"*{title}*"}}]
        if not lines:
            blocks.append({"type":"section","text":{"type":"mrkdwn","text":"Nessuna carenza."}})
        else:
            for s in lines[:30]:
                txt = f"- *{s['item_name']}* · pianificato {s['planned']:.0f}, coperto {s['covered']:.0f}, *mancano {s['missing']:.0f}*"
                blocks.append({"type":"section","text":{"type":"mrkdwn","text":txt}})
        payload = {"blocks": blocks}
        requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type":"application/json"}, timeout=15)
        print("[INFO] Notifica Slack inviata")
    except Exception as e:
        print(f"[WARN] Slack non inviato: {e}", file=sys.stderr)

def notify_email(host, port, user, pwd, sender, to_addr, subject, body):
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_addr
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            if user and pwd:
                s.login(user, pwd)
            s.sendmail(sender, [to_addr], msg.as_string())
        print("[INFO] Email inviata")
    except Exception as e:
        print(f"[WARN] Email non inviata: {e}", file=sys.stderr)

# ========= CLI =========
def main():
    ap = argparse.ArgumentParser(description="Carenze Rentman via /projects/{id}/plannedequipment (stile UI).")
    ap.add_argument("--project-id", type=str, help="ID progetto; se omesso analizza i prossimi N giorni")
    ap.add_argument("--days", type=int, default=15, help="Giorni futuri (default 15)")
    ap.add_argument("--event-date", type=str, help="Filtra alla data evento (YYYY-MM-DD)")
    ap.add_argument("--ui-match", action="store_true",
                    help="Mostra solo righe con Ragione di carenza (con fallback se Ragione mancante)")
    ap.add_argument("--require-reason", action="store_true",
                    help="Identico alla UI: richiede Ragione presente & carenza (niente fallback)")
    ap.add_argument("--strict-date", action="store_true",
                    help="Con --event-date: usa fallback = data progetto; se manca, scarta. Se il filtro svuota, usa tutte le righe.")
    ap.add_argument("--debug", action="store_true", help="Aggiunge sezione DEBUG nel file")
    # Notifiche
    ap.add_argument("--slack-webhook", type=str, help="URL Incoming Webhook Slack")
    ap.add_argument("--email-to", type=str, help="Indirizzo destinatario email")
    ap.add_argument("--email-from", type=str, default=getattr(config, "SMTP_FROM", ""), help="Mittente email")
    ap.add_argument("--smtp-host", type=str, default=getattr(config, "SMTP_HOST", ""), help="SMTP host")
    ap.add_argument("--smtp-port", type=int, default=getattr(config, "SMTP_PORT", 587), help="SMTP port")
    ap.add_argument("--smtp-user", type=str, default=getattr(config, "SMTP_USER", ""), help="SMTP user")
    ap.add_argument("--smtp-pass", type=str, default=getattr(config, "SMTP_PASS", ""), help="SMTP password")
    ap.add_argument("--notify-always", action="store_true", help="Invia notifica anche se non ci sono carenze")
    args = ap.parse_args()

    event_date = None
    if args.event_date:
        try:
            event_date = datetime.fromisoformat(args.event_date).date()
        except Exception:
            print("[ERRORE] --event-date deve essere YYYY-MM-DD", file=sys.stderr)
            sys.exit(2)

    try:
        if args.project_id:
            proj, lines, dbg = calc_shortages_for_project(
                args.project_id, event_date=event_date,
                ui_match=args.ui_match, strict_date=args.strict_date,
                require_reason=args.require_reason, debug=args.debug
            )
            title = f"Rentman • Carenze progetto {proj['name']} (ID {proj['id']})"
            if event_date:
                title += f" — data {event_date.isoformat()}"
            report_path = save_report(lines, title, dbg if args.debug else None)
        else:
            projects = list_projects_next_days(args.days)
            all_lines, all_dbg = [], []
            for p in projects:
                _, lines, dbg = calc_shortages_for_project(
                    str(p["id"]), event_date=event_date,
                    ui_match=args.ui_match, strict_date=args.strict_date,
                    require_reason=args.require_reason, debug=args.debug
                )
                all_lines.extend(lines)
                if args.debug: all_dbg.extend(dbg)
            title = f"Rentman • Carenze (prossimi {args.days} giorni)"
            if event_date:
                title += f" — data {event_date.isoformat()}"
            report_path = save_report(all_lines, title, all_dbg if args.debug else None)
            lines = all_lines

        # Notifiche
        if args.notify_always or lines:
            if args.slack_webhook:
                notify_slack(args.slack_webhook, title, lines)
            if args.email_to and args.smtp_host and args.email_from:
                with open(report_path, "r", encoding="utf-8") as f:
                    body = f.read()
                notify_email(args.smtp_host, args.smtp_port, args.smtp_user, args.smtp_pass,
                             args.email_from, args.email_to, title, body)

    except Exception as e:
        save_report([], "Rentman • Carenze (errore)")
        print(f"[ERRORE] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
