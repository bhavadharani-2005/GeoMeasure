import { FileText } from "lucide-react";
import { Link } from "react-router-dom";
import type { GeospatialFile } from "../../types/api";
import { FILE_TYPE_LABEL, formatDate, formatInt } from "../../utils/format";
import { DeleteButton } from "../ui/DeleteButton";
import { StatusBadge } from "../ui/StatusBadge";

interface Props {
  files: GeospatialFile[];
  onDelete?: (file: GeospatialFile) => Promise<void>;
}

export function FilesTable({ files, onDelete }: Props) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Filename</th>
            <th>Type</th>
            <th className="num">Features</th>
            <th>CRS</th>
            <th>Status</th>
            <th>Uploaded</th>
            <th className="actions-col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.id}>
              <td>
                <Link to={`/files/${file.id}`} className="file-link">
                  <FileText size={16} aria-hidden="true" />
                  <span className="truncate">{file.filename}</span>
                </Link>
              </td>
              <td>{FILE_TYPE_LABEL[file.file_type]}</td>
              <td className="num">{formatInt(file.feature_count)}</td>
              <td>{file.original_crs ?? "—"}</td>
              <td>
                <StatusBadge status={file.status} />
              </td>
              <td className="muted nowrap">{formatDate(file.created_at)}</td>
              <td className="actions-col">
                <span className="inline-actions">
                  <Link to={`/files/${file.id}`} className="btn btn--ghost btn--sm">
                    Open
                  </Link>
                  {onDelete && <DeleteButton iconOnly label={`Delete ${file.filename}`} onConfirm={() => onDelete(file)} />}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
