# Nordic Varda – juridisk och operativ lanseringschecklista

**Intern arbetsfil – inte juridisk rådgivning och inte färdiga köpvillkor.**  
Granskad: 2026-11-08. Butiken ska förbli förhandsvisning tills punkterna nedan är lösta.

## 1. Företagsuppgifter som saknas

Innan försäljning behöver webbplatsen visa korrekt:
- Registrerat företagsnamn och företagsform.
- Organisationsnummer och momsregistreringsstatus.
- Geografisk postadress och fungerande e-postadress.
- Kontaktväg för kundservice och reklamationer.
- Betalnings- och leveransvillkor.
- Vem som är avtalspart och ansvarig säljare.

Använd inte demo-adressen `support@nordicvarda.demo` eller påhittade företagsuppgifter.

## 2. Konsumentinformation – Sverige

- Distansavtal har som huvudregel 14 dagars ångerrätt från dagen efter att konsumenten tagit emot varan.
- Information om ångerrätt, hur den används, returadress, returfrakt och standardformulär ska lämnas före köp.
- Sedan 19 juni 2026 finns nya krav på en lättfunnen ångerfunktion när avtal ingås på webbplats/app. Funktionen ska finnas under ångerfristen och bekräfta mottagandet på ett varaktigt sätt.
- Visa totalpris inklusive moms, frakt och andra avgifter innan beställning.
- Beställningsknappen måste tydligt ange att beställningen medför betalningsskyldighet.
- Skicka orderbekräftelse i varaktig form med obligatorisk information.
- Reklamationsrätt enligt konsumentköplagen ska inte blandas ihop med frivilligt öppet köp. Påstå inte 30 dagars öppet köp om det inte är ett faktiskt beslutat erbjudande.

Källor:
- https://www.konsumentverket.se/marknadsratt-foretag/informationskrav-vid-distansavtal-regler-for-foretag
- https://www.konsumentverket.se/lagar/lagen-om-distansavtal-och-avtal-utanfor-affarslokaler-konsument/
- https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-200559-om-distansavtal-och-avtal-utanfor_sfs-2005-59/

## 3. Produktsäkerhet och import

För varje produkt ska tillverkare, modell/produktidentifierare och ansvarig ekonomisk aktör i EU kunna identifieras. Kontrollera GPSR-krav, varningar, spårbarhet och relevanta specialregler. För elektriska produkter behövs bland annat korrekt CE-/överensstämmelsedokumentation där tillämpligt; kontrollera även RoHS, EMC, radioutrustning, batteri- och producentansvar samt WEEE där produkten omfattas. Sälj inte en produkt enbart för att leverantören har en bild eller påstår att den är CE-märkt.

Källa: https://www.konsumentverket.se/produktsakerhet-foretag/lagar-och-regler-inom-produktsakerhet/

## 4. GDPR, kontaktformulär och nyhetsbrev

- Identifiera personuppgiftsansvarig och dokumentera ändamål, rättslig grund, lagringstid, mottagare/personuppgiftsbiträden och rättigheter.
- Publicera en korrekt integritetspolicy innan formulär samlar in riktiga personuppgifter.
- Nyhetsbrev ska ha ett separat, frivilligt och dokumenterbart samtycke; gör det enkelt att avsluta prenumerationen.
- Spara inte fler uppgifter än nödvändigt och sätt en raderingsrutin.
- Teckna personuppgiftsbiträdesavtal där det krävs och bedöm överföringar utanför EU/EES.
- Cookie-/spårningslösningen måste skilja nödvändiga cookies från analys/marknadsföring och inhämta samtycke där det krävs.

## 5. Drift och orderhantering

- Verifiera leverantör och provprodukt, inköpspris, lager, frakt, leveranstid, spårning och returprocess.
- Räkna marginal efter moms, betalavgifter, frakt, returer, reklamationer och marknadsföring.
- Ha rutiner för orderbekräftelse, betalningsstatus, avbeställning, återbetalning, leveransproblem och kundservice.
- Testa Stripe i testläge med testprodukter och testkort innan live-nycklar används.
- Aktivera inte Stripe live eller riktiga produkter förrän alla kontroller är godkända.

## 6. Tekniskt läge

- Produktposter i databasen är utkast och inaktiva.
- Kassa ska inte öppnas i förhandsvisningen.
- Stripe-hemligheter ska endast ligga i Supabase Function Secrets, aldrig i webbläsarkod eller GitHub.
- Service-role-nycklar får aldrig exponeras i frontend.
- Testa webhook-signatur, dubbla webhook-anrop/idempotens, misslyckad betalning, avbruten checkout, återbetalning och orderstatus innan live.
- Säkerhetskopiera och kontrollera RLS/policies regelbundet.

## 7. Lanseringsspärr

Lansering kräver att företagsuppgifter, slutliga villkor, integritet/cookies, ångerfunktion, leverans/retur, produktdokumentation, leverantörsavtal, provexemplar, moms/skatt, betalning och orderrutiner är klara. Detta dokument är en arbetslista – inte ett godkännande att börja sälja.
