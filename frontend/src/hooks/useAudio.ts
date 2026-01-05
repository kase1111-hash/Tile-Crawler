/**
 * React hook for game audio management
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getAudioEngine, AudioIntent, AudioBatch, AudioSettings } from '../services/audioEngine';

export interface UseAudioReturn {
  // State
  isInitialized: boolean;
  isEnabled: boolean;
  settings: AudioSettings;
  voices: SpeechSynthesisVoice[];

  // Actions
  init: () => Promise<boolean>;
  play: (intent: AudioIntent) => Promise<void>;
  playBatch: (batch: AudioBatch) => Promise<void>;
  stop: () => void;
  updateSettings: (settings: Partial<AudioSettings>) => void;
  setVoice: (voiceName: string) => void;
  toggle: () => void;

  // Quick play helpers
  playSfx: (onomatopoeia: string, options?: Partial<AudioIntent>) => void;
  playUI: (action: 'select' | 'confirm' | 'cancel' | 'error' | 'open' | 'close') => void;
  playMovement: (terrain?: string) => void;
  playCombat: (type: 'hit' | 'miss' | 'critical' | 'block' | 'death') => void;
}

// Onomatopoeia presets for quick play
const UI_SOUNDS: Record<string, AudioIntent> = {
  select: {
    event_type: 'ui_feedback',
    onomatopoeia: 'tick',
    emotion: 'neutral',
    intensity: 0.4,
    pitch_shift: 2,
    speed: 1.2,
    reverb: 0.1,
    style: 'comic_noir',
    loop: false,
    priority: 3,
  },
  confirm: {
    event_type: 'ui_feedback',
    onomatopoeia: 'ding!',
    emotion: 'triumphant',
    intensity: 0.5,
    pitch_shift: 4,
    speed: 1.0,
    reverb: 0.1,
    style: 'comic_noir',
    loop: false,
    priority: 4,
  },
  cancel: {
    event_type: 'ui_feedback',
    onomatopoeia: 'bwop',
    emotion: 'neutral',
    intensity: 0.4,
    pitch_shift: -2,
    speed: 1.0,
    reverb: 0.1,
    style: 'comic_noir',
    loop: false,
    priority: 3,
  },
  error: {
    event_type: 'ui_feedback',
    onomatopoeia: 'BZZZT',
    emotion: 'danger',
    intensity: 0.6,
    pitch_shift: -3,
    speed: 1.0,
    reverb: 0.2,
    style: 'comic_noir',
    loop: false,
    priority: 5,
  },
  open: {
    event_type: 'ui_feedback',
    onomatopoeia: 'fwip',
    emotion: 'neutral',
    intensity: 0.3,
    pitch_shift: 1,
    speed: 1.3,
    reverb: 0.1,
    style: 'comic_noir',
    loop: false,
    priority: 2,
  },
  close: {
    event_type: 'ui_feedback',
    onomatopoeia: 'fwup',
    emotion: 'neutral',
    intensity: 0.3,
    pitch_shift: -1,
    speed: 1.3,
    reverb: 0.1,
    style: 'comic_noir',
    loop: false,
    priority: 2,
  },
};

const COMBAT_SOUNDS: Record<string, AudioIntent> = {
  hit: {
    event_type: 'sfx',
    onomatopoeia: 'THWACK!',
    emotion: 'tense',
    intensity: 0.7,
    pitch_shift: 0,
    speed: 1.0,
    reverb: 0.3,
    style: 'comic_noir',
    loop: false,
    priority: 6,
  },
  miss: {
    event_type: 'sfx',
    onomatopoeia: 'whoosh',
    emotion: 'neutral',
    intensity: 0.4,
    pitch_shift: 1,
    speed: 1.2,
    reverb: 0.2,
    style: 'comic_noir',
    loop: false,
    priority: 5,
  },
  critical: {
    event_type: 'sfx',
    onomatopoeia: 'KA-BOOM!',
    emotion: 'epic',
    intensity: 1.0,
    pitch_shift: 2,
    speed: 1.1,
    reverb: 0.4,
    style: 'comic_noir',
    loop: false,
    priority: 8,
  },
  block: {
    event_type: 'sfx',
    onomatopoeia: 'CLANG!',
    emotion: 'tense',
    intensity: 0.6,
    pitch_shift: 3,
    speed: 1.0,
    reverb: 0.4,
    style: 'comic_noir',
    loop: false,
    priority: 6,
  },
  death: {
    event_type: 'sfx',
    onomatopoeia: 'SPLORCH... thud',
    emotion: 'danger',
    intensity: 0.8,
    pitch_shift: -2,
    speed: 0.8,
    reverb: 0.5,
    style: 'comic_noir',
    loop: false,
    priority: 7,
  },
};

const TERRAIN_SOUNDS: Record<string, string> = {
  stone: 'tap tap tap',
  water: 'splish splash',
  wood: 'creak thump',
  grass: 'swish swish',
  sand: 'scrunch scrunch',
  default: 'tap tap',
};

export function useAudio(): UseAudioReturn {
  const audioEngine = useRef(getAudioEngine());
  const [isInitialized, setIsInitialized] = useState(false);
  const [isEnabled, setIsEnabled] = useState(true);
  const [settings, setSettings] = useState<AudioSettings>(audioEngine.current.getSettings());
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);

  // Initialize on mount
  useEffect(() => {
    // Check availability
    if (!audioEngine.current.isAvailable()) {
      setIsEnabled(false);
      return;
    }

    // Load voices
    const loadVoices = () => {
      const availableVoices = audioEngine.current.getVoices();
      if (availableVoices.length > 0) {
        setVoices(availableVoices);
      }
    };

    loadVoices();

    // Voice list may load async
    if ('speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }

    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, []);

  // Initialize audio (requires user interaction)
  const init = useCallback(async () => {
    const success = await audioEngine.current.init();
    setIsInitialized(success);
    if (success) {
      setSettings(audioEngine.current.getSettings());
    }
    return success;
  }, []);

  // Play audio intent
  const play = useCallback(async (intent: AudioIntent) => {
    if (!isEnabled) return;

    // Auto-init on first play
    if (!isInitialized) {
      await init();
    }

    await audioEngine.current.play(intent);
  }, [isEnabled, isInitialized, init]);

  // Play audio batch
  const playBatch = useCallback(async (batch: AudioBatch) => {
    if (!isEnabled) return;

    if (!isInitialized) {
      await init();
    }

    await audioEngine.current.playBatch(batch);
  }, [isEnabled, isInitialized, init]);

  // Stop all audio
  const stop = useCallback(() => {
    audioEngine.current.stop();
  }, []);

  // Update settings
  const updateSettings = useCallback((newSettings: Partial<AudioSettings>) => {
    audioEngine.current.updateSettings(newSettings);
    setSettings(audioEngine.current.getSettings());
  }, []);

  // Set voice
  const setVoice = useCallback((voiceName: string) => {
    audioEngine.current.setVoice(voiceName);
    setSettings(audioEngine.current.getSettings());
  }, []);

  // Toggle audio on/off
  const toggle = useCallback(() => {
    setIsEnabled(prev => {
      const newValue = !prev;
      if (!newValue) {
        audioEngine.current.stop();
      }
      return newValue;
    });
  }, []);

  // Quick play helpers
  const playSfx = useCallback((onomatopoeia: string, options?: Partial<AudioIntent>) => {
    const intent: AudioIntent = {
      event_type: 'sfx',
      onomatopoeia,
      emotion: 'neutral',
      intensity: 0.6,
      pitch_shift: 0,
      speed: 1.0,
      reverb: 0.3,
      style: 'comic_noir',
      loop: false,
      priority: 5,
      ...options,
    };
    play(intent);
  }, [play]);

  const playUI = useCallback((action: keyof typeof UI_SOUNDS) => {
    const sound = UI_SOUNDS[action];
    if (sound) {
      play(sound);
    }
  }, [play]);

  const playMovement = useCallback((terrain: string = 'default') => {
    const onomatopoeia = TERRAIN_SOUNDS[terrain] || TERRAIN_SOUNDS.default;
    play({
      event_type: 'sfx',
      onomatopoeia,
      emotion: 'neutral',
      intensity: 0.3,
      pitch_shift: 0,
      speed: 1.0,
      reverb: 0.3,
      style: 'comic_noir',
      loop: false,
      priority: 2,
    });
  }, [play]);

  const playCombat = useCallback((type: keyof typeof COMBAT_SOUNDS) => {
    const sound = COMBAT_SOUNDS[type];
    if (sound) {
      play(sound);
    }
  }, [play]);

  return {
    isInitialized,
    isEnabled,
    settings,
    voices,
    init,
    play,
    playBatch,
    stop,
    updateSettings,
    setVoice,
    toggle,
    playSfx,
    playUI,
    playMovement,
    playCombat,
  };
}

export default useAudio;
