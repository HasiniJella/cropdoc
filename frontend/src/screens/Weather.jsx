import React, { useEffect, useState } from 'react';
import { getLiveWeather } from '../utils/api.js';
import axios from 'axios';

// Helper to map OpenWeather icons to Emojis
const getIcon = (condition) => {
  if (condition.includes('Rain')) return '🌧️';
  if (condition.includes('Cloud')) return '⛅';
  if (condition.includes('Clear')) return '☀️';
  if (condition.includes('Storm')) return '⛈️';
  return '🌡️';
};

// Helper to generate farming advice based on weather
const getAdvice = (desc, rain) => {
  if (rain > 5) return 'Heavy rain — avoid all field operations and protect seedlings.';
  if (rain > 0) return 'Light rain — delay fertilizer application to avoid leaching.';
  if (desc.includes('Clear')) return 'Clear day — ideal for harvesting and pesticide spraying.';
  return 'Good day for general maintenance and soil preparation.';
};

export default function Weather() {
  const [forecast, setForecast] = useState([]);
  const [current, setCurrent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

// 1. Import your central api helpers at the top
 

// ... inside the Weather component ...


useEffect(() => {
  if (!navigator.geolocation) {
    setError("Geolocation is not supported by this browser.");
    setLoading(false);
    return;
  }
  
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      try {
        const { latitude, longitude } = pos.coords;
        
        // 2. Use the central helper instead of raw axios
        // This ensures headers/auth-tokens are attached
        const data = await getLiveWeather(latitude, longitude);

        const dailyData = [];
        [0, 8, 16, 24, 32].forEach((index) => {
          const item = data.list[index];
          const date = new Date(item.dt * 1000);
          const rain = item.rain ? item.rain['3h'] || 0 : 0;
          
          dailyData.push({
            day: index === 0 ? 'Today' : date.toLocaleDateString('en-US', { weekday: 'short' }),
            icon: getIcon(item.weather[0].main),
            high: Math.round(item.main.temp_max),
            low: Math.round(item.main.temp_min),
            rain: Math.round(rain),
            desc: item.weather[0].main,
            advice: getAdvice(item.weather[0].main, rain),
            humidity: item.main.humidity,
            wind: item.wind.speed,
            city: data.city.name
          });
        });

        setForecast(dailyData);
        setCurrent(dailyData[0]);
        setLoading(false);
      } catch (err) {
        console.error("Weather error:", err);
        setError("Failed to fetch live weather data.");
        setLoading(false);
      }
    },
    (err) => {
      setError("Location access denied. Please enable GPS.");
      setLoading(false);
    }
  );
}, []);


  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>🛰️ Fetching Satellite Weather...</div>;
  if (error) return <div style={{ padding: 40, textAlign: 'center', color: 'red' }}>❌ {error}</div>;

  return (
    <div style={{ padding: '16px 16px 32px' }}>
      <h2 style={{ fontSize: 22, fontWeight: 900, color: '#064e3b', marginBottom: 4 }}>🌤 Weather Advisory</h2>
      <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 18 }}>{current.city}, Localized Data</p>

      {/* Current weather hero */}
      <div style={{
        background: 'linear-gradient(135deg,#1d4ed8,#3b82f6,#60a5fa)',
        borderRadius: 20, padding: 24, color: '#fff', marginBottom: 16, position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', top: -20, right: -20, fontSize: 80, opacity: 0.15 }}>{current.icon}</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 54, fontWeight: 900, lineHeight: 1 }}>{current.high}°C</div>
            <div style={{ opacity: 0.9, marginTop: 4, fontSize: 16 }}>{current.desc}</div>
            <div style={{ opacity: 0.75, marginTop: 8, fontSize: 14 }}>💧 Humidity: {current.humidity}% · 💨 {current.wind} m/s</div>
          </div>
          <div style={{ fontSize: 72, opacity: 0.8 }}>{current.icon}</div>
        </div>
        <div style={{
          marginTop: 18, background: 'rgba(255,255,255,0.18)',
          borderRadius: 12, padding: '12px 14px',
        }}>
          <div style={{ fontSize: 12, opacity: 0.8, fontWeight: 700, marginBottom: 4 }}>💡 FARMING ALERT</div>
          <div style={{ fontSize: 13 }}>{current.advice}</div>
        </div>
      </div>

      {/* 5-day forecast scroll */}
      <div style={{
        background: '#fff', borderRadius: 16, padding: 16,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)', marginBottom: 16,
      }}>
        <div style={{ fontWeight: 800, color: '#064e3b', marginBottom: 14, fontSize: 15 }}>📅 Daily Forecast</div>
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
          {forecast.map((d, i) => (
            <div key={i} style={{
              flex: '0 0 auto', minWidth: 74,
              background: i === 0 ? '#ecfdf5' : '#f9fafb',
              border: i === 0 ? '2px solid #059669' : '2px solid transparent',
              borderRadius: 14, padding: '12px 8px', textAlign: 'center',
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: i === 0 ? '#059669' : '#9ca3af', marginBottom: 6 }}>{d.day}</div>
              <div style={{ fontSize: 26, marginBottom: 6 }}>{d.icon}</div>
              <div style={{ fontSize: 14, fontWeight: 800, color: '#111827' }}>{d.high}°</div>
              <div style={{ fontSize: 11, color: '#9ca3af' }}>{d.low}°</div>
              {d.rain > 0 && <div style={{ fontSize: 10, color: '#3b82f6', fontWeight: 700, marginTop: 4 }}>💧{d.rain}mm</div>}
            </div>
          ))}
        </div>
      </div>

      {/* Daily farming advice */}
      <div style={{
        background: '#fff', borderRadius: 16, padding: 16,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      }}>
        <div style={{ fontWeight: 800, color: '#064e3b', marginBottom: 14, fontSize: 15 }}>🌾 Farming Advice</div>
        {forecast.map((d, i) => (
          <div key={i} style={{
            display: 'flex', gap: 12, padding: '10px 0',
            borderBottom: i < forecast.length - 1 ? '1px solid #f3f4f6' : 'none',
          }}>
            <div style={{ width: 50, textAlign: 'center', flexShrink: 0 }}>
              <div style={{ fontSize: 22 }}>{d.icon}</div>
              <div style={{ fontSize: 11, color: '#9ca3af', fontWeight: 600 }}>{d.day}</div>
            </div>
            <div>
              <div style={{ fontWeight: 700, color: '#374151', fontSize: 13, marginBottom: 2 }}>
                {d.desc} · {d.high}°C
              </div>
              <div style={{ fontSize: 13, color: '#6b7280', lineHeight: 1.4 }}>{d.advice}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
