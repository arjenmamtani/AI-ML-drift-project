import { useEffect, useState } from "react";
import { getToken } from "./api";
import Login from "./components/Login";
import Sidebar from "./components/Sidebar";
import Overview from "./pages/Overview";
import DriftReports from "./pages/DriftReports";
import Predictions from "./pages/Predictions";
import Training from "./pages/Training";
import Health from "./pages/Health";
import { api } from "./api";
import "./index.css";

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [page, setPage] = useState("overview");
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);

  useEffect(() => {
    if (!authed) return;
    api.models.list()
      .then(ms => { setModels(ms); if (ms.length > 0) setSelectedModel(ms[0]); })
      .catch(console.error);
  }, [authed]);

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  const pages = { overview: Overview, drift: DriftReports, predictions: Predictions, training: Training, health: Health };
  const PageComponent = pages[page] || Overview;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar page={page} onPage={setPage} models={models} selectedModel={selectedModel} onModel={setSelectedModel} />
      <main style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <PageComponent model={selectedModel} />
      </main>
    </div>
  );
}
