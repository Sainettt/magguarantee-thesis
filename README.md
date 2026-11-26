# MAGGuarantee — praca dyplomowa

System do obsługi wniosków z tytułu gwarancji kilometrów dla firmy transportowej
MAGTRANS. Przewoźnik zgłasza wniosek, gdy jego pojazd przejechał w okresie
rozliczeniowym mniej kilometrów, niż gwarantuje umowa; system wylicza dopłatę
w EUR i prowadzi wniosek przez weryfikację, autoryzację i ewentualną reklamację.

To repozytorium jest **zamrożonym stanem projektu z 17.08.2026** (w dokumentacji:
tag `praca-dyplomowa`), przygotowanym jako projekt inżynierski
(„Projekt informatyczny inż.”, Uniwersytet VIZJA, kierunek Informatyka).

## Zawartość

| Katalog | Opis |
|---|---|
| `thesis/` | Dokumentacja projektowa: `dokumentacja.pdf` / `.docx` / `.md`, rysunki w `img/` |
| `magguarantee-app/apps/api` | Backend: NestJS + Prisma |
| `magguarantee-app/apps/web` | Frontend: Next.js 15 (App Router) + Tailwind |
| `magguarantee-app/packages/shared` | Schematy Zod (kontrakt API) i logika domenowa, m.in. silnik `km-calc` |
| `magguarantee-app/packages/database` | Schemat Prisma, 53 migracje, seed |
| `infra/` | Docker Compose, Caddy, skrypty kopii zapasowych |

Repozytorium jest kopią bez historii zmian. Nazwy hostów, adresy i hasła
środowisk zastąpiono wartościami przykładowymi (`example.com`). Wewnętrzna
dokumentacja robocza (`docs/`) i prototyp w Google Apps Script nie są częścią
tej kopii, więc odwołania do nich w komentarzach kodu prowadzą donikąd.

## Uruchomienie lokalne

Wymagania: Node 20 (`nvm use`), npm 10+, Docker.

```bash
cd magguarantee-app
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
cp packages/database/.env.example packages/database/.env

npm install
docker compose -p magguarantee-thesis up -d   # Postgres, Redis, Mailhog, MinIO
npm run db:generate
npm run db:migrate:deploy
npm run db:seed
npm run dev
```

- Aplikacja: http://localhost:3000
- API: http://localhost:3001 (`/health`)
- Mailhog (poczta testowa, kody 2FA): http://localhost:8025

## Konta testowe (seed)

Hasło dla wszystkich: `Test1234!`. Kod logowania 2FA trafia do Mailhog.

| Login | Rola |
|---|---|
| `admin` | administrator |
| `pracownik1` | pracownik (weryfikacja wniosków) |
| `opiekun1` | opiekun przewoźników |
| `planista1` | planista |
| `dyspozytor1`, `dyspozytor2` | dyspozytor |
| `przewoznik1` | przewoźnik |
| `eksport1` | eksport |
| `weryfikator1` | weryfikator kilometrów |

## Testy

```bash
cd magguarantee-app
npm run build -w @magguarantee/shared
npm test --workspaces --if-present
```

## Przebudowanie dokumentacji

`python3 thesis/build_docx.py` (wymaga `pandoc` oraz szablonu uczelni
`thesis/wzor_dokumentacji_projektowej.docx`, którego nie ma w repozytorium).
