import { useState, useEffect } from 'react'
import Home       from './screens/Home.jsx'
import Detect     from './screens/Detect.jsx'
import Weather    from './screens/Weather.jsx'
import Market     from './screens/Market.jsx'
import Calculator from './screens/Calculator.jsx'
import { checkHealth } from './utils/api.js'

const TABS = [
  { id: 'home',       icon: '🏠', label: 'Home'    },
  { id: 'detect',     icon: '🔬', label: 'Detect'  },
  { id: 'weather',    icon: '🌤',  label: 'Weather' },
  { id: 'market',     icon: '📊', label: 'Market'  },
  { id: 'calculator', icon: '🧮', label: 'Profit'  },
]

const SCREENS = {
  home: Home, detect: Detect, weather: Weather,
  market: Market, calculator: Calculator,
}

export default function App() {
  const [tab,    setTab]    = useState('home')
  const [online, setOnline] = useState(true)

  // Check backend health on load
  useEffect(() => {
    checkHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
  }, [])

  const Screen = SCREENS[tab]

  return (
    <div style={{
      maxWidth: 430, margin: '0 auto', minHeight: '100vh',
      background: '#f0fdf4', fontFamily: "'Nunito', sans-serif",
      display: 'flex', flexDirection: 'column', position: 'relative',
      boxShadow: '0 0 40px rgba(0,0,0,0.12)',
    }}>

      {/* ── Header ── */}
      <div style={{
        background: 'linear-gradient(135deg, #065f46, #059669)',
        padding: '14px 16px 12px',
        position: 'sticky', top: 0, zIndex: 100,
        boxShadow: '0 2px 12px rgba(6,78,59,0.25)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 38, height: 38, borderRadius: '50%',
              background: 'rgba(255,255,255,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20,
            }}>🌿</div>
            <div>
              <div style={{ color: '#fff', fontSize: 18, fontWeight: 900, lineHeight: 1 }}>
                CropDoc AI
              </div>
              <div style={{ color: '#a7f3d0', fontSize: 11, fontWeight: 600 }}>
                Smart Farming Assistant
              </div>
            </div>
          </div>
          {/* Backend status dot */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: online ? '#4ade80' : '#f87171',
              boxShadow: online ? '0 0 6px #4ade80' : '0 0 6px #f87171',
            }} />
            <span style={{ color: '#a7f3d0', fontSize: 11 }}>
              {online ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>
      </div>

      {/* ── Screen content ── */}
      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 80 }}>
        {!online && tab === 'detect' && (
          <div style={{
            background: '#fef2f2', borderBottom: '1px solid #fca5a5',
            padding: '10px 16px', fontSize: 13, color: '#dc2626', fontWeight: 600,
          }}>
            ⚠️ Backend offline — start with: <code>python main.py</code>
          </div>
        )}
        <Screen setTab={setTab} />
      </div>

      {/* ── Bottom nav ── */}
      <nav style={{
        position: 'fixed', bottom: 0,
        left: '50%', transform: 'translateX(-50%)',
        width: '100%', maxWidth: 430,
        background: '#fff',
        borderTop: '1px solid #e5e7eb',
        boxShadow: '0 -4px 20px rgba(0,0,0,0.08)',
        display: 'flex', zIndex: 100,
      }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              flex: 1, padding: '8px 0 10px',
              border: 'none', background: 'transparent',
              cursor: 'pointer',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', gap: 2,
              transition: 'background 0.15s',
            }}
          >
            <span style={{ fontSize: 22, lineHeight: 1 }}>{t.icon}</span>
            <span style={{
              fontSize: 10,
              fontWeight: tab === t.id ? 800 : 600,
              color: tab === t.id ? '#059669' : '#9ca3af',
              fontFamily: "'Nunito', sans-serif",
            }}>
              {t.label}
            </span>
            {tab === t.id && (
              <div style={{
                width: 20, height: 3, borderRadius: 2,
                background: '#059669', marginTop: 1,
              }} />
            )}
          </button>
        ))}
      </nav>
    </div>
  )
}