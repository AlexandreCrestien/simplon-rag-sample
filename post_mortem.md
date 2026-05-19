# Post-mortem — Augmentation de la facture LLM


**Date** : 2026-05-18  
**Durée** : 45 minutes (de la détection à la résolution)  
**Sévérité** : SEV-1 (Impact financier direct et dégradation majeure des performances de l'application)  
**Impact** : 100 % des utilisateurs actifs (latence, détérioration de la pertinence des réponses), doublement instantané des coûts de l'API Mistral.


## Timeline (UTC)
- 13:50 : Signalements des utilisateurs (latence et réponses non pertinentes) et du service facturation (facture Mistral excessive).

- 14:05 : Déclenchement de l'alerte automatique Prometheus HighLatencyMessages sur le canal Discord #alerts-prod (latence P95 > 5s pendant plus de 2 minutes).

- 14:10 : Prise en charge par l'équipe DevOps. Analyse du dashboard Grafana : mise en évidence d'un pic sur les transitions evaluate -> rewrite et d'une explosion de la métrique RAG_RETRIEVED_CHUNKS.

- 14:20 : Inspection du code source du nœud evaluate : identification de l'absence de la condition de garde sur la variable retry_count.

- 14:25 : Injection du correctif de sécurité anti-boucle et redéploiement de l'API.

- 14:30 : Validation sur Grafana (la latence chute sous les 2s) et fermeture automatique de l'alerte sur Discord (RESOLVED).


## Détection (alerte auto / signalement)
Signalement de l'entreprise (facturation), signalement des utilisateurs et alertes Discord pour la latence

## Root cause technique (sans blâmer une personne)
Bug dans le noeud d'évaluation (evaluate) du workflow de l'agent. La limite des tentatives du réécriture de la requête utilisateur (retry_count limité à 2) n'était jamais appliquée. Dans le cas d'une question complexe ou d'une réponse jugée imparfaite, l'agent entrait dans une boucle de réécriture (rewrite) infinie, ce qui provoquait de la latence et faisait exploser la facture du LLM.

## Ce qui a bien / mal fonctionné
- La stack d'observabilité (Prometheus + Alertmanager + Discord) a rapidement remonté l'anomalie de latence
- Le dashboard Grafana a permis d'isoler immédiatement le nœud en cause (evaluate / rewrite)
- Pas d'alerte sur le volume de tokens consommés ou sur le coût en temps réel de l'API Mistral

## Actions correctives (owners + dates)
  - [x] Mitigation — @devops — 2026-05-18 : Ajout de la condition 'if retry_count >= 2' pour casser la boucle infinie.

  - [ ] Détection — @devops — 2026-05-20 : Mettre en place une alerte Prometheus basée sur le compteur RAG_AGENT_DECISIONS pour être notifié sur Discord si le pattern rewrite dépasse un ratio anormal par minute.

  - [ ] Prévention — @lead_dev — 2026-05-22 : Écriture d'un test d'intégration pour valider le comportement de l'agent en cas de documents non pertinents (mocking du score à 4.0 pour valider l'arrêt après les retries).

  - [ ] Résilience — @finops — 2026-05-30: Mettre en place un système de budget quotidien (Daily Budget Cap) sur le dashboard de l'API Mistral pour bloquer ou alerter en cas de surconsommation soudaine de tokens.