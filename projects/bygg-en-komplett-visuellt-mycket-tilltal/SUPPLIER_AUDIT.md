# Nordic Varda – produkt- och leverantörsgranskning

**Status: intern arbetsfil – inga produkter godkända för försäljning.**  
Granskad: 2026-11-08. Alla 20 produktposter ligger kvar som inaktiva utkast i Supabase.

## Sammanfattning

De nuvarande 20 posterna är konceptnamn med marknadsföringstexter och externa bildlänkar. De innehåller inte verifierade leverantörs-SKU:er, inköpspriser, lagerstatus, leveranslöften eller dokumentation för produktsäkerhet. Flera bildlänkar kommer från tredjepartswebbplatser och rätt att använda bilderna är inte dokumenterad. Därför är ingen produkt redo att publiceras.

## Granskning per produkt

| SKU i demo | Produkt | Kategori | Viktig kontroll före publicering |
|---|---|---|---|
| NV-BIL-01 | Lumina Trådlös Bordslampa | Belysning | Exakt modell, batteri/CE, laddare, IP54-bevis, EU-ansvarig aktör, bildlicens |
| NV-INN-02 | Aura Aromaspridare & Luftfuktare | Inredning | Exakt modell, elektrisk säkerhet/CE, oljekompatibilitet, tankkapacitet, bildlicens |
| NV-KOK-03 | Krona Smart Vattenkokare | Kök | Exakt modell, livsmedelskontakt, elektrisk säkerhet, app/plattform, garanti, bildlicens |
| NV-INN-04 | Terra Minimalistisk Väggklocka | Inredning | Exakt modell, mått/material, batteri, ljudnivå, bildlicens |
| NV-SMA-05 | Nexus Smart Laddstation | Smart hem | Qi-certifiering, kompatibla enheter, effekt per spole, nätadapter, CE, bildlicens |
| NV-SMA-06 | Nordic Breeze Bordsfläkt | Smart hem | Exakt modell, batteri/USB-C, ljudnivå, säkerhet, bildlicens |
| NV-KOK-07 | Vera Keramisk Kaffebryggare | Kök | Exakt modell, material/livsmedelskontakt, mått, bildlicens |
| NV-BIL-08 | Solros Wake-up Ljusväckarklocka | Belysning | Exakt modell, ljusintensitet, ljudfunktioner, elektrisk säkerhet, bildlicens |
| NV-KOK-09 | Fjord Termosflaska 0.7L | Kök | Exakt modell, volym, material/livsmedelskontakt, täthet/temperaturtest, bildlicens |
| NV-SMA-10 | Echo Smart Inomhussensor | Smart hem | Exakt modell, CO₂-sensortyp (inte bara uppskattning), app, radio/CE, dataskydd, bildlicens |
| NV-KOK-11 | Hugin Elektrisk Salt- & Pepparkvarn | Kök | Exakt modell, material/livsmedelskontakt, batterier, säkerhet, bildlicens |
| NV-INN-12 | Nordic Leaf Ullpläd | Inredning | Exakt fiberinnehåll, ursprung, skötselråd, textilmärkning, bildlicens |
| NV-BIL-13 | Zenith Golvlampa i Matt Metall | Belysning | Exakt modell, material, elektrisk säkerhet, stabilitet, CE, bildlicens |
| NV-INN-14 | Kust Handtvålpump i Stengods | Inredning | Exakt modell, material, mått, pumpmaterial, bildlicens |
| NV-SMA-15 | Nova Smart Vägguttag med Energiövervakning | Smart hem | Hög risk: CE/försäkran, maxlast, överhettningsskydd, radio/RED, svensk stickpropp, återkallelser |
| NV-KOK-16 | Atlas Skärbräda i Ädelträ | Kök | Exakt träslag/ursprung, ytbehandling och livsmedelskontakt, mått, bildlicens |
| NV-BIL-17 | Borealis Nattlampa med Rörelsesensor | Belysning | Exakt modell, batteri/laddning, elektrisk säkerhet, sensor, bildlicens |
| NV-INN-18 | Lager Minimalistisk Magasinhållare | Inredning | Exakt modell, material, mått, läderursprung, bildlicens |
| NV-KOK-19 | Strata Digital Kökshushållsvåg | Kök | Exakt modell, kapacitet/noggrannhet, material, batteri, bildlicens |
| NV-SMA-20 | Nimbus Luftrenare för Mindre Rum | Smart hem | CADR och rumsstorlek, HEPA-teststandard, filterkostnad/tillgång, el/CE, bildlicens |

## Obligatoriskt leverantörsunderlag per produkt

- Juridiskt företagsnamn, adress och kontaktperson.
- Exakt leverantörslänk och tillverkarens modellnummer/SKU.
- Inköpspris, valuta, moms/importvillkor och fraktkostnad till Sverige.
- Bekräftad leveranstid till Sverige, spårning, lagerstatus och uppdateringsfrekvens.
- Returadress, reklamationsprocess, defektrutin och vem som betalar returfrakt.
- Produktbilder med skriftlig användningsrätt.
- Tillverkar-/EU-ansvarig-uppgifter, säkerhetsvarningar och relevanta försäkringar/försäkran om överensstämmelse.
- Provexemplar kontrollerat innan försäljning.
- Beräknad täckningsmarginal efter produkt, frakt, betalavgift, moms, returer och marknadsföring.

## Leverantörsspår – ej godkända eller avtalade

- **ScaleOrder Sverige:** deras webbplats uppger betalning per order utan månadsavgift/startkostnad och erbjuder sourcing. Nästa steg är att begära skriftlig offert för exakta produkter, frakt till Sverige, returer, moms/import, produktdokumentation och provexemplar. Inget avtal eller konto är skapat.
- **Syncee:** gratisnivån tillåter främst att bläddra bland produkter; import och löpande hantering kräver betald plan enligt deras prisinformation. Därför passar det inte nuvarande krav på inga månadskostnader.
- **GALLAY:** uppger dropshipping utan månads-/medlemsavgift men är främst smyckesgrossist, inte en verifierad källa för den nuvarande hemkollektionen.

Källor:
- https://www.scaleorder.se/
- https://help.syncee.com/en/articles/8885830-pricing-and-plans
- https://www.gallay.eu/

## Beslut

Behåll samtliga 20 produkter som `active=false`. Byt inte till aktiva produkter förrän dokumentationen ovan är verifierad. Produktnamn och priser i demon är inte bevis på en verklig leverantörsprodukt eller lönsamhet.
