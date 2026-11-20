# Pregătire pentru interviu

Întrebări despre proiect și răspunsurile mele, adăugate pe măsură ce proiectul avansează.
La final e un glosar cu termenii folosiți.

## Prezentarea proiectului în 30 de secunde

FinDoc Assistant răspunde la întrebări despre rapoartele anuale ale unor companii listate la
Bursa de Valori București (Banca Transilvania, Hidroelectrica, MedLife), citând pagina din care
provine fiecare informație. Folosește tehnica RAG: caută fragmentele relevante după sens, cu
embeddings și pgvector, iar un LLM formulează răspunsul doar pe baza lor. Codul a fost generat
cu un asistent AI; eu am luat deciziile de arhitectură, am făcut review la fiecare pull request,
am verificat comportamentul prin experimente și am scris setul de întrebări de evaluare.

## PR 1 – Scheletul

### De ce două endpoint-uri de sănătate, `/health` și `/health/ready`?

`/health` verifică doar că aplicația rulează. Dacă nu răspunde, aplicația e blocată și e
repornită. `/health/ready` verifică și baza de date; dacă baza nu răspunde, întoarce 503,
iar aplicația nu mai primește utilizatori până își revine baza, dar nu e repornită. Dacă aș
avea doar un endpoint legat de baza de date, o cădere temporară a bazei ar face ca aplicația
să fie repornită în buclă, fără motiv, pentru că repornirea ei nu repară baza de date.
Când baza revine, următoarea verificare reușește și aplicația primește iar trafic, automat.

### De ce PostgreSQL cu pgvector și nu o bază de date vectorială dedicată?

La volumul meu (aproximativ 6.100 de fragmente), pgvector e suficient de rapid și am un singur
sistem de administrat. Vectorul stă pe același rând cu textul, pagina, compania și anul, deci
pot combina căutarea după sens cu filtre SQL („doar Hidroelectrica, doar 2025") într-o singură
interogare, iar datele se scriu împreună, într-o singură tranzacție. O bază vectorială dedicată
ar fi un sistem separat de întreținut și de ținut sincronizat: timp, bani și efort în plus fără
un câștig în acest context. Aș reconsidera la milioane de vectori sau dacă latența căutării ar
deveni o problemă măsurată.

### Ce este RAG?

RAG (Retrieval-Augmented Generation) e o tehnică prin care un LLM răspunde pe baza documentelor
mele, nu doar pe baza a ce a învățat la antrenare. O singură dată, împart rapoartele PDF în
fragmente, le transform în vectori cu Voyage și îi salvez în PostgreSQL cu pgvector. La fiecare
întrebare, Voyage transformă întrebarea într-un vector, pgvector găsește fragmentele cu vectorii
cei mai apropiați, adică cu sensul cel mai apropiat, iar aplicația trimite textul lor la LLM,
împreună cu întrebarea și cu instrucțiunea să răspundă doar din ele, să citeze pagina și să spună
că nu știe dacă informația lipsește. Așa evit halucinațiile, iar răspunsul poate fi verificat.

### Unde se folosește RAG și unde nu?

Când un LLM trebuie să răspundă din informații pe care nu le cunoaște: documente private,
recente sau foarte specifice (proceduri interne ale unei bănci, contracte, documentație de
produs, ghiduri medicale), mai ales când răspunsul trebuie să aibă o sursă verificabilă. Nu e
potrivit pentru cunoștințe generale, pentru analiza unui document întreg (RAG aduce doar câteva
fragmente) sau pentru calcule pe date tabelare, unde SQL pe date structurate e mai bun.

## Glosar

| Termen | Pe scurt |
|--------|----------|
| API | Program care primește cereri prin HTTP și trimite răspunsuri, de obicei în JSON. |
| FastAPI | Framework Python pentru API-uri; generează automat documentația interactivă de la `/docs`. |
| Cod HTTP 200 / 500 / 503 | 200 = totul e în regulă; 500 = eroare în aplicație (bug); 503 = aplicația funcționează, dar nu poate servi cereri acum. |
| Liveness / readiness | „Ești în viață?" (dacă nu → repornire) / „Poți primi cereri?" (dacă nu → fără trafic, fără repornire). |
| Container / imagine | Imaginea e „rețeta" unui pachet izolat cu aplicația și tot ce îi trebuie; containerul e imaginea pornită. |
| Docker Compose | Pornește mai multe containere împreună, după `docker-compose.yml`. |
| Variabile de mediu, `.env` | Configurare ținută în afara codului (adrese, parole, chei API); `.env` nu se urcă pe GitHub. |
| CI (Continuous Integration) | Verificări automate (lint, teste, pornirea aplicației) la fiecare pull request. |
| Mocking / izolarea dependențelor | În teste, înlocuiești o piesă reală (baza de date, un API) cu una simulată. |
| ADR | Architecture Decision Record: document scurt cu contextul, decizia, alternativele și consecințele. |
| PostgreSQL | Bază de date relațională: tabele cu rânduri și coloane, interogate cu SQL. |
| Extensie PostgreSQL | Modul care adaugă funcții noi în PostgreSQL, instalat cu `CREATE EXTENSION`. |
| Tranzacție | Un grup de operații care reușesc toate sau nu se aplică niciuna. |
| Migrare | Fișier SQL numerotat care modifică structura bazei de date; aplicat o singură dată, în ordine. |
| Fragment (chunk) | Bucată de text de cel mult 200 de cuvinte, dintr-o singură pagină, cu documentul și pagina ei. |
| Suprapunere (overlap) | Ultimele propoziții dintr-un fragment se repetă la începutul următorului, ca să nu se piardă contextul. |
| Idempotent | O operație care, repetată, are același efect ca o singură execuție (ingestia unui fișier neschimbat nu modifică nimic). |
| Token | Bucată de cuvânt cu care lucrează modelele; după tokeni se calculează costul și limitele. |
| Vector | Listă ordonată de numere; la noi, 1024 de numere. |
| Embedding | Vectorul care reprezintă sensul unui text, ca o adresă pe o „hartă a sensurilor": texte cu sens apropiat au vectori apropiați. Un fragment → un vector. |
| Model de embeddings | Rețea neuronală antrenată pe perechi de texte potrivite și nepotrivite ca să producă embeddings (la noi, Voyage `voyage-4`). |
| Similaritate cosinus | Cât de mult arată doi vectori în aceeași direcție: 1 = sens foarte apropiat, 0 = fără legătură. |
| Top-k | Primele k rezultate după scor, de exemplu cele mai apropiate 5 fragmente. |
| pgvector | Extensie PostgreSQL care adaugă coloane de tip vector, operatori de distanță (`<=>`) și indexuri pentru căutare după similaritate. |
| Bază de date vectorială dedicată | Sistem construit doar pentru vectori (Qdrant, Pinecone, Weaviate); merită la volume foarte mari. |
| LLM | Large Language Model: model care generează text (de exemplu ChatGPT, Gemini, Llama). |
| Halucinație | Răspuns inventat de un LLM, spus cu siguranță. |
| RAG | Retrieval-Augmented Generation: întâi cauți fragmentele relevante, apoi LLM-ul răspunde pe baza lor. |
| Fereastra de context | Cât text poate lua în calcul un LLM într-un singur apel. |
| Strat, atenție, parametri | Interiorul unei rețele neuronale: straturi succesive în care fiecare token își ajustează sensul după ceilalți (atenție), folosind miliarde de numere fixate la antrenare (parametri). |
| Coborâre pe gradient | Metoda de antrenare: parametrii sunt ajustați puțin, de foarte multe ori, în direcția care reduce greșeala. |
| Rate limit (limită de cereri) | Câte cereri sau câți tokeni ai voie să trimiți unui API pe minut; peste limită primești HTTP 429. |
| Backoff exponențial cu jitter | După o eroare temporară aștepți tot mai mult (1 s, 2 s, 4 s…), plus o întârziere aleatorie, ca mulți clienți să nu reîncerce simultan. |
| Rotirea cheii API | Creezi o cheie nouă, o pui în configurare și o revoci pe cea veche. |
