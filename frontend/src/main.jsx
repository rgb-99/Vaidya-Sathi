import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import SharePage from './components/SharePage.jsx'
import './index.css'

const shareToken = window.location.pathname.match(/^\/share\/([\w-]+)$/)?.[1]
ReactDOM.createRoot(document.getElementById('root')).render(shareToken ? <SharePage token={shareToken} /> : <App />)

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}))
}
