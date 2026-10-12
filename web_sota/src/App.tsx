import {
  Navigate,
  Route,
  BrowserRouter as Router,
  Routes,
} from "react-router-dom";
import FloatingChat from "@/components/FloatingChat";
import { AppLayout } from "@/components/layout/app-layout";
import { Dashboard } from "@/pages/dashboard";
import Logging from "@/pages/Logging";
import { Reader } from "@/pages/reader";
import { Search } from "@/pages/search";
import { Settings } from "@/pages/settings";
import { VolumeDetail } from "@/pages/volume-detail";
import { Volumes } from "@/pages/volumes";

function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/volumes" element={<Volumes />} />
          <Route path="/volumes/:volumeId" element={<VolumeDetail />} />
          <Route path="/read/:volumeId/:record" element={<Reader />} />
          <Route path="/search" element={<Search />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/chat" element={<Navigate to="/search" replace />} />
          <Route path="/logging" element={<Logging />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
      <FloatingChat />
    </Router>
  );
}

export default App;
