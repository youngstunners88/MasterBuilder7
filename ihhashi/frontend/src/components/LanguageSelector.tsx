import { useState } from 'react'

const LANGUAGES = [
  { code: 'en', name: 'English', native: 'English' },
  { code: 'zu', name: 'Zulu', native: 'isiZulu' },
  { code: 'st', name: 'Sotho', native: 'Sesotho' },
  { code: 'af', name: 'Afrikaans', native: 'Afrikaans' },
  { code: 'tn', name: 'Tswana', native: 'Setswana' },
  { code: 'xh', name: 'Xhosa', native: 'isiXhosa' },
]

interface LanguageSelectorProps {
  compact?: boolean
}

export default function LanguageSelector({ compact = false }: LanguageSelectorProps) {
  const [currentLang, setCurrentLang] = useState(() => {
    return localStorage.getItem('language') || 'en'
  })

  const handleLanguageChange = (code: string) => {
    setCurrentLang(code)
    localStorage.setItem('language', code)
    // In a full i18n implementation, this would trigger a re-render with translations
    window.location.reload()
  }

  if (compact) {
    return (
      <select
        value={currentLang}
        onChange={(e) => handleLanguageChange(e.target.value)}
        className="bg-transparent border border-gray-300 rounded px-2 py-1 text-sm"
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.native}
          </option>
        ))}
      </select>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-gray-700">Language / Ulimi / Taal</label>
      <div className="flex flex-wrap gap-2">
        {LANGUAGES.map((lang) => (
          <button
            key={lang.code}
            onClick={() => handleLanguageChange(lang.code)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              currentLang === lang.code
                ? 'bg-yellow-400 text-black'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {lang.native}
          </button>
        ))}
      </div>
    </div>
  )
}
