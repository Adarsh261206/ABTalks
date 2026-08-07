import { HashRouter, Route, Routes } from "react-router-dom";
import { InterviewRoom } from "./pages/InterviewRoom";
import { Landing } from "./pages/Landing";
import { Report } from "./pages/Report";

export function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/interview" element={<InterviewRoom />} />
        <Route path="/report" element={<Report />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </HashRouter>
  );
}
