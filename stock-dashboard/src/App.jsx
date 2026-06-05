import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [stockData, setStockData] = useState({ top_gainers: [], top_losers: [], advance_info: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStocks = async () => {
      try {
        const apiUrl = '/api/top-stocks';
        const response = await fetch(apiUrl);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setStockData(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch on mount
    fetchStocks();

    // Polling every 1 minute (60,000 ms)
    const intervalId = setInterval(fetchStocks, 60000);
    return () => clearInterval(intervalId);
  }, []);

  if (loading) return <div className="message loading">Loading stock data from NSE...</div>;
  if (error) return <div className="message error">Error: {error}</div>;

  // Component to render a mini candlestick chart (sparkline)
  const MiniCandlestickChart = ({ symbol, type }) => {
    const [candles, setCandles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [hoveredCandle, setHoveredCandle] = useState(null);

    useEffect(() => {
      const fetchCandles = async () => {
        try {
          const response = await fetch(`/api/stock-candles/${encodeURIComponent(symbol)}`);
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const data = await response.json();
          setCandles(data.candles);
          setError(null);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      };

      fetchCandles();
      const intervalId = setInterval(fetchCandles, 60000);
      return () => clearInterval(intervalId);
    }, [symbol]);

    if (loading) return <div className="no-data" style={{ height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading chart...</div>;
    if (error) return <div className="no-data" style={{ height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Error: {error}</div>;
    if (!candles || candles.length === 0) return <div className="no-data" style={{ height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>No candle data available</div>;

    // Calculate min and max for scaling the Y-axis
    const minLow = Math.min(...candles.map(c => c.Low));
    const maxHigh = Math.max(...candles.map(c => c.High));
    const maxVolume = Math.max(...candles.map(c => c.Volume)) || 1;
    
    // Determine the target color for the lowest volume highlight based on stock type
    const targetColor = type === 'gainers' ? 'Red' : 'Green';
    const eligibleCandles = candles.filter(c => c.Color === targetColor);
    const targetMinVolume = eligibleCandles.length > 0 
      ? Math.min(...eligibleCandles.map(c => c.Volume)) 
      : -1;
    const range = maxHigh - minLow || 1;

    const width = 400;
    const height = 120;
    const padding = 5;
    const volumeAreaHeight = 30; // pixels reserved for volume at the bottom
    const candleAreaHeight = height - volumeAreaHeight - padding * 2;
    const step = width / candles.length;
    const candleWidth = Math.max(2, step * 0.6);

    const getY = (val) => padding + candleAreaHeight - ((val - minLow) / range) * candleAreaHeight;

    return (
      <div className="chart-container">
        <div className="candle-tooltip">
          {hoveredCandle ? (
            <span>
              <strong>O:</strong> {hoveredCandle.Open.toFixed(2)} &nbsp;|&nbsp; 
              <strong>H:</strong> {hoveredCandle.High.toFixed(2)} &nbsp;|&nbsp; 
              <strong>L:</strong> {hoveredCandle.Low.toFixed(2)} &nbsp;|&nbsp; 
              <strong>C:</strong> {hoveredCandle.Close.toFixed(2)} &nbsp;|&nbsp; 
              <strong>Vol:</strong> {hoveredCandle.Volume.toLocaleString()}
            </span>
          ) : (
            <span className="text-muted">Hover over chart for details</span>
          )}
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} className="mini-chart">
          {candles.map((c, i) => {
            const x = i * step + step / 2;
            const top = getY(Math.max(c.Open, c.Close));
            const bottom = getY(Math.min(c.Open, c.Close));
            const highY = getY(c.High);
            const lowY = getY(c.Low);
            const color = c.Color === 'Green' ? '#00b894' : '#d63031';
            
            const volHeight = (c.Volume / maxVolume) * volumeAreaHeight;
            const volY = height - padding - volHeight;
            const isLowestVolumeHighlight = c.Volume === targetMinVolume && c.Color === targetColor;

            return (
              <g 
                key={c.datetime || i}
                onMouseEnter={() => setHoveredCandle(c)}
                onMouseLeave={() => setHoveredCandle(null)}
                style={{ cursor: 'crosshair' }}
              >
                {/* Background rect for easier hovering and lowest volume highlight */}
                <rect x={x - step / 2} y={0} width={step} height={height} fill={isLowestVolumeHighlight ? "rgba(255, 215, 0, 0.3)" : "transparent"} />
                {/* Wick */}
                <line x1={x} y1={highY} x2={x} y2={lowY} stroke={color} strokeWidth="1" />
                {/* Body */}
                <rect x={x - candleWidth / 2} y={top} width={candleWidth} height={Math.max(1, bottom - top)} fill={color} />
                {/* Volume */}
                <rect x={x - candleWidth / 2} y={volY} width={candleWidth} height={volHeight} fill={color} opacity="0.3" />
              </g>
            );
          })}
        </svg>
      </div>
    );
  };

  // Reusable component for a list of stocks
  const StockList = ({ title, stocks, type }) => (
    <div className="stock-column">
      <h2 className={`title ${type}`}>{title}</h2>
      <div className="stock-list">
        {stocks.map((stock) => (
          <div key={stock.symbol} className="stock-card">
            <div className="stock-header">
              <h3>{stock.symbol}</h3>
              <span className={`badge ${type}`}>
                {stock.pChange > 0 ? '+' : ''}{stock.pChange.toFixed(2)}%
              </span>
            </div>
            <div className="stock-details">
              <p>Last Price: <strong>₹{stock.lastPrice}</strong></p>
              <MiniCandlestickChart symbol={stock.symbol} type={type} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="app-container">
      <header>
        <h1>NSE Top Stocks Dashboard</h1>
        {stockData.advance_info && (
          <div className="market-status" style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginTop: '10px', fontSize: '1.1rem' }}>
            <div style={{ color: '#00b894' }}><strong>Advances:</strong> {stockData.advance_info.advances}</div>
            <div style={{ color: '#d63031' }}><strong>Declines:</strong> {stockData.advance_info.declines}</div>
            <div style={{ color: '#636e72' }}><strong>Unchanged:</strong> {stockData.advance_info.unchanged}</div>
          </div>
        )}
      </header>
      <main className="dashboard">
        <StockList title="Top Gainers" stocks={stockData.top_gainers} type="gainers" />
        <StockList title="Top Losers" stocks={stockData.top_losers} type="losers" />
      </main>
    </div>
  );
}

export default App;
