import { useState } from "react"
import axios from "axios"
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet"
import { useNavigate } from "react-router-dom"

function TestAI() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [coords, setCoords] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleFileChange = (e) => {
    const selected = e.target.files[0]
    setFile(selected)
    setPreview(URL.createObjectURL(selected))
    setCoords(null)
  }

  const handleSubmit = async () => {
    if (!file) return

    const formData = new FormData()
    formData.append("file", file)

    setLoading(true)
    setError(null)

    try {
      const response = await axios.post("http://localhost:8000/predict", formData)
      setCoords(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong")
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
        <h1 className="text-lg font-semibold">Test the AI</h1>
        <div className="w-16"/>
      </div>

      <div className="flex flex-1 overflow-hidden">

        {/* left: upload */}
        <div className="w-1/2 p-6 flex flex-col gap-4">
          <p className="text-gray-400 text-sm">Upload a street photo and see where the AI thinks it was taken.</p>

          {/* upload area */}
          <label className="flex flex-col items-center justify-center border-2 border-dashed border-gray-700 rounded-xl p-8 cursor-pointer hover:border-gray-500 transition">
            <span className="text-gray-400 text-sm mb-2">Click to upload an image</span>
            <span className="text-gray-600 text-xs">JPEG, PNG, WEBP up to 10MB</span>
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
          </label>

          {/* image preview */}
          {preview && (
            <img
              src={preview}
              className="w-full rounded-xl object-cover max-h-64"
            />
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={!file || loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition"
          >
            {loading ? "Predicting..." : "Predict Location"}
          </button>

          {coords && (
            <div className="bg-gray-900 rounded-xl p-4">
              <p className="text-gray-400 text-sm">Predicted coordinates</p>
              <p className="font-semibold">{coords.lat.toFixed(4)}, {coords.lng.toFixed(4)}</p>
            </div>
          )}
        </div>

        {/* right: map */}
        <div className="w-1/2 p-6">
          {coords ? (
            <div className="h-full rounded-xl overflow-hidden">
              <MapContainer
                center={[coords.lat, coords.lng]}
                zoom={5}
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <Marker position={[coords.lat, coords.lng]}>
                  <Popup>{coords.lat.toFixed(4)}, {coords.lng.toFixed(4)}</Popup>
                </Marker>
              </MapContainer>
            </div>
          ) : (
            <div className="h-full bg-gray-900 rounded-xl flex items-center justify-center">
              <p className="text-gray-500">Map will appear after prediction</p>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}

export default TestAI