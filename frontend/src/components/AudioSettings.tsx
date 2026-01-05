/**
 * Audio Settings Component
 *
 * Provides UI for configuring TTS-based audio system
 */

import React from 'react';
import { AudioSettings as AudioSettingsType } from '../services/audioEngine';

interface AudioSettingsProps {
  settings: AudioSettingsType;
  voices: SpeechSynthesisVoice[];
  isEnabled: boolean;
  onToggle: () => void;
  onUpdateSettings: (settings: Partial<AudioSettingsType>) => void;
  onSetVoice: (voiceName: string) => void;
  onClose: () => void;
  onTestSound: () => void;
}

export const AudioSettings: React.FC<AudioSettingsProps> = ({
  settings,
  voices,
  isEnabled,
  onToggle,
  onUpdateSettings,
  onSetVoice,
  onClose,
  onTestSound,
}) => {
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
      <div className="bg-gray-900 border-2 border-yellow-600 rounded-lg p-6 w-96 max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-yellow-500">Audio Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        {/* Master Toggle */}
        <div className="mb-6 p-3 bg-gray-800 rounded">
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-gray-300">Enable Audio</span>
            <div
              className={`w-12 h-6 rounded-full transition-colors ${
                isEnabled ? 'bg-green-600' : 'bg-gray-600'
              }`}
              onClick={onToggle}
            >
              <div
                className={`w-5 h-5 rounded-full bg-white transform transition-transform mt-0.5 ${
                  isEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </div>
          </label>
          <p className="text-xs text-gray-500 mt-1">
            TTS-based procedural audio synthesis
          </p>
        </div>

        {isEnabled && (
          <>
            {/* Volume Controls */}
            <div className="space-y-4 mb-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase">Volume</h3>

              <div>
                <label className="flex justify-between text-sm text-gray-300 mb-1">
                  <span>Master Volume</span>
                  <span>{Math.round(settings.masterVolume * 100)}%</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={settings.masterVolume * 100}
                  onChange={(e) => onUpdateSettings({ masterVolume: Number(e.target.value) / 100 })}
                  className="w-full accent-yellow-500"
                />
              </div>

              <div>
                <label className="flex justify-between text-sm text-gray-300 mb-1">
                  <span>Sound Effects</span>
                  <span>{Math.round(settings.sfxVolume * 100)}%</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={settings.sfxVolume * 100}
                  onChange={(e) => onUpdateSettings({ sfxVolume: Number(e.target.value) / 100 })}
                  className="w-full accent-yellow-500"
                />
              </div>

              <div>
                <label className="flex justify-between text-sm text-gray-300 mb-1">
                  <span>Music</span>
                  <span>{Math.round(settings.musicVolume * 100)}%</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={settings.musicVolume * 100}
                  onChange={(e) => onUpdateSettings({ musicVolume: Number(e.target.value) / 100 })}
                  className="w-full accent-yellow-500"
                />
              </div>

              <div>
                <label className="flex justify-between text-sm text-gray-300 mb-1">
                  <span>Ambient</span>
                  <span>{Math.round(settings.ambientVolume * 100)}%</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={settings.ambientVolume * 100}
                  onChange={(e) => onUpdateSettings({ ambientVolume: Number(e.target.value) / 100 })}
                  className="w-full accent-yellow-500"
                />
              </div>
            </div>

            {/* Voice Selection */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase mb-2">Voice</h3>
              <select
                value={settings.ttsVoice}
                onChange={(e) => onSetVoice(e.target.value)}
                className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-gray-300"
              >
                {voices.map((voice) => (
                  <option key={voice.name} value={voice.name}>
                    {voice.name} ({voice.lang})
                  </option>
                ))}
              </select>
            </div>

            {/* TTS Adjustments */}
            <div className="space-y-4 mb-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase">Voice Tuning</h3>

              <div>
                <label className="flex justify-between text-sm text-gray-300 mb-1">
                  <span>Speed</span>
                  <span>{settings.ttsRate.toFixed(1)}x</span>
                </label>
                <input
                  type="range"
                  min="50"
                  max="200"
                  value={settings.ttsRate * 100}
                  onChange={(e) => onUpdateSettings({ ttsRate: Number(e.target.value) / 100 })}
                  className="w-full accent-yellow-500"
                />
              </div>

              <div>
                <label className="flex justify-between text-sm text-gray-300 mb-1">
                  <span>Pitch</span>
                  <span>{settings.ttsPitch.toFixed(1)}x</span>
                </label>
                <input
                  type="range"
                  min="50"
                  max="200"
                  value={settings.ttsPitch * 100}
                  onChange={(e) => onUpdateSettings({ ttsPitch: Number(e.target.value) / 100 })}
                  className="w-full accent-yellow-500"
                />
              </div>
            </div>

            {/* Test Sound */}
            <button
              onClick={onTestSound}
              className="w-full bg-yellow-600 hover:bg-yellow-500 text-black font-bold py-2 px-4 rounded transition-colors"
            >
              Test Sound: "KRAKOOM!"
            </button>

            {/* Info */}
            <div className="mt-4 p-3 bg-gray-800 rounded text-xs text-gray-400">
              <p className="mb-2">
                <strong className="text-yellow-500">How it works:</strong>
              </p>
              <p>
                Audio is generated using Text-to-Speech synthesis of comic-book style
                onomatopoeia (CRASH!, WHOOSH!, etc.) with real-time audio processing.
                This creates procedural, context-aware game audio without pre-recorded samples.
              </p>
            </div>
          </>
        )}

        {/* Close Button */}
        <button
          onClick={onClose}
          className="w-full mt-4 bg-gray-700 hover:bg-gray-600 text-gray-300 py-2 px-4 rounded transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
};

export default AudioSettings;
