import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import NewApplication from './pages/NewApplication';
import ReviewEdit from './pages/ReviewEdit';
import ExportResume from './pages/ExportResume';
import ProfilePage from './pages/ProfilePage';
import HistoryPage from './pages/HistoryPage';
import ConfigPage from './pages/ConfigPage';

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewApplication />} />
        <Route path="/review/:id" element={<ReviewEdit />} />
        <Route path="/export/:id" element={<ExportResume />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/config" element={<ConfigPage />} />
      </Route>
    </Routes>
  );
}
