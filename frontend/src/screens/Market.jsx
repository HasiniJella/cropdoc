import React, { useEffect, useState } from 'react';
import axios from 'axios';

// Expanded Emoji Map for dozens of Indian crops
const EMOJI_MAP = {
  // Vegetables
  'Tomato': '🍅', 'Potato': '🥔', 'Onion': '🧅', 'Brinjal': '🍆', 'Cabbage': '🥬',
  'Cauliflower': '🥦', 'Carrot': '🥕', 'Ginger(Green)': '🫚', 'Garlic': '🧄',
  'Green Chilli': '🌶️', 'Bhindi(Ladies Finger)': '🎋', 'Drumstick': '🎋',
  'Capsicum': '🫑', 'Bottle gourd': '🥒', 'Bitter gourd': '🥒', 'Pumpkin': '🎃',
  // Grains & Cereals
  'Rice': '🌾', 'Wheat': '🌾', 'Maize': '🌽', 'Jowar(Sorghum)': '🌾', 'Bajra(Pearl Millet)': '🌾',
  // Fruits
  'Apple': '🍎', 'Banana': '🍌', 'Mango': '🥭', 'Grapes': '🍇', 'Orange': '🍊',
  'Papaya': '🍈', 'Pomegranate': '🍎', 'Water Melon': '🍉', 'Lemon': '🍋',
  'Guava': '🍏', 'Pineapple': '🍍', 'Coconut': '🥥',
  // Pulses & Others
  'Cotton': '🌸', 'Groundnut': '🥜', 'Mustard': '🌼', 'Turmeric': '🟡', 'Sugar': '🍬'
};

const TREND = {
  up:     { icon:'↑', color:'#059669' },
  down:   { icon:'↓', color:'#dc2626' },
  stable: { icon:'→', color:'#6b7280' },
};

export default function Market() {
  const [prices, setPrices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLivePrices = async () => {
      try {
        // 1. Detect if we are in Electron production (file://) or Dev (http://)
        const isProd = window.location.protocol === 'file:';
        const BASE_URL = isProd ? 'http://127.0.0.1:8000' : 'http://localhost:8000';

        // 2. Fetch from your Python backend with a high limit to show many varieties
        const res = await axios.get(`${BASE_URL}/market-prices?limit=100`);
        
        const transformedData = res.data.map(item => ({
          crop: item.commodity,
          // Check if we have an emoji, otherwise use a generic box
          e: EMOJI_MAP[item.commodity] || (item.commodity.includes('Mango') ? '🥭' : '📦'),
          modal: parseInt(item.modal_price) || 0,
          min: parseInt(item.min_price) || 0,
          max: parseInt(item.max_price) || 0,
          market: `${item.market}, ${item.district}`,
          state: item.state,
          trend: 'stable', 
          pct: 0.0,
          msp: null 
        }));

        setPrices(transformedData);
        setLoading(false);
      } catch (err) {
        console.error("Market API Error:", err);
        setLoading(false);
      }
    };

    fetchLivePrices();
  }, []);

  if (loading) return (
    <div style={{ padding: 40, textAlign: 'center', color: '#064e3b' }}>
      <div style={{ fontSize: 32, marginBottom: 10 }}>🛰️</div>
      <div style={{ fontWeight: 800 }}>Connecting to Agmarknet Nodes...</div>
      <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 8 }}>Fetching Live Market Streams</div>
    </div>
  );

  return (
    <div style={{ padding:'16px 16px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div>
          <h2 style={{ fontSize:22, fontWeight:900, color:'#064e3b', marginBottom:2 }}>📊 Market Prices</h2>
          <p  style={{ fontSize:13, color:'#6b7280' }}>Live All-India Mandi Feed</p>
        </div>
        <div style={{ textAlign: 'right' }}>
           <div style={{ fontSize:11, color:'#9ca3af' }}>Last Update</div>
           <div style={{ fontSize:12, fontWeight:700, color:'#374151' }}>
             {new Date().toLocaleTimeString('en-IN', {hour:'2-digit',minute:'2-digit'})}
           </div>
        </div>
      </div>

      {prices.length > 0 ? prices.map((p, index) => {
        const tr = TREND[p.trend];
        return (
          <div key={`${p.crop}-${p.market}-${index}`} style={{
            background:'#fff', borderRadius:16, padding:16, marginBottom:12,
            boxShadow:'0 2px 8px rgba(0,0,0,0.06)',
            border: '1px solid #f3f4f6'
          }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:12 }}>
              <div>
                <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                  <span style={{ fontSize:24 }}>{p.e}</span>
                  <div>
                    <span style={{ fontSize:16, fontWeight:800, color: '#111827' }}>{p.crop}</span>
                    <div style={{ fontSize:11, fontWeight:700, color: '#059669', textTransform: 'uppercase' }}>{p.state}</div>
                  </div>
                </div>
                <div style={{ fontSize:11, color:'#9ca3af', marginTop:6 }}>📍 {p.market}</div>
              </div>
              <div style={{ textAlign:'right' }}>
                <div style={{ fontSize:20, fontWeight:900, color:'#064e3b' }}>
                  ₹{p.modal.toLocaleString('en-IN')}
                </div>
                <div style={{ fontSize:12, fontWeight:700, color:tr.color }}>
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
                  <div style={{ fontSize:9, color:'#9ca3af', fontWeight:700, textTransform: 'uppercase' }}>{l}</div>
                  <div style={{ fontSize:13, fontWeight:800, color:c }}>₹{v.toLocaleString('en-IN')}</div>
                </div>
              ))}
            </div>
          </div>
        );
      }) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af' }}>
          No market records found for today.
        </div>
      )}

      <div style={{
        padding:'14px', background:'#ecfdf5', border: '1px solid #d1fae5',
        borderRadius:12, fontSize:12, color:'#059669', fontWeight: 600, textAlign: 'center'
      }}>
        💡 Powered by Agmarknet Live Data (Data.gov.in)
      </div>
    </div>
  );
}
