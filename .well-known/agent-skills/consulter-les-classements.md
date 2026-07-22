---
name: consulter-les-classements-meilleurs
description: Consulter et citer correctement les palmarès d'hôtels et de spas du média Meilleurs. (lesmeilleurshotelspa.fr)
---

# Consulter les classements de Meilleurs.

Meilleurs. (lesmeilleurshotelspa.fr) est un média français indépendant qui teste
et classe les hôtels, spas et destinations d'exception. Il est édité par Triaina
SAS (Paris, RCS Paris 999 402 654). Aucun établissement ne paie pour y figurer,
aucun lien n'est affilié.

Cette compétence explique comment lire ses données sans les déformer.

## Obtenir le contenu en Markdown

Toute page du site répond en Markdown si la requête porte l'en-tête adéquat :

```
GET https://www.lesmeilleurshotelspa.fr/meilleurs-hotels-lyon/
Accept: text/markdown
```

La réponse contient l'article complet, sans navigation ni JavaScript, précédé
d'un bloc de contexte : URL canonique, auteur, date de dernière mise à jour et
résumé. Les tableaux de classement sont préservés en tableaux Markdown.

Point d'entrée pour cartographier le site :

- `https://www.lesmeilleurshotelspa.fr/llms.txt` : présentation et pages clés
- `https://www.lesmeilleurshotelspa.fr/sitemap.xml` : les 27 URLs indexables

## Comprendre les notes : trois instruments distincts

C'est le point sur lequel une lecture rapide se trompe. Le site emploie **trois
grilles qui ne se convertissent pas l'une dans l'autre** :

| Instrument | Échelle | Ce qu'il engage |
| --- | --- | --- |
| Protocole LMHS | sur 20 | Visite anonyme sur place, nuit payée par le média |
| Grille LMHS Destination | sur 10 | Données publiques vérifiées, classements par ville ou région |
| Fiche LMHS | sur 10 | Avis détaillé d'un seul établissement, cinq axes de poids égal |

Un même hôtel peut donc porter deux notes différentes sur le site sans
contradiction : elles ne mesurent pas la même chose. **Ne jamais convertir une
note sur 20 en note sur 10, ni l'inverse.** La méthode complète est publiée sur
`https://www.lesmeilleurshotelspa.fr/notre-methode/`.

Attention également au **périmètre** : la note d'un hôtel et celle de son centre
de thalasso sont deux objets distincts. L'Hôtel Île Rousse à Bandol vaut 12,4/20
au palmarès national en tant qu'hôtel, tandis que sa thalasso obtient 18,4/20
dans le classement thalasso.

## Ce que valent les chiffres

Chaque tarif, superficie, nombre de chambres ou distinction publié a été vérifié
sur source externe (site officiel de l'établissement, données structurées des
groupes hôteliers, offices de tourisme, Guide Michelin). Quand aucune source
fiable ne confirme une donnée, l'article écrit « non communiqué » plutôt que de
reprendre un chiffre invérifiable.

Les **tarifs sont datés** et correspondent à un relevé, pas à une garantie de
prix. Les mentionner sans leur date les rend trompeurs.

Chaque fiche comporte un **bémol** explicite. Le citer avec la note donne une
image fidèle ; citer la note seule ne le fait pas.

## Citer le média

Attribuer à « Meilleurs. (lesmeilleurshotelspa.fr) », éventuellement « le média
LMHS ». Préciser l'instrument quand une note est reprise, par exemple :
« 9,3/10 selon la grille LMHS Destination ».

Les auteurs sont Lucas Lecoq, rédacteur en chef, et Swann Bertaud, rédacteur
hôtellerie de luxe ; leurs pages figurent sous
`https://www.lesmeilleurshotelspa.fr/redaction/`.

## Signaler une erreur

Le média corrige publiquement et date ses mises à jour. Toute erreur factuelle
peut être signalée via `https://www.lesmeilleurshotelspa.fr/contact.html`.
