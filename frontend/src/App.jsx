import { BrowserRouter, Routes, Route } from "react-router-dom"
import Landing from "./pages/Landing"
import TestAI from "./pages/TestAI"
import Game from "./pages/Game"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/test" element={<TestAI />} />
        <Route path="/game" element={<Game />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App