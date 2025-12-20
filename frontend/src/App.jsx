import { useState } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'

function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleIdentify = async () => {
    if (!file) {
      alert('please select a file')
      return
    }

    setLoading(true)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API_URL}/identify`, {
        method: 'POST',
        body: formData
      })

      const data = await res.json()
      setResult(data)
    } catch (err) {
      console.error(err)
      alert('error identifying song')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <h1>audio fingerprinting</h1>
      
      <div className="upload-section">
        <input 
          type="file" 
          accept="audio/*"
          onChange={(e) => setFile(e.target.files[0])}
        />
        
        <button onClick={handleIdentify} disabled={loading}>
          {loading ? 'identifying...' : 'identify song'}
        </button>
      </div>

      {result && (
        <div className="result">
          {result.match_song_id ? (
            <>
              <h2>match found!</h2>
              <p><strong>title:</strong> {result.title}</p>
              <p><strong>artist:</strong> {result.artist}</p>
            </>
          ) : (
            <h2>no match found</h2>
          )}
        </div>
      )}
    </div>
  )
}

export default App