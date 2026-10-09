import { Compass } from "lucide-react";
import { Link, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { EmptyState } from "./components/ui/EmptyState";
import { FileDetailsPage } from "./pages/FileDetailsPage";
import { FilesPage } from "./pages/FilesPage";
import { OverviewPage } from "./pages/OverviewPage";
import { UploadPage } from "./pages/UploadPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="files" element={<FilesPage />} />
        <Route path="files/:id" element={<FileDetailsPage />} />
        <Route
          path="*"
          element={
            <EmptyState
              icon={Compass}
              title="Page not found"
              action={
                <Link to="/" className="btn btn--primary btn--sm">
                  Back to overview
                </Link>
              }
            />
          }
        />
      </Route>
    </Routes>
  );
}
