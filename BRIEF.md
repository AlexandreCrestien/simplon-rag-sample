# Brief Simplonline — Observabilité d'un Chatbot RAG

| Item | Détail |
|------|--------|
| Métier | Dev IA — Référentiel RNCP 2023 |
| Durée | 2 jours (J2 + J3 de la semaine) |
| Modalité | Binôme |
| Prérequis | Avoir suivi le J1 (Docker, CI/CD) |

---

## 📁 Brief projet

### 🏷️ Titre

> Observabilité d'une API et Frontend d'un agent RAG : instrumentaliser un chatbot RAG
> pour un centre de formation

*(94 / 100 caractères)*

### 📝 Description rapide

Vous reprenez un projet existant : une API FastAPI (LangGraph + Mistral + pgvector) qui
expose un chatbot RAG, et un frontend Streamlit qui consomme l'API. L'application est
livrée sans observabilité.

Votre mission : la rendre observable de bout en bout avec une stack complète
conteneurisée — logs JSON structurés, métriques Prometheus, dashboard Grafana, alertes
Alertmanager vers Discord pour la partie applicative ET RAG, tracing Langfuse self-hosted
pour la partie LLM (coût tokens Mistral, latence retrieval/generate/evaluate, qualité,
drift).

Vous serez évalués lors d'un **game day** qui simule des incidents applicatifs et des
dérapages LLM.

*(≈ 700 / 900 caractères)*

### 🎯 Compétences et niveaux

| Compétence | Intitulé | Niveau |
|-----------|----------|--------|
| C11 | Monitorer un modèle d'IA | Niveau 3 — Transposer |
| C20 | Surveiller une application d'IA | Niveau 3 — Transposer |
| C21 | Résoudre les incidents techniques | Niveau 2 — Adapter |

### 📖 Contexte

**Contexte professionnel** : vous êtes développeur·euse backend chez **Simplon**, un
centre de formation qui souhaite digitaliser la gestion de sa base documentaire
pédagogique (référentiels RNCP, supports de cours, FAQ apprenants, conditions d'admission,
etc.). Une équipe a livré il y a 6 semaines un **chatbot RAG** qui répond aux questions
des apprenants et de l'équipe administrative à partir de ce corpus.

Le projet est composé de deux services Python (un repo, mais déployés indépendamment) :

- **`api/`** — une API FastAPI qui expose 8 endpoints sous `/api/v1` :
  - `POST /documents/ingest-urls` + `POST /documents/ingest-pdf` — ingestion de PDF et
    de pages web (chunking + embeddings Mistral + stockage pgvector, dédoublonnage
    SHA-256)
  - `POST /conversations` + `POST /conversations/{id}/messages` +
    `GET /conversations/{id}/messages` — conversation persistée avec un agent LangGraph
    (`guard_route → retrieve → generate → evaluate → save_turn`), retries d'écriture,
    escalade si l'évaluateur n'est pas satisfait
  - `POST /eval/run` — déclenchement d'une évaluation Ragas (faithfulness,
    answer_relevancy, context_recall)
  - `GET /health` — healthcheck
- **`frontend/`** — une UI Streamlit qui crée des conversations et affiche les réponses +
  sources.

**Trafic actuel observé en pic** :

- `/conversations/{id}/messages` (chat) — environ **5 req/s**, latence variable selon
  retrieval + LLM
- `/documents/ingest-*` — pics ponctuels lors de l'ingestion d'un référentiel (50 PDF
  d'un coup)

Depuis quelques semaines, les retours se dégradent côté apprenants ET côté finance :

- *« Le chatbot répond moins bien qu'avant à mes questions sur les modalités de
  formation »* (apprenant)
- *« L'agent met parfois 8 secondes à répondre »* (équipe pédagogique)
- *« La facture Mistral a doublé ce mois-ci sans qu'on sache pourquoi »* (la direction)
- *« Une réponse a mentionné un référentiel d'une autre formation qui n'avait rien à voir
  avec la question »* (équipe support — risque de fuite par hallucination)

**Le problème** : personne dans l'équipe ne peut confirmer ces signaux. L'API renvoie
des 200 OK dans les logs FastAPI, mais on ne sait ni :

- combien de messages sont servis par minute, par endpoint ;
- quelle est la latence p50 / p95 / p99 ressentie côté client (par endpoint, par étape
  du graphe LangGraph) ;
- combien de tokens Mistral sont consommés, par conversation, pour quel coût ;
- où sont les 8 secondes : retrieval pgvector ? generate Mistral ? evaluate ?
  rewrite-loop qui boucle ?
- si les réponses de l'agent sont de bonne qualité (taux d'escalade, score d'évaluation,
  hallucinations) ;
- comment reconstituer le parcours d'une requête `/messages` quand un apprenant signale
  un problème.

Le CTO vous confie deux jours pour transformer cette application en système observable
de bout en bout, à la fois côté applicatif et côté LLM. Il exige une démonstration en
fin de J3 sous forme d'un **game day** où il injectera lui-même 3 à 4 incidents (dont
au moins 1 LLM-specific) pour vérifier que votre instrumentation les détecte et permet
de les diagnostiquer.

#### Stack imposée

**Stack applicative**

- Logs : sortie stdout en JSON (`python-json-logger`)
- Collecte logs : Loki (pour la corrélation logs ↔ métriques
  dans Grafana)
- Métriques : Prometheus + `prometheus-client` côté API (et frontend si pertinent)
- Dashboards : Grafana
- Alertes : Alertmanager + webhook Discord (canal dédié)

**Stack LLM observability**

- Tracing LLM : **Langfuse** self-hosted (à ajouter au `docker-compose.yml`)
- Coût et latence par span : Langfuse natif (intégration `langchain-langfuse`)
- Scoring qualité : Langfuse (user feedback + score d'évaluation du nœud `evaluate` du
  graphe LangGraph)
- Alerte coût : exporter le coût quotidien Langfuse vers Prometheus puis Alertmanager

**Stack conteneurisation**

- Tout le projet (API + frontend + Postgres/pgvector + Prometheus + Grafana +
  Alertmanager + Langfuse + Loki) doit être lancé par un **unique
  `docker compose up`**.
- Dockerfile écrit pour `api/` et `frontend/`.

#### Point de départ

Le repo de départ contient déjà :

- l'API FastAPI fonctionnelle (`api/`),
- le frontend Streamlit (`frontend/`),
- les migrations Alembic (`api/data/alembic/`),
- un `docker-compose.yml` partiel,
- un corpus de test (placez vos PDF dans `data/docs/`, vos URLs sources dans
  `data/evaluation/samples.json`).

Aucune instrumentation applicative n'est présente. À vous de la concevoir.

Une clé API Mistral partagée vous est remise avec un budget plafonné à **20 € par
binôme**. Vous pouvez basculer sur Ollama local si besoin (un modèle est pré-téléchargé
sur la machine du formateur).

> ⚠️ **RGPD et confidentialité** : les conversations peuvent contenir des informations
> sur des apprenants (nom, parcours, situation). Vos logs et vos traces Langfuse ne
> doivent **jamais** contenir le contenu brut d'une conversation ni d'identifiant
> directement nominatif. L'incident de « fuite par hallucination » évoqué plus haut doit
> nourrir votre vigilance : que stocker, que ne pas stocker ? Comment auditer une trace
> sans exposer la donnée brute ?

---

## 🧭 Modalités pédagogiques

### Organisation générale

- Travail en binôme
- Durée : 2 journées pleines (J2 + J3)
- Fork Obligatoire
- Peer programming : 1 personne derrière le clavier par étape et switch sur l'étape suivante
- Une branch par étape

### Phase 1 — Logs structurés *(J2 matin, ~2 h)*

Reprenez le repo de départ. Mettez en place :

- Un logging JSON structuré (vu en J1 avec `python-json-logger`) côté `api/` et
  `frontend/`
- Un middleware FastAPI qui génère un `request_id` (UUID v4) à l'entrée de chaque
  requête et le propage dans **tous** les logs
- Niveaux de log respectés : `INFO` pour les événements applicatifs nominaux, `WARNING`
  pour les retries de l'agent, `ERROR` pour les exceptions, `DEBUG` réservé au dev
- Pas de log de contenu brut de conversation ni de PII

**Questions guidantes**

- Quels champs structurés dans chaque log pour reconstituer une session ? (`request_id`,
  `conversation_id`, `node`, `latency_ms`...)
- Comment garantir aucune PII / aucun contenu utilisateur ?

### Phase 2 — Métriques applicatives + Prometheus *(J2 après-midi, ~3 h)*

- Métriques HTTP RED (Request rate, Errors, Duration) sur chaque endpoint, avec
  différenciation `/messages` / `/documents/ingest-*` / `/eval/run` / `/health`
- Buckets d'histogramme adaptés (rapide pour `/health`, plus large pour `/messages` qui
  inclut LLM)
- Métriques métier RAG :
  - distribution des décisions de l'agent (`guard_route` : `in_scope` / `out_of_scope`)
  - taux d'escalade
  - (en option) distribution du score d'évaluation (nœud `evaluate`)
  - (en option) nombre moyen de chunks retrouvés par requête
  - (en option) latence par nœud du graphe (`generate`, `retrieve`, etc.)
- Endpoint `/metrics` exposé sur l'API, scrappé par Prometheus
- Démarrer Prometheus dans le `docker-compose.yml`

**Questions guidantes**

- Quels labels sans exploser la cardinalité ? (éviter `conversation_id` en label)
- Si le modèle se met à escalader 30 % des requêtes, votre instrumentation le voit-elle ?
- Comment représenter la latence par nœud du graphe ?

### Phase 3 — Dashboard Grafana + alertes Discord *(J3 matin, ~2 h 30)*

- Lancer Grafana via le `docker-compose.yml` (datasource Prometheus
  auto-provisionnée)
- Construire un dashboard **« Simplon RAG Overview »** provisionné automatiquement,
  comprenant :
  - panels RED par endpoint (requêtes/s, erreurs %, latence p50/p95/p99)
  - panel *agent* : taux d'escalade, distribution score d'évaluation, retries
  - (en option) panel *ingestion* : volume de documents ingérés, chunks créés
- ajouter **Loki** au compose et configurer Grafana pour
  corréler logs ↔ métriques via `request_id`
- Configurer Alertmanager + webhook Discord
- **Au minimum 2 alertes** définies + runbooks :
  - latence p95 trop haute sur `/messages`
  - taux d'erreur 5xx élevé

**Questions guidantes**

- Si la latence p99 explose mais pas la p50, votre dashboard distingue-t-il les deux ?
- Vos alertes sont-elles sur des symptômes (latence ressentie) ou des causes (CPU) ?
- Quelle sévérité pour quelle alerte ? Discord canal `#alerts-prod` vs `#alerts-info` ?

### Phase 4 — Langfuse *(J3 matin, ~2 h)*

- Ajouter Langfuse self-hosted (image Docker + Postgres dédié) au `docker-compose.yml`
- `request_id` (UUID v4) propagé dans **toutes** les traces Langfuse d'une
  même requête (via `contextvars`)
- Instrumenter l'agent LangGraph avec le `CallbackHandler` Langfuse — chaque appel à
  `/messages` doit produire une trace avec **au moins les spans** suivants :
  `guard_route`, `retrieve`, `generate`, `evaluate`
- Champs à faire apparaître dans chaque trace :
  - `user_id_hash` (pseudonymisé)
  - `conversation_id`
  - `model` (`mistral-large-latest` / `mistral-small-latest`)
  - `request_id` (lien avec les logs Prometheus)
- (en option) **Coût** : exporter quotidiennement le coût total Langfuse vers une Gauge Prometheus
  (`llm_daily_cost_euros`) via un script ou un job cron dans le compose
- (en option)  **Qualité** : exposer un endpoint
  `POST /api/v1/conversations/{id}/messages/{msg_id}/feedback` qui permet de noter une
  réponse (👍/👎) et écrit le score dans Langfuse via `trace.score()`
- (en option) Ajouter une **3ᵉ alerte Discord** : dépassement du budget LLM journalier

**Questions guidantes**

- Comment logger les nœuds du graphe LangGraph (`guard_route`, `retrieve`, `generate`,
  `evaluate`) ?
- Quel niveau de détail logger dans les inputs Langfuse pour pouvoir diagnostiquer sans
  violer le RGPD ?
- Si demain le retrieval pgvector prend 3 s, comment l'identifier dans Langfuse ?
- Comment savoir quelle conversation consomme anormalement de tokens ?

### Phase 5 — Game day et post-mortem *(J3 après-midi, ~3 h)*

Le formateur incarne le rôle du CTO. Sans prévenir, 3 à 4 incidents sont injectés. Pour
chacun :

- 25 min pour détecter, diagnostiquer (logs + dashboards + traces Langfuse) et mitiger
- À la fin, choisissez **1 incident** et rédigez un post-mortem d'une page selon la
  trame de cours

Au moins **1 incident sera LLM-specific** (par exemple : un prompt cassé qui produit des
réponses incohérentes, ou la rewrite-loop de l'agent qui boucle et consomme 10× plus de
tokens). Vous devez le diagnostiquer dans Langfuse, pas dans Prometheus.

### Phase 6 — APM *(optionnel)*

Si vous avez le temps : ajouter un APM (OpenTelemetry → Tempo / Jaeger, ou Sentry) pour
le tracing distribué `frontend Streamlit → API FastAPI → DB pgvector → Mistral`.
Démontrer une trace de bout en bout en soutenance.

###  *(optionnel)* Soutenance *(J3 fin de journée, 15 min/binôme)*

- **10 min de démo** : faites vivre un incident applicatif et un incident LLM, montrez
  comment votre stack permet de les détecter et de les résoudre.
- **5 min de questions** du jury.

Travail attendu en autonomie **Niveau 3** sur C11 et C20, **Niveau 2** sur C21.
Documentez et justifiez vos choix d'outils dans le README (notamment : pourquoi Langfuse
et pas LangSmith / Phoenix / W&B / MLflow ?).

---

## 📊 Modalités d'évaluation

L'évaluation se fait en **2 volets complémentaires**.

### Volet 1 — Évaluation continue *(40 %)*

Le formateur passe sur chaque binôme à intervalles réguliers (matin et après-midi de
chaque journée). Il observe :

- la progression effective sur les phases
- la pertinence des choix techniques
- la capacité à expliquer pourquoi vous avez fait tel ou tel choix
- la qualité des commits (atomiques, messages clairs — Conventional Commits)

### Volet 2 — Soutenance et livrables *(60 %)*

- Démonstration en direct de 10 min, scénario libre — à vous de mettre en valeur votre
  travail
- Questions du jury (5 min) sur des choix techniques précis
- Évaluation de la complétude des livrables (cf. checklist correspondante)
- Évaluation du post-mortem rédigé

### Conditions de passage

- Le repo GitHub est **public** et accessible
- `docker compose up` démarre la stack complète sans erreur sur la machine du formateur
- Au moins **2 incidents sur 3 ou 4** du game day ont été détectés via vos alertes ou
  dashboards
- Le post-mortem couvre les **6 sections** de la trame fournie

Une compétence est validée si tous les critères de performance correspondants sont
remplis. Le détail figure dans la section **Critères de performance** ci-dessous.

---

## 📦 Livrables attendus

### Livrable principal — Repo GitHub PUBLIC

Structure du repo existant, complétée :

```text
simplon-rag-sample/
├── README.md                       (description, archi, lancement, choix techniques)
├── docker-compose.yml              (API + Frontend + Postgres/pgvector + Prometheus
│                                    + Grafana + Alertmanager + Langfuse + Loki(opt))
├── api/
│   ├── Dockerfile                  (NOUVEAU)
│   ├── pyproject.toml              (ajout : prometheus-client, python-json-logger,
│   │                                langfuse, langchain-langfuse)
│   ├── main.py                     (instrumentation request_id + /metrics)
│   ├── src/rag/
│   │   ├── observability/          (NOUVEAU dossier)
│   │   │   ├── logging.py          (config python-json-logger + middleware request_id)
│   │   │   ├── metrics.py          (définitions Prometheus : RED + RAG métier)
│   │   │   └── langfuse_handler.py (CallbackHandler Langfuse + helpers)
│   │   ├── api/
│   │   │   ├── app.py              (ajout middleware logs + /metrics)
│   │   │   └── routers/            (ajout endpoint feedback)
│   │   └── rag/agent/              (callback handler câblé sur le graphe LangGraph)
│   └── tests/
├── frontend/
│   ├── Dockerfile                  (NOUVEAU)
│   ├── pyproject.toml              (ajout : python-json-logger)
│   └── src/app/                    (logs structurés sur les appels API)
├── prometheus/
│   ├── prometheus.yml
│   └── rules.yml                   (règles d'alerte, dont alerte coût LLM)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/            (Prometheus + Loki si choisi)
│   │   └── dashboards/dashboards.yml
│   └── dashboards/
│       └── simplon-rag-overview.json
├── alertmanager/
│   └── alertmanager.yml            (webhook Discord)
├── langfuse/
│   └── README.md                   (procédure de bootstrap + clés à mettre en .env.example)
├── loki/                           (optionnel)
│   └── loki-config.yaml
├── jobs/
│   └── export_langfuse_cost.py     (script qui pousse le coût quotidien dans Prometheus)
├── runbooks/
│   ├── high-latency-messages.md
│   ├── high-error-rate.md
│   └── llm-budget-exceeded.md
└── post-mortem/
    └── incident-XXX.md
```

### Contenu obligatoire du README

- Description du projet (positionnement Simplon, finalité du chatbot)
- Architecture (FastAPI + LangGraph + Mistral + pgvector + Streamlit)
- Technologies utilisées (avec versions)
- Instructions d'installation et de lancement (`docker compose up` + procédure de
  bootstrap Langfuse)
- Schéma d'architecture (Mermaid ou image), incluant le flux d'observabilité
- Liste des métriques Prometheus exposées avec une phrase d'explication par métrique
- Liste des spans Langfuse créés sur l'agent LangGraph avec leur rôle
- Liste des alertes (≥ 2 + alerte coût LLM) avec leur logique
- Justification du choix Langfuse vs LangSmith / Phoenix / W&B / MLflow (1 paragraphe)
- Procédure pour générer du trafic de test (script `bench.py` à fournir)
- Auteur·rice·s

### Hors repo (à présenter en soutenance)

- Démo en direct de la stack en fonctionnement (un seul `docker compose up`)
- Démonstration d'au moins 1 incident applicatif et 1 incident LLM, diagnostiqués via
  Prometheus / Grafana **ET** Langfuse
- Réponses aux questions techniques du jury

---

## ✅ Critères de performance

### C11 — Monitorer un modèle d'IA *(Niveau 3)*

Couvre l'agent RAG ET le LLM.

- Au moins **3 métriques métier RAG** exposées (distribution `guard_route`, score
  d'évaluation moyen, taux d'escalade)
- Latence décomposée par nœud du graphe LangGraph (`retrieve`, `generate`, `evaluate`)
- Chaque appel `/messages` génère une trace Langfuse avec au moins **4 spans**
  (`guard_route`, `retrieve`, `generate`, `evaluate`)
- Coût (€) et tokens Mistral visibles dans Langfuse pour chaque appel
- Endpoint `/feedback` permettant d'écrire un score `trace.score()` dans Langfuse
- Cardinalité des labels Prometheus maîtrisée (**pas de `conversation_id` en label**)
- Dashboard Grafana rend visible une dérive (ex : taux d'escalade qui passe de 5 % à
  30 %) en **< 2 min**
- Conformité RGPD : aucun contenu de conversation brut ni PII dans logs / métriques /
  traces (pseudonymisation `user_id_hash`)
- Justification écrite du choix Langfuse vs alternatives (LangSmith, Phoenix, W&B,
  MLflow)

### C20 — Surveiller une application d'IA *(Niveau 3)*

- Logging JSON structuré sur stdout (API + frontend)
- `request_id` propagé dans tous les logs **ET** dans les métadonnées Langfuse
- Métriques HTTP RED instrumentées avec différenciation des endpoints
- Endpoint `/metrics` scrappé par Prometheus
- Stack complète déployable via **un unique `docker compose up`** (API + Frontend +
  Postgres + Prometheus + Grafana + Alertmanager + Langfuse)
- Dockerfile fourni pour `api/` et `frontend/`
- Dashboard Grafana provisionné automatiquement
- Au moins 2 alertes définies sur Discord + 1 alerte budget LLM (**= 3 alertes
  minimum**)
- Chaque alerte est associée à un **runbook**

### C21 — Résoudre les incidents *(Niveau 2)*

- Au moins 2 des 3-4 incidents du game day sont détectés via le système (dont
  l'incident LLM)
- L'incident LLM est diagnostiqué en consultant les traces Langfuse (preuve visuelle en
  soutenance)
- Démarche documentée dans le post-mortem (timeline)
- Trame respectée : résumé, timeline, détection, root cause, ce qui a / n'a pas
  fonctionné, actions
- Post-mortem **blameless**
- Au moins 2 actions correctives avec owner et échéance

---

## 🔗 Ressources suggérées

### Repo

- [Repo starter Simplon RAG](https://github.com/) — ce repo (`simplon-rag-sample`)

### Observabilité applicative

- [Documentation Prometheus](https://prometheus.io/docs/introduction/overview/)
- [Documentation Grafana](https://grafana.com/docs/grafana/latest/)
- [Client Python Prometheus](https://github.com/prometheus/client_python)
- [Méthode RED (Grafana Labs)](https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/)
- [SRE Book — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Trame de post-mortem (PagerDuty)](https://postmortems.pagerduty.com/)
- [Loki — logs Grafana](https://grafana.com/docs/loki/latest/)
- [OpenTelemetry Python (APM optionnel)](https://opentelemetry.io/docs/languages/python/)

### Observabilité LLM

- [Langfuse — documentation](https://langfuse.com/docs)
- [Langfuse — self-host](https://langfuse.com/docs/deployment/self-host)
- [Langfuse — intégration LangChain/LangGraph](https://langfuse.com/docs/integrations/langchain/python)
- [LangSmith — comparatif](https://docs.smith.langchain.com/)
- [Phoenix — Arize, comparatif](https://docs.arize.com/phoenix)
- [W&B Weave — comparatif](https://wandb.ai/site/weave)
- [MLflow Tracking — comparatif](https://mlflow.org/docs/latest/tracking.html)

### LLM provider

- [Mistral API Pricing](https://mistral.ai/products/la-plateforme#pricing)
