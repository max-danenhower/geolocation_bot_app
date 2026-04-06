import { useState, useEffect } from "react"
import axios from "axios"
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from "react-leaflet"
import { useNavigate } from "react-router-dom"

function PinPlacer({ onPin, submitted }) {
  useMapEvents({
    click(e) {
        if (submitted) return
        onPin([e.latlng.lat, e.latlng.lng])
    }
  })
  return null
}

import { divIcon } from "leaflet"

const userIcon = divIcon({
  className: "",
  html: `<div style="width:16px;height:16px;background:#3b82f6;border-radius:50%;border:2px solid white"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8]
})

const aiIcon = divIcon({
  className: "",
  html: `<div style="width:16px;height:16px;background:#a855f7;border-radius:50%;border:2px solid white"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8]
})

const trueIcon = divIcon({
  className: "",
  html: `<div style="width:16px;height:16px;background:#22c55e;border-radius:50%;border:2px solid white"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8]
})

function Game() {
  const [image, setImage] = useState(null)
  const [roundId, setRoundId] = useState(null)
  const [userPin, setUserPin] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const navigate = useNavigate()

  const fetchRound = async () => {
    setUserPin(null)
    setResult(null)
    setImage(null)
    const response = await axios.get("http://localhost:8000/round")
    setImage(response.data.image)
    setRoundId(response.data.round_id)
  }

  useEffect(() => {
    fetchRound()
  }, [])

  const handleSubmit = async () => {
    if (!userPin) return
    setLoading(true)
    try {
      const response = await axios.post("http://localhost:8000/score", {
        round_id: roundId,
        user_lat: userPin[0],
        user_lng: userPin[1]
      })
      setResult(response.data)
      setSubmitted(true)
    } catch (err) {
      console.log(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-white">

      {/* navbar */}
      <div className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
        <button
          onClick={() => navigate("/")}
          className="text-gray-400 hover:text-white transition text-sm"
        >
          ← Back
        </button>
        <h1 className="text-lg font-semibold">Play vs AI</h1>
        <div className="w-16"/>
      </div>

      {/* main content */}
      <div className="flex flex-1 overflow-hidden">

        {/* left: image */}
        <div className="w-1/2 p-6 flex flex-col gap-4">
          <p className="text-gray-400 text-sm">Where in the world was this photo taken?</p>
          {image ? (
            <img
              src={`data:image/jpeg;base64,${image}`}
              className="w-full h-full object-cover rounded-xl"
            />
          ) : (
            <div className="w-full h-full bg-gray-800 rounded-xl flex items-center justify-center">
              <p className="text-gray-500">Loading image...</p>
            </div>
          )}
        </div>

        {/* right: map + controls */}
        <div className="w-1/2 p-6 flex flex-col gap-4">
          <p className="text-gray-400 text-sm">
            {userPin
              ? `Pin placed: ${userPin[0].toFixed(4)}, ${userPin[1].toFixed(4)}`
              : "Click the map to place your guess"}
          </p>

          <div className="flex-1 rounded-xl overflow-hidden">
            <MapContainer center={[20, 0]} zoom={2} style={{ height: "100%", width: "100%" }}>
              <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <PinPlacer onPin={setUserPin} submitted={submitted}/>
              {userPin && <Marker position={userPin} icon={userIcon}>
                <Popup>Your guess</Popup>
              </Marker>}
              {result && (
                <>
                  <Marker position={[result.true_lat, result.true_lng]} icon={trueIcon}>
                    <Popup>True location</Popup>
                  </Marker>
                  <Marker position={[result.ai_lat, result.ai_lng]} icon={aiIcon}>
                    <Popup>AI guess</Popup>
                  </Marker>
                </>
              )}
            </MapContainer>
          </div>

          {!result ? (
            <button
              onClick={handleSubmit}
              disabled={!userPin || loading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition"
            >
              {loading ? "Submitting..." : "Submit Guess"}
            </button>
          ) : (
            <div className="bg-gray-900 rounded-xl p-4 flex flex-col gap-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Your distance</span>
                <span className="font-semibold">{result.user_distance_km.toFixed(1)} mi</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">AI distance</span>
                <span className="font-semibold">{result.ai_distance_km.toFixed(1)} mi</span>
              </div>
              <div className={`text-center font-bold text-lg ${result.user_won ? "text-green-400" : "text-red-400"}`}>
                {result.user_won ? "You beat the AI!" : "AI wins this round"}
              </div>
              <button
                onClick={fetchRound}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition"
              >
                Next Round
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Game