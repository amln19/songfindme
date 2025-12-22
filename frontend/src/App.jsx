import { Route, Routes } from "react-router";
import { AuthProvider } from "./context/AuthContext";

import HomePage from "./pages/HomePage";
import AddSongPage from "./pages/AddSongPage";
import IdentifySongPage from "./pages/IdentifySongPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import HistoryPage from "./pages/HistoryPage";

const App = () => {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-base-300">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/add-song" element={<AddSongPage />} />
          <Route path="/identify-song" element={<IdentifySongPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </div>
    </AuthProvider>
  );
};

export default App;