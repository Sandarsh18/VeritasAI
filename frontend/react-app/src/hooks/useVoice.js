import { useState, useEffect, useRef, useCallback } from 'react'

let isSpeaking = false

export const speakText = async (text) => {
  if (!text) return

  if (isSpeaking) {
    console.warn('Already speaking, ignoring...')
    return
  }

  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    console.warn('Text-to-speech not supported')
    return
  }

  const synth = window.speechSynthesis

  if (synth.speaking) {
    synth.cancel()
  }

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'en-US'
  utterance.rate = 1

  utterance.onstart = () => {
    isSpeaking = true
    console.log('[Voice] Speech start')
  }

  utterance.onend = () => {
    isSpeaking = false
    console.log('[Voice] Speech end')
  }

  utterance.onerror = (e) => {
    if (e.error !== 'interrupted') {
      console.error('TTS error:', e)
    }
    isSpeaking = false
  }

  synth.speak(utterance)
}

export const stopSpeech = () => {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  isSpeaking = false
}

const getSpeechRecognition = () => {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

const isSecureSpeechContext = () => {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  const isLocalHost = host === 'localhost' || host === '127.0.0.1' || host === '::1'
  return window.isSecureContext || isLocalHost
}

export function useVoice(onTranscript) {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [inputSupported] = useState(() => Boolean(getSpeechRecognition()))
  const [error, setError] = useState('')

  const recognitionRef = useRef(null)
  const callbackRef = useRef(onTranscript)
  const synthRef = useRef(null)
  const micPermissionRef = useRef('unknown')

  useEffect(() => {
    callbackRef.current = onTranscript
  }, [onTranscript])

  useEffect(() => {
    if (typeof window === 'undefined') return undefined

    const recognitionCtor = getSpeechRecognition()
    synthRef.current = 'speechSynthesis' in window ? window.speechSynthesis : null

    if (!recognitionCtor) {
      console.warn('[Voice] Speech recognition not supported in this browser')
      return undefined
    }

    const recognition = new recognitionCtor()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'
    recognition.maxAlternatives = 1

    recognition.onstart = () => {
      console.log('[Voice] Recognition started')
      setIsListening(true)
      setError('')
    }

    recognition.onresult = (event) => {
      const segment = event?.results?.[0]?.[0]?.transcript || ''
      const nextTranscript = segment.trim()
      console.log('[Voice] Transcript received:', nextTranscript)
      setTranscript(nextTranscript)
      callbackRef.current?.(nextTranscript)
    }

    recognition.onerror = (event) => {
      const speechError = event?.error || 'unknown-error'
      console.error('[Voice] Recognition error:', speechError, event)
      let message = `Speech recognition error: ${speechError}`
      if (speechError === 'not-allowed' || speechError === 'service-not-allowed') {
        message = 'Microphone permission denied. Please allow microphone access in browser settings.'
      }
      if (speechError === 'no-speech') {
        message = 'No speech detected. Please try again.'
      }
      setError(message)
      setIsListening(false)
    }

    recognition.onend = () => {
      console.log('[Voice] Recognition ended')
      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      try {
        recognition.abort()
      } catch {
        // Ignore teardown failures.
      }
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return undefined
    if (!navigator.permissions?.query) return undefined

    let active = true
    let permissionStatusRef = null

    navigator.permissions
      .query({ name: 'microphone' })
      .then((status) => {
        if (!active) return
        permissionStatusRef = status
        micPermissionRef.current = status.state
        console.log('[Voice] Mic permission status:', status.state)
        status.onchange = () => {
          micPermissionRef.current = status.state
          console.log('[Voice] Mic permission status changed:', status.state)
        }
      })
      .catch((queryError) => {
        console.log('[Voice] Mic permission status unavailable:', queryError?.message || queryError)
      })

    return () => {
      active = false
      if (permissionStatusRef) {
        permissionStatusRef.onchange = null
      }
    }
  }, [])

  const requestMicrophonePermission = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone API is unavailable in this browser.')
      return false
    }

    try {
      console.log('[Voice] Requesting microphone permission')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach((track) => track.stop())
      micPermissionRef.current = 'granted'
      console.log('[Voice] Mic permission status: granted')
      return true
    } catch (permissionError) {
      const denied =
        permissionError?.name === 'NotAllowedError' || permissionError?.name === 'PermissionDeniedError'
      micPermissionRef.current = denied ? 'denied' : 'unknown'

      const message = denied
        ? 'Microphone permission denied. Please enable microphone access and try again.'
        : `Unable to access microphone: ${permissionError?.message || permissionError?.name || 'unknown'}`

      console.error('[Voice] Microphone permission error:', permissionError)
      console.log('[Voice] Mic permission status:', micPermissionRef.current)
      setError(message)
      return false
    }
  }, [])

  const startListening = useCallback(async () => {
    if (!isSecureSpeechContext()) {
      const message = 'Voice input requires localhost or HTTPS.'
      console.error('[Voice] Insecure context:', window.location.href)
      setError(message)
      return false
    }

    const recognition = recognitionRef.current
    if (!recognition) {
      const message = 'Speech recognition not supported in this browser.'
      setError(message)
      console.error('[Voice] Start listening failed:', message)
      return false
    }

    if (isListening) {
      return true
    }

    setError('')
    const permissionGranted = await requestMicrophonePermission()
    console.log('[Voice] Mic permission status:', permissionGranted ? 'granted' : micPermissionRef.current)
    if (!permissionGranted) {
      return false
    }

    try {
      recognition.start()
      return true
    } catch (startError) {
      console.error('[Voice] Recognition start error:', startError)
      const message = `Could not start microphone: ${startError?.message || startError?.name || 'unknown'}`
      setError(message)
      return false
    }
  }, [isListening, requestMicrophonePermission])

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return
    try {
      recognitionRef.current.stop()
    } catch {
      // Ignore stop failures.
    }
    setIsListening(false)
    console.log('[Voice] Listening stopped by user')
  }, [])

  return {
    isListening,
    transcript,
    inputSupported,
    error,
    startListening,
    stopListening,
  }
}

// Backward-compatible exports for existing consumers.
export function useVoiceInput(onTranscript) {
  const voice = useVoice(onTranscript)
  return {
    isListening: voice.isListening,
    transcript: voice.transcript,
    isSupported: voice.inputSupported,
    error: voice.error,
    startListening: voice.startListening,
    stopListening: voice.stopListening,
  }
}

export function useVoiceOutput() {
  const voice = useVoice()
  return {
    isSpeaking: false,
    speak: speakText,
    stopSpeaking: stopSpeech,
    isSupported: typeof window !== 'undefined' && 'speechSynthesis' in window,
    error: voice.error,
  }
}
