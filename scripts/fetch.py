#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Radar de licitaciones y subvenciones — fetch diario, sin dependencias externas.

Fuentes:
- PLACE (Contratación del Estado) Atom: licitaciones abiertas.
- BDNS (Infosubvenciones) convocatorias: subvenciones abiertas.

Salida:
- data/items.json  (histórico, 90 días)
- data/latest.json (nuevos de esta pasada)
- data/meta.json   (conteos y fecha)

Uso:
  python3 scripts/fetch.py --out data
  python3 scripts/fetch.py --insecure   # solo local con proxy MITM
"""

import argparse
import datetime as dt
import json
import os
import re
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET

PLACE_ATOM = "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom"
BDNS_CALLS = "https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda"
BDNS_DETAIL = "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/{id}"
UA = "RadarLicitaciones/0.1 (+https://github.com/obonhector/radar-licitaciones)"


def get(url, insecure=False, timeout=45):
    ctx = ssl._create_unverified_context() if insecure else ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, application/atom+xml, */*"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def text(x):
    return re.sub(r"\s+", " ", (x or "")).strip()


def first(pattern, s, default=""):
    m = re.search(pattern, s, re.I | re.S)
    return text(m.group(1)) if m else default


def parse_amount(s):
    if not s:
        return None
    s = s.strip().replace("EUR", "").replace(" ", "")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") == 1 and len(s.split(".")[-1]) == 2:
        pass
    else:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_place(raw):
    root = ET.fromstring(raw)
    ns = "{http://www.w3.org/2005/Atom}"
    items = []
    for e in root.findall(ns + "entry"):
        title = text(e.findtext(ns + "title", default=""))
        summary = text(e.findtext(ns + "summary", default=""))
        updated = text(e.findtext(ns + "updated", default=""))
        link = ""
        for l in e.findall(ns + "link"):
            if l.attrib.get("href"):
                link = l.attrib["href"]
                break
        if not link:
            link = text(e.findtext(ns + "id", default=""))
        raw_e = ET.tostring(e, encoding="unicode")
        organ = first(r"Órgano de Contratación:\s*([^;]+)", summary)
        status = first(r"Estado:\s*([^;]+)", summary)
        amount_s = first(r"Importe:\s*([\d.,]+)\s*EUR", summary)
        amount = parse_amount(amount_s)
        if amount is None:
            for tag in ("EstimatedOverallContractAmount", "TaxExclusiveAmount", "TotalAmount"):
                m = re.search(r"<%s[^>]*>([\d.]+)</%s>" % (tag, tag), raw_e)
                if m:
                    amount = parse_amount(m.group(1))
                    if amount is not None:
                        break
        city = first(r"<[^>]*CityName>([^<]+)<", raw_e)
        nuts = first(r"<[^>]*CountrySubentityCode[^>]*>([^<]+)<", raw_e)
        cpv = first(r"<[^>]*ItemClassificationCode[^>]*>(\d{4,8})<", raw_e)
        deadline = first(r"<[^>]*EndDate>([^<]+)<", raw_e)
        items.append({
            "id": text(e.findtext(ns + "id", default="")) or link,
            "type": "contract",
            "title": title,
            "summary": summary,
            "organ": organ,
            "location": city,
            "nuts": nuts,
            "cpv": cpv,
            "amount": amount,
            "deadline": deadline,
            "published": updated,
            "status": status,
            "url": link,
            "source": "PLACE",
        })
    return items


def fetch_bdns_calls(days=30, max_pages=5, insecure=False):
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    items = []
    for page in range(max_pages):
        url = "%s?page=%d&pageSize=100" % (BDNS_CALLS, page)
        data = json.loads(get(url, insecure=insecure).decode("utf-8"))
        content = data.get("content") or []
        if not content:
            break
        stop = False
        for c in content:
            date = (c.get("fechaRecepcion") or "")[:10]
            if date and date < cutoff:
                stop = True
                continue
            desc = text(c.get("descripcion") or c.get("descripcionLeng") or "")
            if not desc:
                continue
            items.append({
                "id": "bdns-call-%s" % c.get("id"),
                "type": "grant_call",
                "title": desc,
                "summary": desc,
                "organ": text(c.get("nivel3") or ""),
                "location": text(c.get("nivel2") or ""),
                "nuts": "",
                "cpv": "",
                "amount": None,
                "deadline": "",
                "published": date,
                "status": text(c.get("nivel1") or ""),
                "url": BDNS_DETAIL.format(id=c.get("id")),
                "source": "BDNS convocatorias",
            })
        if stop:
            break
    return items


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--bdns-days", type=int, default=30)
    ap.add_argument("--max-pages", type=int, default=5)
    ap.add_argument("--insecure", action="store_true", help="solo para redes con proxy MITM")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    old = load(os.path.join(args.out, "items.json"), [])
    old_ids = {x.get("id") for x in old}

    new_items = []
    errors = []

    try:
        place = parse_place(get(PLACE_ATOM, insecure=args.insecure))
        new_items.extend(place)
    except Exception as e:
        errors.append("PLACE: %s" % e)

    try:
        calls = fetch_bdns_calls(days=args.bdns_days, max_pages=args.max_pages, insecure=args.insecure)
        new_items.extend(calls)
    except Exception as e:
        errors.append("BDNS: %s" % e)

    # dedupe dentro de la pasada
    by_id = {}
    for x in new_items:
        if x.get("id"):
            by_id[x["id"]] = x

    cutoff = (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
    merged = []
    seen = set()
    for x in list(by_id.values()) + old:
        i = x.get("id")
        if not i or i in seen:
            continue
        seen.add(i)
        d = (x.get("published") or "")[:10]
        if d and d < cutoff:
            continue
        merged.append(x)

    merged.sort(key=lambda x: (x.get("published") or "", x.get("title") or ""), reverse=True)
    merged = merged[:5000]
    latest = [x for x in merged if x.get("id") not in old_ids]

    with open(os.path.join(args.out, "items.json"), "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=1)
    meta = {
        "generated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "total": len(merged),
        "new": len(latest),
        "contracts": sum(1 for x in merged if x.get("type") == "contract"),
        "grant_calls": sum(1 for x in merged if x.get("type") == "grant_call"),
        "errors": errors,
        "sources": ["PLACE", "BDNS convocatorias"],
    }
    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
