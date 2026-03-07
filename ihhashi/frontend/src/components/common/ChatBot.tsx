import { useState } from 'react'
import { X, Send } from 'lucide-react'

export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<{text: string, isUser: boolean}[]>([
    { text: "Hi! I'm Nduna, your iHhashi assistant. How can I help you today?", isUser: false }
  ])
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim()) return
    setMessages([...messages, { text: input, isUser: true }])
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        text: "Thanks for your message! A support agent will assist you shortly.", 
        isUser: false 
      }])
    }, 1000)
    setInput('')
  }

  return (
    <>
      {/* Nduna Button - Black circle with white horse icon */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-24 right-4 w-14 h-14 bg-secondary rounded-full shadow-lg flex items-center justify-center z-50 hover:scale-105 transition-transform border-2 border-white"
      >
        <img src="/images/nduna.png" alt="Nduna" className="w-14 h-14 rounded-full shadow-lg" />
      </button>

      {/* Chat Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-4">
          <div className="bg-white w-full max-w-sm rounded-2xl overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="bg-secondary p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
                  <svg width="20" height="20" viewBox="0 0 100 100" fill="none">
                    <path d="M25 80C20 75 15 65 20 55C25 45 35 40 40 35C45 30 50 20 55 15C60 10 65 7 70 7C75 7 80 13 80 20C80 27 75 33 70 37C65 41 60 45 57 50C55 55 57 60 60 65C63 70 67 75 67 80C67 87 63 93 57 93C51 93 47 87 43 80C39 73 33 80 25 80Z" fill="#1A1A1A"/>
                    <ellipse cx="73" cy="23" rx="3" ry="4" fill="white"/>
                  </svg>
                </div>
                <div>
                  <h3 className="font-bold text-white">Nduna</h3>
                  <p className="text-xs text-white/70">iHhashi Assistant</p>
                </div>
              </div>
              <button onClick={() => setIsOpen(false)} className="text-white hover:bg-white/20 rounded-full p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages */}
            <div className="h-64 overflow-y-auto p-4 space-y-3 bg-gray-50">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.isUser ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] px-4 py-2 rounded-2xl ${
                    msg.isUser ? 'bg-secondary text-white rounded-br-none' : 'bg-white text-gray-800 rounded-bl-none shadow-sm'
                  }`}>
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>

            {/* Input */}
            <div className="p-3 bg-white border-t flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Type a message..."
                className="flex-1 px-4 py-2 bg-gray-100 rounded-full focus:outline-none focus:ring-2 focus:ring-secondary/20"
              />
              <button 
                onClick={handleSend}
                className="w-10 h-10 bg-secondary rounded-full flex items-center justify-center hover:bg-secondary/80 transition-colors"
              >
                <Send className="w-4 h-4 text-white" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
