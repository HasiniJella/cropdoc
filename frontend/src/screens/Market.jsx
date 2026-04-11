const PRICES = [
  { crop:'Tomato', e:'🍅', modal:1600, min:800,  max:2400, trend:'up',   pct:8.5, market:'Warangal APMC',    msp:null  },
  { crop:'Potato', e:'🥔', modal:1100, min:700,  max:1500, trend:'stable',pct:0.5,market:'Nizamabad APMC',   msp:null  },
  { crop:'Pepper', e:'🫑', modal:9500, min:8000, max:11000,trend:'down',  pct:2.1, market:'Khammam APMC',    msp:null  },
  { crop:'Onion',  e:'🧅', modal:1200, min:600,  max:2000, trend:'up',   pct:5.2, market:'Karimnagar APMC',  msp:null  },
  { crop:'Rice',   e:'🌾', modal:2050, min:1820, max:2180, trend:'up',   pct:3.2, market:'Warangal APMC',    msp:2183  },
  { crop:'Cotton', e:'🌸', modal:6150, min:5900, max:6400, trend:'down', pct:1.8, market:'Warangal APMC',    msp:6620  },
]

const TREND = {
  up:     { icon:'↑', color:'#059669' },
  down:   { icon:'↓', color:'#dc2626' },
  stable: { icon:'→', color:'#6b7280' },
}

export default function Market() {
  return (
    <div style={{ padding:'16px 16px 32px' }}>
      <h2 style={{ fontSize:22, fontWeight:900, color:'#064e3b', marginBottom:4 }}>📊 Market Prices</h2>
      <p  style={{ fontSize:13, color:'#6b7280', marginBottom:4 }}>Telangana APMC Markets</p>
      <p  style={{ fontSize:11, color:'#9ca3af', marginBottom:18 }}>
        Last updated: {new Date().toLocaleTimeString('en-IN', {hour:'2-digit',minute:'2-digit'})}
      </p>

      {PRICES.map(p => {
        const tr = TREND[p.trend]
        return (
          <div key={p.crop} style={{
            background:'#fff', borderRadius:16, padding:16, marginBottom:12,
            boxShadow:'0 2px 8px rgba(0,0,0,0.06)',
          }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:12 }}>
              <div>
                <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                  <span style={{ fontSize:24 }}>{p.e}</span>
                  <span style={{ fontSize:17, fontWeight:800 }}>{p.crop}</span>
                </div>
                <div style={{ fontSize:12, color:'#9ca3af', marginTop:2 }}>{p.market}</div>
              </div>
              <div style={{ textAlign:'right' }}>
                <div style={{ fontSize:22, fontWeight:900, color:'#064e3b' }}>
                  ₹{p.modal.toLocaleString('en-IN')}
                </div>
                <div style={{ fontSize:13, fontWeight:700, color:tr.color }}>
                  {tr.icon} {p.pct}%
                </div>
              </div>
            </div>

            <div style={{ display:'flex', gap:8 }}>
              {[['Min',p.min,'#dc2626'],['Max',p.max,'#059669'],['Modal',p.modal,'#1d4ed8']].map(([l,v,c]) => (
                <div key={l} style={{
                  flex:1, textAlign:'center', background:'#f9fafb',
                  borderRadius:10, padding:'8px 4px',
                }}>
                  <div style={{ fontSize:10, color:'#9ca3af', fontWeight:600 }}>{l}</div>
                  <div style={{ fontSize:13, fontWeight:800, color:c }}>₹{v.toLocaleString('en-IN')}</div>
                </div>
              ))}
            </div>

            {p.msp && (
              <div style={{
                marginTop:10, padding:'6px 12px',
                background: p.modal < p.msp ? '#fef2f2' : '#ecfdf5',
                borderRadius:8, fontSize:12, fontWeight:600,
                color: p.modal < p.msp ? '#dc2626' : '#059669',
              }}>
                {p.modal < p.msp
                  ? `⚠️ Below MSP by ₹${(p.msp - p.modal).toLocaleString('en-IN')}`
                  : `✅ Above MSP (₹${p.msp.toLocaleString('en-IN')})`}
              </div>
            )}
          </div>
        )
      })}

      <div style={{
        padding:'12px 14px', background:'#fffbeb',
        borderRadius:12, fontSize:12, color:'#92400e',
      }}>
        💡 Connect e-NAM / Agmarknet API in backend for live APMC prices
      </div>
    </div>
  )
}