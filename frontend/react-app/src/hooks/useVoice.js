import { useState, useEffect, useRef, useCallback } from 'react'

// Voice Input (Speech to Text)
export function useVoiceInput(onTranscript) {
  const [isListening, setIsListening] = useState(false)
  const [isSupported, setIsSupported] = useState(false)
  const [error, setError] = useState(null)
  const recognitionRef = useRef(null)
  const callbackRef = useRef(onTranscript)

  // Keep callback ref fresh
  useEffect(() => {
    callbackRef.current = onTranscript
  }, [onTranscript])

  useEffect(() => {
    // Check browser support
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition

    if (!SR) {
      console.warn('Speech Recognition not supported')
      setIsSupported(false)
      return
    }

    setIsSupported(true)
    const recognition = new SR()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'en-IN'
    recognition.maxAlternatives = 1

    recognition.onstart = () => {
      console.log('[Voice] Started listening')
      setIsListening(true)
      setError(null)
    }

    recognition.onresult = (event) => {
      const last = event.results.length - 1
      const transcript = event.results[last][0].transcript
      console.log('[Voice] Transcript:', transcript)
      callbackRef.current(transcript)
    }

    recognition.onerror = (event) => {
      console.error('[Voice] Error:', event.error)
      setError(event.error)
      setIsListening(false)
    }

    recognition.onend = () => {
      console.log('[Voice] Ended')
      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      try {
        recognition.abort()
      } catch (e) {
        // no-op
      }
    }
  }, [])

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return
    if (isListening) return
    try {
      setError(null)
      recognitionRef.current.start()
    } catch (e) {
      console.error('[Voice] Start error:', e)
      // Reset if already started
      try {
        recognitionRef.current.abort()
        setTimeout(() => {
          recognitionRef.current.start()
        }, 200)
      } catch (e2) {
        // no-op
      }
    }
  }, [isListening])

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return
    try {
      recognitionRef.current.stop()
    } catch (e) {
      // no-op
    }
    setIsListening(false)
  }, [])

  return {
    isListening,
    isSupported,
    error,
    startListening,
    stopListening,
  }
}

// Voice Output (Text to Speech)
export function useVoiceOutput() {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const synthRef = useRef(window.speechSynthesis)

  // Load voices (needed for some browsers)
  useEffect(() => {
    if (synthRef.current && synthRef.current.onvoiceschanged !== undefined) {
      synthRef.current.onvoiceschanged = () => {
        synthRef.current.getVoices()
      }
    }
  }, [])

  const speak = useCallback((text, options = {}) => {
    if (!synthRef.current || !text) return

    // Cancel any ongoing speech
    synthRef.current.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = options.rate ?? 0.88
    utterance.pitch = options.pitch ?? 1.0
    utterance.volume = options.volume ?? 1.0
    utterance.lang = 'en-IN'

    // Try to pick Indian English voice
    const voices = synthRef.current.getVoices()
    const preferred = voices.find(
      (voice) =>
        voice.lang === 'en-IN' ||
        voice.name.includes('India') ||
        voice.name.includes('Ravi') ||
        voice.name.includes('Veena')
    )
    if (preferred) utterance.voice = preferred

    utterance.onstart = () => {
      console.log('[TTS] Started speaking')
      setIsSpeaking(true)
    }
    utterance.onend = () => {
      console.log('[TTS] Finished')
      setIsSpeaking(false)
    }
    utterance.onerror = (event) => {
      console.error('[TTS] Error:', event)
      setIsSpeaking(false)
    }

    // Small delay for browser readiness
    setTimeout(() => {
      synthRef.current.speak(utterance)
    }, 100)
  }, [])

  const stopSpeaking = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel()
    }
    setIsSpeaking(false)
  }, [])

  return {
    isSpeaking,
    speak,
    stopSpeaking,
    isSupported: !!window.speechSynthesis,
  }
}
