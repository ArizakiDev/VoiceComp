import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import sounddevice as sd
import numpy as np
import threading
import os
import tempfile
import wave
from scipy.io import wavfile
import speech_recognition as sr
from difflib import SequenceMatcher
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import pyaudio
import subprocess
import sys
import json
from datetime import datetime

class SpeechComparisonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Application de Comparaison de Parole by Arizaki")
        self.root.geometry("800x700")
        
        self.load_settings()
        
        # Appliquer le thème
        self.apply_theme()

        self.comparison_frame = None
        self.recording_frame = None
        self.settings_frame = None
        
        # Style
        self.style = ttk.Style()
        self.update_style()

        self.recognizer = sr.Recognizer()
        self.audio_file = None
        self.recording = False
        self.duration = 5
        self.audio_data = []
        self.ani = None
        self.monitoring = False
        
        p = pyaudio.PyAudio()
        self.mic_devices = [(i, p.get_device_info_by_index(i)['name']) 
                           for i in range(p.get_device_count()) 
                           if p.get_device_info_by_index(i).get('maxInputChannels') > 0]
        p.terminate()
        
        self.create_menu()
        
        self.switch_to_mode(self.settings["app_mode"])
        
    def get_selected_mic_index(self):
        """Retourne l'indice du microphone sélectionné"""
        if hasattr(self, 'mic_var') and self.mic_var.get():
            selected_name = self.mic_var.get()
            for device in self.mic_devices:
                if device[1] == selected_name:
                    return device[0]
        
        return self.settings["selected_mic"]
        
    def update_audio_plot(self, frame):
        """Met à jour la visualisation audio"""
        if (self.recording or self.monitoring) and self.audio_data:
            data = self.audio_data[-100:] if len(self.audio_data) > 100 else self.audio_data
            self.line.set_data(range(len(data)), data)
            self.ax.set_xlim(0, len(data))
        return self.line,
        
    def test_microphone(self):
        """Teste le microphone sélectionné"""
        if not self.monitoring:
            self.monitoring = True
            self.audio_data = []
            self.ani = animation.FuncAnimation(
                self.fig, self.update_audio_plot, interval=30, blit=True, cache_frame_data=False)
            self.canvas.draw()
            threading.Thread(target=self.monitor_audio).start()
            self.status_var.set("Test du microphone en cours...")
        else:
            self.monitoring = False
            self.status_var.set("Test du microphone arrêté")
            
    def monitor_audio(self):
        """Surveille l'entrée audio pour le test de microphone"""
        mic_index = self.get_selected_mic_index()
        sample_rate = 44100
        
        def callback(indata, frames, time, status):
            if status:
                print(status)
            self.audio_data.extend(indata[:, 0])
            
        with sd.InputStream(device=mic_index, channels=1, callback=callback,
                          samplerate=sample_rate):
            while self.monitoring:
                sd.sleep(100)
        
    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.record_button.config(text="Arrêter l'enregistrement")
            self.duration = self.duration_var.get()
            self.audio_data = []
            
            self.ani = animation.FuncAnimation(
                self.fig, self.update_audio_plot, interval=30, blit=True, cache_frame_data=False)
            self.canvas.draw()
            
            threading.Thread(target=self.record_audio_to_file).start()
        else:
            self.recording = False
            self.record_button.config(text="Commencer l'enregistrement")
            
    def record_audio_to_file(self):
        """Enregistre l'audio dans un fichier WAV"""
        self.status_var.set("Préparation de l'enregistrement...")
        sample_rate = 44100  # Hz
        mic_index = self.get_selected_mic_index()
        
        for i in range(3, 0, -1):
            self.status_var.set(f"L'enregistrement commence dans {i}...")
            self.root.update()
            self.root.after(1000)
            
        self.status_var.set("Enregistrement en cours...")
        
        filename = self.filename_var.get() if hasattr(self, 'filename_var') else f"Enregistrement_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not filename.endswith('.wav'):
            filename += '.wav'
            
        filepath = os.path.join(self.settings["audio_dir"], filename)
        
        counter = 1
        base_name, ext = os.path.splitext(filepath)
        while os.path.exists(filepath):
            filepath = f"{base_name}_{counter}{ext}"
            counter += 1
        
        def callback(indata, frames, time, status):
            if status:
                print(status)
            self.audio_data.extend(indata[:, 0])
        
        with sd.InputStream(device=mic_index, channels=1, callback=callback,
                          samplerate=sample_rate):
            while self.recording:
                self.status_var.set(f"Enregistrement en cours... Durée: {len(self.audio_data)/sample_rate:.1f}s")
                self.root.update()
                sd.sleep(100)
        
        if len(self.audio_data) > 0:
            audio_array = np.array(self.audio_data)
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes((audio_array * 32767).astype(np.int16).tobytes())
            
            self.audio_file = filepath
            messagebox.showinfo("Enregistrement", f"Enregistrement terminé avec succès.\nSauvegardé sous: {os.path.basename(filepath)}")
            
            if self.settings["app_mode"] == "recording":
                self.refresh_recordings_list()
                
            if hasattr(self, 'filename_var'):
                self.filename_var.set(f"Enregistrement_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        else:
            messagebox.showwarning("Avertissement", "Aucune donnée audio enregistrée.")
        
        self.recording = False
        self.record_button.config(text="Commencer l'enregistrement")
        self.status_var.set("Enregistrement terminé")
        
    def compare_text(self):
        """Compare le texte écrit avec le texte parlé"""
        if self.audio_file is None:
            messagebox.showwarning("Attention", "Aucun audio enregistré.")
            return
            
        try:
            self.status_var.set("Analyse de l'audio...")
            
            with sr.AudioFile(self.audio_file) as source:
                audio_data = self.recognizer.record(source)
                
            text = self.recognizer.recognize_google(audio_data, language="fr-FR")
            
            written_text = self.text_area.get(1.0, tk.END).strip()
            
            self.result_area.delete(1.0, tk.END)
            self.result_area.insert(tk.INSERT, f"Texte prononcé: {text}\n\n")
            self.result_area.insert(tk.INSERT, "Comparaison:\n")
            
            self.highlight_differences(written_text, text)
            
            similarity = SequenceMatcher(None, written_text.lower(), text.lower()).ratio()
            score = int(similarity * 100)
            
            self.result_area.insert(tk.END, f"\n\nScore de similarité: {score}%")
            
            self.status_var.set(f"Comparaison terminée. Score: {score}%")
            
        except sr.UnknownValueError:
            messagebox.showerror("Erreur", "Impossible de comprendre l'audio")
            self.status_var.set("Erreur: Audio incompréhensible")
        except sr.RequestError as e:
            messagebox.showerror("Erreur", f"Erreur de service de reconnaissance vocale; {e}")
            self.status_var.set("Erreur de service")
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur s'est produite: {e}")
            self.status_var.set("Erreur lors de la comparaison")
            
    def highlight_differences(self, written_text, spoken_text):
        """Met en évidence les différences entre les textes"""
        if self.settings["theme"] == "light" or (self.settings["theme"] == "auto" and 6 <= datetime.now().hour < 20):
            self.result_area.tag_configure("correct", foreground="green", font=("Arial", 11, "bold"))
            self.result_area.tag_configure("incorrect", foreground="red", font=("Arial", 11, "bold"))
            self.result_area.tag_configure("missing", foreground="blue", font=("Arial", 11, "italic"))
        else:
            self.result_area.tag_configure("correct", foreground="#00ff00", font=("Arial", 11, "bold"))
            self.result_area.tag_configure("incorrect", foreground="#ff6666", font=("Arial", 11, "bold"))
            self.result_area.tag_configure("missing", foreground="#66b3ff", font=("Arial", 11, "italic"))
        
        written_words = written_text.lower().split()
        spoken_words = spoken_text.lower().split()
        
        for word in written_words:
            if word in spoken_words:
                self.result_area.insert(tk.END, word + " ", "correct")
                spoken_words.remove(word)
            else:
                self.result_area.insert(tk.END, word + " ", "incorrect")
                
        if spoken_words:
            self.result_area.insert(tk.END, "\n\nMots supplémentaires détectés: ", "missing")
            for word in spoken_words:
                self.result_area.insert(tk.END, word + " ", "missing")

    def load_settings(self):
        """Charge les paramètres ou crée le fichier s'il n'existe pas"""
        default_settings = {
            "theme": "light",
            "audio_dir": os.path.join(os.path.expanduser("~"), "Documents", "AudioRecordings"),
            "app_mode": "comparison",
            "selected_mic": 0,
            "visualizer_size": "small"
        }
        
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
            else:
                self.settings = default_settings
                os.makedirs(self.settings["audio_dir"], exist_ok=True)
                self.save_settings()
        except Exception as e:
            print(f"Erreur lors du chargement des paramètres: {e}")
            self.settings = default_settings
            
    def save_settings(self):
        """Sauvegarde les paramètres dans un fichier JSON"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des paramètres: {e}")
            
    def apply_theme(self):
        """Applique le thème selon les paramètres"""
        if self.settings["theme"] == "light":
            self.bg_color = "#f0f0f0"
            self.fg_color = "#333333"
            self.secondary_fg = "#555555"
            self.text_bg = "white"
        elif self.settings["theme"] == "dark":
            self.bg_color = "#2d2d2d"
            self.fg_color = "#ffffff"
            self.secondary_fg = "#bbbbbb"
            self.text_bg = "#3d3d3d"
        elif self.settings["theme"] == "auto":
            hour = datetime.now().hour
            if 6 <= hour < 20:
                self.bg_color = "#f0f0f0"
                self.fg_color = "#333333"
                self.secondary_fg = "#555555"
                self.text_bg = "white"
            else:
                self.bg_color = "#2d2d2d"
                self.fg_color = "#ffffff"
                self.secondary_fg = "#bbbbbb"
                self.text_bg = "#3d3d3d"
        
        self.root.configure(bg=self.bg_color)
        
    def update_style(self):
        """Met à jour les styles selon le thème actuel"""
        self.style.configure("TButton", font=("Arial", 10, "bold"), padding=10)
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        self.style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color)
        self.style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.fg_color)
        
    def create_menu(self):
        """Crée la barre de menu de l'application"""
        menubar = tk.Menu(self.root)
        
        mode_menu = tk.Menu(menubar, tearoff=0)
        mode_menu.add_command(label="Mode Comparaison", command=lambda: self.switch_to_mode("comparison"))
        mode_menu.add_command(label="Mode Enregistrement", command=lambda: self.switch_to_mode("recording"))
        menubar.add_cascade(label="Mode", menu=mode_menu)
        
        menubar.add_command(label="Paramètres", command=self.open_settings)
        
        self.root.config(menu=menubar)
        
    def switch_to_mode(self, mode):
        """Change le mode de l'application"""
        self.settings["app_mode"] = mode
        self.save_settings()
        
        self.clear_interface()
        
        if mode == "comparison":
            self.create_comparison_interface()
        elif mode == "recording":
            self.create_recording_interface()
            
    def clear_interface(self):
        """Efface l'interface actuelle"""
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Menu):
                continue
            widget.destroy()
            
        self.comparison_frame = None
        self.recording_frame = None
        self.settings_frame = None
        
    def open_settings(self):
        """Ouvre la page des paramètres"""
        previous_mode = self.settings["app_mode"]
        
        self.clear_interface()
        
        self.create_settings_interface(previous_mode)

    def create_settings_interface(self, previous_mode):
        """Crée l'interface des paramètres"""
        self.settings_frame = ttk.Frame(self.root, style="TFrame")
        self.settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(self.settings_frame, text="Paramètres", 
                              font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.fg_color)
        title_label.pack(pady=10)
        
        notebook = ttk.Notebook(self.settings_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        general_tab = ttk.Frame(notebook)
        notebook.add(general_tab, text="Général")
        
        theme_frame = ttk.LabelFrame(general_tab, text="Thème")
        theme_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.theme_var = tk.StringVar(value=self.settings["theme"])
        
        ttk.Radiobutton(theme_frame, text="Clair", variable=self.theme_var, 
                       value="light").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Radiobutton(theme_frame, text="Sombre", variable=self.theme_var, 
                       value="dark").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Radiobutton(theme_frame, text="Automatique", variable=self.theme_var, 
                       value="auto").pack(anchor=tk.W, padx=20, pady=5)
        
        mode_frame = ttk.LabelFrame(general_tab, text="Mode d'application par défaut")
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.mode_var = tk.StringVar(value=self.settings["app_mode"])
        
        ttk.Radiobutton(mode_frame, text="Comparaison de parole", variable=self.mode_var, 
                       value="comparison").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Radiobutton(mode_frame, text="Enregistrement audio", variable=self.mode_var, 
                       value="recording").pack(anchor=tk.W, padx=20, pady=5)
        
        folder_frame = ttk.LabelFrame(general_tab, text="Dossier d'archivage audio")
        folder_frame.pack(fill=tk.X, padx=10, pady=10)
        
        folder_entry_frame = ttk.Frame(folder_frame)
        folder_entry_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.folder_var = tk.StringVar(value=self.settings["audio_dir"])
        folder_entry = ttk.Entry(folder_entry_frame, textvariable=self.folder_var, width=50)
        folder_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        browse_button = ttk.Button(folder_entry_frame, text="Parcourir", 
                                  command=self.browse_folder)
        browse_button.pack(side=tk.LEFT, padx=5)
        
        audio_tab = ttk.Frame(notebook)
        notebook.add(audio_tab, text="Audio")
        
        mic_frame = ttk.LabelFrame(audio_tab, text="Configuration du microphone")
        mic_frame.pack(fill=tk.X, padx=10, pady=10)
        
        mic_select_frame = ttk.Frame(mic_frame)
        mic_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(mic_select_frame, text="Sélectionner un microphone:").pack(anchor=tk.W, padx=5, pady=5)
        
        p = pyaudio.PyAudio()
        self.mic_devices = [(i, p.get_device_info_by_index(i)['name']) 
                           for i in range(p.get_device_count()) 
                           if p.get_device_info_by_index(i).get('maxInputChannels') > 0]
        p.terminate()
        
        self.mic_var = tk.StringVar()
        if self.mic_devices:
            selected_index = self.settings["selected_mic"]
            if 0 <= selected_index < len(self.mic_devices):
                self.mic_var.set(self.mic_devices[selected_index][1])
            else:
                self.mic_var.set(self.mic_devices[0][1])
        
        mic_dropdown = ttk.Combobox(mic_select_frame, textvariable=self.mic_var, state="readonly")
        mic_dropdown['values'] = [device[1] for device in self.mic_devices]
        mic_dropdown.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)
        
        visualizer_frame = ttk.LabelFrame(audio_tab, text="Taille de la visualisation audio")
        visualizer_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.visualizer_var = tk.StringVar(value=self.settings["visualizer_size"])
        
        ttk.Radiobutton(visualizer_frame, text="Petite", variable=self.visualizer_var, 
                       value="small").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Radiobutton(visualizer_frame, text="Moyenne", variable=self.visualizer_var, 
                       value="medium").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Radiobutton(visualizer_frame, text="Grande", variable=self.visualizer_var, 
                       value="large").pack(anchor=tk.W, padx=20, pady=5)
        
        test_frame = ttk.LabelFrame(audio_tab, text="Test du microphone")
        test_frame.pack(fill=tk.X, padx=10, pady=10)
        
        fig_size = (4, 1)
        self.fig = plt.Figure(figsize=fig_size, dpi=100)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=test_frame)
        self.canvas.get_tk_widget().pack(padx=10, pady=5, fill=tk.X)
        
        self.line, = self.ax.plot([], [], lw=2)
        self.ax.set_ylim(-1, 1)
        self.ax.set_xlim(0, 100)
        self.ax.set_title('Niveau audio')
        self.ax.set_yticks([])
        self.ax.set_xticks([])
        self.fig.tight_layout()
        
        test_mic_button = ttk.Button(test_frame, text="Tester le microphone", 
                                   command=self.test_microphone)
        test_mic_button.pack(pady=5)
        
        button_frame = ttk.Frame(self.settings_frame)
        button_frame.pack(pady=20)
        
        save_button = ttk.Button(button_frame, text="Enregistrer", 
                               command=lambda: self.save_settings_and_return(previous_mode))
        save_button.pack(side=tk.LEFT, padx=10)
        
        cancel_button = ttk.Button(button_frame, text="Annuler", 
                                 command=lambda: self.switch_to_mode(previous_mode))
        cancel_button.pack(side=tk.LEFT, padx=10)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Prêt")
        status_bar = tk.Label(self.settings_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def browse_folder(self):
        """Ouvre une boîte de dialogue pour sélectionner un dossier"""
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)
            
    def save_settings_and_return(self, previous_mode):
        """Sauvegarde les paramètres et retourne au mode précédent"""
        self.settings["theme"] = self.theme_var.get()
        self.settings["app_mode"] = self.mode_var.get()
        self.settings["audio_dir"] = self.folder_var.get()
        self.settings["visualizer_size"] = self.visualizer_var.get()
        
        selected_name = self.mic_var.get()
        for idx, device in enumerate(self.mic_devices):
            if device[1] == selected_name:
                self.settings["selected_mic"] = idx
                break
        
        os.makedirs(self.settings["audio_dir"], exist_ok=True)
        
        self.save_settings()
        
        self.apply_theme()
        self.update_style()
        
        self.switch_to_mode(previous_mode)
        
    def create_comparison_interface(self):
        """Crée l'interface pour le mode comparaison"""
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(main_frame, text="Comparez votre prononciation", 
                              font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.fg_color)
        title_label.pack(pady=10)
        
        instruction_label = tk.Label(main_frame, text="Écrivez le texte, puis enregistrez votre voix pour comparer", 
                                    font=("Arial", 10), bg=self.bg_color, fg=self.secondary_fg)
        instruction_label.pack(pady=5)
        
        text_frame = ttk.LabelFrame(main_frame, text="Texte à prononcer")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=70, height=8,
                                                 font=("Arial", 11), bg=self.text_bg, fg=self.fg_color)
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        mic_frame = ttk.LabelFrame(main_frame, text="Niveau audio")
        mic_frame.pack(fill=tk.X, pady=10)
        
        if self.settings["visualizer_size"] == "small":
            fig_size = (6, 1)
        elif self.settings["visualizer_size"] == "medium":
            fig_size = (6, 1.5)
        else:  # large
            fig_size = (6, 2)
            
        self.fig = plt.Figure(figsize=fig_size, dpi=100)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=mic_frame)
        self.canvas.get_tk_widget().pack(padx=10, pady=5, fill=tk.X)
        
        self.line, = self.ax.plot([], [], lw=2)
        self.ax.set_ylim(-1, 1)
        self.ax.set_xlim(0, 100)
        self.ax.set_title('Niveau audio')
        self.ax.set_yticks([])
        self.ax.set_xticks([])
        self.fig.tight_layout()
        
        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.pack(pady=10)
        
        self.record_button = ttk.Button(button_frame, text="Commencer l'enregistrement", 
                                      command=self.start_recording)
        self.record_button.pack(side=tk.LEFT, padx=10)
        
        self.compare_button = ttk.Button(button_frame, text="Comparer le texte", 
                                       command=self.compare_text)
        self.compare_button.pack(side=tk.LEFT, padx=10)
        
        result_frame = ttk.LabelFrame(main_frame, text="Résultat de la comparaison")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.result_area = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, width=70, height=8,
                                                   font=("Arial", 11), bg=self.text_bg, fg=self.fg_color)
        self.result_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Prêt")
        status_bar = tk.Label(main_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W,
                             bg=self.bg_color, fg=self.fg_color)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.comparison_frame = main_frame
        
    def create_recording_interface(self):
        """Crée l'interface pour le mode enregistrement audio simple"""
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(main_frame, text="Enregistrement Audio", 
                              font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.fg_color)
        title_label.pack(pady=10)
        
        instruction_label = tk.Label(main_frame, text="Enregistrez votre voix", 
                                    font=("Arial", 10), bg=self.bg_color, fg=self.secondary_fg)
        instruction_label.pack(pady=5)
        
        mic_frame = ttk.LabelFrame(main_frame, text="Niveau audio")
        mic_frame.pack(fill=tk.X, expand=True, pady=10)
        
        if self.settings["visualizer_size"] == "small":
            fig_size = (6, 1.5)
        elif self.settings["visualizer_size"] == "medium":
            fig_size = (6, 2.5)
        else:  # large
            fig_size = (6, 3.5)
            
        self.fig = plt.Figure(figsize=fig_size, dpi=100)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=mic_frame)
        self.canvas.get_tk_widget().pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.line, = self.ax.plot([], [], lw=2)
        self.ax.set_ylim(-1, 1)
        self.ax.set_xlim(0, 100)
        self.ax.set_title('Niveau audio')
        self.ax.set_yticks([])
        self.ax.set_xticks([])
        self.fig.tight_layout()
        
        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.pack(pady=20)
        
        self.record_button = ttk.Button(button_frame, text="Commencer l'enregistrement", 
                                      command=self.start_recording)
        self.record_button.pack(side=tk.LEFT, padx=10)
        
        filename_frame = ttk.Frame(main_frame)
        filename_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(filename_frame, text="Nom du fichier:").pack(side=tk.LEFT, padx=5)
        
        self.filename_var = tk.StringVar(value=f"Enregistrement_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        filename_entry = ttk.Entry(filename_frame, textvariable=self.filename_var, width=40)
        filename_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        recordings_frame = ttk.LabelFrame(main_frame, text="Enregistrements récents")
        recordings_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.recordings_listbox = tk.Listbox(recordings_frame, bg=self.text_bg, fg=self.fg_color,
                                          font=("Arial", 10), height=10)
        self.recordings_listbox.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(recordings_frame, orient=tk.VERTICAL, command=self.recordings_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        self.recordings_listbox.config(yscrollcommand=scrollbar.set)
        
        rec_buttons_frame = ttk.Frame(main_frame)
        rec_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(rec_buttons_frame, text="Écouter", command=self.play_recording).pack(side=tk.LEFT, padx=5)
        ttk.Button(rec_buttons_frame, text="Supprimer", command=self.delete_recording).pack(side=tk.LEFT, padx=5)
        ttk.Button(rec_buttons_frame, text="Actualiser", command=self.refresh_recordings_list).pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Prêt")
        status_bar = tk.Label(main_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W,
                             bg=self.bg_color, fg=self.fg_color)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.recording_frame = main_frame
        
        self.refresh_recordings_list()
        
    def refresh_recordings_list(self):
        """Actualise la liste des enregistrements"""
        self.recordings_listbox.delete(0, tk.END)
        
        audio_dir = self.settings["audio_dir"]
        if not os.path.exists(audio_dir):
            return
            
        files = [f for f in os.listdir(audio_dir) if f.endswith('.wav')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(audio_dir, x)), reverse=True)
        
        for file in files:
            self.recordings_listbox.insert(tk.END, file)
            
    def play_recording(self):
        """Joue l'enregistrement sélectionné"""
        selection = self.recordings_listbox.curselection()
        if not selection:
            messagebox.showinfo("Information", "Veuillez sélectionner un enregistrement")
            return
            
        filename = self.recordings_listbox.get(selection[0])
        filepath = os.path.join(self.settings["audio_dir"], filename)
        
        if sys.platform == "win32":
            os.startfile(filepath)
        elif sys.platform == "darwin":  # macOS
            subprocess.call(["open", filepath])
        else:  # linux
            subprocess.call(["xdg-open", filepath])
            
    def delete_recording(self):
        """Supprime l'enregistrement sélectionné"""
        selection = self.recordings_listbox.curselection()
        if not selection:
            messagebox.showinfo("Information", "Veuillez sélectionner un enregistrement")
            return
            
        filename = self.recordings_listbox.get(selection[0])
        filepath = os.path.join(self.settings["audio_dir"], filename)
        
        if messagebox.askyesno("Confirmation", f"Voulez-vous vraiment supprimer {filename} ?"):
            try:
                os.remove(filepath)
                self.refresh_recordings_list()
                self.status_var.set(f"Fichier {filename} supprimé")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de supprimer le fichier: {e}")
                
    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.record_button.config(text="Arrêter l'enregistrement")
            self.audio_data = []
            
            self.ani = animation.FuncAnimation(
                self.fig, self.update_audio_plot, interval=30, blit=True, cache_frame_data=False)
            self.canvas.draw()
            
            threading.Thread(target=self.record_audio_to_file).start()
        else:
            self.recording = False
            self.record_button.config(text="Commencer l'enregistrement")

if __name__ == "__main__":
    root = tk.Tk()
    app = SpeechComparisonApp(root)
    root.mainloop()
