const FORECAST = [
  { day:'Today', icon:'⛅', high:32, low:24, rain:0,  desc:'Partly Cloudy', advice:'Good day for spraying — no rain expected.' },
  { day:'Tue',   icon:'🌦', high:30, low:23, rain:5,  desc:'Light Rain',    advice:'Light rain — delay fertilizer application.' },
  { day:'Wed',   icon:'🌧', high:28, low:22, rain:20, desc:'Heavy Rain',    advice:'Heavy rain — avoid all field operations.' },
  { day:'Thu',   icon:'⛈', high:29, low:23, rain:15, desc:'Thunderstorm',  advice:'High humidity — monitor crops for fungal disease.' },
  { day:'Fri',   icon:'☀️', high:35, low:25, rain:0,  desc:'Sunny',        advice:'Clear day — ideal for harvesting and spraying.' },
  { day:'Sat',   icon:'🌤', high:34, low:25, rain:0,  desc:'Mostly Clear', advice:'Good conditions for soil preparation.' },
  { day:'Sun',   icon:'☁️', high:31, low:23, rain:2,  desc:'Cloudy',       advice:'Mild conditions — good for transplanting.' },
]

export default function Weather() {
  return (
    <div style={{ padding:'16px 16px 32px' }}>
      <h2 style={{ fontSize:22, fontWeight:900, color:'#064e3b', marginBottom:4 }}>🌤 Weather Advisory</h2>
      <p  style={{ fontSize:13, color:'#6b7280', marginBottom:18 }}>Hyderabad, Telangana</p>

      {/* Current weather hero */}
      <div style={{
        background:'linear-gradient(135deg,#1d4ed8,#3b82f6,#60a5fa)',
        borderRadius:20, padding:24, color:'#fff', marginBottom:16, position:'relative', overflow:'hidden',
      }}>
        <div style={{ position:'absolute', top:-20, right:-20, fontSize:80, opacity:0.15 }}>⛅</div>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
          <div>
            <div style={{ fontSize:54, fontWeight:900, lineHeight:1 }}>31°C</div>
            <div style={{ opacity:0.9, marginTop:4, fontSize:16 }}>Partly Cloudy</div>
            <div style={{ opacity:0.75, marginTop:8, fontSize:14 }}>💧 Humidity: 68% · 💨 12 km/h</div>
          </div>
          <div style={{ fontSize:72, opacity:0.8 }}>⛅</div>
        </div>
        <div style={{
          marginTop:18, background:'rgba(255,255,255,0.18)',
          borderRadius:12, padding:'12px 14px',
        }}>
          <div style={{ fontSize:12, opacity:0.8, fontWeight:700, marginBottom:4 }}>💡 FARMING ALERT</div>
          <div style={{ fontSize:13 }}>Rain expected tomorrow. Delay fertilizer application to avoid leaching.</div>
        </div>
      </div>

      {/* 7-day forecast scroll */}
      <div style={{
        background:'#fff', borderRadius:16, padding:16,
        boxShadow:'0 2px 8px rgba(0,0,0,0.06)', marginBottom:16,
      }}>
        <div style={{ fontWeight:800, color:'#064e3b', marginBottom:14, fontSize:15 }}>📅 7-Day Forecast</div>
        <div style={{ display:'flex', gap:8, overflowX:'auto', paddingBottom:4 }}>
          {FORECAST.map((d, i) => (
            <div key={i} style={{
              flex:'0 0 auto', minWidth:74,
              background: i===0 ? '#ecfdf5' : '#f9fafb',
              border: i===0 ? '2px solid #059669' : '2px solid transparent',
              borderRadius:14, padding:'12px 8px', textAlign:'center',
            }}>
              <div style={{ fontSize:11, fontWeight:700, color: i===0?'#059669':'#9ca3af', marginBottom:6 }}>{d.day}</div>
              <div style={{ fontSize:26, marginBottom:6 }}>{d.icon}</div>
              <div style={{ fontSize:14, fontWeight:800, color:'#111827' }}>{d.high}°</div>
              <div style={{ fontSize:11, color:'#9ca3af' }}>{d.low}°</div>
              {d.rain > 0 && <div style={{ fontSize:10, color:'#3b82f6', fontWeight:700, marginTop:4 }}>💧{d.rain}mm</div>}
            </div>
          ))}
        </div>
      </div>

      {/* Daily farming advice */}
      <div style={{
        background:'#fff', borderRadius:16, padding:16,
        boxShadow:'0 2px 8px rgba(0,0,0,0.06)',
      }}>
        <div style={{ fontWeight:800, color:'#064e3b', marginBottom:14, fontSize:15 }}>🌾 Farming Advice</div>
        {FORECAST.slice(0, 5).map((d, i) => (
          <div key={i} style={{
            display:'flex', gap:12, padding:'10px 0',
            borderBottom: i < 4 ? '1px solid #f3f4f6' : 'none',
          }}>
            <div style={{ width:50, textAlign:'center', flexShrink:0 }}>
              <div style={{ fontSize:22 }}>{d.icon}</div>
              <div style={{ fontSize:11, color:'#9ca3af', fontWeight:600 }}>{d.day}</div>
            </div>
            <div>
              <div style={{ fontWeight:700, color:'#374151', fontSize:13, marginBottom:2 }}>
                {d.desc} · {d.high}°C
              </div>
              <div style={{ fontSize:13, color:'#6b7280', lineHeight:1.4 }}>{d.advice}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{
        marginTop:14, padding:'10px 14px',
        background:'#eff6ff', borderRadius:12, fontSize:12, color:'#1d4ed8',
      }}>
        💡 Add OpenWeather API key to backend for live forecasts
      </div>
    </div>
  )
}