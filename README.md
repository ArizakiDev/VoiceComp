# VoiceComp - Application de Comparaison de Parole

VoiceComp est une application desktop qui permet d'enregistrer votre voix et de comparer votre prononciation avec un texte de référence. Idéale pour l'apprentissage des langues ou pour améliorer vos compétences en élocution.

![Screenshot de l'application](https://imgur.com/Pokxw6L.png)

## Fonctionnalités

- **Mode Comparaison** : Écrivez un texte et enregistrez-vous en train de le lire. L'application compare ensuite votre prononciation avec le texte original.
- **Mode Enregistrement** : Enregistrez simplement votre voix pour une utilisation ultérieure.
- **Visualisation audio** : Visualisez votre niveau sonore en temps réel pendant l'enregistrement.
- **Choix du microphone** : Sélectionnez parmi les périphériques d'entrée disponibles.
- **Thèmes personnalisables** : Choisissez entre un thème clair, sombre ou automatique (basé sur l'heure de la journée).
- **Gestion des enregistrements** : Écoutez et supprimez facilement vos enregistrements.

## Prérequis

- Python 3.6 ou supérieur
- Bibliothèques requises listées dans `requirements.txt`

## Installation

1. Clonez le repository:
```bash
git clone https://github.com/ArizakiDev/voicecomp.git
cd voicecomp
```

2. Créez un environnement virtuel (non-recommandé):
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installez les dépendances:
```bash
pip install -r requirements.txt
```

## Utilisation

Lancez l'application:
```bash
python main.py
```

### Mode Comparaison
1. Saisissez le texte que vous souhaitez prononcer dans la zone de texte
2. Cliquez sur "Commencer l'enregistrement" et lisez le texte à voix haute
3. Cliquez sur "Arrêter l'enregistrement" une fois terminé
4. Appuyez sur "Comparer le texte" pour voir les résultats

### Mode Enregistrement
1. Entrez un nom de fichier ou utilisez celui proposé par défaut
2. Cliquez sur "Commencer l'enregistrement"
3. Parlez dans votre microphone
4. Cliquez sur "Arrêter l'enregistrement" une fois terminé

### Paramètres
Accédez aux paramètres depuis le menu pour configurer:
- Le thème de l'application
- Le mode par défaut
- Le dossier d'archivage des enregistrements
- Le microphone à utiliser
- La taille de la visualisation audio

## Dépendances principales

- tkinter - Interface graphique
- sounddevice, pyaudio - Gestion de l'audio
- scipy, numpy - Traitement du signal
- matplotlib - Visualisation audio
- speech_recognition - Reconnaissance vocale

## Contribution

Arizaki - Développeur & Concepteur

## Licence

Ce projet est sous licence MIT.
