# Radar de licitaciones y subvenciones

Beta de un radar diario de **contratos públicos** y **convocatorias de subvenciones** en España. Datos oficiales, sin registro para consultar, coste 0 € mientras quepa en los planes gratuitos.

> Repo público a propósito: GitHub Actions es gratis en repos públicos. No hay secretos ni datos privados; solo código y datos públicos.

## Qué hace

- Descarga cada día las licitaciones del feed Atom de **PLACE** (Contratación del Estado).
- Descarga las convocatorias abiertas de **BDNS** (Infosubvenciones).
- Normaliza, deduplica y guarda `data/items.json` (90 días).
- Publica una web estática con filtros por tipo, territorio, importe y texto.
- Deja `data/latest.json` con lo nuevo de la pasada, listo para un email diario.

## Demo en vivo

**https://radar-licitaciones-eight.vercel.app/**

Beta desplegada en Vercel. Repo: https://github.com/obonhector/radar-licitaciones

## Arquitectura 0 €

```
GitHub Actions (cron diario)
  → scripts/fetch.py (stdlib)
  → data/items.json + latest.json
  → commit al repo
  → Vercel (auto-deploy desde main)
```

No hay servidor, base de datos ni cola. Todo es estático.

**Por qué el repo es público:** GitHub Actions es gratis en repos públicos. No hay secretos ni datos privados; solo código y datos públicos. Vercel Hobby es gratis para beta; antes de cobrar, mover a Cloudflare Pages (comercial permitido).

## Coste real

| Pieza | Plan gratuito | Límite |
|---|---|---|
| GitHub Actions | 2.000 min/mes en repo privado; ilimitado en público | 1 ejecución/día ~1 min |
| GitHub Pages | 1 GB sitio, 100 GB/mes | Suficiente para beta |
| Cloudflare Pages | Gratis, comercia permitido | 500 builds/mes |
| Email (Buttondown/MailerLite) | 100–1.000 suscriptores según plan | Confirmar al crear |
| Dominio | `*.github.io` o `*.pages.dev` | 0 € |
| Dominio propio | `alertas.hochq.com` | DNS existente |

**Aviso:** GitHub Pages no está pensado para tiendas/SaaS comerciales. Para una beta gratis vale; antes de cobrar, mover a **Cloudflare Pages** o Netlify.

## Ejecutar en local

```bash
python3 scripts/fetch.py --out data --insecure   # --insecure solo si tu red tiene proxy MITM
cd site && python3 -m http.server 8788
# http://127.0.0.1:8788
```

Sin `--insecure` en producción/GitHub Actions.

## Desplegar

1. Crear repo `radar-licitaciones`.
2. Subir `scripts/`, `site/`, `data/`, `.github/`.
3. Activar Pages con GitHub Actions como fuente.
4. Ejecutar el workflow `radar` a mano una vez.
5. Opcional: CNAME `alertas.hochq.com` → `obonhector.github.io`.

## Alternativas de host

| Host | Ventaja | Límite | Cuándo |
|---|---|---|---|
| **GitHub Pages** | Ya está en GitHub, 0 config | No comercial; 100 GB/mes | Beta inmediata |
| **Cloudflare Pages** | Comercial, CDN, 0 € | 500 builds/mes | Producción |
| **Netlify** | Deploy simple, formularios | 100 GB/mes | Alternativa |
| **Vercel Hobby** | Ya lo usas | No comercial | Solo demo |
| **Oracle Cloud Always Free** | VM para `esd serve` + cron | Requiere tarjeta de verificación | Si quieres API dinámica |

## Email

- **Buttondown**: simple, API, plan gratis limitado.
- **MailerLite**: plan gratis con más suscriptores.
- **Resend**: 3.000 emails/mes, 100/día; necesita dominio verificado.
- Para empezar: botón “Avísame” con `mailto:` o Tally; cuando haya 20 suscriptores, conectar API.

## Roadmap

1. Beta con contratos + convocatorias; filtros y email semanal.
2. Añadir **concesiones** (BDNS) y **Aragón** (`esd aragon backfill`) para nicho local.
3. Alertas personalizadas por sector/provincia (requiere base de suscriptores).
4. Plan de pago con Stripe Payment Links/Gumroad; sin servidor.
5. API de pago para integradores.

## Aviso

Datos públicos de PLACE y BDNS. Verifica siempre la fuente oficial antes de presentar una oferta. No es asesoramiento jurídico ni garantía de exactitud; las fuentes pueden cambiar o retrasarse.
