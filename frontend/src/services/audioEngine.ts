/**
 * Audio Engine for Tile-Crawler
 *
 * TTS-based procedural sound synthesis using Web Audio API.
 * Converts onomatopoeia text into game audio through speech synthesis
 * and real-time audio processing.
 */

// Types
export interface AudioIntent {
  event_type: 'sfx' | 'ambient' | 'music_motif' | 'ui_feedback' | 'dialogue' | 'environmental';
  onomatopoeia: string;
  emotion: string;
  intensity: number;
  pitch_shift: number;
  speed: number;
  reverb: number;
  style: string;
  spatial?: { pan: number; distance: number };
  loop: boolean;
  priority: number;
}

export interface AudioBatch {
  primary: AudioIntent;
  ambient?: AudioIntent;
  music?: AudioIntent;
  layers?: AudioIntent[];
}

export interface AudioSettings {
  masterVolume: number;
  sfxVolume: number;
  musicVolume: number;
  ambientVolume: number;
  ttsEnabled: boolean;
  ttsVoice: string;
  ttsRate: number;
  ttsPitch: number;
}

// Default settings
const DEFAULT_SETTINGS: AudioSettings = {
  masterVolume: 0.7,
  sfxVolume: 0.8,
  musicVolume: 0.5,
  ambientVolume: 0.4,
  ttsEnabled: true,
  ttsVoice: '',
  ttsRate: 1.0,
  ttsPitch: 1.0,
};

/**
 * Main Audio Engine class
 */
export class AudioEngine {
  private audioContext: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private sfxGain: GainNode | null = null;
  private musicGain: GainNode | null = null;
  private ambientGain: GainNode | null = null;

  // Effects nodes
  private convolver: ConvolverNode | null = null;
  private compressor: DynamicsCompressorNode | null = null;

  // TTS
  private synth: SpeechSynthesis | null = null;
  private voices: SpeechSynthesisVoice[] = [];
  private selectedVoice: SpeechSynthesisVoice | null = null;

  // State
  private settings: AudioSettings = { ...DEFAULT_SETTINGS };
  private isInitialized = false;
  private activeAmbient: AudioBufferSourceNode | null = null;
  private activeMusic: AudioBufferSourceNode | null = null;
  private audioQueue: AudioIntent[] = [];
  private isProcessingQueue = false;

  constructor() {
    // Load saved settings
    this.loadSettings();
  }

  /**
   * Initialize the audio engine (must be called after user interaction)
   */
  async init(): Promise<boolean> {
    if (this.isInitialized) return true;

    try {
      // Create audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();

      // Create gain nodes for mixing
      this.masterGain = this.audioContext.createGain();
      this.sfxGain = this.audioContext.createGain();
      this.musicGain = this.audioContext.createGain();
      this.ambientGain = this.audioContext.createGain();

      // Create compressor for dynamics
      this.compressor = this.audioContext.createDynamicsCompressor();
      this.compressor.threshold.value = -24;
      this.compressor.knee.value = 30;
      this.compressor.ratio.value = 12;
      this.compressor.attack.value = 0.003;
      this.compressor.release.value = 0.25;

      // Connect audio graph
      this.sfxGain.connect(this.compressor);
      this.musicGain.connect(this.compressor);
      this.ambientGain.connect(this.compressor);
      this.compressor.connect(this.masterGain);
      this.masterGain.connect(this.audioContext.destination);

      // Apply volume settings
      this.applyVolumeSettings();

      // Create reverb impulse response
      await this.createReverbImpulse();

      // Initialize TTS
      this.initTTS();

      this.isInitialized = true;
      console.log('🔊 Audio Engine initialized');
      return true;
    } catch (error) {
      console.error('Failed to initialize audio engine:', error);
      return false;
    }
  }

  /**
   * Initialize Text-to-Speech
   */
  private initTTS(): void {
    if (!('speechSynthesis' in window)) {
      console.warn('Text-to-Speech not supported');
      this.settings.ttsEnabled = false;
      return;
    }

    this.synth = window.speechSynthesis;

    // Load voices (may be async)
    const loadVoices = () => {
      this.voices = this.synth!.getVoices();

      // Prefer English voices with interesting qualities
      const preferredVoices = [
        'Google UK English Male',
        'Google UK English Female',
        'Microsoft David',
        'Microsoft Zira',
        'Alex',
        'Daniel',
      ];

      for (const preferred of preferredVoices) {
        const voice = this.voices.find(v => v.name.includes(preferred));
        if (voice) {
          this.selectedVoice = voice;
          break;
        }
      }

      // Fallback to first English voice
      if (!this.selectedVoice) {
        this.selectedVoice = this.voices.find(v => v.lang.startsWith('en')) || this.voices[0];
      }

      if (this.settings.ttsVoice) {
        const savedVoice = this.voices.find(v => v.name === this.settings.ttsVoice);
        if (savedVoice) this.selectedVoice = savedVoice;
      }
    };

    loadVoices();
    if (this.synth.onvoiceschanged !== undefined) {
      this.synth.onvoiceschanged = loadVoices;
    }
  }

  /**
   * Create reverb impulse response
   */
  private async createReverbImpulse(): Promise<void> {
    if (!this.audioContext) return;

    const sampleRate = this.audioContext.sampleRate;
    const length = sampleRate * 2; // 2 second reverb
    const impulse = this.audioContext.createBuffer(2, length, sampleRate);

    for (let channel = 0; channel < 2; channel++) {
      const channelData = impulse.getChannelData(channel);
      for (let i = 0; i < length; i++) {
        // Exponential decay with some randomness
        const decay = Math.exp(-3 * i / length);
        channelData[i] = (Math.random() * 2 - 1) * decay;
      }
    }

    this.convolver = this.audioContext.createConvolver();
    this.convolver.buffer = impulse;
  }

  /**
   * Apply volume settings to gain nodes
   */
  private applyVolumeSettings(): void {
    if (this.masterGain) {
      this.masterGain.gain.value = this.settings.masterVolume;
    }
    if (this.sfxGain) {
      this.sfxGain.gain.value = this.settings.sfxVolume;
    }
    if (this.musicGain) {
      this.musicGain.gain.value = this.settings.musicVolume;
    }
    if (this.ambientGain) {
      this.ambientGain.gain.value = this.settings.ambientVolume;
    }
  }

  /**
   * Play an audio intent
   */
  async play(intent: AudioIntent): Promise<void> {
    if (!this.isInitialized) {
      await this.init();
    }

    if (!this.audioContext || !this.settings.ttsEnabled) return;

    // Add to queue based on priority
    this.audioQueue.push(intent);
    this.audioQueue.sort((a, b) => b.priority - a.priority);

    // Process queue
    if (!this.isProcessingQueue) {
      this.processQueue();
    }
  }

  /**
   * Play an audio batch (multiple related sounds)
   */
  async playBatch(batch: AudioBatch): Promise<void> {
    // Play primary sound
    await this.play(batch.primary);

    // Play ambient if provided
    if (batch.ambient) {
      this.playAmbient(batch.ambient);
    }

    // Play music motif if provided
    if (batch.music) {
      this.playMusic(batch.music);
    }

    // Play additional layers
    if (batch.layers) {
      for (const layer of batch.layers) {
        await this.play(layer);
      }
    }
  }

  /**
   * Process the audio queue
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessingQueue || this.audioQueue.length === 0) return;

    this.isProcessingQueue = true;

    while (this.audioQueue.length > 0) {
      const intent = this.audioQueue.shift();
      if (intent) {
        await this.synthesizeAndPlay(intent);
      }
    }

    this.isProcessingQueue = false;
  }

  /**
   * Synthesize speech and play with effects
   */
  private async synthesizeAndPlay(intent: AudioIntent): Promise<void> {
    if (!this.synth || !this.audioContext) return;

    return new Promise<void>((resolve) => {
      const utterance = new SpeechSynthesisUtterance(intent.onomatopoeia);

      // Set voice
      if (this.selectedVoice) {
        utterance.voice = this.selectedVoice;
      }

      // Apply intent parameters
      utterance.rate = intent.speed * this.settings.ttsRate;
      utterance.pitch = this.calculatePitch(intent.pitch_shift) * this.settings.ttsPitch;
      utterance.volume = intent.intensity * this.getVolumeForType(intent.event_type);

      // Emotion-based adjustments
      switch (intent.emotion) {
        case 'danger':
        case 'tense':
          utterance.rate *= 1.2;
          break;
        case 'peaceful':
        case 'melancholy':
          utterance.rate *= 0.8;
          break;
        case 'triumphant':
        case 'epic':
          utterance.volume = Math.min(1, utterance.volume * 1.2);
          break;
        case 'mysterious':
          utterance.rate *= 0.9;
          utterance.pitch *= 0.9;
          break;
      }

      utterance.onend = () => resolve();
      utterance.onerror = () => resolve();

      // Cancel any overlapping speech for high priority sounds
      if (intent.priority >= 8) {
        this.synth!.cancel();
      }

      this.synth!.speak(utterance);

      // Timeout fallback
      setTimeout(resolve, 5000);
    });
  }

  /**
   * Calculate pitch multiplier from semitone shift
   */
  private calculatePitch(semitones: number): number {
    // Pitch is 0-2 in Web Speech API, 1 is normal
    // Map -12 to +12 semitones to 0.5 to 2.0
    const ratio = Math.pow(2, semitones / 12);
    return Math.max(0.5, Math.min(2, ratio));
  }

  /**
   * Get volume multiplier for event type
   */
  private getVolumeForType(eventType: string): number {
    switch (eventType) {
      case 'sfx':
        return this.settings.sfxVolume;
      case 'music_motif':
        return this.settings.musicVolume;
      case 'ambient':
      case 'environmental':
        return this.settings.ambientVolume;
      case 'ui_feedback':
        return this.settings.sfxVolume * 0.7;
      case 'dialogue':
        return this.settings.sfxVolume * 1.2;
      default:
        return this.settings.sfxVolume;
    }
  }

  /**
   * Play looping ambient sound
   */
  private playAmbient(intent: AudioIntent): void {
    // For ambient, we'll use a softer, looping approach
    if (!this.synth || !intent.loop) {
      this.play(intent);
      return;
    }

    // Create ambient loop with intervals
    const playAmbientLoop = () => {
      if (!this.settings.ttsEnabled) return;

      const utterance = new SpeechSynthesisUtterance(intent.onomatopoeia);
      if (this.selectedVoice) utterance.voice = this.selectedVoice;
      utterance.rate = intent.speed * 0.7;
      utterance.pitch = this.calculatePitch(intent.pitch_shift);
      utterance.volume = intent.intensity * this.settings.ambientVolume * 0.5;

      this.synth!.speak(utterance);
    };

    // Play immediately and schedule loops
    playAmbientLoop();
  }

  /**
   * Play music motif
   */
  private playMusic(intent: AudioIntent): void {
    if (!this.synth) return;

    const utterance = new SpeechSynthesisUtterance(intent.onomatopoeia);
    if (this.selectedVoice) utterance.voice = this.selectedVoice;
    utterance.rate = intent.speed;
    utterance.pitch = this.calculatePitch(intent.pitch_shift);
    utterance.volume = intent.intensity * this.settings.musicVolume;

    this.synth.speak(utterance);
  }

  /**
   * Stop all audio
   */
  stop(): void {
    if (this.synth) {
      this.synth.cancel();
    }
    this.audioQueue = [];
    this.isProcessingQueue = false;
  }

  /**
   * Update settings
   */
  updateSettings(newSettings: Partial<AudioSettings>): void {
    this.settings = { ...this.settings, ...newSettings };
    this.applyVolumeSettings();
    this.saveSettings();
  }

  /**
   * Get current settings
   */
  getSettings(): AudioSettings {
    return { ...this.settings };
  }

  /**
   * Get available voices
   */
  getVoices(): SpeechSynthesisVoice[] {
    return this.voices;
  }

  /**
   * Set TTS voice
   */
  setVoice(voiceName: string): void {
    const voice = this.voices.find(v => v.name === voiceName);
    if (voice) {
      this.selectedVoice = voice;
      this.settings.ttsVoice = voiceName;
      this.saveSettings();
    }
  }

  /**
   * Save settings to localStorage
   */
  private saveSettings(): void {
    try {
      localStorage.setItem('tileCrawlerAudioSettings', JSON.stringify(this.settings));
    } catch (e) {
      console.warn('Could not save audio settings');
    }
  }

  /**
   * Load settings from localStorage
   */
  private loadSettings(): void {
    try {
      const saved = localStorage.getItem('tileCrawlerAudioSettings');
      if (saved) {
        this.settings = { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.warn('Could not load audio settings');
    }
  }

  /**
   * Check if audio is available
   */
  isAvailable(): boolean {
    return 'AudioContext' in window && 'speechSynthesis' in window;
  }

  /**
   * Resume audio context (needed after user interaction)
   */
  async resume(): Promise<void> {
    if (this.audioContext?.state === 'suspended') {
      await this.audioContext.resume();
    }
  }
}

// Singleton instance
let audioEngineInstance: AudioEngine | null = null;

export function getAudioEngine(): AudioEngine {
  if (!audioEngineInstance) {
    audioEngineInstance = new AudioEngine();
  }
  return audioEngineInstance;
}

export default AudioEngine;
