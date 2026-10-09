import { FolderOpen, Upload } from "lucide-react";
import { Link } from "react-router-dom";
import { toApiError } from "../api/client";
import { filesApi } from "../api/files";
import { FilesTable } from "../components/files/FilesTable";
import { PageHeader } from "../components/layout/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorNotice, PanelSkeleton } from "../components/ui/Feedback";
import { useAsync } from "../hooks/useAsync";
import { useState } from "react";

export function FilesPage() {
  const files = useAsync(() => filesApi.list(200), []);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        title="Geospatial files"
        subtitle="Every dataset uploaded to this workspace."
        actions={
          <Link to="/upload" className="btn btn--primary">
            <Upload size={16} aria-hidden="true" /> Upload
          </Link>
        }
      />
      <section className="panel">
        {deleteError && <ErrorNotice message={deleteError} />}
        {files.loading ? (
          <PanelSkeleton rows={5} />
        ) : files.error ? (
          <ErrorNotice message={files.error} onRetry={files.reload} />
        ) : files.data && files.data.length > 0 ? (
          <FilesTable
            files={files.data}
            onDelete={async (file) => {
              try {
                setDeleteError(null);
                await filesApi.remove(file.id);
                files.reload();
              } catch (err) {
                setDeleteError(toApiError(err).message);
              }
            }}
          />
        ) : (
          <EmptyState icon={FolderOpen} title="No files uploaded yet">
            Files you upload will be listed here with their CRS, feature counts and status.
          </EmptyState>
        )}
      </section>
    </>
  );
}
