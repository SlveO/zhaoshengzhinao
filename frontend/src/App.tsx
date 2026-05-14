import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Recommendations from './pages/Recommendations'
import ErrorBoundary from './components/common/ErrorBoundary'
import Layout from './components/common/Layout'
import ProtectedRoute from './components/common/ProtectedRoute'

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/chat" element={<Chat />} />
            <Route path="/recommendations" element={<Recommendations />} />
          </Route>
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}
