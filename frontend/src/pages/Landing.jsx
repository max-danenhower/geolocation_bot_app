import { useNavigate } from "react-router-dom"

function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center gap-8">
      <div className="text-center">
        <h1 className="text-5xl font-bold mb-3">GeoGuessr AI</h1>
        <p className="text-gray-400 text-lg">Test the AI with your own photo, or go head to head.</p>
      </div>

      <div className="flex gap-4">
        <button
          onClick={() => navigate("/test")}
          className="px-8 py-4 bg-white text-gray-950 font-semibold rounded-xl hover:bg-gray-200 transition"
        >
          Test the AI
        </button>
        <button
          onClick={() => navigate("/game")}
          className="px-8 py-4 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition"
        >
          Play vs AI
        </button>
      </div>
    </div>
  )
}

export default Landing