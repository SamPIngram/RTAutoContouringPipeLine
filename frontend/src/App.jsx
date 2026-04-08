import { NavLink, Route, Routes } from 'react-router-dom'
import Ingestion from './pages/Ingestion'
import Datasets from './pages/Datasets'
import Training from './pages/Training'
import Deployments from './pages/Deployments'
import Guardrails from './pages/Guardrails'
import Audit from './pages/Audit'

export default function App() {
  return (
    <>
      <nav>
        <span className="brand">RT Auto-Contouring</span>
        <NavLink to="/ingestion">Ingestion</NavLink>
        <NavLink to="/datasets">Datasets</NavLink>
        <NavLink to="/training">Training</NavLink>
        <NavLink to="/deployments">Deployments</NavLink>
        <NavLink to="/guardrails">Guardrails</NavLink>
        <NavLink to="/audit">Audit</NavLink>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Ingestion />} />
          <Route path="/ingestion" element={<Ingestion />} />
          <Route path="/datasets" element={<Datasets />} />
          <Route path="/training" element={<Training />} />
          <Route path="/deployments" element={<Deployments />} />
          <Route path="/guardrails" element={<Guardrails />} />
          <Route path="/audit" element={<Audit />} />
        </Routes>
      </main>
    </>
  )
}
