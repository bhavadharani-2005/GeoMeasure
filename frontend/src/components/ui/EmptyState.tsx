import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  icon: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ icon: Icon, title, children, action, compact }: Props) {
  return (
    <div className={`empty${compact ? " empty--compact" : ""}`}>
      <Icon className="empty__icon" size={compact ? 20 : 26} strokeWidth={1.5} aria-hidden="true" />
      <p className="empty__title">{title}</p>
      {children && <p className="empty__text">{children}</p>}
      {action}
    </div>
  );
}
