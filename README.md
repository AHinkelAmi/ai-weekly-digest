# Weekly AI Digest – Setup

Erstellt automatisch jede Woche ein PDF mit den neuesten Meldungen aus
seriösen AI-Quellen (OpenAI, Google Research, MIT Technology Review, MIT News,
MarkTechPost). Kein API-Key, kein externer Dienst, keine Zugangsdaten nötig –
nur ein kostenloses GitHub-Konto.

## Was das Skript tut (und was nicht)

Es liest die RSS-Feeds aus `feeds.yaml`, filtert Artikel der letzten 7 Tage
und listet sie mit Titel, Datum, Original-Teaser und Link in einem PDF auf.
Es fasst **nicht** mit einem Sprachmodell zusammen – der Teaser-Text ist die
von der Quelle selbst gelieferte RSS-Beschreibung, nur gekürzt. Das ist ohne
API-Key nicht anders möglich. Für eine echte KI-Zusammenfassung müsstest du
später einen API-Key ergänzen (dann reicht ein Zweizeiler im Skript) – bis
dahin ist es ein sauberer, seriöser Kurier-Digest.

## Einmalige Einrichtung (ca. 10 Minuten)

1. **Neues GitHub-Repository anlegen** (privat oder öffentlich, spielt keine
   Rolle) – z. B. `ai-weekly-digest`.
2. Die Dateien aus diesem Ordner (`generate_digest.py`, `feeds.yaml`, den
   Ordner `.github/`) in das Repository hochladen. Am einfachsten über die
   GitHub-Weboberfläche: "Add file" → "Upload files" → alles reinziehen →
   Commit.
3. Fertig. Der Workflow läuft automatisch jeden **Montag um 07:00 UTC**.

Kein Secret, kein Token, kein API-Key einzutragen – `GITHUB_TOKEN` wird von
GitHub selbst pro Lauf automatisch bereitgestellt.

## Wie du das PDF bekommst

Jeder Lauf legt unter **Releases** (rechte Seitenleiste des Repos) einen
neuen Eintrag mit dem PDF als Anhang an, z. B. "AI Digest – 2026-07-06".
Du kannst das Repo mit dem Glocken-Symbol ("Watch" → "Custom" → "Releases")
abonnieren, dann bekommst du bei jedem neuen Digest automatisch eine
E-Mail-Benachrichtigung von GitHub – ganz ohne zusätzliche Konfiguration.

## Manuell testen, ohne auf Montag zu warten

Im Repo: Reiter **Actions** → "Weekly AI Digest" → **Run workflow**. Läuft
sofort und legt ein Release an, so kannst du das Ergebnis direkt prüfen.

## Was ist neu: Anthropic & Ethics-Kategorie

**Anthropic** hat weiterhin keinen eigenen RSS-Feed. Gelöst über einen vom
**Alan Turing Institute** öffentlich gepflegten Feed-Generator (`ai-rss-feeds`
auf GitHub), der die Anthropic-News-Seite automatisch in einen Feed umwandelt
und aktuell hält. Kein Drittanbieter-Account nötig, da der Feed direkt als
Rohdatei auf GitHub liegt (`raw.githubusercontent.com`).

**Neue Kategorie "Ethics & Governance"** – bisher deckte die Quellenliste nur
Forschung, Fachpresse und regulatorische Compliance ab, keine ethische
Auseinandersetzung mit AI. Jetzt dabei:
- **Alan Turing Institute** (Blog + News) – UK-weites Institut für Data
  Science/AI, mit eigenem Ethik-Forschungsstrang
- **Montreal AI Ethics Institute** – "The AI Ethics Brief", international
  anerkannte Non-Profit, von UNESCO als zivilgesellschaftliche
  Referenzorganisation gelistet

Noch offen (kein verifizierbarer RSS-Feed gefunden): Ada Lovelace Institute,
UNESCO Ethics of AI, OECD.AI – siehe Hinweise am Ende von `feeds.yaml`.
Lösung wie gehabt: einmalig via rss.app einen Feed erzeugen.

## Quellen anpassen

`feeds.yaml` öffnen, Zeile im Format

```yaml
  - name: "Anzeigename"
    url: "https://beispiel.com/feed"
```

hinzufügen oder entfernen. Änderungen wirken sich ab dem nächsten Lauf aus.

**Keyword-Filter:** Manche offizielle Feeds (z. B. alle Pressemitteilungen der
EU-Kommission, oder NISTs allgemeiner IT-/Cybersecurity-Feed) sind nicht
AI-exklusiv. Für solche Quellen kann man eine `keywords`-Liste angeben – nur
Artikel, die mindestens eines der Stichwörter im Titel oder in der
Beschreibung enthalten, landen im PDF:

```yaml
  - name: "Beispielquelle (gefiltert)"
    url: "https://beispiel.com/feed"
    keywords: ["artificial intelligence", "ai act"]
```

So sind aktuell bereits eingebunden:
- **NIST** (Information Technology + Cybersecurity, gefiltert auf AI/CAISI-Begriffe)
- **EU-Kommission** (alle Pressemitteilungen, gefiltert auf AI Act / AI Office / "artificial intelligence")

Damit sind NIST und die EU-Regulierungsseite abgedeckt, ohne dass es dafür
eigene offizielle AI-Feeds bräuchte.

**Weiterhin ohne offiziellen RSS-Feed** (Stand Juli 2026, siehe Hinweise in
`feeds.yaml`): Anthropic News und OECD.AI/The AI Wonk. Für Stanford HAI gibt
es vermutlich einen Feed, aber die URL ließ sich nicht zuverlässig
verifizieren – zwei Kandidaten stehen zum Testen in `feeds.yaml`.

Für diese drei lässt sich ohne Zusatzdienst nichts automatisieren. rss.app
(kostenlose Stufe, kein API-Key, nur E-Mail-Login) erzeugt aus praktisch
jeder Webseite einen Feed – die erzeugte URL trägst du dann einfach in
`feeds.yaml` ein, wie jede andere Quelle auch.

## Sicherheitsassessment

Siehe [`SECURITY_ASSESSMENT.md`](./SECURITY_ASSESSMENT.md) – formales
Risk-Register (CC-Domain-Struktur: Security Operations, Access Control,
Security Principles, Availability), Datenklassifizierung und Sign-off-Feld.
Für die Kollegen/das Management gedacht, falls das Repo geprüft wird.

## Sicherheitshinweis: Actions auf Commit-SHA pinnen

`actions/checkout` und `actions/setup-python` sind GitHub-eigene Actions –
unkritisch. `softprops/action-gh-release` ist eine Community-Action; Tags
wie `@v2` können nachträglich auf anderen Code verweisen. Für produktiven
Einsatz empfehlenswert: den Tag durch den konkreten Commit-SHA ersetzen.

So holst du den SHA (im GitHub-Repo, nicht hier):
1. Gehe zu `github.com/softprops/action-gh-release`
2. Tab "Tags" → neuesten Release-Tag (z. B. `v2`) anklicken
3. Den vollen Commit-SHA kopieren
4. In `weekly-ai-digest.yml` ersetzen:
   ```yaml
   uses: softprops/action-gh-release@<SHA>  # v2, gepinnt am <Datum>
   ```

Dependencies sind bereits über `requirements.txt` versionsgepinnt (kein
`pip install <paket>` ohne Version mehr im Workflow).



- Manche Seiten ändern ihre Feed-Struktur ohne Ankündigung. Wenn eine Quelle
  im PDF als "Could not retrieve this feed" erscheint, die URL in
  `feeds.yaml` prüfen (im Browser aufrufen – muss XML anzeigen, keine
  HTML-Fehlerseite).
- Ohne API-Key gibt es keine inhaltliche Bewertung oder Priorisierung –
  das PDF listet, was die Quellen selbst als Beschreibung liefern.
